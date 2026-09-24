"""render.py draws a part on a facet foreshortened and marks it for 3D."""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC, LIB = ROOT / "spec", ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"

SKIN = ('<svg xmlns="http://www.w3.org/2000/svg" width="25mm" height="100mm" viewBox="0 0 25 100">'
        '<rect id="face" width="25" height="100" fill="#ccc"/>'
        '<rect id="housing" x="0" y="40" width="25" height="30" fill="#999"/></svg>')


def plant_card(tmp, rotate=None, occupant=False):
    lib = tmp / "lib"
    d = lib / "components/acme/tilt-card/v1"
    (d / "skins").mkdir(parents=True)
    part = {"ref": "std/qsfp28@1", "id": "p1", "at": [2.5, 45.0], "on": "housing"}
    if rotate:
        part["rotate"] = rotate
    (d / "contract.yaml").write_text(yaml.safe_dump({
        "format": 1, "kind": "module", "name": "tilt-card", "version": "1.0.0",
        "class": "line-card", "behaviour": "fills", "size": {"w": 25.0, "h": 100.0},
        "elements": {"face": {"at": [0, 0], "size": [25, 100], "class": "panel"},
                     "housing": {"at": [0.0, 40.0], "size": [25.0, 30.0], "class": "panel"}},
        "relief": {"features": [{"node": "housing", "facet": {"deg": 30, "facing": "up"},
                                 "confidence": "drawing", "source": "fixture"}]},
        "parts": [part],
        "connection-points": {"mate": {"at": [12.5, 50.0], "direction": "rear"}},
        "skins": ["default"]}))
    (d / "skins/default.svg").write_text(SKIN)
    dev = tmp / "device.yaml"
    placements = [{"ref": "acme/tilt-card@1", "id": "card", "at": [0, 0]}]
    if occupant:
        # `mate-to` targets a device-level PLACEMENT id, not a path into it
        # (render.py's `hosts` dict is keyed by placement id only - see the
        # fixed-point loop in render_view). "card" forwards to `p1`'s own
        # `mate` connection-point through presented_interface exactly as any
        # other composed aperture does, since `card` composes exactly one
        # part (`p1`) that declares an `interface` + `mate`.
        placements.append({"ref": "generic/qsfp-lc@1", "id": "optic", "mate-to": "card"})
    dev.write_text(yaml.safe_dump({
        "format": 1, "kind": "device", "name": "tilt-dev", "version": "0.1.0",
        "maturity": "draft", "manufacturer": "Acme", "model": "T", "profile": "networking",
        "chassis": {"width": 25, "height": 100, "depth": 200},
        "views": {"front": {"size": {"w": 25, "h": 100},
                            "components": {"placements": placements}}}}, sort_keys=False))
    out = tmp / "o"
    out.mkdir()
    r = subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                        "--library", str(lib), "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return ET.parse(out / "tilt-dev.front.svg").getroot()


def by_id(root, suffix):
    return next(e for e in root.iter() if (e.get("id") or "").endswith(suffix))


def test_the_facet_node_carries_its_derived_wedge(tmp_path):
    root = plant_card(tmp_path)
    h = by_id(root, "--housing")
    assert h.get("data-facet-deg") == "30" and h.get("data-facet-facing") == "up"
    assert h.get("data-z-profile-y").startswith("0:0,30:")
    assert float(h.get("data-z-out")) > 17.3          # 30 x tan 30 = 17.32


def test_a_part_on_a_facet_is_scaled_and_marked(tmp_path):
    root = plant_card(tmp_path)
    p = by_id(root, "--p1")
    assert "scale(1,0.866025)" in p.get("transform")
    assert p.get("data-tilt") == "30" and p.get("data-tilt-facing") == "up"
    assert p.get("data-tilt-on").endswith("--housing")


def test_the_scale_comes_before_the_parts_own_rotate(tmp_path):
    tf = by_id(plant_card(tmp_path, rotate=90), "--p1").get("transform")
    assert tf.index("scale(") < tf.index("rotate(")


def test_an_occupant_inherits_the_tilt(tmp_path):
    root = plant_card(tmp_path, occupant=True)
    o = next(e for e in root.iter() if (e.get("data-path") or e.get("id") or "").endswith("optic"))
    assert o.get("data-tilt") == "30"
    assert o.get("data-tilt-on").endswith("--housing")
