"""The EX6200 2100 W DC supply: its two terminal columns are seats a two-hole lug lands on, and it states one DC port.

The EX6210 hardware guide draws the supply's input as two columns of two studs, a Positive input terminal on the left
and a Negative one on the right, and names the lug of the DC input "Panduit LCD4-14A-L". Panduit's catalog prints for
that lug a 1/4 in. stud hole and a stud hole spacing of 0.63 in., the catalog's rounding of 0.625 in., which is the
registered 5/8 in. pair. The supply composes each column as a pair of hex nuts on studs, with a washer under each nut,
as Figure 23 draws them, and states one input port with the poles `pos` (left) and `neg` (right). The port states no voltage, current or wire size:
the guide's nominal is a range, its current is a pair, and it prints no wire size.

These run against the real library and read no library/dist.
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SUPPLY = LIB / "components/juniper/ex6200-pwr-dc2100/v1"


def contract():
    return yaml.safe_load((SUPPLY / "contract.yaml").read_text())


def part_dir(ref):
    name, version = ref.split("@")
    return LIB / "components" / name / f"v{version}"


def part_contract(ref):
    return yaml.safe_load((part_dir(ref) / "contract.yaml").read_text())


def part_skin(ref):
    return (part_dir(ref) / "skins/default.svg").read_text()


def pole_ref():
    refs = {p["ref"] for p in contract()["parts"]}
    assert len(refs) == 1
    return refs.pop()


def stud_ref():
    refs = {p["ref"] for p in part_contract(pole_ref())["parts"]}
    assert len(refs) == 1
    return refs.pop()


def test_the_two_columns_are_pole_parts_left_to_right():
    parts = contract()["parts"]
    assert [p["id"] for p in parts] == ["pole-pos", "pole-neg"]
    assert parts[0]["at"][0] < parts[1]["at"][0]
    assert all(p["rotate"] == 90 for p in parts)


def test_each_pair_is_centred_on_the_two_studs_the_skin_draws():
    svg = (SUPPLY / "skins/default.svg").read_text()
    size = part_contract(pole_ref())["size"]
    for part, (cx, cy) in zip(contract()["parts"], ((11.9, 31.75), (29.3, 33.25))):
        assert f'cx="{cx}"' in svg
        assert abs(part["at"][0] + size["w"] / 2 - cx) < 1e-6 and abs(part["at"][1] + size["h"] / 2 - cy) < 1e-6


def test_the_pole_keeps_the_registered_pair_and_its_pitch():
    pole = part_contract(pole_ref())
    assert pole["interface"] == "stud-pair-5-8" and pole["attrs"]["connector"] == "stud-pair-5-8"
    studs = pole["parts"]
    assert len(studs) == 2 and abs(studs[1]["at"][0] - studs[0]["at"][0] - 15.875) < 1e-6


def test_each_stud_draws_as_a_hex_nut_on_a_stud_with_a_washer():
    ref = stud_ref()
    svg = part_skin(ref)
    hexagon = re.search(r'<path id="nut"[^>]* d="([^"]+)"', svg)
    assert hexagon and len(re.findall(r"[lLvVhH]", hexagon.group(1))) == 5     # six corners
    assert 'id="washer"' in svg and 'id="stud"' in svg
    assert "<line" not in svg and 'id="slot"' not in svg                       # no cross or slot
    nodes = {f["node"]: f for f in part_contract(ref)["relief"]["features"]}
    assert set(nodes) == {"washer", "nut", "stud"}
    assert nodes["washer"]["out"] < nodes["nut"]["out"] < nodes["stud"]["cyl"]
    assert all(f["confidence"] == "estimated" for f in nodes.values())


def test_every_size_of_the_nut_part_is_estimated_and_cites_the_figure():
    doc = part_contract(stud_ref())
    assert set(doc["size-confidence"].values()) == {"estimated"}
    cited = doc["provenance"]["size"] + doc["provenance"]["nut"]
    assert "Figure 23" in cited and "page 79" in cited


def test_the_left_pair_sits_on_a_bracket_the_skin_draws():
    svg = (SUPPLY / "skins/default.svg").read_text()
    assert 'id="bracket"' in svg


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


def test_the_drawn_discs_the_studs_stand_over_are_kept():
    svg = (SUPPLY / "skins/default.svg").read_text()
    assert svg.count("<circle cx=\"11.9\"") == 4 and svg.count("<circle cx=\"29.3\"") == 4


def test_the_device_takes_a_minor_then_a_patch_and_its_lock_reads_the_port():
    doc = yaml.safe_load((LIB / "devices/juniper/ex6210/device.yaml").read_text())
    assert doc["version"] == "0.2.1"
    text = (LIB / "devices/juniper/ex6210/device.lock.json").read_text()
    assert "pole-pos" in text and "pole-neg" in text and json.loads(text)


def test_the_supply_has_no_conformance_record_and_the_cap_is_the_row_count():
    doc = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())
    rows = {(r["part"], r["code"]) for r in doc["rows"]}
    assert ("juniper/ex6200-pwr-dc2100@1", "C19") not in rows
    assert doc["cap"] == len(doc["rows"])
