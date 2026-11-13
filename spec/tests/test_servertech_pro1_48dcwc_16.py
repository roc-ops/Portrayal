"""The Server Technology PRO1 -48VDC Switched PDU 48DCWC-16-2X100-A0 (Primary), a 2U rack PDU.

What is true of the library once the device is in it: the device exists under its maker with the body the
drawing gives, its two input blocks each seat three stud pairs on the 5/8 in. interface, four output blocks
and two lamps stand on the front, the rear plate carries the three jacks that have a key, and the two
things with no key (the output terminals and the 4P4C sensor jacks) are stated as gaps. Each part contract
states where its figures come from.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "servertech" / "pro1-48dcwc-16-2x100-a0" / "device.yaml"
COMPONENTS = ROOT / "library" / "components" / "servertech"

INPUT = "servertech/pro1-dc-input-block"
OUTPUT = "servertech/pro1-dc-output-block"
PLATE = "servertech/pro1-dc-controller-plate"
STUD_PAIR = "common/hex-nut-stud-pair-5-8"


def _device():
    return yaml.safe_load(DEVICE.read_text(encoding="utf-8"))


def _contract(name):
    path = COMPONENTS / name / "v1" / "contract.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _placements(dev, view):
    return (dev["views"][view].get("components") or {}).get("placements") or []


def _ref(entry):
    return entry["ref"].split("@")[0]


def test_the_device_is_a_two_unit_rack_box_of_the_drawn_size():
    dev = _device()
    assert dev["manufacturer"] == "Server Technology"
    assert dev["model"] == "48DCWC-16-2X100-A0"
    chassis = dev["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"], chassis["ru"]) == (432.0, 88.0, 304.8, 2)


def test_it_has_six_faces():
    assert set(_device()["views"]) == {"front", "rear", "top", "bottom", "left", "right"}


def test_two_input_blocks_each_compose_three_stud_pairs_on_the_five_eighths_interface():
    dev = _device()
    inputs = [p for p in _placements(dev, "front") if _ref(p) == INPUT]
    assert sorted(p["id"] for p in inputs) == ["input-a", "input-b"]
    contract = _contract("pro1-dc-input-block")
    pairs = [part for part in contract["parts"] if _ref(part) == STUD_PAIR]
    assert [part["id"] for part in pairs] == ["rtn", "gnd", "neg48"]
    pair = yaml.safe_load((ROOT / "library" / "components" / "common" / "hex-nut-stud-pair-5-8" / "v1"
                           / "contract.yaml").read_text(encoding="utf-8"))
    assert pair["interface"] == "stud-pair-5-8"
    assert pair["parts"][1]["at"][0] - pair["parts"][0]["at"][0] == 15.875


def test_the_input_contract_states_the_two_figures_for_the_stud_spacing():
    notes = _contract("pro1-dc-input-block")["provenance"]["pitch"]
    assert "5/8 in." in notes and "16.0" in notes


def test_the_right_input_block_is_the_left_one_mirrored():
    dev = _device()
    by_id = {p["id"]: p for p in _placements(dev, "front")}
    assert not by_id["input-a"].get("mirror")
    assert by_id["input-b"]["mirror"] is True
    left, right = by_id["input-a"]["at"][0], by_id["input-b"]["at"][0]
    assert abs(left - (432.0 - right - 43.9)) < 0.5


def test_four_output_blocks_carry_sixteen_numerals():
    dev = _device()
    blocks = [p for p in _placements(dev, "front") if _ref(p) == OUTPUT]
    assert sorted(p["id"] for p in blocks) == ["out-a1", "out-a2", "out-b1", "out-b2"]
    texts = {m["text"] for m in dev["views"]["front"]["silkscreen"]}
    assert {f"{side}{n}" for side in "AB" for n in range(1, 9)} <= texts


def test_lamps_a_and_b_are_placed_and_lettered():
    dev = _device()
    lamps = {p["id"] for p in _placements(dev, "front") if p["ref"].startswith("common/led-indicator")}
    assert lamps == {"lamp-a", "lamp-b"}
    texts = {m["text"] for m in dev["views"]["front"]["silkscreen"]}
    assert {"A", "B", "+RTN", "GND", "-48VDC"} <= texts


def test_the_rear_plate_names_the_five_jacks():
    dev = _device()
    assert [p["id"] for p in _placements(dev, "rear")] == ["controller"]
    contract = _contract("pro1-dc-controller-plate")
    assert [part["id"] for part in contract["parts"]] == ["lnk", "ser", "net"]
    skin = (COMPONENTS / "pro1-dc-controller-plate" / "v1" / "skins" / "default.svg").read_text(encoding="utf-8")
    for legend in ("LNK", "SER", "NET", "TAM2", "TAM1"):
        assert f">{legend}<" in skin


def test_the_two_things_with_no_registry_key_are_gaps():
    gaps = {g["what"] for g in _device()["gaps"]}
    assert {"output-terminals", "sensor-jacks"} <= gaps


def test_each_part_states_its_sources():
    for name in ("pro1-dc-input-block", "pro1-dc-output-block", "pro1-dc-controller-plate"):
        contract = _contract(name)
        text = " ".join(str(v) for v in contract["provenance"].values())
        assert contract["provenance"].get("size"), name
        assert "48DCWC-16-2X100-A0" in text or "4811" in text, name
