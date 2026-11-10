"""The ALARM connector of the Juniper MX104 is a placed part that presents the `hd15` key, with a dark insulator.

The MX104 Universal Routing Platform Hardware Guide calls the port a 15-pin D-type connector that takes a DE-15 alarm cable. The
front photograph shows a female high-density D-sub, three rows of five sockets, a dark insulator in a metal shell, with a threaded
hole either side. It was drawn as a plain cutout. It is now `std/vga@1`, which presents `hd15` (`generic/hd15-plug@1` mates it),
with the insulator colour the photograph shows set on the placement.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
DEVICE = LIBRARY / "devices" / "juniper" / "mx104" / "device.yaml"
VGA = LIBRARY / "components" / "std" / "vga" / "v1"


def device():
    return yaml.safe_load(DEVICE.read_text())


def test_the_alarm_connector_is_a_placed_hd15_part_and_not_a_cutout():
    front = device()["views"]["front"]
    placed = {p["id"]: p for p in front["components"]["placements"]}
    assert placed["alarm"]["ref"].split("@")[0] == "std/vga", "the DE-15 alarm connector is the library's HD-15 receptacle"
    assert placed["alarm"]["group"] == "mgmt"
    assert "alarm" in {c["id"] for c in front["panel"]["cutouts"]}, "the panel hole the connector sits in keeps its id"


@pytest.mark.heavy
def test_a_cable_plug_in_the_library_mates_the_key_the_connector_presents():
    vga = yaml.safe_load((VGA / "contract.yaml").read_text())
    assert vga["interface"] == "hd15"
    mates = []
    for path in (LIBRARY / "components").glob("*/*/v*/contract.yaml"):
        doc = yaml.safe_load(path.read_text()) or {}
        if doc.get("mates") == "hd15":
            mates.append(path.parts[-4] + "/" + path.parts[-3])
    assert mates, "a part that mates hd15 is the cable end of the alarm connector"


def test_the_insulator_colour_is_a_field_the_placement_sets_and_the_default_is_unchanged():
    vga = yaml.safe_load((VGA / "contract.yaml").read_text())
    assert "insulator" in vga["fields"], "colour is a field, not a skin"
    skin = (VGA / "skins" / "default.svg").read_text()
    node = re.search(r'<path id="insert"[^>]*>', skin).group(0)
    assert 'data-fill-from="insulator"' in node and 'data-stroke-from="insulator"' in node, "the outline follows the colour too"
    assert 'fill="#1f4f9e"' in node and 'stroke="#16376e"' in node, "an unset field keeps the blue a VGA receptacle carries"
    relief = next(f for f in vga["relief"]["features"] if f["node"] == "insert")
    assert "color" not in relief, "the 3D insulator follows the field, so the relief states no colour of its own"
    alarm = next(p for p in device()["views"]["front"]["components"]["placements"] if p["id"] == "alarm")
    assert re.fullmatch(r"#[0-9a-f]{6}", str(alarm["attrs"]["insulator"])), "the photograph shows a dark insulator"


def test_the_alarm_gap_is_closed():
    assert "alarm-connector" not in {g["what"] for g in device()["gaps"]}
