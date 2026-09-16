"""Shared fixtures over the once-parsed library. See libdata.py for why."""
import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import libdata  # noqa: E402

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


@pytest.fixture(scope="session")
def library():
    return libdata.library()


@pytest.fixture(scope="session")
def devices():
    return {slug: doc for slug, doc in libdata.devices()}


@pytest.fixture(scope="session")
def components():
    return libdata.components()
