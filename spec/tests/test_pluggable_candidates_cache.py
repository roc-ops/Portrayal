"""render.py's pluggable candidate walk, cached on disk by the CONTENT of what
it reads (#543), the way L62's vocabulary is (#542, test_id_vocab_cache.py).

`_pluggable_candidates` parses every contract in the library to find the ones
that declare `mates:`. Which ones those are is kept in a file named for a
digest of every contract's bytes and of the code, and a later process with the
same bytes reads the selection instead of parsing.

THE THING THAT MUST NEVER HAPPEN is a cached answer that differs from a fresh
one: a stale selection silently changes what a cage offers. So the tests here
are that a hit gives exactly what a computation gives, that an edit which
changes the answer misses, and that a damaged entry is computed past.
"""
import json
import shutil
from pathlib import Path

import pytest

from portrayal import render as R

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


@pytest.fixture(autouse=True)
def cache_dir(tmp_path, monkeypatch):
    """A cache of this test's own, and an empty per-contract memo before and
    after, so every call below goes to disk the way a new process would."""
    d = tmp_path / "cache"
    monkeypatch.setenv("PORTRAYAL_CACHE_DIR", str(d))
    R._CANDIDATE_MATES.clear()
    yield d
    R._CANDIDATE_MATES.clear()


def entries(d):
    return sorted(Path(d).glob("pluggable-candidates-*.json")) if Path(d).is_dir() else []


def fresh(roots):
    """One call as a new process would make it."""
    R._CANDIDATE_MATES.clear()
    return R._pluggable_candidates([str(r) for r in roots])


def shape(cands):
    """What a caller can see: interfaces in order, and for each the refs in
    order with the contract each one carries."""
    return [(k, [(ref, c) for ref, c in v]) for k, v in cands.items()]


class NoParse:
    """Fails the test if a contract is parsed to decide the selection - which
    is what a hit must not do."""

    def __init__(self, monkeypatch):
        def refuse(data, sha):
            raise AssertionError("a cache hit parsed a contract to select it")
        monkeypatch.setattr(R, "_candidate_mates", refuse)


@pytest.fixture
def lib(tmp_path):
    """A private copy of the contracts a test may edit."""
    dst = tmp_path / "library"
    for f in libwalk_contracts():
        t = dst / f.relative_to(LIB)
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, t)
    return dst


def libwalk_contracts():
    from portrayal import libwalk
    return libwalk.iter_components([LIB])


def test_the_selection_is_not_empty():
    """Everything below is only worth something if there are candidates."""
    got = fresh([LIB])
    assert sum(len(v) for v in got.values()) > 30 and len(got) > 10


def reference(roots):
    """The walk as it was before the cache: every contract through load_yaml."""
    from portrayal import libwalk
    out = {}
    for cf in libwalk.iter_components([str(r) for r in roots]):
        c = R.load_yaml(cf) or {}
        if c.get("superseded-by") or not c.get("mates"):
            continue
        out.setdefault(c["mates"], []).append((libwalk.ref_of(cf), c))
    return out


def test_a_hit_answers_exactly_what_a_computation_does(cache_dir, monkeypatch):
    first = fresh([LIB])
    assert shape(first) == shape(reference([LIB]))
    assert len(entries(cache_dir)) == 1
    NoParse(monkeypatch)
    second = fresh([LIB])
    assert shape(second) == shape(first)
    assert list(second) == list(first)


def test_changing_one_contracts_mates_misses_the_cache(lib, cache_dir):
    """The stale entry the cache must make impossible: a contract that stops
    mating one interface and starts mating another moves in the answer."""
    before = fresh([lib])
    ref, contract = before["sfp"][0]
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    f = lib / "components" / ns / name / f"v{major}" / "contract.yaml"
    f.write_text(f.read_text().replace("mates: sfp", "mates: not-an-interface", 1))
    after = fresh([lib])
    assert ref not in [r for r, _c in after.get("sfp", [])]
    assert [r for r, _c in after["not-an-interface"]] == [ref]
    assert len(entries(cache_dir)) == 2


def test_superseding_a_candidate_misses_the_cache(lib):
    before = fresh([lib])
    ref, _c = before["sfp"][0]
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    f = lib / "components" / ns / name / f"v{major}" / "contract.yaml"
    f.write_text(f.read_text() + "\nsuperseded-by: generic/nothing@1\n")
    after = fresh([lib])
    assert ref not in [r for r, _c in after.get("sfp", [])]


def test_a_shared_entry_still_answers_from_its_own_roots(lib, cache_dir):
    """The digest leaves absolute paths out, so a byte-identical copy shares
    the real library's entry - and the contracts handed back are still read
    from the roots this call was given, in their order."""
    a = fresh([lib, LIB])
    b = fresh([LIB, lib])
    assert len(entries(cache_dir)) == 1
    n = len(a["sfp"]) // 2
    assert n and [r for r, _c in a["sfp"]] == [r for r, _c in b["sfp"]]
    sfp_ref = a["sfp"][0][0]
    ns, rest = sfp_ref.split("/")
    name, major = rest.split("@")
    rel = Path("components") / ns / name / f"v{major}" / "contract.yaml"
    assert a["sfp"][0][1] is R.load_yaml(lib / rel)
    assert b["sfp"][0][1] is R.load_yaml(LIB / rel)
    # and an edit to one root makes the order matter, and so the key
    f = lib / rel
    f.write_text(f.read_text() + "\n# edited\n")
    fresh([lib, LIB])
    fresh([LIB, lib])
    assert len(entries(cache_dir)) == 3


@pytest.mark.parametrize("damage", [
    b"", b"{", b"[]", b'{"format": 1}',
    None,          # replaced below by a well-formed entry with a bad index
])
def test_a_damaged_entry_is_computed_past(cache_dir, damage):
    want = shape(fresh([LIB]))
    (entry,) = entries(cache_dir)
    if damage is None:
        doc = json.loads(entry.read_text())
        doc["picked"][0][1] = doc["files"] + 5
        damage = json.dumps(doc).encode()
    entry.write_bytes(damage)
    assert shape(fresh([LIB])) == want


def test_an_unwritable_cache_still_answers(tmp_path, monkeypatch):
    f = tmp_path / "a-file"
    f.write_text("not a directory")
    monkeypatch.setenv("PORTRAYAL_CACHE_DIR", str(f))
    assert fresh([LIB])["sfp"]


def test_the_cache_is_lints(cache_dir):
    """One setting moves both caches."""
    from portrayal import lint
    assert R._candidates_cache_dir() == lint._id_corpus_cache_dir() == cache_dir
