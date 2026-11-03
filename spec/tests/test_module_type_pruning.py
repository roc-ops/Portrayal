"""The exporter removes the module-type files it no longer writes (#70).

A component that gains `part-numbers` is exported under new model names, and the
file it used to be exported under stayed in `library/exports` beside them. The
module-type export now removes a `.yaml` file under `<target>/module-types/<maker>/`
that nothing in the whole build writes, prints each one, and touches nothing else.

The kept set is the whole build's. Module types are shared between devices, and
only `--modules` writes them, so a `--device` run has no business there at all.
"""
import copy
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
TOOL = ROOT / "spec" / "tools" / "portrayal" / "dcim_export.py"
TEMPLATE = "juniper/mpc7e-mrate@2"
TARGETS = ("netbox", "nautobot")


def _dist():
    if not (DIST / "components.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    from portrayal.artifacts import Dist
    return Dist(str(DIST))


class _With:
    """The real build with `modules()` narrowed to the entries a test passes."""

    def __init__(self, dist, entries):
        self._dist, self._entries = dist, list(entries)
        self._by_ref = {f"{c['ns']}/{c['name']}@{str(c['major'])[1:]}": c for c in self._entries}

    def modules(self):
        return list(self._entries)

    def component_by_ref(self, ref):
        return self._by_ref.get(ref) or self._dist.component_by_ref(ref)

    def __getattr__(self, name):
        return getattr(self._dist, name)


def _card(dist, name, part_numbers):
    c = copy.deepcopy(dist.component_by_ref(TEMPLATE))
    c.update({"name": name, "major": "v1", "version": "1.0.0"})
    c.pop("superseded-by", None)
    c["attrs"] = {k: v for k, v in (c.get("attrs") or {}).items() if k != "model"}
    c["part-numbers"] = {k: {"part": k} for k in part_numbers}
    return c


def _export(dist, entries, root):
    from portrayal.dcim_export import export_modules
    export_modules(_With(dist, entries), str(root))


def _dir(root, target, dist, card):
    return Path(root) / target / "module-types" / dist.manufacturer_of(card["ns"])


@pytest.mark.heavy
def test_a_module_type_no_component_writes_any_more_is_removed(tmp_path, capsys):
    dist = _dist()
    two = _card(dist, "prune-card", ["PRUNE-OPEN", "PRUNE-NOLIC"])
    _export(dist, [two], tmp_path)
    for t in TARGETS:
        assert (_dir(tmp_path, t, dist, two) / "PRUNE-NOLIC.yaml").exists()
    # the card now has one order code: the other type is no longer written
    one = _card(dist, "prune-card", ["PRUNE-OPEN"])
    capsys.readouterr()
    _export(dist, [one], tmp_path)
    out = capsys.readouterr().out
    for t in TARGETS:
        d = _dir(tmp_path, t, dist, one)
        assert sorted(p.name for p in d.glob("*.yaml")) == ["PRUNE-OPEN.yaml"], t
        assert f"removed {d / 'PRUNE-NOLIC.yaml'}" in out, "each removal is printed"
    assert "PRUNE-OPEN.yaml" not in out.split("removed", 1)[-1], "a kept file is not reported"


@pytest.mark.heavy
def test_a_file_the_library_still_writes_is_kept_byte_for_byte(tmp_path, capsys):
    dist = _dist()
    card = _card(dist, "prune-card", ["PRUNE-OPEN", "PRUNE-NOLIC"])
    _export(dist, [card], tmp_path)
    before = {t: {p.name: p.read_bytes() for p in _dir(tmp_path, t, dist, card).glob("*.yaml")}
              for t in TARGETS}
    capsys.readouterr()
    _export(dist, [card], tmp_path)
    assert "removed" not in capsys.readouterr().out
    for t in TARGETS:
        now = {p.name: p.read_bytes() for p in _dir(tmp_path, t, dist, card).glob("*.yaml")}
        assert now == before[t] and len(now) == 2, t


@pytest.mark.heavy
def test_only_the_exporters_own_kind_of_file_is_removed(tmp_path):
    dist = _dist()
    card = _card(dist, "prune-card", ["PRUNE-OPEN"])
    _export(dist, [card], tmp_path)
    others = []
    for t in TARGETS:
        d = _dir(tmp_path, t, dist, card)
        others += [d / "NOTES.md", d / "kept.yml", d / "model.yaml.bak", d / "sub" / "deep.yaml",
                   Path(tmp_path) / t / "device-types" / dist.manufacturer_of(card["ns"]) / "old.yaml"]
    others += [Path(tmp_path) / "fibre-maps" / "X" / "old.yaml", Path(tmp_path) / "LICENSE"]
    for f in others:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("not a module type\n")
    stale = _dir(tmp_path, "netbox", dist, card) / "STALE.yaml"
    stale.write_text("old\n")
    _export(dist, [card], tmp_path)
    assert not stale.exists()
    for f in others:
        assert f.read_text() == "not a module type\n", f


def test_a_maker_with_no_module_left_is_pruned_too(tmp_path):
    """The kept set is every file written, not the makers written to."""
    dist = _dist()
    card = _card(dist, "prune-card", ["PRUNE-OPEN"])
    gone = tmp_path / "netbox" / "module-types" / "Vanished Maker" / "OLD.yaml"
    gone.parent.mkdir(parents=True)
    gone.write_text("old\n")
    _export(dist, [card], tmp_path)
    assert not gone.exists()


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), "--dist", str(DIST), "--no-raster", *args],
                          capture_output=True, text=True, cwd=ROOT,
                          env={"PYTHONPATH": str(ROOT / "spec" / "tools"), "PATH": "/usr/bin:/bin"})


def test_a_run_for_one_device_never_removes_a_module_type(tmp_path):
    """Module types are shared between devices; one device's run does not
    know which another writes, so it removes none."""
    _dist()
    planted = []
    for t in TARGETS:
        for name in ("BDM2M-W.yaml", "NO-COMPONENT-WRITES-THIS.yaml"):
            f = tmp_path / t / "module-types" / "Casa Systems" / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("planted\n")
            planted.append(f)
    r = _run("--out", str(tmp_path), "--device", "c100g")
    assert r.returncode == 0, r.stderr[-1500:]
    assert "removed" not in r.stdout
    assert [f.read_text() for f in planted] == ["planted\n"] * len(planted)


@pytest.mark.heavy
def test_a_modules_run_keeps_what_any_device_needs_and_removes_the_rest(tmp_path):
    """The whole build decides: BDM2M-W is written for the C100G and the C40G
    both, so it is rewritten, and the planted one nothing writes is gone."""
    _dist()
    real = tmp_path / "netbox" / "module-types" / "Casa Systems" / "BDM2M-W.yaml"
    stale = real.with_name("BDM2m.yaml")
    real.parent.mkdir(parents=True)
    real.write_text("planted\n")
    stale.write_text("planted\n")
    r = _run("--out", str(tmp_path), "--modules")
    assert r.returncode == 0, r.stderr[-1500:]
    assert real.read_text() != "planted\n", "the type a component writes is written"
    assert not stale.exists()
    assert f"removed {stale}" in r.stdout
    assert r.stdout.count("\nremoved ") == 1, "nothing else was in the way"
