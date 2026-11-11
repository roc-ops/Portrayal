"""The StarTech.com 1U horizontal PDUs: the 8NS8-RACK-MOUNT-PDU, the PDU08C13H and the RKPW081915.

The 8NS8-RACK-MOUNT-PDU is a switched strip with eight NEMA 5-15R outlets on the rear, a covered rocker switch for each on the front, a breaker and a
fixed 8 ft cord. The PDU08C13H is a basic strip with eight IEC C13 outlets, two push buttons and a C20 inlet on the front. The RKPW081915 is a basic
strip with a surge lamp, a ground lamp and a rocker on the front, and eight 5-15R outlets and a fixed 6 ft cord on the rear. What is true of the library
once they are in:

  - each is a device of the maker, the size its data sheet gives, with six views, and a bare view says what was searched;
  - each outlet is a part that presents the interface its plug mates, and the outlets are numbered as the unit prints them;
  - the input is a part that states its plug, and the DCIM files write that plug and every outlet the drawing places;
  - a figure no document gives is declared an estimate in the contract or the device that carries it.

These read the contracts and the device sources, and the DCIM files the exporter wrote. They render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SKUS = {
    "8ns8-rack-mount-pdu": dict(model="8NS8-RACK-MOUNT-PDU", size=(440, 44, 95.5), plug="nema-5-15p", outlet="std/nema-5-15r@1", view="rear"),
    "pdu08c13h": dict(model="PDU08C13H", size=(440, 44, 98.8), plug="iec-60320-c20", outlet="std/c13-outlet@1", view="front"),
    "rkpw081915": dict(model="RKPW081915", size=(440, 42.7, 95.5), plug="nema-5-15p", outlet="std/nema-5-15r@1", view="rear"),
}
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]
NEW_PARTS = ["startech/outlet-switch-cover@1", "startech/pdu-cord-5-15p@1"]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device(sku):
    return yaml.safe_load((LIB / "devices" / "startech" / sku / "device.yaml").read_text())


def placements(sku, view):
    comps = (device(sku)["views"][view].get("components") or {})
    return {p["id"]: p for p in (comps.get("placements") or [])}


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_sku_is_a_device_of_the_maker_the_size_the_data_sheet_gives(sku):
    d = device(sku)
    assert (d["manufacturer"], d["model"]) == ("StarTech.com", SKUS[sku]["model"])
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == SKUS[sku]["size"]
    assert c["ru"] == 1


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched(sku):
    views = device(sku)["views"]
    assert sorted(views) == sorted(VIEWS)
    for name, v in views.items():
        drawn = (v.get("components") or {}).get("placements")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{sku} {name}: neither drawn nor an `empty:` sentence"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_each_strip_places_eight_outlets_of_the_part_its_data_sheet_names_and_numbers_them_as_printed(sku):
    spec = SKUS[sku]
    outlets = {i: p for i, p in placements(sku, spec["view"]).items() if i.startswith("outlet-")}
    assert sorted(outlets, key=lambda i: int(i.split("-")[1])) == [f"outlet-{n}" for n in range(1, 9)]
    assert {p["ref"] for p in outlets.values()} == {spec["outlet"]}
    assert {p["fed-by"] for p in outlets.values()} == {"input"}
    rules = {r["physical"]: r for r in device(sku)["interfaces"]}
    assert rules["outlet-{n}"]["name"] == "{n}" and rules["outlet-{n}"]["range"] == "1-8"


def test_the_switched_strip_has_a_covered_switch_for_each_outlet_and_a_breaker_on_the_front():
    front = placements("8ns8-rack-mount-pdu", "front")
    switches = {i for i, p in front.items() if p["ref"] == "startech/outlet-switch-cover@1"}
    assert switches == {f"switch-{n}" for n in range(1, 9)}
    assert front["breaker"]["ref"] == "common/breaker-push-reset@1"
    assert placements("8ns8-rack-mount-pdu", "rear")["input"]["ref"] == "startech/pdu-cord-5-15p@1"
    mgmt = device("8ns8-rack-mount-pdu")["attrs"]["management"]
    assert (mgmt["metering-scope"], mgmt["outlet-switching"]) == ("none", True)
    assert all(p.get("states") == ["on", "off"] for i, p in placements("8ns8-rack-mount-pdu", "rear").items() if i.startswith("outlet-"))


def test_the_c13_strip_takes_its_power_at_a_c20_inlet_on_the_front_beside_two_push_buttons():
    front = placements("pdu08c13h", "front")
    assert front["input"]["ref"] == "std/c20-inlet@1"
    assert sorted(i for i, p in front.items() if p["ref"] == "common/breaker-push-reset@1") == ["breaker-1", "breaker-2"]
    assert device("pdu08c13h")["attrs"]["power"]["input-cord"] == "detachable"


def test_the_surge_strip_front_carries_its_two_lamps_and_its_rocker_and_no_outlet():
    front = placements("rkpw081915", "front")
    assert sorted(front) == ["ground-led", "power-switch", "surge-led"]
    assert front["power-switch"]["ref"] == "common/rocker-switch@1"
    assert placements("rkpw081915", "rear")["input"]["ref"] == "startech/pdu-cord-5-15p@1"


@pytest.mark.parametrize("sku", ["pdu08c13h", "rkpw081915"])
def test_a_strip_that_switches_no_outlet_declares_no_outlet_state(sku):
    assert device(sku)["attrs"]["management"]["outlet-switching"] is False
    outlets = [p for i, p in placements(sku, SKUS[sku]["view"]).items() if i.startswith("outlet-")]
    assert outlets and not any("states" in p for p in outlets)


@pytest.mark.parametrize("ref", NEW_PARTS)
def test_a_new_part_says_where_each_figure_came_from_and_which_are_estimates(ref):
    c = contract(ref)
    assert "size" in c["provenance"]
    conf = c.get("size-confidence") or {}
    assert conf, f"{ref}: no size-confidence"
    assert set(conf.values()) <= {"drawing", "datasheet", "photo-measured", "measured", "estimated", "borrowed", "registry"}
    assert "ESTIMATED" in c["provenance"]["size"]


def test_the_cord_part_states_only_the_plug_on_its_far_end():
    """`attrs` equals the plug alone, so a stated length (or any other attribute) would fail it."""
    c = contract("startech/pdu-cord-5-15p@1")
    assert c["class"] == "inlet"
    assert c["attrs"] == {"plug": "nema-5-15p"}


@pytest.mark.parametrize("sku", ["8ns8-rack-mount-pdu", "rkpw081915"])
def test_the_rear_outlets_stand_in_one_row_8_7_mm_from_the_top_as_the_guide_draws_them(sku):
    """An independent literal: the guide's rear diagram puts the outlet blocks 9.3 to 35.8 mm below the body's top, so the part's
    placement (rotated 270, 13.5 mm below its origin) sits at 8.7. A drift of an outlet's position fails this."""
    ys = {p["at"][1] for i, p in placements(sku, "rear").items() if i.startswith("outlet-")}
    assert ys == {8.7}


def test_no_text_calls_the_switch_cover_hinged():
    """The guide says only "Remove Cover to Access Switch"; no document says hinged."""
    for p in [LIB / "components" / "startech" / "outlet-switch-cover" / "v1" / "contract.yaml",
              LIB / "devices" / "startech" / "8ns8-rack-mount-pdu" / "device.yaml"]:
        assert "hinged" not in p.read_text().lower(), p


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_a_view_no_document_shows_is_a_declared_gap(sku):
    gaps = device(sku)["gaps"]
    assert any(set(g["scope"]) >= {"top", "bottom", "left", "right"} for g in gaps)


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_exporter_writes_the_input_plug_and_every_outlet_the_drawing_places(sku):
    """The DCIM file the exporter wrote, not the source, carries the input's plug and the eight outlets."""
    model = SKUS[sku]["model"]
    exported = yaml.safe_load((LIB / "exports" / "netbox" / "device-types" / "StarTech.com" / f"{model}.yaml").read_text())
    assert [p["type"] for p in exported["power-ports"]] == [SKUS[sku]["plug"]]
    assert len(exported["power-outlets"]) == 8
    assert {o["power_port"] for o in exported["power-outlets"]} == {"input"}
    assert (LIB / "exports" / "nautobot" / "device-types" / "StarTech.com" / f"{model}.yaml").is_file()
