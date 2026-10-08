"""preflight.py: every check FAILS on a violation planted for it, and passes on
a clean tree (#924).

A preflight that passes everything is indistinguishable from one whose checks
stopped looking, so each check here is shown a seeded fault first. The diff is
real: each seeded case is a git repository in tmp_path with a base commit and
an edit on top, read through the same `changed_files` / `added_lines` the
command uses.

CHEAP ON PURPOSE. The command's point is speed, and so is this file's: the
library the lock and lint tests edit is ONE device and the parts it reaches,
not a copy of 235; the planning tests read the real tree and write nothing;
the export stub is proved against the build the suite already has rather than
by a second full export.

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

from portrayal import devicelock, lint, preflight

# the one-device library is built once per worker; keep its users on one worker
pytestmark = pytest.mark.xdist_group("preflight")

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
DIST = LIBRARY / "dist"
DEVICE = "edgecore/as7726-32x"          # a switch with a lock and baseline warnings
COMPONENT = "library/components/common/led-dot/v1/contract.yaml"   # placed widely


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          text=True).stdout


def make_repo(root, files=None):
    root.mkdir(parents=True, exist_ok=True)
    for rel, text in (files or {}).items():
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
    # each of these mentions a prerequisite and still fires on CI
    ('pytest.skip("cairosvg not installed")', False),                  # CI has no cairosvg
    ('pytest.skip("too slow, run ./build.sh by hand some day")', False),
    ('pytest.skip("common/zz-renamed-part not built")', False),        # a part, not a build
    ('pytest.skip("the multi-window lamp part not in this library")', True),
    ('pytest.skip("library/dist not built - run ./build.sh")', True),  # CI builds it
    ('pytest.skip("node not installed")', True),                       # CI installs it
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

def test_exports_fail_on_a_stale_a_missing_and_an_extra_file(tmp_path):
    fresh, tree = tmp_path / "fresh", tmp_path / "tree"
    for d in (fresh, tree):
        (d / "netbox/X").mkdir(parents=True)
        (d / "netbox/X/same.yaml").write_text("same\n")
    (fresh / "netbox/X/edited.yaml").write_text("new\n")
    (tree / "netbox/X/edited.yaml").write_text("old\n")
    (fresh / "netbox/X/added.yaml").write_text("a\n")
    (tree / "netbox/X/renamed-away.yaml").write_text("r\n")
    assert preflight.compare_exports(fresh, tree) == (
        ["netbox/X/edited.yaml"], ["netbox/X/added.yaml"], ["netbox/X/renamed-away.yaml"])
    assert preflight.compare_exports(fresh, fresh) == ([], [], [])


def test_exports_fail_when_current_but_not_committed(tmp_path, monkeypatch):
    base = make_repo(tmp_path, {"library/exports/netbox/a.yaml": "old\n"})
    (tmp_path / "library/exports/netbox/a.yaml").write_text("new\n")

    def regenerate(root, out):            # what publish.sh would now write
        (Path(out) / "netbox").mkdir(parents=True)
        (Path(out) / "netbox/a.yaml").write_text("new\n")
        return []
    monkeypatch.setattr(preflight, "regenerate_exports", regenerate)
    res = preflight.check_exports(ctx_of(tmp_path, base))
    assert not res.ok and "not committed" in res.summary, res.summary
    git(tmp_path, "commit", "-qam", "regenerated")
    assert preflight.check_exports(ctx_of(tmp_path, base)).ok


@pytest.mark.skipif(not (DIST / "devices.json").exists(),
                    reason="library/dist not built - run ./build.sh")
def test_the_stub_dist_carries_what_the_build_does(tmp_path):
    """THE STUB IS PROVED AGAINST THE REAL BUILD. Everything the exporter reads
    from a dist, the stub must say as the build says it: the devices.json
    fields, the manifest byte for byte, and which faces each configuration
    draws (the exporter's `front_image`/`rear_image`)."""
    n = preflight._stub_dist(LIBRARY, tmp_path)
    real = {d["name"]: d for d in json.loads((DIST / "devices.json").read_text())["devices"]}
    stub = json.loads((tmp_path / "devices.json").read_text())["devices"]
    assert n == len(stub) == len(real) > 100
    assert [d["name"] for d in stub] == list(real), "devices.json order differs"
    for d in stub:
        assert d == {k: real[d["name"]].get(k) for k in d}, d["name"]
        name = d["name"]
        assert (tmp_path / f"{name}.source.json").read_bytes() == \
            (DIST / f"{name}.source.json").read_bytes(), name
        faces = lambda root: {c["name"]: sorted(c.get("files") or {})          # noqa: E731
                              for c in json.loads((root / f"{name}.configs.json")
                                                  .read_text())["configs"]}
        assert faces(tmp_path) == faces(DIST), name


# ---------------------------------------- lint planning, on the real tree, read-only ---

def test_a_touched_component_fans_out_to_every_device_that_places_it():
    ctx = preflight.Context(ROOT, None, [COMPONENT])
    devices, contracts, full, _ = preflight.lint_plan(ctx)
    assert full == []
    assert [str(c.relative_to(ROOT)) for c in contracts] == [COMPONENT]
    assert len(devices) > 20, f"led-dot reaches only {len(devices)} device(s)?"
    devs = LIBRARY / "devices"
    assert devs / "aurcore/ais2001" in devices            # places it by name
    # reaches it only through a card's parts: the walk is transitive
    assert "common/led-dot@1" not in (devs / "commscope/ch3000/device.yaml").read_text()
    assert devs / "commscope/ch3000" in devices


def test_a_library_wide_change_asks_for_the_full_lint():
    lab = str(next((LIBRARY / "labs").rglob("lab.yaml")).relative_to(ROOT))
    _, _, full, _ = preflight.lint_plan(preflight.Context(ROOT, None, [lab]))
    assert full == [lab]


# ------------------------ devicelock and lint, on a one-device library in git ---

@pytest.fixture(scope="module")
def library_repo(tmp_path_factory):
    """A git repository holding ONE device and every file its drawing reaches,
    the lint baseline, committed as the base. The `fresh` fixture puts it back
    after each test."""
    root = tmp_path_factory.mktemp("repo")
    lib = root / "library"
    dev = LIBRARY / "devices" / DEVICE
    shutil.copytree(dev, lib / "devices" / DEVICE)
    for f in lint.device_dependencies(dev / "device.yaml", [str(LIBRARY)]):
        f = Path(f).resolve()
        if f.name == "contract.yaml":              # the whole major: skins and all
            dst = lib / f.parent.relative_to(LIBRARY.resolve())
            if not dst.exists():
                shutil.copytree(f.parent, dst)
    # THE BASELINE DESCRIBES THE LIBRARY IT SITS IN. A one-device library
    # draws library-wide warnings the full one does not (L103: a pluggable
    # family with no part in it), so what the library-wide rules say about
    # this copy is added to its baseline before the base commit - exactly
    # what `--update-baseline` would record for it.
    counts = json.loads((LIBRARY / "lint-baseline.json").read_text())
    wide = preflight._worker("lint", {"mode": "library", "schemas": str(preflight.SCHEMAS),
                                      "library": str(lib)}, root)
    assert not wide["errors"], wide["errors"]
    for f, rules in wide["counts"].items():
        for code, n in rules.items():
            counts.setdefault(f, {})[code] = max(n, counts.get(f, {}).get(code, 0))
    (lib / "lint-baseline.json").write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
    base = make_repo(root, {"changelog.d/README.md": "how\n"})
    return root, base


@pytest.fixture
def fresh(library_repo):
    root, base = library_repo
    yield root, base
    git(root, "reset", "-q", "--hard", base)
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
    assert res.summary.startswith("1 device(s) + library-wide rules:"), res.summary


def test_devicelock_fails_on_an_unbumped_change_and_on_a_relock_without_the_bump(fresh):
    """`--update` before the bump re-records the change and the working-tree
    check goes quiet; the merge-base lock still has the old version."""
    root, base = fresh
    dev = root / "library/devices" / DEVICE / "device.yaml"
    _edit(dev, "\ndescription: ", "\ndescription: Planted - ")
    res = preflight.check_devicelock(ctx_of(root, base))
    assert not res.ok
    assert any(DEVICE in d and "bump" in d for d in res.details), res.details
    devicelock.update(root / "library")
    res = preflight.check_devicelock(ctx_of(root, base))
    assert not res.ok
    assert all(d.startswith("against the merge base") for d in res.details), res.details
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
    key = f"devices/{DEVICE}/device.yaml"
    path = root / "library" / "lint-baseline.json"
    counts = json.loads(path.read_text())
    code = sorted(counts[key])[0]
    counts[key][code] -= 1
    path.write_text(json.dumps(counts, indent=1, sort_keys=True) + "\n")
    git(root, "commit", "-qam", "baseline forgets one")
    base2 = git(root, "rev-parse", "HEAD").strip()
    dev = root / "library" / key
    dev.write_text(dev.read_text() + "# touched\n")
    res = preflight.check_lint(ctx_of(root, base2))
    assert not res.ok
    assert any(d.startswith(f"+1 [{code}] {key} - e.g.") for d in res.details), res.details


def test_lint_fails_on_a_component_no_device_places(fresh):
    """L89 is a library-wide rule a `--device` run skips. A new major nothing
    seats is an error in CI's full lint, and must be one here."""
    root, base = fresh
    src = ROOT / COMPONENT                        # a part this device does not seat
    dst = root / "library/components/common/zz-preflight-probe/v1/contract.yaml"
    shutil.copytree(src.parent, dst.parent)
    _edit(dst, "name: led-dot", "name: zz-preflight-probe")
    ctx = ctx_of(root, base)
    assert preflight.lint_plan(ctx)[3], "a new major must bring L89 in"
    res = preflight.check_lint(ctx)
    assert not res.ok
    assert any("[L89]" in d and "zz-preflight-probe" in d for d in res.details), res.details
