"""The two ConnectX-7 cards for OCP NIC 3.0: one tall small form factor card with one OSFP cage and
one small form factor card with two QSFP112 cages, each on the thumbscrew (pull tab) bracket.

NVIDIA ConnectX-7 Cards for OCP Spec 3.0 User Manual: ordering table (page 5), specifications
(pages 79 and 81), board and bracket drawings (pages 83 and 84), LED section (page 20). Every
case reads files; none builds anything.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
NVIDIA = ROOT / "library/components/nvidia"

# name: (form-factor key, bracket height, cage ref, cage media, cages, lamps, speed, part numbers)
CARDS = {
    "mcx75343-ocp3-tsff": ("ocp3-tsff", 17.8, "std/osfp@1", "osfp", 1, 2, "400g",
                           ("900-9X7AX-004NMC0", "900-9X7AX-003NMC0", "MCX75343AMC-NEAC", "MCX75343AMS-NEAC")),
    "mcx753436-ocp3-sff": ("ocp3-sff", 15.1, "std/qsfp56@1", "qsfp112", 2, 4, "200g",
                           ("900-9X760-0018-MB2", "900-9X760-0078-MB0", "MCX753436MC-HEAB", "MCX753436MS-HEAB")),
}


def _load(name):
    return yaml.safe_load((NVIDIA / name / "v1/contract.yaml").read_text())


@pytest.fixture(scope="module")
def standards():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


@pytest.mark.parametrize("name", CARDS)
def test_the_card_is_a_module_of_its_form_factor(name, standards):
    key = CARDS[name][0]
    c = _load(name)
    assert c["kind"] == "module" and c["name"] == name
    assert c["attrs"]["form-factor"] == key
    assert key in standards, "the key is a registered OCP form factor"
    assert c["size"]["d"] == pytest.approx(standards[key]["h"]), "the board is the table's 115.00 deep"


@pytest.mark.parametrize("name", CARDS)
def test_the_face_is_the_manuals_thumbscrew_bracket(name):
    c = _load(name)
    assert c["size"]["w"] == pytest.approx(82.5)
    assert c["size"]["h"] == pytest.approx(CARDS[name][1])
    assert (NVIDIA / name / "v1/skins/default.svg").is_file()


@pytest.mark.parametrize("name", CARDS)
def test_the_cages_and_their_group(name):
    _, _, ref, media, count, _, speed, _ = CARDS[name]
    c = _load(name)
    cages = [p for p in c["parts"] if p["ref"] == ref]
    assert len(cages) == count
    for p in cages:
        assert p["attrs"] == {"media": media, "speed": speed}
        assert p["group"] == media
    assert c["groups"][media]["attrs"] == {"media": media, "speed": speed}
    assert c["attrs"]["ports"] == count and c["attrs"][media] == count


@pytest.mark.parametrize("name", CARDS)
def test_each_port_has_a_bicolour_and_a_green_lamp(name):
    lamps = [p for p in _load(name)["parts"] if p["ref"] == "common/led-dot@1"]
    assert len(lamps) == CARDS[name][5]
    for i, lamp in enumerate(lamps):
        states = {s if isinstance(s, str) else s["name"]: s for s in lamp["states"]["lamp"]}
        colours = {s["color"] for s in states.values() if not isinstance(s, str)}
        assert colours == ({"#22c55e", "#eab308"} if i % 2 == 0 else {"#22c55e"}), lamp["id"]
        assert "link-up" in states and "activity" in states


@pytest.mark.parametrize("name", CARDS)
def test_both_part_numbers_of_the_board_are_listed(name):
    listed = _load(name)["attrs"]["part-numbers"]
    for pn in CARDS[name][7]:
        assert pn in listed


@pytest.mark.parametrize("name", CARDS)
def test_the_sources_name_their_pages_and_the_estimates_are_declared(name):
    prov = _load(name)["provenance"]
    text = " ".join(prov.values())
    for needle in ("page 5", "page 83", "page 84", "page 20", "Table 5, page 25"):
        assert needle in text, needle
    assert prov["colour"].startswith("estimated")
    assert prov["port"].startswith("estimated"), "the cage against the drawn window is an estimate"
    assert "power-draw-max-w" in prov["power"], "the missing maximum is said, not filled"
    assert "not held" in prov["power"]
    assert "No photograph" in prov["sources"]


def test_each_card_records_its_thickness_and_says_why_no_bay_lists_it():
    tall, short = _load("mcx75343-ocp3-tsff"), _load("mcx753436-ocp3-sff")
    assert "14.20" in tall["provenance"]["thickness"]
    assert "11.50" in short["provenance"]["thickness"]
    assert "ocp3-tsff" in tall["unplaced"] and "ocp3-sff" in short["unplaced"]
