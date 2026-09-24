"""L62's id vocabulary, cached on disk by the CONTENT of what it reads (#542).

`_id_corpus` reads every contract and every device manifest in the library to
learn what the library calls things. `build.sh` renders each device in its own
process, so that read used to be paid once per device - about 95% of a render.
The answer is now kept in a file named for a digest of the bytes it was
computed from, and a later process with the same bytes reads the file instead.

THE THING THAT MUST NEVER HAPPEN is a cached answer that differs from what a
fresh computation would say. A stale vocabulary does not crash anything: it
quietly hides a real L62 finding, or invents one. So most of what is here is
the other half - an edit that changes the answer must miss the cache - and the
failure cases, where the cache must step aside and let the computation run.

Every test points PORTRAYAL_CACHE_DIR at its own directory, on top of the
session-wide one conftest sets, so no test reads another's entries or the
user's real ~/.cache.
"""
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

from portrayal import lint as L

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


# --- helpers ------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _cache_dir(tmp_path, monkeypatch):
    """A cache directory of this test's own, and an empty in-process cache
    before and after, so every call below really goes to disk."""
    d = tmp_path / "cache"
    monkeypatch.setenv("PORTRAYAL_CACHE_DIR", str(d))
    L._ID_VOCAB_CACHE.clear()
    yield d
    L._ID_VOCAB_CACHE.clear()


def entries(d):
    return sorted(Path(d).glob("id-corpus-*.json")) if Path(d).is_dir() else []


def corpus(roots):
    """One call as a new process would make it: nothing in memory."""
    L._ID_VOCAB_CACHE.clear()
    return L._id_corpus([str(r) for r in roots])


def uncached(roots):
    """The computation with no cache anywhere near it."""
    return L._id_corpus_compute(L._id_corpus_files([str(r) for r in roots]))


def assert_same(a, b):
    """Equal AND of the same Python types, down to the tuples inside
    `preferred` and its key order - what a caller gets must not depend on
    whether it came from disk."""
    words_a, pref_a, whole_a = a
    words_b, pref_b, whole_b = b
    assert type(a) is type(b) is tuple
    assert type(words_a) is type(words_b) is set
    assert type(pref_a) is type(pref_b) is dict
    assert type(whole_a) is type(whole_b) is set
    assert words_a == words_b
    assert whole_a == whole_b
    assert list(pref_a.items()) == list(pref_b.items())
    for v in list(pref_a.values()) + list(pref_b.values()):
        assert type(v) is tuple and len(v) == 2
        assert type(v[0]) is int and type(v[1]) is str


class Parses:
    """Counts the per-file parses `_id_corpus` makes. With forbid=True any
    parse, or any load_yaml, fails the test: that is what a hit must make."""

    def __init__(self, monkeypatch, forbid=False):
        self.n = 0
        real = L._id_corpus_parse

        def counted(data):
            if forbid:
                raise AssertionError("a cache hit parsed a library file")
            self.n += 1
            return real(data)

        monkeypatch.setattr(L, "_id_corpus_parse", counted)
        if forbid:
            def no_load_yaml(*a, **k):
                raise AssertionError("a cache hit called load_yaml")
            monkeypatch.setattr(L, "load_yaml", no_load_yaml)


def _copy_corpus(dst):
    """Just the files `_id_corpus` reads, at the same relative paths."""
    for pattern, sub in (("contract.yaml", "components"), ("*.yaml", "devices")):
        for f in (LIB / sub).rglob(pattern):
            t = dst / f.relative_to(LIB)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, t)
    return dst


@pytest.fixture(scope="module")
def pristine(tmp_path_factory):
    return _copy_corpus(tmp_path_factory.mktemp("pristine") / "library")


@pytest.fixture
def lib(pristine, tmp_path):
    """A private copy a test may edit."""
    dst = tmp_path / "library"
    shutil.copytree(pristine, dst)
    return dst


MINI_CONTRACTS = {
    "std/sma-jack": "class: port\nconforms: sma-jack\nattrs:\n  media: sma\n",
    "std/rj45": "class: port\nattrs:\n  media: rj45\n",
    "common/esd-jack": "class: ground\nattrs:\n  media: esd\n",
}
MINI_IDS = ["clk-10mhz", "clk-10mhz", "clk-1pps", "sma-10mhz-out", "port-1",
            "port-2", "usb", "reset", "reset"]


@pytest.fixture
def mini(tmp_path):
    """A library of three contracts and three devices, for the tests about the
    cache itself rather than about the corpus - a damaged entry or a full
    directory does not need 855 files to be damaged. Its answer is checked
    non-empty below, so these tests cannot pass on nothing."""
    root = tmp_path / "mini"
    for ref, text in MINI_CONTRACTS.items():
        f = root / "components" / ref / "v1" / "contract.yaml"
        f.parent.mkdir(parents=True)
        f.write_text(text)
    for n in range(3):
        f = root / "devices" / "v" / f"d{n}" / "device.yaml"
        f.parent.mkdir(parents=True)
        f.write_text(yaml.safe_dump({"views": {"front": {"components": {"placements": [
            {"id": i, "ref": "std/sma-jack@1"} for i in MINI_IDS]}}}}))
    words, preferred, whole = uncached([root])
    assert words and preferred and whole, (words, preferred, whole)
    return root


def _again(monkeypatch, cache_dir, forbid=False):
    """Drop the patches so far and count afresh, keeping this test's cache."""
    monkeypatch.undo()
    monkeypatch.setenv("PORTRAYAL_CACHE_DIR", str(cache_dir))
    return Parses(monkeypatch, forbid=forbid)


# --- the census: every count below is of something real -----------------------

def test_the_corpus_is_not_empty():
    """Every other assertion here is only worth something if the vocabulary
    and the files it came from are actually there."""
    files = L._id_corpus_files([str(LIB)])
    comps = [f for f in files if f[0] == "components"]
    devs = [f for f in files if f[0] == "devices"]
    assert len(comps) > 100 and len(devs) > 50, (len(comps), len(devs))
    words, preferred, whole = uncached([LIB])
    assert len(words) > 10 and len(preferred) > 10 and len(whole) > 10


def test_the_suite_never_touches_the_users_cache(monkeypatch):
    """conftest points the whole session somewhere under pytest's tmp dir.
    This test's own override is taken off to look at the session's."""
    monkeypatch.undo()
    d = Path(os.environ["PORTRAYAL_CACHE_DIR"])
    assert Path.home() / ".cache" not in d.parents
    assert "pytest" in str(d)
    assert L._id_corpus_cache_dir() == d


# --- the cached answer IS the fresh answer ------------------------------------

@pytest.mark.parametrize("which", ["real", "copy"])
def test_a_hit_returns_exactly_what_a_fresh_computation_does(which, lib, _cache_dir, monkeypatch):
    root = LIB if which == "real" else lib
    fresh = uncached([root])

    p = Parses(monkeypatch)
    miss = corpus([root])
    assert p.n > 100, "the miss did not parse the library"
    assert len(entries(_cache_dir)) == 1, "the miss wrote no cache entry"
    assert_same(miss, fresh)

    _again(monkeypatch, _cache_dir, forbid=True)
    assert_same(corpus([root]), fresh)


def test_the_real_library_and_its_copy_share_one_entry(lib, _cache_dir, monkeypatch):
    """Keyed on relative paths and bytes, not on where the checkout lives - so
    every worktree of one commit shares an entry, and it is still correct."""
    corpus([LIB])
    Parses(monkeypatch, forbid=True)
    hit = corpus([lib])
    assert len(entries(_cache_dir)) == 1
    monkeypatch.undo()
    fresh = uncached([lib])
    # EQUAL, but `preferred`'s key ORDER is the writer's directory walk, which
    # two trees need not share. Nothing reads that order (L62 only ever does
    # `preferred.get`), so the contents are what has to agree here.
    assert hit[0] == fresh[0] and hit[2] == fresh[2]
    assert hit[1] == fresh[1]


def test_a_repeat_call_in_one_process_reads_nothing(mini, monkeypatch):
    lib = mini
    """The in-process cache is still in front of the disk one."""
    first = corpus([lib])

    def boom(*a, **k):
        raise AssertionError("the in-process cache was bypassed")

    monkeypatch.setattr(L, "_id_corpus_files", boom)
    assert L._id_corpus([str(lib)]) is first


# --- an edit that changes the answer misses ------------------------------------

def _rewrite(path, edit):
    doc = yaml.safe_load(path.read_text())
    edit(doc)
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


def test_changing_a_conforms_misses_and_changes_the_answer(lib, _cache_dir, monkeypatch):
    before = corpus([lib])
    target = next(f for f in sorted((lib / "components").rglob("contract.yaml"))
                  if (yaml.safe_load(f.read_text()) or {}).get("conforms"))
    _rewrite(target, lambda d: d.__setitem__("conforms", "zzq-probe-standard"))

    p = Parses(monkeypatch)
    after = corpus([lib])
    assert p.n > 100, "an edited contract was answered from the cache"
    assert len(entries(_cache_dir)) == 2
    assert "zzq-probe-standard" in after[0] and "zzq" in after[0]
    assert after != before
    assert_same(after, uncached([lib]))


def _placements(doc):
    for view in (doc.get("views") or {}).values():
        for q in (((view or {}).get("components") or {}).get("placements") or []):
            if isinstance(q.get("id"), str):
                yield q


def test_changing_a_placement_id_misses_and_changes_the_answer(lib, _cache_dir, monkeypatch):
    before = corpus([lib])
    # an id the library uses exactly twice is in `whole`; renaming one of the
    # two takes it out, so the answer has to move
    counts, where = {}, {}
    for f in sorted((lib / "devices").rglob("*.yaml")):
        d = yaml.safe_load(f.read_text()) or {}
        if d.get("kind") not in (None, "device"):
            continue
        for q in _placements(d):
            counts[q["id"]] = counts.get(q["id"], 0) + 1
            where.setdefault(q["id"], f)
    pid = next(i for i, n in sorted(counts.items()) if n == 2)
    assert pid in before[2]

    def rename(doc):
        q = next(q for q in _placements(doc) if q["id"] == pid)
        q["id"] = "zzq-renamed-probe"

    _rewrite(where[pid], rename)
    p = Parses(monkeypatch)
    after = corpus([lib])
    assert p.n > 100, "an edited device was answered from the cache"
    assert len(entries(_cache_dir)) == 2
    assert pid not in after[2]
    assert_same(after, uncached([lib]))


def test_a_new_file_misses(lib, _cache_dir, monkeypatch):
    corpus([lib])
    extra = lib / "components" / "zzq" / "probe" / "v1" / "contract.yaml"
    extra.parent.mkdir(parents=True)
    extra.write_text("conforms: zzq-new-file\n")
    p = Parses(monkeypatch)
    after = corpus([lib])
    assert p.n > 100
    assert "zzq-new-file" in after[0]


def test_an_mtime_only_change_hits(lib, _cache_dir, monkeypatch):
    """Same bytes, same answer: a checkout or a `touch` must not cost a miss."""
    before = corpus([lib])
    n = 0
    for f in lib.rglob("*.yaml"):
        st = f.stat()
        os.utime(f, (st.st_atime + 86400, st.st_mtime + 86400))
        n += 1
    assert n > 100
    Parses(monkeypatch, forbid=True)
    assert_same(corpus([lib]), before)
    assert len(entries(_cache_dir)) == 1


def test_the_digest_covers_root_order_and_the_format(mini, tmp_path, monkeypatch):
    lib = mini
    other = tmp_path / "other"
    c = other / "components" / "x" / "y" / "v1" / "contract.yaml"
    c.parent.mkdir(parents=True)
    c.write_text("conforms: zzq-other\n")
    ab = L._id_corpus_digest(L._id_corpus_files([str(lib), str(other)]))
    ba = L._id_corpus_digest(L._id_corpus_files([str(other), str(lib)]))
    assert ab != ba
    monkeypatch.setattr(L, "_ID_CORPUS_CACHE_FORMAT", L._ID_CORPUS_CACHE_FORMAT + 1)
    assert L._id_corpus_digest(L._id_corpus_files([str(lib), str(other)])) != ab


# --- when the cache cannot be trusted, it steps aside --------------------------

@pytest.mark.parametrize("damage", ["garbage", "truncated", "empty", "wrong-shape",
                                    "wrong-digest", "wrong-format"])
def test_a_damaged_entry_is_ignored_and_recomputed(damage, mini, _cache_dir, monkeypatch):
    lib = mini
    good = corpus([lib])
    (entry,) = entries(_cache_dir)
    text = entry.read_text()
    payload = json.loads(text)
    if damage == "garbage":
        entry.write_bytes(b"\x00\xffnot json")
    elif damage == "truncated":
        entry.write_text(text[: len(text) // 2])
    elif damage == "empty":
        entry.write_text("")
    elif damage == "wrong-shape":
        payload["preferred"] = [["x", "not-an-int", "y"]]
        entry.write_text(json.dumps(payload))
    elif damage == "wrong-digest":
        payload["digest"] = "0" * 64
        entry.write_text(json.dumps(payload))
    elif damage == "wrong-format":
        payload["format"] = -1
        entry.write_text(json.dumps(payload))

    p = Parses(monkeypatch)
    again = corpus([lib])
    assert p.n == len(MINI_CONTRACTS) + 3, "a damaged entry was believed"
    assert_same(again, good)
    # and the recomputation repaired the entry
    _again(monkeypatch, _cache_dir, forbid=True)
    assert_same(corpus([lib]), good)


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0,
                    reason="root ignores directory permissions")
def test_an_unwritable_cache_dir_still_gives_the_right_answer(mini, _cache_dir):
    lib = mini
    _cache_dir.mkdir()
    _cache_dir.chmod(0o500)
    try:
        assert_same(corpus([lib]), uncached([lib]))
        assert entries(_cache_dir) == []
    finally:
        _cache_dir.chmod(0o700)


def test_a_cache_dir_that_is_a_file_still_gives_the_right_answer(mini, tmp_path, monkeypatch):
    lib = mini
    f = tmp_path / "not-a-dir"
    f.write_text("x")
    monkeypatch.setenv("PORTRAYAL_CACHE_DIR", str(f))
    assert_same(corpus([lib]), uncached([lib]))
    assert f.read_text() == "x"


def test_the_default_location_is_outside_the_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("PORTRAYAL_CACHE_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert L._id_corpus_cache_dir() == tmp_path / "xdg" / "portrayal"
    monkeypatch.delenv("XDG_CACHE_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert L._id_corpus_cache_dir() == tmp_path / "home" / ".cache" / "portrayal"


# --- pruning -------------------------------------------------------------------

def test_pruning_keeps_the_newest_n(mini, _cache_dir, monkeypatch):
    lib = mini
    monkeypatch.setattr(L, "_ID_CORPUS_CACHE_KEEP", 3)
    _cache_dir.mkdir()
    old = []
    for i in range(6):
        e = _cache_dir / f"id-corpus-{i:064x}.json"
        e.write_text("{}")
        os.utime(e, (1000 + i, 1000 + i))
        old.append(e)
    bystander = _cache_dir / "notes.txt"
    bystander.write_text("not ours")
    os.utime(bystander, (1, 1))

    corpus([lib])
    left = entries(_cache_dir)
    assert len(left) == 3, left
    new = set(left) - set(old)
    assert len(new) == 1, "the entry just written was pruned"
    assert set(left) == {old[4], old[5]} | new, "pruning did not take the oldest first"
    assert bystander.exists(), "pruning removed a file it did not write"
    assert not list(_cache_dir.glob("*.tmp")), "a temp file was left behind"


# --- two processes at once -----------------------------------------------------

RACER = textwrap.dedent("""
    import json, os, sys, time
    from portrayal import lint as L
    go = sys.argv[2]
    while not os.path.exists(go):
        time.sleep(0.01)
    w, p, h = L._id_corpus([sys.argv[1]])
    print(json.dumps([sorted(w), list(p.items()), sorted(h)]))
""")


def test_two_processes_computing_at_once_leave_a_good_entry(lib, tmp_path, _cache_dir):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "spec" / "tools"),
           "PORTRAYAL_CACHE_DIR": str(_cache_dir)}
    go = tmp_path / "go"
    procs = [subprocess.Popen([sys.executable, "-c", RACER, str(lib), str(go)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env=env)
             for _ in range(2)]
    go.write_text("")
    outs = []
    for pr in procs:
        out, err = pr.communicate(timeout=300)
        assert pr.returncode == 0, err
        outs.append(json.loads(out))

    words, preferred, whole = uncached([lib])
    expect = [sorted(words), [[k, list(v)] for k, v in preferred.items()], sorted(whole)]
    assert outs[0] == outs[1] == expect

    (entry,) = entries(_cache_dir)
    assert not list(_cache_dir.glob("*.tmp")), "a temp file was left behind"
    digest = L._id_corpus_digest(L._id_corpus_files([str(lib)]))
    assert entry.name == f"id-corpus-{digest}.json"
    assert_same(L._id_corpus_cache_load(entry, digest), (words, preferred, whole))
