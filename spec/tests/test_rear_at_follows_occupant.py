"""A back seen through a rear cutout lands where the SEATED module's body stands.

fs/fhd-1ufce's bays used to say where a back lands (`rear.at`), and the four
figures they gave were an FHD cassette's: the cutout plus its 99 x 31 body,
centred behind a 108.97 x 35.05 plate and mirrored. An FHD adapter panel seats
in the same bay with an 88 x 34.8 body hard against the top of its plate, and
drawn at the cassette's offset its back sat 5.5 mm left of the hole's centre
and 1.9 mm high. Where a back lands is the occupant's to say, so render.py
reads it from the seated module's own `body.footprint`, mirrored across the bay
(faces.rear_at), and the hole's `data-rear-at` says the same for the kit.

The panel here is a stand-in with an adapter panel's body; the cassette is the
real fs/fhd-1mtp6lcd-os2-a@4. Both are seated in bay-1, one configuration each.
"""
import re
import shutil
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

import warmrender
from test_nested_occupants import LIB, SPEC

from portrayal.faces import rear_at

CASSETTE = "fs/fhd-1mtp6lcd-os2-a@4"
PANEL = "test/fhd-panel@1"
PANEL_BACK = "test/fhd-panel-rear@1"
BACK1 = (332.97, 4.475, 108.97, 35.05)          # cutout back-1: bay-1 from behind

SKIN = ('<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
        'viewBox="0 0 {w} {h}"><rect x="0" y="0" width="{w}" height="{h}" '
        'fill="#2a2d31"/></svg>\n')


def component(root, ref, data):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    d = root / "components" / ns / name / f"v{major}"
    (d / "skins").mkdir(parents=True)
    (d / "contract.yaml").write_text(yaml.safe_dump(
        {"format": 1, "kind": "component", "name": name, "version": f"{major}.0.0",
         "description": "test stand-in", **data, "skins": ["default"]}, sort_keys=False))
    (d / "skins" / "default.svg").write_text(SKIN.format(**data["size"]))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("rear-at")
    extra = tmp / "lib"
    component(extra, PANEL, {
        "class": "adapter-panel", "size": {"w": 108.97, "h": 35.05},
        "body": {"depth": 60.0, "footprint": {"at": [10.485, 0.125], "size": [88.0, 34.8]}},
        "faces": {"rear": {"ref": PANEL_BACK}}})
    component(extra, PANEL_BACK, {"class": "adapter-panel", "size": {"w": 88.0, "h": 34.8}})
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp / "fhd") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    bay = next(b for b in d["views"]["front"]["components"]["bays"] if b["id"] == "bay-1")
    bay["accepts"].append(PANEL)
    d["configurations"]["cas"] = {"kind": "example", "description": "c", "bays": {"bay-1": CASSETTE}}
    d["configurations"]["pan"] = {"kind": "example", "description": "p", "bays": {"bay-1": PANEL}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / "o"
    r = warmrender.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--library", str(extra), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return {c: ET.parse(out / f"fhd-1ufce.{c}.rear.svg").getroot() for c in ("cas", "pan")}


def by_id(root, nid):
    hits = [n for n in root.iter() if n.get("id") == nid]
    assert len(hits) == 1, (nid, len(hits))
    return hits[0]


def translate(el):
    m = re.fullmatch(r"translate\(([-\d.]+),\s*([-\d.]+)\)", el.get("transform") or "")
    assert m, el.get("transform")
    return float(m.group(1)), float(m.group(2))


@pytest.mark.parametrize("config, back", [("cas", (99.0, 31.0)), ("pan", (88.0, 34.8))])
def test_each_back_is_centred_on_the_cutout_it_is_seen_through(built, config, back):
    root = built[config]
    x, y = translate(by_id(root, "bay-1-rear"))
    cx, cy, cw, ch = BACK1
    assert abs(x + back[0] / 2 - (cx + cw / 2)) < 1e-6, (config, x)
    assert abs(y + back[1] / 2 - (cy + ch / 2)) < 1e-6, (config, y)
    # the hole says the same, for a swap to read
    hole = by_id(root, "cutout--back-1")
    assert tuple(map(float, hole.get("data-rear-at").split(","))) == pytest.approx((x, y))
    assert hole.get("data-rear-bay") == "332.97,4.475,108.97,35.05"


def test_the_two_backs_land_in_different_places(built):
    assert translate(by_id(built["cas"], "bay-1-rear")) == pytest.approx((337.955, 6.5))
    assert translate(by_id(built["pan"], "bay-1-rear")) == pytest.approx((343.455, 4.6))


def test_an_empty_hole_says_where_the_bay_is_but_not_where_a_back_is(built):
    hole = by_id(built["cas"], "cutout--back-2")
    assert hole.get("data-rear-bay") == "224,4.475,108.97,35.05"
    assert hole.get("data-rear-at") is None


def test_the_mirror_is_across_the_bay_not_the_body():
    # an off-centre body lands on the OTHER side of the hole from behind
    bay = {"size": {"w": 100.0, "h": 40.0}}
    cut = {"at": [10.0, 5.0]}
    c = {"size": {"w": 100.0, "h": 40.0}, "body": {"footprint": {"at": [0, 3], "size": [60, 30]}}}
    assert rear_at(bay, cut, c) == [50.0, 8.0]
    # no footprint: the body fills the face
    assert rear_at(bay, cut, {"size": {"w": 100.0, "h": 40.0}}) == [10.0, 5.0]
