"""The DVI-D video jack has its own connector key, `dvi-d`, and its own part, `std/dvi-d-jack@1`.

What is true of the library once they are in it: the registry names the key like the other plain
standard connectors and names the part that presents it, the part declares that its size and its
contact layout are read off a photograph, the Raritan DSX2-32 places it between its two thumbscrews
and no longer lists the jack as a gap, and the exporter says why a video jack is not a DCIM port.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from portrayal import dcim_export as dx
from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"

KEY = "dvi-d"
REF = "std/dvi-d-jack@1"
DEVICE = LIB / "devices/raritan/dsx2-32"


def contract():
    return yaml.safe_load((LIB / "components/std/dvi-d-jack/v1/contract.yaml").read_text())


def skin_ids():
    root = ET.parse(LIB / "components/std/dvi-d-jack/v1/skins/default.svg").getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def standards():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def device():
    return yaml.safe_load((DEVICE / "device.yaml").read_text())


def test_the_registry_names_the_key_like_the_other_standard_connectors():
    entry = render_mod._connector_registry()[KEY]
    assert entry.get("standard") == KEY
    assert REF in entry["note"] and "DVI-D" in entry["note"]
    assert "unmated" not in entry
    assert "std/dvi-d-jack@1" in entry["note"]


def test_the_part_presents_the_key_and_conforms_to_its_standards_entry():
    c = contract()
    assert c["class"] == "port" and c["interface"] == KEY and c["conforms"] == KEY
    assert c["attrs"]["media"] == KEY
    entry = standards()[KEY]
    assert (c["size"]["w"], c["size"]["h"]) == (entry["w"], entry["h"])


def test_the_size_and_the_contact_layout_are_declared_estimated_for_want_of_a_standard_document():
    c = contract()
    assert c["size-confidence"] == {"w": "estimated", "h": "estimated"}
    entry = standards()[KEY]
    assert entry["confidence"] == "estimated"
    for text in (c["provenance"]["size"], c["provenance"]["contacts"], entry["source"]):
        assert "estimated" in text.lower() or "photograph" in text.lower()
    assert "data sheet" in entry["source"] and "Raritan" in entry["source"]
    assert "no dvi standard document is held" in c["provenance"]["size"].lower()


def test_the_skin_draws_three_rows_of_eight_contact_cells_and_a_blade_and_no_analogue_pins():
    ids = skin_ids()
    cells = [i for i in ids if i.startswith("cell-")]
    assert len(cells) == 24
    assert {(i.split("-")[1]) for i in cells} == {"1", "2", "3"}
    assert {(i.split("-")[2]) for i in cells} == {str(n) for n in range(1, 9)}
    assert "blade" in ids
    assert not [i for i in ids if i.startswith("analog")]


def test_the_dsx2_32_places_the_jack_once_on_the_rear_between_its_two_screws():
    d = device()
    rear = {p["id"]: p for p in d["views"]["rear"]["components"]["placements"]}
    jack = rear["video"]
    assert jack["ref"] == REF and jack["group"] == "video"
    decor = {x["id"]: x for x in d["views"]["rear"]["panel"]["decor"]}
    left, right = decor["dvi-screw-left"], decor["dvi-screw-right"]
    width = contract()["size"]["w"]
    assert left["at"][0] + left["size"][0] <= jack["at"][0]
    assert jack["at"][0] + width <= right["at"][0]
    placed = [p for v in d["views"].values() for p in (v.get("components") or {}).get("placements", [])
              if p["ref"] == REF]
    assert len(placed) == 1
    assert d["groups"]["video"]["attrs"] == {"media": KEY}


def test_the_dsx2_32_no_longer_lists_the_jack_as_a_gap_or_a_region():
    d = device()
    assert "dvi-d" not in {g["what"] for g in d["gaps"]}
    assert "dvi-d" not in {r["id"] for r in d["views"]["rear"].get("components", {}).get("regions", [])}


def test_the_exporter_says_why_a_video_jack_is_not_a_dcim_port():
    why = dx.NOT_A_DCIM_PORT["std/dvi-d-jack"]
    assert len(why) >= 40 and "video" in why
