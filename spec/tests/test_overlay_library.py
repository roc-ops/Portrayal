"""An overlay: a second library, kept in another folder, built on top of this one.

`build.sh --overlay-library DIR --overlay-out DIR` lints and renders the overlay's
devices against the public components plus the overlay's own, and writes the
overlay's indexes to the out folder only. It is how a downstream project keeps
its own devices without forking this repository (CONTRIBUTING.md, "An overlay
library").

What is held here, each with the fixture in spec/tests/fixtures/overlay-example
(one made-up device, `example/overlay-switch`, built only from public parts):

  - the overlay builds into its own folder, with the indexes and the rack entry;
  - the public dist is byte for byte what it was, and the public library tree
    is untouched;
  - an overlay device or component whose id is already public is refused,
    naming both, and nothing is rendered;
  - an overlay device that names a public component that does not exist is
    refused, naming the ref.

The kit half is held below with the same build: `loadSlots([publicDist,
overlayDist])`, `loadCatalog`, and the 2D shell over a list of dist roots
(spec/tests/js/overlay-*.mjs).
"""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "spec" / "tests" / "fixtures" / "overlay-example"
DIST = ROOT / "library" / "dist"
DEVICE = "overlay-switch"

# ONE WORKER WITH THE TEST THAT WRITES INTO library/dist. This hashes the public
# dist across a build, and test_part_conformance_report writes its report there;
# on two workers the report can land between the two hashes
# (test_dist_writers_share_a_group.py).
pytestmark = pytest.mark.xdist_group("public-dist")


def build(overlay, out, timeout=900):
    return subprocess.run(
        ["bash", str(ROOT / "build.sh"), "--overlay-library", str(overlay),
         "--overlay-out", str(out)],
        capture_output=True, text=True, timeout=timeout, cwd=ROOT)


def tree_hash(root):
    """Every file under root, by relative path and content."""
    h = hashlib.sha256()
    for f in sorted(p for p in Path(root).rglob("*") if p.is_file()):
        h.update(str(f.relative_to(root)).encode() + b"\0")
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def public_state():
    if not DIST.is_dir():
        pytest.skip("library/dist not built - run ./build.sh")
    status = subprocess.run(["git", "status", "--porcelain", "--", "library"],
                            capture_output=True, text=True, cwd=ROOT).stdout
    return tree_hash(DIST), status


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    before = public_state()
    out = tmp_path_factory.mktemp("overlay-out") / "dist"
    r = build(FIXTURE, out)
    return r, out, before, public_state()


def copy_overlay(tmp_path):
    dst = tmp_path / "overlay"
    shutil.copytree(FIXTURE, dst)
    return dst


def device_file(overlay):
    return overlay / "devices" / "example" / DEVICE / "device.yaml"


def test_the_fixture_overlay_builds_into_its_own_folder(built):
    r, out, _, _ = built
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    devices = json.loads((out / "devices.json").read_text())["devices"]
    assert [d["name"] for d in devices] == [DEVICE]
    assert devices[0]["ns"] == "example"
    # components.json lists the overlay's own parts, and the fixture has none:
    # the public parts it seats are answered by the public dist beside it
    assert json.loads((out / "components.json").read_text())["components"] == []
    configs = json.loads((out / f"{DEVICE}.configs.json").read_text())
    assert configs["device"] == DEVICE and configs["default"] == "base"
    for view in ("front", "rear", "top", "bottom", "left", "right"):
        assert (out / f"{DEVICE}.base.{view}.svg").is_file(), view
    rack = json.loads((out / "rack.json").read_text())["devices"]
    assert list(rack) == [DEVICE] and rack[DEVICE]["ru"] == 1


def test_the_overlay_build_names_the_fixture_as_a_fixture(built):
    """Nothing guessed is presented as fact: the device says what it is."""
    doc = yaml.safe_load(device_file(FIXTURE).read_text())
    notes = " ".join(v["note"] for v in doc["provenance"].values())
    assert notes.count("test fixture") >= len(doc["provenance"])
    assert all(v["confidence"] == "estimated" for v in doc["provenance"].values())


def test_the_public_dist_is_byte_identical_with_and_without_an_overlay(built):
    r, _, before, after = built
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    assert after == before, "an overlay build changed the public dist or the library tree"


def test_a_public_device_name_in_the_overlay_is_refused_naming_both(tmp_path):
    public = sorted((ROOT / "library" / "devices").glob("*/*/device.yaml"))[0]
    name = yaml.safe_load(public.read_text())["name"]
    overlay = copy_overlay(tmp_path)
    f = device_file(overlay)
    f.write_text(f.read_text().replace(f"name: {DEVICE}\n", f"name: {name}\n", 1))
    out = tmp_path / "out"
    r = build(overlay, out)
    text = r.stdout + r.stderr
    assert r.returncode != 0, text[-2000:]
    assert str(f) in text and str(public.relative_to(ROOT)) in text and name in text, text[-2000:]
    assert not out.exists() or not list(out.glob("*.svg")), "a refused overlay was rendered"


def test_a_public_device_path_in_the_overlay_is_refused_naming_both(tmp_path):
    public = sorted((ROOT / "library" / "devices").glob("*/*/device.yaml"))[0]
    overlay = copy_overlay(tmp_path)
    clash = overlay / "devices" / public.parent.parent.name / public.parent.name
    clash.mkdir(parents=True)
    shutil.copy(device_file(overlay), clash / "device.yaml")
    r = build(overlay, tmp_path / "out")
    text = r.stdout + r.stderr
    assert r.returncode != 0, text[-2000:]
    assert str(clash / "device.yaml") in text and str(public.relative_to(ROOT)) in text, text[-2000:]


def test_a_public_component_ref_in_the_overlay_is_refused_naming_both(tmp_path):
    public = ROOT / "library" / "components" / "common" / "led-dot" / "v1" / "contract.yaml"
    overlay = copy_overlay(tmp_path)
    clash = overlay / "components" / "common" / "led-dot" / "v1"
    clash.mkdir(parents=True)
    shutil.copy(public, clash / "contract.yaml")
    r = build(overlay, tmp_path / "out")
    text = r.stdout + r.stderr
    assert r.returncode != 0, text[-2000:]
    assert str(clash / "contract.yaml") in text and str(public.relative_to(ROOT)) in text, text[-2000:]
    assert "common/led-dot@1" in text, text[-2000:]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("script", ["overlay-dist.mjs", "overlay-shell.mjs"])
def test_the_kit_loads_the_overlay_device_beside_a_public_one(built, script):
    """loadSlots, loadCatalog and the 2D shell, over [public dist, overlay dist]."""
    r, out, _, _ = built
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    js = ROOT / "spec" / "tests" / "js"
    p = subprocess.run(["node", "--test", str(js / script)], capture_output=True, text=True,
                       cwd=js, timeout=300, env={**os.environ, "PUBLIC_DIST": str(DIST), "OVERLAY_DIST": str(out)})
    assert p.returncode == 0, p.stdout[-4000:] + p.stderr[-2000:]
    assert "# pass 0" not in p.stdout and "# pass" in p.stdout, p.stdout[-2000:]


def test_the_3d_viewer_reads_its_indexes_through_the_layered_reader():
    """viewer3d.js needs three.js and cannot be mounted under node, so what is
    held is the line that matters: its component index comes through
    readIndex, which merges a list of dist roots, and not from one root's URL.
    overlay-dist.mjs holds that the resolver it is given sends
    `<device>.configs.json`, a face and a skin to the right root."""
    src = (ROOT / "kit" / "viewer3d.js").read_text()
    assert "readIndex(distAt, 'components.json')" in src
    assert "jdist(distAt('components.json'))" not in src
    shell = (ROOT / "kit" / "shell.js").read_text()
    assert "readIndex(distAt, 'devices.json')" in shell and "readIndex(distAt, 'components.json')" in shell


def test_an_out_folder_that_is_not_an_earlier_overlay_build_is_not_emptied(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "devices.json").write_text("{}")      # a public-style dist is not an overlay build
    r = subprocess.run(["bash", str(ROOT / "build.sh"), "--overlay-library", str(FIXTURE),
                        "--overlay-out", str(out)], capture_output=True, text=True,
                       cwd=ROOT, env={**os.environ, "NO_LINT": "1"})
    assert r.returncode != 0 and "refusing to empty" in r.stderr, r.stdout + r.stderr
    assert (out / "devices.json").read_text() == "{}"


def test_a_device_naming_a_public_component_that_does_not_exist_is_refused(tmp_path):
    overlay = copy_overlay(tmp_path)
    f = device_file(overlay)
    f.write_text(f.read_text().replace("ref: std/sfp@1,", "ref: std/no-such-part@7,", 1))
    r = build(overlay, tmp_path / "out")
    text = r.stdout + r.stderr
    assert r.returncode != 0, text[-2000:]
    assert "std/no-such-part@7" in text, text[-2000:]
