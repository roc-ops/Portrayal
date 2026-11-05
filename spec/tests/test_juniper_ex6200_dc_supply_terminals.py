"""The EX6200 2100 W DC supply: its two terminal columns are seats a two-hole lug lands on, and it states one DC port.

The EX6210 hardware guide draws the supply's input as two columns of two studs, a Positive input terminal on the left
and a Negative one on the right, and names the lug of the DC input "Panduit LCD4-14A-L". Panduit's catalog prints for
that lug a 1/4 in. stud hole and a stud hole spacing of 0.63 in., the catalog's rounding of 0.625 in., which is the
registered 5/8 in. pair. The supply composes each column as `juniper/mx240-dc-pole@1` and states one input port with
the poles `pos` (left) and `neg` (right). Its skin is not redrawn. The port states no voltage, current or wire size:
the guide's nominal is a range, its current is a pair, and it prints no wire size.

These run against the real library and read no library/dist.
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SUPPLY = LIB / "components/juniper/ex6200-pwr-dc2100/v1"
POLE = "juniper/mx240-dc-pole@1"


def contract():
    return yaml.safe_load((SUPPLY / "contract.yaml").read_text())


def test_the_two_columns_are_pole_parts_left_to_right():
    parts = contract()["parts"]
    assert [(p["id"], p["ref"]) for p in parts] == [("pole-pos", POLE), ("pole-neg", POLE)]
    assert parts[0]["at"][0] < parts[1]["at"][0]
    assert all(p["rotate"] == 90 for p in parts)


def test_each_pair_is_centred_on_the_two_studs_the_skin_draws():
    svg = (SUPPLY / "skins/default.svg").read_text()
    for part, (cx, cy) in zip(contract()["parts"], ((11.9, 31.75), (29.3, 33.25))):
        assert f'cx="{cx}"' in svg
        assert abs(part["at"][0] + 9.6375 - cx) < 1e-6 and abs(part["at"][1] + 1.7 - cy) < 1e-6


def test_the_port_states_only_what_a_table_prints():
    (port,) = contract()["dc"]["ports"]
    assert port["id"] == "input" and port["direction"] == "input"
    assert [(p["role"], p["slot"]) for p in port["poles"]] == [("pos", "pole-pos"), ("neg", "pole-neg")]
    for key in ("voltage", "rating-a", "awg"):
        assert key not in port  # a range, a pair of currents and no wire size


def test_the_lug_and_its_spacing_are_cited_with_the_catalogs_rounding():
    seats = contract()["provenance"]["seats"]
    assert "LCD4-14A-L" in seats and "0.63" in seats and "0.625" in seats
    assert "page 9" in seats and "Panduit" in seats


def test_the_skin_is_the_one_on_main():
    svg = (SUPPLY / "skins/default.svg").read_text()
    assert svg.count("<circle cx=\"11.9\"") == 4 and svg.count("<circle cx=\"29.3\"") == 4


def test_the_device_takes_a_minor_and_its_lock_reads_the_port():
    doc = yaml.safe_load((LIB / "devices/juniper/ex6210/device.yaml").read_text())
    assert doc["version"] == "0.2.0"
    text = (LIB / "devices/juniper/ex6210/device.lock.json").read_text()
    assert "pole-pos" in text and "pole-neg" in text and json.loads(text)


def test_the_supply_has_no_conformance_record_and_the_cap_is_the_row_count():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    assert ("juniper/ex6200-pwr-dc2100@1", "C19") not in rows
    assert doc["cap"] == len(doc["rows"])
