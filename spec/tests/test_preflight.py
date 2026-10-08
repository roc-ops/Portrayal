"""preflight.py: every check FAILS on a violation planted for it, and passes on
a clean tree (#924).

A preflight that passes everything is indistinguishable from one whose checks
stopped looking, so each check here is shown a seeded fault first. The diff is
real: each seeded case is a git repository in tmp_path with a base commit and
an edit on top, read through the same `changed_files` / `added_lines` the
command uses.

THE PRIVATE STRINGS BELOW ARE ASSEMBLED, never written out: this file is
tracked, and test_no_internal_hosts sweeps every tracked file for exactly the
patterns these tests need to plant.
"""
import json
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

from portrayal import devicelock, preflight

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
DEVICE = "edgecore/as7726-32x"          # a switch with a lock and NOS listings
COMPONENT = "library/components/common/led-dot/v1/contract.yaml"   # placed widely


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          text=True).stdout


def make_repo(root, files):
    root.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(root, "init", "-q")
    git(root, "config", "user.email", "preflight@example.com")
    git(root, "config", "user.name", "preflight test")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    return git(root, "rev-parse", "HEAD").strip()


def ctx_of(root, mbase):
    return preflight.Context(root, mbase, preflight.changed_files(root, mbase))


# ------------------------------------------------------------------ the diff ---

def test_the_diff_is_the_working_tree_plus_untracked_and_only_added_lines(tmp_path):
    base = make_repo(tmp_path, {"a.txt": "one\ntwo\nthree\n", "b.txt": "keep\n"})
    (tmp_path / "a.txt").write_text("one\nTWO\nthree\nfour\n")      # unstaged edit
    (tmp_path / "new.txt").write_text("x\ny\n")                       # untracked
    ctx = ctx_of(tmp_path, base)
    assert ctx.changed == ["a.txt", "new.txt"]
    assert ctx.added == {"a.txt": {2: "TWO", 4: "four"}, "new.txt": {1: "x", 2: "y"}}


# --------------------------------------------------------------------- skips ---

SKIPS_BASE = {
    "spec/allowed-skips.txt": "# comment\nmulti-window lamp part not in this library\n",
    "spec/tests/test_x.py": textwrap.dedent("""\
        import pytest

        def test_old():
            pytest.skip("an old reason nobody allowed")
        """),
}


@pytest.mark.parametrize("added,ok", [
    ('pytest.skip("a brand new reason")', False),
    ('pytest.skip(f"{ref} is gone")', False),
    ('pytest.skip(REASON)', False),                                    # not a literal
    ('pytest.skip("the multi-window lamp part not in this library")', True),
    ('pytest.skip("library/dist not built - run ./build.sh")', True),  # CI builds it
    ('x = 1', True),
])
def test_skips_fail_on_a_new_reason_the_allow_list_does_not_carry(tmp_path, added, ok):
    base = make_repo(tmp_path, SKIPS_BASE)
    f = tmp_path / "spec/tests/test_x.py"
    f.write_text(f.read_text() + f"\n\ndef test_new():\n    {added}\n")
    res = preflight.check_skips(ctx_of(tmp_path, base))
    assert res.ok is ok, res.details
    # the old, unallowed skip is not in the diff, so it is never reported
    assert not any("old reason" in d for d in res.details)


def test_skip_reasons_reads_every_spelling():
    src = textwrap.dedent("""\
        import pytest
        pytestmark = pytest.mark.skipif(True, reason="a" + "b")
        yaml = pytest.importorskip("yaml")
        @pytest.mark.skip(reason=f"x {1} y")
        def test_a():
            pytest.skip(msg="m")
        """)
    assert [r for _, _, r in preflight.skip_reasons(src)] == \
        ["ab", "could not import 'yaml'", "x {...} y", "m"]


# ------------------------------------------------------------------- private ---

def test_private_fails_on_an_added_machine_path_address_or_email(tmp_path):
    base = make_repo(tmp_path, {"notes.md": "clean\n"})
    planted = ["see " + "/" + "Volumes/Disk/x", "host 10" + ".1.2.3",
               "mail someone" + "@" + "corp.com"]
    (tmp_path / "notes.md").write_text("clean\n" + "\n".join(planted) + "\n")
    res = preflight.check_private(ctx_of(tmp_path, base))
    assert not res.ok
    assert len(res.details) == 3, res.details
    assert all(d.startswith("notes.md:") for d in res.details)


def test_private_passes_on_clean_added_lines_and_ignores_old_ones(tmp_path):
    old = "/" + "Users/someone/old"                   # in the base, so not in the diff
    base = make_repo(tmp_path, {"notes.md": old + "\n"})
    (tmp_path / "notes.md").write_text(old + "\nlibrary/devices/x and 192.0.2.4\n")
    res = preflight.check_private(ctx_of(tmp_path, base))
    assert res.ok, res.details
    assert "1 added line" in res.summary


# ----------------------------------------------------------------- changelog ---

CHANGELOG_BASE = {"changelog.d/README.md": "how\n", "library/x.yaml": "a: 1\n",
                  "docs/x.md": "doc\n"}


def test_changelog_fails_when_library_changes_without_a_fragment(tmp_path):
    base = make_repo(tmp_path, CHANGELOG_BASE)
    (tmp_path / "library/x.yaml").write_text("a: 2\n")
    assert not preflight.check_changelog(ctx_of(tmp_path, base)).ok
    (tmp_path / "changelog.d/topic.md").write_text("### Fixed\n- The thing (#1).\n")
    assert preflight.check_changelog(ctx_of(tmp_path, base)).ok


def test_changelog_fails_on_a_malformed_fragment(tmp_path):
    base = make_repo(tmp_path, CHANGELOG_BASE)
    (tmp_path / "library/x.yaml").write_text("a: 2\n")
    (tmp_path / "changelog.d/topic.md").write_text("### Improved\n- Not a heading.\n")
    res = preflight.check_changelog(ctx_of(tmp_path, base))
    assert not res.ok and "Improved" in res.details[0]


def test_changelog_wants_no_fragment_for_docs(tmp_path):
    base = make_repo(tmp_path, CHANGELOG_BASE)
    (tmp_path / "docs/x.md").write_text("more doc\n")
    assert preflight.check_changelog(ctx_of(tmp_path, base)).ok


# ----------------------------------------------------------------------- kit ---

@pytest.mark.skipif(shutil.which("npm") is None, reason="npm not installed")
@pytest.mark.parametrize("script,ok", [("exit 1", False), ("exit 0", True)])
def test_kit_runs_npm_test_when_kit_changes(tmp_path, script, ok):
    pkg = {"name": "k", "version": "0.0.0", "scripts": {"test": script}}
    base = make_repo(tmp_path, {"kit/package.json": json.dumps(pkg), "kit/a.js": "1\n"})
    ctx = ctx_of(tmp_path, base)
    assert preflight.check_kit(ctx).ok, "kit unchanged must pass without running"
    (tmp_path / "kit/a.js").write_text("2\n")
    assert preflight.check_kit(ctx_of(tmp_path, base)).ok is ok


# ------------------------------------------------------------------- exports ---

@pytest.fixture(scope="module")
def regenerated(tmp_path_factory):
    out = tmp_path_factory.mktemp("exports")
    errors = preflight.regenerate_exports(ROOT, out)
    assert not errors, errors
    return out


def test_the_regeneration_matches_the_committed_exports(regenerated):
    """THE STUB DIST IS PROVED HERE. The exports are regenerated from sources
    with no render, and on a tree whose exports are current - which CI's
    `exports are current` step guarantees before the suite runs - every byte
    must agree. Non-vacuous: the comparison covers the whole tree."""
    stale, missing, extra = preflight.compare_exports(regenerated, LIBRARY / "exports", ROOT)
    n = len(preflight._tree_files(regenerated))
    assert n > 1000, f"only {n} files regenerated"
    assert (stale, missing, extra) == ([], [], []), (stale[:5], missing[:5], extra[:5])


def test_exports_fail_on_a_stale_a_missing_and_an_extra_file(regenerated, tmp_path):
    tree = tmp_path / "exports"
    shutil.copytree(regenerated, tree)
    files = sorted(p for p in tree.rglob("*.yaml"))
    files[0].write_text(files[0].read_text() + "# hand edit\n")
    files[1].unlink()
    (files[2].parent / "Gone-Model.yaml").write_text("---\n")
    stale, missing, extra = preflight.compare_exports(regenerated, tree)
    rel = lambda p: str(p.relative_to(tree))               # noqa: E731
    assert stale == [rel(files[0])]
    assert missing == [rel(files[1])]
    assert extra == [rel(files[2].parent / "Gone-Model.yaml")]


# --------------------------------------- devicelock and lint, on a library copy ---

@pytest.fixture(scope="module")
def library_repo(tmp_path_factory):
    """A git repository holding a copy of the library, committed as the base.
    Each test edits it and the `fresh` fixture puts it back."""
    root = tmp_path_factory.mktemp("repo")
    shutil.copytree(LIBRARY, root / "library",
                    ignore=shutil.ignore_patterns("dist", "packages", "exports", "CATALOGUE.md"))
    base = make_repo(root, {"changelog.d/README.md": "how\n"})
    return root, base


@pytest.fixture
def fresh(library_repo):
    root, base = library_repo
    yield root, base
    git(root, "checkout", "-q", "--", ".")
    git(root, "clean", "-qfd")


def _edit(path, old, new):
    text = path.read_text()
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new, 1))


def _version(device_yaml):
    for line in device_yaml.read_text().splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"no version in {device_yaml}")


def _bump(v):
    a, b, c = v.split(".")
    return f"{a}.{b}.{int(c) + 1}"


def test_devicelock_and_lint_pass_on_the_clean_copy(fresh):
    root, base = fresh
    dev = root / "library/devices" / DEVICE / "device.yaml"
    dev.write_text(dev.read_text() + "# touched, nothing changed\n")
    ctx = ctx_of(root, base)
    res = preflight.check_devicelock(ctx)
    assert res.ok, res.details
    res = preflight.check_lint(ctx)
    assert res.ok, res.details
    assert res.summary.startswith("1 device(s)"), res.summary


def test_devicelock_fails_on_an_unbumped_change(fresh):
    root, base = fresh
    dev = root / "library/devices" / DEVICE / "device.yaml"
    _edit(dev, "\ndescription: ", "\ndescription: Planted - ")
    res = preflight.check_devicelock(ctx_of(root, base))
    assert not res.ok
    assert any(DEVICE in d and "bump" in d for d in res.details), res.details


def test_devicelock_fails_on_a_relock_without_the_bump(fresh):
    """`--update` before the bump re-records the change and the working-tree
    check goes quiet; the merge-base lock still has the old version."""
    root, base = fresh
    dev = root / "library/devices" / DEVICE / "device.yaml"
    _edit(dev, "\ndescription: ", "\ndescription: Planted - ")
    devicelock.update(root / "library")
    assert devicelock.check(root / "library") == []          # the gap this closes
    res = preflight.check_devicelock(ctx_of(root, base))
    assert not res.ok
    assert any(d.startswith("against the merge base") for d in res.details), res.details
    # and the right order passes
    _edit(dev, f"version: {_version(dev)}", f"version: {_bump(_version(dev))}")
    devicelock.update(root / "library")
    res = preflight.check_devicelock(ctx_of(root, base))
    assert res.ok, res.details


def test_lint_fails_on_an_error_in_a_touched_device(fresh):
    root, base = fresh
    dev = root / "library/devices" / DEVICE / "device.yaml"
    dev.write_text(dev.read_text() + "planted-unknown-key: 1\n")
    res = preflight.check_lint(ctx_of(root, base))
    assert not res.ok
    assert any(d.startswith("error:") and "as7726-32x" in d for d in res.details), res.details


def test_lint_fails_on_a_warning_the_baseline_does_not_carry(fresh):
    """Seeded from the other side: the baseline forgets one of the device's
    warnings, committed into the base, so the same warning is now new."""
    root, base = fresh
    path = root / "library" / "lint-baseline.json"
    counts = json.loads(path.read_text())
    key = next(k for k in sorted(counts) if k.startswith("devices/")
               and (root / "library" / k).exists() and k.endswith("device.yaml"))
    code = sorted(counts[key])[0]
    counts[key][code] -= 1
    path.write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
    git(root, "commit", "-qam", "baseline forgets one")
    base2 = git(root, "rev-parse", "HEAD").strip()
    try:
        dev = root / "library" / key
        dev.write_text(dev.read_text() + "# touched\n")
        res = preflight.check_lint(ctx_of(root, base2))
        assert not res.ok
        assert any(f"[{code}] {key}" in d for d in res.details), res.details
    finally:
        git(root, "reset", "-q", "--hard", base)


def test_a_touched_component_fans_out_to_every_device_that_places_it(fresh):
    root, base = fresh
    (root / COMPONENT).write_text((root / COMPONENT).read_text() + "# touched\n")
    devices, contracts, full = preflight.lint_plan(ctx_of(root, base))
    assert full == []
    assert [str(c.relative_to(root)) for c in contracts] == [COMPONENT]
    assert len(devices) > 20, f"led-dot reaches only {len(devices)} device(s)?"
    devs = root / "library/devices"
    assert devs / "aurcore/ais2001" in devices            # places it by name
    # reaches it only through a card's parts: the walk is transitive
    assert "common/led-dot@1" not in (devs / "commscope/ch3000/device.yaml").read_text()
    assert devs / "commscope/ch3000" in devices


def test_lint_reaches_a_component_no_device_places(fresh):
    root, base = fresh
    src = root / COMPONENT
    dst = root / "library/components/common/zz-preflight-probe/v1/contract.yaml"
    shutil.copytree(src.parent, dst.parent)
    _edit(dst, "name: led-dot", "name: zz-preflight-probe")
    dst.write_text(dst.read_text() + "planted-unknown-key: 1\n")
    res = preflight.check_lint(ctx_of(root, base))
    assert not res.ok
    assert any("zz-preflight-probe" in d for d in res.details), res.details


def test_a_library_wide_change_asks_for_the_full_lint(fresh):
    root, base = fresh
    lab = next((root / "library/labs").rglob("lab.yaml"))
    lab.write_text(lab.read_text() + "# touched\n")
    devices, contracts, full = preflight.lint_plan(ctx_of(root, base))
    assert full == [str(lab.relative_to(root))]
