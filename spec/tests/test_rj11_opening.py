"""The RJ11 plug opening is a standard part, and the RJ11 jack composes it.

std/rj11@1 is the six-position plug opening as TE customer drawing C-1775675
rev C draws it: one width the drawing prints (9.88), the depth it prints (20.57),
the three tiers read off the same front view. A maker's drawing is the source, and
the contract says so, because IEC 60603-7 governs the plug interface and is not
held. common/rj11-jack@1 is the housing around it and keeps its face.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal.manifest import presented_interface

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "library/components"
JACK, STD = "common/rj11-jack@1", "std/rj11@1"


def contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((COMPONENTS / ns / name / f"v{major}" / "contract.yaml").read_text())


def skin(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    root = ET.parse(COMPONENTS / ns / name / f"v{major}" / "skins" / "default.svg").getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def registry():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]["rj11"]


def flat(text):
    return " ".join(str(text).split())


def test_the_opening_is_a_standard_part_that_presents_rj11():
    c = contract(STD)
    assert c["class"] == "port" and c["conforms"] == "rj11" and c["interface"] == "rj11"
    assert c["size"] == {"w": 9.88, "h": 11.26, "d": 20.57}
    assert c["attrs"] == {"media": "rj11"}
    assert c["elements"]["opening"]["class"] == "cutout"


def test_the_registry_entry_claims_the_opening_the_part_draws():
    reg, c = registry(), contract(STD)
    assert (reg["w"], reg["h"], reg["depth"]) == (c["size"]["w"], c["size"]["h"], c["size"]["d"])
    assert reg["cavity"] == {"w": 9.88, "h": 11.26}
    assert [t["name"] for t in reg["tiers"]] == ["body", "shoulder", "slot"]
    assert "NO ENVELOPE IS CLAIMED" not in reg["notes"]


def test_the_source_is_the_makers_drawing_and_says_the_standard_is_not_held():
    prov = contract(STD)["provenance"]
    text = flat(prov["size"]) + " " + flat(prov["opening"])
    assert "C-1775675" in text and "TE" in text
    assert "IEC 60603-7" in text and "not held" in text
    assert "9.88" in text and "scaled" in text.lower()
    assert "TE" in registry()["registry"] and "C-1775675" in registry()["registry"]


def test_the_cavity_is_the_three_tier_outline_the_jack_drew():
    c = contract(STD)
    assert c["relief"]["cavity"] == "cavity"
    assert c["relief"]["size"] == {"w": 9.88, "h": 11.26}
    d = skin(STD)["cavity"].get("d").split()
    assert d[:3] == ["M", "0", "0"]
    steps = [(d[i], float(d[i + 1])) for i in range(3, len(d) - 1, 2)]
    assert steps == [("h", 9.88), ("v", 6.85), ("h", -1.64), ("v", 1.69), ("h", -1.28),
                     ("v", 2.72), ("h", -4.04), ("v", -2.72), ("h", -1.28), ("v", -1.69),
                     ("h", -1.64)]


def test_two_contacts_are_loaded_on_the_1_02_pitch():
    pins = [e for e in skin(STD)["pins"] if e.tag.endswith("rect")]
    xs = [float(e.get("x")) + float(e.get("width")) / 2 for e in pins]
    assert len(xs) == 2
    assert xs[1] - xs[0] == pytest.approx(1.02)
    assert sum(xs) / 2 == pytest.approx(9.88 / 2)


def test_the_jack_composes_the_opening_where_it_drew_it():
    j = contract(JACK)
    parts = [p for p in j["parts"] if p["ref"] == STD]
    assert len(parts) == 1 and parts[0]["at"] == [2.06, 1.5]
    assert j["size"] == {"w": 14.0, "h": 13.5, "d": 20.57}
    assert j["elements"]["jack"] == {"at": [2.06, 1.5], "size": [9.88, 11.26], "class": "jack"}
    assert not [e for e in j["elements"].values() if e.get("class") == "cutout"]
    assert "relief" not in j


def test_the_jack_still_presents_rj11_at_the_centre_of_the_body_tier():
    j = contract(JACK)
    got, at, lift = presented_interface(j, contract)
    assert got == "rj11" and lift == 0.0
    assert at == pytest.approx([7.0, 4.925])
    assert j["connection-points"]["mate"]["at"] == [7.0, 4.925]
    assert j["connection-points"]["tel"]["at"] == j["connection-points"]["mate"]["at"]
    std_mate = contract(STD)["connection-points"]["mate"]["at"]
    assert [std_mate[0] + 2.06, std_mate[1] + 1.5] == pytest.approx([7.0, 4.925])


def test_the_jack_housing_has_the_same_hole_the_part_fills():
    d = skin(JACK)["housing"].get("d")
    assert "M 2.06 1.5 h 9.88 v 6.85" in " ".join(d.split())
    assert "cavity" not in skin(JACK) and "jack-pins" not in skin(JACK)
