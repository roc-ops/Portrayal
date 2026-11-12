"""The DVI-D jack has a cable end: `generic/dvi-d-plug@1` mates the `dvi-d` key.

What is true of the library once it is in it: the plug mates the key the jack presents, it states the
figures the Digital Display Working Group's Digital Visual Interface specification, Revision 1.0, prints
for a digital plug (Figure 5-5, page 47) and says which figures it estimates, its skin is the plug seen
from the cable end, and the registry and the standards file no longer say that no plug part is in the
library or that the specification is not held.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"

KEY = "dvi-d"
PLUG = "generic/dvi-d-plug@1"
JACK = "std/dvi-d-jack@1"
PLUG_DIR = LIB / "components/generic/dvi-d-plug/v1"


def contract():
    return yaml.safe_load((PLUG_DIR / "contract.yaml").read_text())


def skin():
    root = ET.parse(PLUG_DIR / "skins/default.svg").getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def standards():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def features():
    return {f["node"]: f for f in contract()["relief"]["features"]}


def test_the_plug_mates_the_key_the_jack_presents():
    c = contract()
    jack = yaml.safe_load((LIB / "components/std/dvi-d-jack/v1/contract.yaml").read_text())
    assert c["class"] == "port" and c["mates"] == KEY and jack["interface"] == KEY
    assert c["attrs"]["media"] == jack["attrs"]["media"] == KEY
    assert c["attrs"]["gender"] == "male"
    assert c["connection-points"]["mate"]["direction"] == "front"


def test_the_plug_conforms_to_its_standards_entry_and_the_entry_cites_the_specification():
    c = contract()
    entry = standards()[c["conforms"]]
    assert (c["size"]["w"], c["size"]["h"]) == (entry["w"], entry["h"]) == (39.5, 15.13)
    assert c["size-confidence"] == {"w": "drawing", "h": "drawing"}
    text = " ".join(str(entry["source"]).split())
    for word in ("Digital Display Working Group", "Revision 1.0", "Figure 5-5", "47"):
        assert word in text, word


def test_the_plug_draws_the_shell_and_the_two_jackscrews_the_figure_dimensions():
    ids = skin()
    shell = ids["shell"]
    assert shell.get("d") or shell.get("width")
    left, right = ids["screw-l"], ids["screw-r"]
    assert abs(float(right.get("cx")) - float(left.get("cx")) - 32.51) < 0.01
    assert left.get("cy") == right.get("cy")
    mate = contract()["connection-points"]["mate"]["at"]
    assert abs((float(left.get("cx")) + float(right.get("cx"))) / 2 - mate[0]) < 0.01
    assert "stub" in ids and "stub" in features()


def test_the_contact_grid_is_recorded_as_twenty_four_positions_and_is_not_drawn():
    c = contract()
    text = " ".join(str(c["provenance"]["contacts"]).split())
    for word in ("24", "three rows of eight", "1.905", "Table 5-1", "Figure 5-5"):
        assert word in text, word
    assert not [i for i in skin() if i.startswith(("pin-", "cell-"))]


def test_every_estimate_of_the_plug_is_declared():
    c = contract()
    prov = c["provenance"]
    for key in ("size", "contacts", "shell", "depth", "hood", "stub", "cable-od", "colour"):
        assert key in prov, key
    assert features()["stub"]["confidence"] == "estimated"
    assert features()["shell"]["confidence"] == "estimated"
    assert "estimated" in " ".join(str(prov["hood"]).split()).lower()


def test_the_registry_names_the_plug_and_no_longer_says_none_is_in_the_library():
    entry = render_mod._connector_registry()[KEY]
    note = " ".join(entry["note"].split())
    assert PLUG in note and JACK in note
    assert "no plug part is in the library" not in note
    assert "is not held" not in note
    assert "unmated" not in entry


def test_the_jack_standards_entry_no_longer_says_the_specification_is_not_held():
    entry = standards()[KEY]
    text = " ".join(f"{entry['source']} {entry['notes']}".split())
    assert "standard is not held" not in text
    assert "Revision 1.0" in text
