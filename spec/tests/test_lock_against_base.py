"""A device lock that moved against its base has to carry the version bump.

`devicelock.check` compares a lock with the device as it is now, so after
`--update` the two agree whatever the `version:` line says. `check_base`
compares the lock the base commit holds with the lock the branch holds, by the
rule `check` applies. The cases are the smallest locks that can express each
outcome, in memory, and then the same on a real git history so the command
that CI runs is tried as well.
"""
import json
import pathlib
import subprocess

from portrayal import devicelock as dl

from test_device_versioning import dev


def lock(version="1.0.0", **kw):
    return {"format": dl.FORMAT, **dl.entry(dev(version=version, **kw))}


def composed_moved(entry):
    """The same lock after a part it draws was redrawn."""
    return {**entry, "composed": {"x/y@1": "other"}, "composed-refs": {"x/y@1": "1.0.1"}}


def findings(base, head):
    return dl.check_base({"v/m": base}, {"v/m": head})


# ---- the five cases ---------------------------------------------------------

def test_a_lock_that_moved_with_the_version_unchanged_fails_and_names_the_device():
    base = lock()
    got = findings(base, composed_moved(base))
    assert [(n, k) for n, k, _ in got] == [("v/m", "unbumped")]
    assert "v/m" in got[0][2] and "composed" in got[0][2]
    assert "still 1.0.0" in got[0][2]


def test_the_same_lock_with_the_patch_bump_passes():
    base = lock()
    assert findings(base, {**composed_moved(base), "version": "1.0.1"}) == []


def test_a_lock_that_did_not_move_passes():
    base = lock()
    assert findings(base, dict(base)) == []


def test_a_version_that_went_backwards_fails():
    base = lock(version="1.2.0")
    got = findings(base, {**base, "version": "1.1.0"})
    assert [(n, k) for n, k, _ in got] == [("v/m", "backwards")]


def test_a_device_new_in_the_head_and_a_device_gone_pass():
    base, head = lock(), composed_moved(lock())
    assert dl.check_base({}, {"v/new": head}) == []
    assert dl.check_base({"v/gone": base}, {}) == []


# ---- the rule is the one check applies --------------------------------------

def test_a_patch_does_not_cover_a_move_that_needs_a_minor():
    base = lock()
    head = {**lock(extra_bay="slot-1"), "version": "1.0.1"}
    got = findings(base, head)
    assert [(n, k) for n, k, _ in got] == [("v/m", "unbumped")]
    assert "at least a minor" in got[0][2]
    assert findings(base, {**head, "version": "1.1.0"}) == []


def test_a_move_that_needs_no_bump_is_not_a_finding():
    base = lock()
    assert findings(base, {**base, "composed-refs": {"x/y@1": "9.9.9"}}) == []


def test_the_base_the_branch_was_merged_onto_is_the_one_that_sees_a_masked_move():
    """The base moved on with a patch of its own. A branch merged onto it that
    moves the lock again and leaves the version alone is only seen against the
    base it was merged onto: against the older tip the version looks bumped."""
    old = lock()
    tip = {**composed_moved(old), "version": "1.0.1"}
    head = {**tip, "composed": {"x/y@1": "again"}}
    assert [k for _, k, _ in findings(tip, head)] == ["unbumped"]
    assert findings(old, head) == []


# ---- the command, on a real history -----------------------------------------

def git(root, *args):
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org",
                           "-C", str(root), *args], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def write(root, slug, body):
    path = root / "library" / "devices" / slug / dl.DEVICE_LOCK_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n")


def history(tmp_path):
    git(tmp_path, "init", "-q")
    base = lock()
    write(tmp_path, "v/m", base)
    write(tmp_path, "v/same", base)
    write(tmp_path, "v/gone", base)
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    return base, git(tmp_path, "rev-parse", "HEAD")


def test_the_command_reads_the_base_from_git_and_fails_on_a_planted_move(tmp_path):
    base, sha = history(tmp_path)
    write(tmp_path, "v/m", composed_moved(base))
    write(tmp_path, "v/new", composed_moved(base))
    (tmp_path / "library/devices/v/gone" / dl.DEVICE_LOCK_NAME).unlink()
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "head")
    library = tmp_path / "library"
    was, now = dl.base_locks_changed(library, sha)
    assert sorted(was) == sorted(now) == ["v/m"]
    assert dl.main(["--library", str(library), "--base", sha]) == 1
    write(tmp_path, "v/m", {**composed_moved(base), "version": "1.0.1"})
    assert dl.main(["--library", str(library), "--base", sha]) == 0
