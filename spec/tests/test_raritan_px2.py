"""The Raritan PX2-2475 zero-U rack PDU and the cord part it needed.

The PX2-2475 is a 1539 x 52 x 65 mm strip with 24 NEMA 5-20R outlets in three groups of eight, a controller panel between the first
and second groups, and a 3 m cord that ends in a NEMA L5-20P plug. What is true of the library once it is in:

  - the device is a device of the maker, with the size the technical specification gives and six views;
  - its 24 outlets are the registered NEMA 5-20R part, each switched, on the pitch the maker's drawing prints, and each is
    named as the unit numbers it;
  - the input is one cord part that states its plug, and the DCIM export names it as a NEMA L5-20P power port;
  - the controller panel carries every jack the maker's drawing shows, each a part;
  - the input conflict and the places the maker's documents are silent are written down as gaps, not drawn as if known.

These read the contracts and the device source. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices" / "raritan" / "px2-2475" / "device.yaml"
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device():
    return yaml.safe_load(DEVICE.read_text())


def placements(view):
    comps = (device()["views"][view].get("components") or {})
    return {p["id"]: p for p in (comps.get("placements") or [])}


def test_it_is_a_device_of_the_maker_at_the_size_the_specification_gives():
    d = device()
    assert (d["manufacturer"], d["model"]) == ("Raritan", "PX2-2475")
    assert (d["chassis"]["width"], d["chassis"]["height"], d["chassis"]["depth"]) == (52, 1539, 65)
    assert d["chassis"]["mount"] == "rack-side"


def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched():
    views = device()["views"]
    assert sorted(views) == sorted(VIEWS)
    for name, v in views.items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{name}: neither drawn nor an `empty:` sentence"


def test_the_24_outlets_are_nema_5_20r_each_switched_and_fed_from_the_input():
    outlets = {i: p for i, p in placements("front").items() if i.startswith("outlet-")}
    assert sorted(outlets, key=lambda i: int(i.split("-")[1])) == [f"outlet-{n}" for n in range(1, 25)]
    for p in outlets.values():
        assert p["ref"] == "std/nema-5-20r@1"
        assert p["fed-by"] == "input"
        assert p["states"] == ["on", "off"]


def test_the_outlets_stand_in_three_groups_of_eight_on_the_pitch_the_drawing_prints():
    """The drawing prints 35.00 between neighbours and 245.00 across a group of eight (page 6, view B)."""
    ys = [placements("front")[f"outlet-{n}"]["at"][1] for n in range(1, 25)]
    for first in (0, 8, 16):
        group = ys[first:first + 8]
        assert [round(b - a, 1) for a, b in zip(group, group[1:])] == [35.0] * 7
        assert round(group[-1] - group[0], 1) == 245.0
    assert ys == sorted(ys)


def test_the_outlets_are_named_as_the_unit_prints_them():
    rules = {r["physical"]: r for r in device()["interfaces"]}
    assert rules["outlet-{n}"]["name"] == "{n}"
    assert rules["outlet-{n}"]["range"] == "1-24"


def test_each_numeral_sits_by_its_own_outlet():
    d = device()
    outlets = placements("front")
    marks = [s for s in d["views"]["front"]["silkscreen"] if s["for"].startswith("outlet-")]
    assert [m["text"] for m in marks] == [str(n) for n in range(1, 25)]
    for m in marks:
        assert m["for"] == f"outlet-{m['text']}"
        assert abs(m["at"][1] - outlets[m["for"]]["at"][1]) < 20.0


def test_the_input_is_one_cord_part_that_states_its_plug():
    front = placements("front")
    inputs = [p for p in front.values() if p["ref"].startswith("raritan/px2-cord")]
    assert len(inputs) == 1
    c = contract(inputs[0]["ref"])
    assert c["attrs"]["plug"] == "nema-l5-20p"
    assert set(c["size-confidence"].values()) == {"estimated"}
    assert "size" in c["provenance"]


def test_the_cord_part_exports_as_a_nema_l5_20p_power_port():
    from portrayal import dcim_export

    assert dcim_export.PART_POWER["raritan/px2-cord-l5-20p"] == "nema-l5-20p"


def test_the_controller_panel_carries_every_jack_the_drawing_shows():
    refs = {i: p["ref"] for i, p in placements("front").items()}
    assert refs["usb-b"] == "raritan/pxo-usb-b@1"
    assert refs["usb-a"] == "std/usb-a@1"
    assert placements("front")["usb-a"]["skin"] == "usb2"  # the one USB-A port runs at 12 Mbps
    assert refs["console"] == "std/db9@1"
    assert {refs[i] for i in ("sensor", "feature")} == {"std/rj45@2"}
    assert refs["eth"] == "common/rj45-eth@1"
    assert refs["reset"] == "common/reset-button@1"
    assert sorted(i for i in refs if i.startswith("lamp-")) == [
        "lamp-current", "lamp-power", "lamp-sensor", "lamp-ub-load", "lamp-unlabelled", "lamp-voltage"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_device_type_lists_one_de_9_console_one_100base_tx_jack_and_24_outlets(target):
    export = yaml.safe_load((LIB / "exports" / target / "device-types" / "Raritan" / "PX2-2475.yaml").read_text())
    assert export["console-ports"] == [{"name": "Console", "type": "de-9"}]
    assert [i["type"] for i in export["interfaces"]] == ["100base-tx"]
    assert [o["type"] for o in export["power-outlets"]] == ["nema-5-20r"] * 24
    assert [p["type"] for p in export["power-ports"]] == ["nema-l5-20p"]


def test_the_console_jack_is_stated_as_one_and_the_sensor_jack_is_not():
    front = placements("front")
    assert front["console"]["attrs"]["role"] == "console"
    assert (front["sensor"].get("attrs") or {}).get("role") != "console"


def test_the_mounting_buttons_stand_the_distance_apart_the_drawing_prints():
    rear = placements("rear")
    assert sorted(rear) == ["button-1", "button-2"]
    assert round(rear["button-2"]["at"][1] - rear["button-1"]["at"][1], 1) == 1244.0


def test_the_input_conflict_and_the_silent_places_are_gaps():
    gaps = {g["what"]: g for g in device()["gaps"]}
    assert gaps["input-conflict"]["reason"] == "sources-disagree"
    assert "IEC320 C20" in gaps["input-conflict"]["note"] and "NEMA L5-20P" in gaps["input-conflict"]["note"]
    for what in ("outlet-lamps", "sensor-jack-type", "mounting-button-size"):
        assert what in gaps


def test_the_estimated_colours_say_so():
    note = device()["provenance"]["colours"]
    assert note["confidence"] == "estimated"
