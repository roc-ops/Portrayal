"""The warm-render server's start-up reads each library file once.

`warmrender._warm` fills three memos: the parse of each file (`load_yaml`),
lint's per-file facts for L62, and the candidate walk's per-contract mates. The
last two used to parse again the bytes `load_yaml` had just parsed, so a
contract was parsed three times. These tests run `_warm` over a small library
and count the parses. They also check that the memos hold what a cold parse
gives, so the saving is not a change of answer.
"""
import hashlib
import os

import pytest
import yaml

import warmrender
from portrayal import lint, manifest, render

CONTRACT = "conforms: sfp-plus\nclass: port\nattrs:\n  media: sfp\nmates: sfp-plus\n"
DEVICE = ("kind: device\nviews:\n  front:\n    components:\n      placements:\n"
          "        - id: sfp-plus-1\n        - id: mgmt\n")
LAB = "kind: lab\nname: bench\n"
SCHEMA = "title: a schema\n"


@pytest.fixture
def library(tmp_path, monkeypatch):
    lib, schemas = tmp_path / "library", tmp_path / "schemas"
    files = {
        lib / "components/ns/one/v1/contract.yaml": CONTRACT,
        lib / "components/ns/two/v1/contract.yaml": CONTRACT.replace("sfp-plus", "qsfp"),
        lib / "devices/acme/box/device.yaml": DEVICE,
        lib / "labs/bench/lab.yaml": LAB,
        schemas / "a.schema.yaml": SCHEMA,
    }
    for f, text in files.items():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    monkeypatch.setattr(warmrender, "LIB", lib)
    monkeypatch.setattr(warmrender, "SCHEMAS", schemas)
    # the process's own memos are left as they were
    monkeypatch.setattr(manifest, "_CACHE", {})
    monkeypatch.setattr(lint, "_ID_CORPUS_FACTS", {})
    monkeypatch.setattr(render, "_CANDIDATE_MATES", {})
    return lib, schemas, files


def _count_parses(monkeypatch):
    """The yaml.load calls made from now on, as a list of what each parsed."""
    real, seen = yaml.load, []

    def counting(stream, Loader=None):
        seen.append(hashlib.sha256(stream).hexdigest() if isinstance(stream, bytes)
                    else stream.name)
        return real(stream, Loader=Loader)

    monkeypatch.setattr(yaml, "load", counting)
    return seen


def test_a_warm_up_parses_each_file_once(library, monkeypatch):
    _lib, _schemas, files = library
    seen = _count_parses(monkeypatch)
    warmrender._warm()
    assert len(seen) == len(files), (
        f"{len(files)} files were parsed {len(seen)} times: "
        "the memos parsed again what load_yaml had parsed")


def test_the_memos_hold_what_a_cold_parse_gives(library, monkeypatch):
    lib, _schemas, _files = library
    warmrender._warm()
    warm_facts, warm_mates = dict(lint._ID_CORPUS_FACTS), dict(render._CANDIDATE_MATES)
    assert warm_facts and warm_mates
    monkeypatch.setattr(lint, "_ID_CORPUS_FACTS", {})
    monkeypatch.setattr(render, "_CANDIDATE_MATES", {})
    lint._id_corpus_prime([lib])
    render._candidates_prime([lib])
    assert warm_facts == lint._ID_CORPUS_FACTS
    assert warm_mates == render._CANDIDATE_MATES


def test_the_parse_is_kept_by_path_and_mtime_as_load_yaml_keeps_it(library, monkeypatch):
    _lib, _schemas, files = library
    warmrender._warm()
    seen = _count_parses(monkeypatch)
    for f in files:
        assert (str(f), f.stat().st_mtime_ns) in manifest._CACHE, f
        assert manifest.load_yaml(f) is manifest._CACHE[(str(f), f.stat().st_mtime_ns)]
    assert seen == [], "a file the warm-up read was parsed again by load_yaml"


def test_a_file_changed_after_the_warm_up_is_parsed_afresh(library, monkeypatch):
    lib, _schemas, _files = library
    warmrender._warm()
    f = lib / "components/ns/one/v1/contract.yaml"
    old = f.stat().st_mtime_ns
    f.write_text(CONTRACT.replace("sfp-plus", "xfp"))
    os.utime(f, ns=(old + 10**9, old + 10**9))
    assert manifest.load_yaml(f)["conforms"] == "xfp"
    # the memo is keyed by the bytes: changed bytes are a new key, answered afresh
    data = f.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    assert ("components", sha) not in lint._ID_CORPUS_FACTS
    assert lint._id_corpus_facts("components", data, sha) == ("xfp", "sfp")


def test_the_server_gets_the_real_loader_back(library, monkeypatch):
    real = yaml.load
    warmrender._warm()
    assert yaml.load is real

    def boom(_roots):
        raise RuntimeError("a prime failed")

    monkeypatch.setattr(lint, "_id_corpus_prime", boom)
    with pytest.raises(RuntimeError):
        warmrender._warm()
    assert yaml.load is real, "a failed warm-up left yaml.load replaced"
