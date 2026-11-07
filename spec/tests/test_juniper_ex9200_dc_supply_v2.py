"""The EX9200 2400 W DC supply, version 2: its two terminal columns are seats a two-hole lug lands on, and it states one DC port.

Version 1 drew two studs side by side in its skin and offered no place for a lug. The Juniper EX9204 and MX480 hardware guides draw
the terminal block of this supply as two columns of two studs, the two studs of a column one above the other, and print RTN over
the left column and -48V over the right. A two-hole cable lug, holes 0.625 in. apart, lands across the two studs of a column. Version 2
composes each column as `juniper/mx240-dc-pole@1` (a pair of studs on 5/8 in. centres) and states one input port with the poles
`rtn` (left) and `batt` (right). Version 1 keeps its own drawing and says it is superseded. The EX9204 and the EX9208 seat both
majors in every bay and show version 2 in their DC configurations.

These run against the real library and a components index built by the indexer the build runs. They read no library/dist.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SUPPLY = LIB / "components/juniper/ex9200-pwr-mx480-2400-dc"
V1, V2 = "juniper/ex9200-pwr-mx480-2400-dc@1", "juniper/ex9200-pwr-mx480-2400-dc@2"
POLE = "juniper/mx240-dc-pole@1"
DEVICES = ["ex9204", "ex9208"]


def contract(major):
    return yaml.safe_load((SUPPLY / f"v{major}" / "contract.yaml").read_text())


def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def device(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def test_version_two_has_its_own_folder():
    assert (SUPPLY / "v2" / "contract.yaml").is_file()
    assert (SUPPLY / "v2" / "skins" / "default.svg").is_file()
    assert contract(2)["version"].startswith("2.")


def test_version_one_is_kept_and_says_it_is_superseded():
    c = contract(1)
    assert c["superseded-by"] == V2
    assert "parts" not in c and "dc" not in c
    assert c["version"] == "1.0.1"


def test_the_two_columns_are_pole_parts_left_to_right():
    parts = contract(2)["parts"]
    assert [(p["id"], p["ref"]) for p in parts] == [("pole-rtn", POLE), ("pole-batt", POLE)]
    assert parts[0]["at"][0] < parts[1]["at"][0]
    assert all(p["rotate"] == 90 for p in parts)


def test_the_port_states_what_every_guide_prints():
    (port,) = contract(2)["dc"]["ports"]
    assert port["id"] == "input" and port["direction"] == "input"
    assert [(p["role"], p["slot"]) for p in port["poles"]] == [("rtn", "pole-rtn"), ("batt", "pole-batt")]
    assert port["voltage"] == {"nominal": -48, "range": [-40.5, -72]}
    assert port["awg"] == [6]
    assert "rating-a" not in port  # 60 A and 70 A: two figures, no one rating


def test_the_skin_prints_the_two_legends():
    svg = (SUPPLY / "v2" / "skins" / "default.svg").read_text()
    assert ">RTN<" in svg and ">-48V<" in svg
    assert svg.index(">RTN<") < svg.index(">-48V<")
    assert "<circle cx=\"37.0\" cy=\"50.0\"" not in svg  # the old drawn studs are the parts now


@pytest.mark.parametrize("name", DEVICES)
def test_each_bay_accepts_both_majors_and_the_dc_configurations_seat_version_two(name):
    doc = device(name)
    bays = [b for b in walk(doc["views"]) if str(b.get("id", "")).startswith("pem") and "accepts" in b]
    assert len(bays) == 4
    for b in bays:
        assert V1 in b["accepts"] and V2 in b["accepts"], b["id"]
    seated = {ref for cfg in doc["configurations"].values() for ref in (cfg.get("bays") or {}).values() if ref}
    assert V2 in seated and V1 not in seated


@pytest.mark.parametrize("name", DEVICES)
def test_each_lock_reads_version_two_and_its_port(name):
    import json
    lock = json.loads((LIB / "devices/juniper" / name / "device.lock.json").read_text())
    text = json.dumps(lock)
    assert "ex9200-pwr-mx480-2400-dc@2" in text
    assert "pole-rtn" in text and "pole-batt" in text
