"""Shared fixtures over the once-parsed library. See libdata.py for why."""
import pathlib
import sys

import pytest
import yaml

import libdata  # noqa: E402

# `--shard I/N`: CI splits the suite across several jobs. The hooks live with
# the tool that checks the split afterwards (spec/tools/portrayal/shards.py), and
# do nothing unless the option is given.
from portrayal.shards import pytest_addoption, pytest_collection_modifyitems  # noqa: E402,F401

# PyYAML SHIPS TWO PARSERS AND THE TESTS WERE USING THE SLOW ONE. `yaml.safe_load`
# is the pure-Python loader; libyaml's CSafeLoader reads the same documents 7.4x
# faster - 89 device manifests in 2.4s against 17.6s, measured on this corpus.
#
# That 17.6s was the shape of the whole suite. 47 test modules across 152 call
# sites parse the library for themselves, so nearly every library-wide test cost
# one full parse, and `--durations` was a wall of tests at 16-27s each that were
# doing nothing but reading YAML. Swapping the loader took the suite from 1030s
# to 358s with no other change.
#
# PATCHED HERE RATHER THAN AT 152 CALL SITES, and that is the point: a rule that
# says "always pass Loader=" is a rule somebody forgets on the next test, and the
# cost of forgetting is invisible - the test passes, it is just slow. One line in
# conftest cannot be forgotten.
#
# SAFE BECAUSE IT IS THE SAME PARSER THE BUILD ALREADY TRUSTS: manifest.load_yaml
# has read every one of these documents with CSafeLoader all along, so the whole
# library is compiled through it on every build. Nothing in the suite asserts on
# the parser's identity or its error types.
if hasattr(yaml, "CSafeLoader"):
    def _safe_load_fast(stream, _Loader=yaml.CSafeLoader):
        return yaml.load(stream, Loader=_Loader)

    yaml.safe_load = _safe_load_fast


# THE SUITE NEVER READS OR WRITES THE USER'S CACHE. lint keeps L62's id
# vocabulary on disk, keyed by the content of the library (#542), in
# $PORTRAYAL_CACHE_DIR or ~/.cache/portrayal. A test run that fell through to
# the home directory would read entries some other checkout wrote, and leave
# its own behind - so the whole session, and every subprocess it spawns, is
# pointed at pytest's tmp dir instead. Under xdist the workers share one
# directory (the parent of their per-worker basetemps): entries are written
# atomically and named by content, so sharing is safe and saves each worker
# the first computation.
@pytest.fixture(scope="session", autouse=True)
def _portrayal_cache_dir(tmp_path_factory):
    import os
    base = tmp_path_factory.getbasetemp()
    if os.environ.get("PYTEST_XDIST_WORKER"):
        base = base.parent
    d = base / "portrayal-cache"
    old = os.environ.get("PORTRAYAL_CACHE_DIR")
    os.environ["PORTRAYAL_CACHE_DIR"] = str(d)
    yield d
    if old is None:
        os.environ.pop("PORTRAYAL_CACHE_DIR", None)
    else:
        os.environ["PORTRAYAL_CACHE_DIR"] = old


# ONE DIRECTORY EVERY WORKER SHARES, for the runs onebuild.py makes once per
# session - the whole-library lint, the component index. Named in the
# environment rather than handed out as a fixture because the helpers that need
# it are plain functions several test files import from each other.
@pytest.fixture(scope="session", autouse=True)
def _shared_builds(tmp_path_factory):
    import os
    base = tmp_path_factory.getbasetemp()
    if os.environ.get("PYTEST_XDIST_WORKER"):
        base = base.parent
    old = os.environ.get("PORTRAYAL_TEST_SHARED")
    os.environ["PORTRAYAL_TEST_SHARED"] = str(base / "shared-builds")
    yield
    if old is None:
        os.environ.pop("PORTRAYAL_TEST_SHARED", None)
    else:
        os.environ["PORTRAYAL_TEST_SHARED"] = old


@pytest.fixture(scope="session")
def library():
    return libdata.library()


@pytest.fixture(scope="session")
def devices():
    return {slug: doc for slug, doc in libdata.devices()}


@pytest.fixture(scope="session")
def components():
    return libdata.components()
