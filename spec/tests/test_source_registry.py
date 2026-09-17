"""Every device says which documents it was built from, and every hash is real.

A device could always register its sources - `datasheet:` and `references:` -
and 37 of 89 did not, while naming a document in their provenance prose anyway
(#274). The information existed and was not reachable: a tool asking what the
library was built from found 52 of 89, and a reader wanting the source for one
of the 37 had to read several paragraphs to find a title buried in one of them.

THE `sha256` RULE, which was not written down anywhere before #274: a hash is
present exactly when the document is STAGED LOCALLY, and absent when it was read
but is not held. That is what makes it checkable rather than decorative - a hash
for a file nobody has is a claim nobody can test. It was already the practice
(all 37 hashes in the library resolved to a staged file, none missing); it just
had no rule and no test, which is why 22-of-96 read as neither a policy nor an
accident.
"""
import hashlib
import pathlib
import subprocess

import pytest
import yaml

from portrayal import libwalk

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def _corpus():
    """`working/` lives in the MAIN checkout, so a worktree must go find it.

    The same reasoning as test_panel_measure._corpus: gitignored files in a
    worktree die with the worktree, so the corpus is staged in the main checkout
    only and these checks skip wherever it is absent - CI included.
    """
    try:
        shared = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"], cwd=ROOT,
            capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ROOT / "working"
    main = (ROOT / shared).resolve().parent
    staged = main / "working"
    return staged if staged.is_dir() else ROOT / "working"


def _devices():
    """One walk, libwalk's - the grammar and the traversal live there (#181)."""
    for p in libwalk.iter_devices([LIB]):
        yield p, (yaml.safe_load(p.read_text()) or {})


def _entries():
    """(device slug, entry) for the datasheet and every reference."""
    for p, d in _devices():
        slug = f"{p.parts[-3]}/{p.parts[-2]}"
        ds = d.get("datasheet")
        if isinstance(ds, dict):
            yield slug, ds
        for r in (d.get("references") or []):
            if isinstance(r, dict):
                yield slug, r


def test_every_device_registers_at_least_one_source():
    """The census #274 closed. It may only stay at zero."""
    silent = [f"{p.parts[-3]}/{p.parts[-2]}" for p, d in _devices()
              if not d.get("datasheet") and not d.get("references")]
    assert not silent, (
        f"{len(silent)} device(s) register no source document, though every model "
        f"was built from one: {silent}")


def test_every_entry_has_a_title():
    """A url or a hash without a title is a citation a reader cannot look up."""
    bad = [(s, e) for s, e in _entries() if not (e.get("title") or "").strip()]
    assert not bad, bad


def test_archive_is_gone():
    """It was in the schema from the start, no entry ever used it and no tool
    ever read it. Removed in #274; this catches one coming back by copy-paste."""
    stale = [s for s, e in _entries() if "archive" in e]
    assert not stale, f"`archive` was removed from the schema: {stale}"


@pytest.fixture(scope="module")
def staged_hashes():
    """sha256 -> path for every PDF in the corpus, or None when it is absent.

    Hashing the corpus once costs a few seconds and is the only way to answer
    the question honestly: the entry records a hash, not a path, so the only
    proof that the file is held is finding a file that hashes to it.
    """
    corpus = _corpus()
    if not corpus.is_dir():
        return None
    out = {}
    for f in corpus.rglob("*.pdf"):
        try:
            out.setdefault(hashlib.sha256(f.read_bytes()).hexdigest(), f)
        except OSError:
            continue
    return out or None


def test_every_hash_resolves_to_a_staged_file(staged_hashes):
    """THE RULE: a sha256 means the document is held. No exceptions in either
    direction - a hash nobody can resolve is a claim nobody can test."""
    if staged_hashes is None:
        pytest.skip("no working/ corpus here; this runs where the intake lives")
    hashed = [(s, e) for s, e in _entries() if e.get("sha256")]
    missing = [(s, e.get("title"), e["sha256"][:12])
               for s, e in hashed if e["sha256"] not in staged_hashes]
    assert not missing, (
        "these entries carry a hash that matches no staged file, so either the "
        f"document was never held or the hash is wrong: {missing}")
    # A GUARD AGAINST PASSING VACUOUSLY. If `_entries()` ever stops finding
    # anything this test goes green while checking nothing, which is the shape
    # of every check that quietly stopped running.
    assert len(hashed) > 60, f"only {len(hashed)} hashed entries reached the sweep"
