"""The Raritan PXO compact PDU, both SKUs, and the parts it needed that the library did not hold.

PXO-2401CR carries four locking IEC C13 outlets and PXO-2402R four NEMA 5-20R outlets; both take a C20 inlet at one end of the
outlet face and share one controller face (two Ethernet jacks, a console jack, a sensor jack, a USB-B and a USB-A jack, a reset
button, a colour display and four buttons). What is true of the library once they are in:

  - each SKU is a device of the maker, 220 x 44 x 133 mm as the data sheet gives them, with six views;
  - each outlet is a part that presents the interface its plug mates, and the locking C13 outlets each have their release button;
  - the USB-B jack presents a registered interface and a generic plug mates it, both declaring the figures no document gives;
  - the controller face carries every port, lamp and button the maker's pictures show, each a part;
  - the maker is registered.

These read the contracts and the device sources. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMAS = ROOT / "spec" / "schemas"

SKUS = {
    "pxo-2401cr": dict(model="PXO-2401CR", outlet="std/c13-outlet@1", locking=True),
    "pxo-2402r": dict(model="PXO-2402R", outlet="std/nema-5-20r@1", locking=False),
}
VIEWS = ["front", "rear", "top", "bottom", "left", "right"]
NEW_PARTS = [
    "raritan/pxo-usb-b@1",
    "generic/usb-b-plug@1",
    "raritan/pxo-lock-button@1",
    "raritan/pxo-lcd@1",
    "raritan/pxo-button@1",
]


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device(sku):
    return yaml.safe_load((LIB / "devices" / "raritan" / sku / "device.yaml").read_text())


def placements(sku, view):
    comps = (device(sku)["views"][view].get("components") or {})
    return {p["id"]: p for p in (comps.get("placements") or [])}


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_sku_is_a_device_of_the_maker_the_size_the_data_sheet_gives(sku):
    d = device(sku)
    assert (d["manufacturer"], d["model"]) == ("Raritan", SKUS[sku]["model"])
    assert (d["chassis"]["width"], d["chassis"]["height"], d["chassis"]["depth"]) == (220, 44, 133)


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_all_six_views_are_there_and_a_bare_one_says_what_was_searched(sku):
    views = device(sku)["views"]
    assert sorted(views) == sorted(VIEWS)
    for name, v in views.items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{sku} {name}: neither drawn nor an `empty:` sentence"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_four_outlets_and_a_c20_inlet_stand_on_the_outlet_face(sku):
    rear = placements(sku, "rear")
    outlets = {i: p for i, p in rear.items() if i.startswith("outlet-")}
    assert sorted(outlets) == ["outlet-1", "outlet-2", "outlet-3", "outlet-4"]
    assert {p["ref"] for p in outlets.values()} == {SKUS[sku]["outlet"]}
    assert rear["input"]["ref"] == "std/c20-inlet@1"


def test_each_locking_c13_outlet_has_its_release_button_and_the_nema_ones_have_none():
    rear = placements("pxo-2401cr", "rear")
    buttons = {p["for"] for p in rear.values() if p["ref"] == "raritan/pxo-lock-button@1"}
    assert buttons == {f"outlet-{n}" for n in range(1, 5)}
    assert not [p for p in placements("pxo-2402r", "rear").values() if p["ref"] == "raritan/pxo-lock-button@1"]


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_each_outlet_has_its_lamp(sku):
    rear = placements(sku, "rear")
    lamps = {p["for"] for p in rear.values() if p["ref"] == "common/led-dot@1"}
    assert lamps == {f"outlet-{n}" for n in range(1, 5)}


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_controller_face_carries_every_port_and_button_the_pictures_show(sku):
    front = placements(sku, "front")
    refs = {i: p["ref"] for i, p in front.items()}
    assert refs["usb-b"] == "raritan/pxo-usb-b@1"
    assert refs["usb-a"] == "std/usb-a@1"
    assert {refs[i] for i in ("sensor", "console")} == {"std/rj45@2"}
    assert {refs[i] for i in ("eth-1", "eth-2")} == {"common/rj45-eth@1"}
    assert refs["reset"] == "common/reset-button@1"
    assert refs["display"] == "raritan/pxo-lcd@1"
    assert sorted(i for i, r in refs.items() if r == "raritan/pxo-button@1") == ["button-back", "button-down", "button-ok", "button-up"]


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_console_jack_is_stated_as_one_and_the_sensor_jack_is_not(sku):
    front = placements(sku, "front")
    assert front["console"]["attrs"]["role"] == "console"
    assert front["console"]["attrs"]["media"] == "rj45-serial"
    assert (front["sensor"].get("attrs") or {}).get("role") != "console"


@pytest.mark.parametrize("sku", sorted(SKUS))
def test_the_outlets_are_named_as_the_unit_prints_them(sku):
    rules = {r["physical"]: r for r in device(sku)["interfaces"]}
    assert rules["outlet-{n}"]["name"] == "{n}"
    assert rules["outlet-{n}"]["range"] == "1-4"


@pytest.mark.parametrize("sku,left_to_right", [("pxo-2401cr", ["1", "2", "3", "4"]), ("pxo-2402r", ["4", "3", "2", "1"])])
def test_the_numerals_run_the_way_each_unit_prints_them_and_each_sits_over_its_own_outlet(sku, left_to_right):
    """The data sheet photographs print 1 to 4 on the PXO-2401CR and 4 to 1 on the PXO-2402R, left to right."""
    d = device(sku)
    marks = sorted(d["views"]["rear"]["silkscreen"], key=lambda s: s["at"][0])
    assert [m["text"] for m in marks] == left_to_right
    outlets = placements(sku, "rear")
    for m in marks:
        assert m["for"] == f"outlet-{m['text']}"
        assert abs(m["at"][0] - outlets[m["for"]]["at"][0]) < 40.0
    xs = [outlets[m["for"]]["at"][0] for m in marks]
    assert xs == sorted(xs)


def test_the_usb_b_jack_presents_a_registered_interface_and_a_generic_plug_mates_it():
    keys = yaml.safe_load((SCHEMAS / "connectors.yaml").read_text())["interfaces"]
    assert "usb-b" in keys
    assert contract("raritan/pxo-usb-b@1")["interface"] == "usb-b"
    assert contract("generic/usb-b-plug@1")["mates"] == "usb-b"


@pytest.mark.parametrize("ref", NEW_PARTS)
def test_a_new_part_says_where_each_figure_came_from_and_which_are_estimates(ref):
    c = contract(ref)
    assert "size" in c["provenance"]
    conf = c.get("size-confidence") or {}
    assert conf, f"{ref}: no size-confidence"
    assert {v for v in conf.values()} <= {"drawing", "datasheet", "photo-measured", "measured", "estimated", "borrowed", "registry"}


def test_the_two_figures_no_document_gives_are_declared_estimated():
    assert set(contract("raritan/pxo-lock-button@1")["size-confidence"].values()) == {"estimated"}
    assert set(contract("generic/usb-b-plug@1")["size-confidence"].values()) <= {"estimated", "borrowed"}


def test_the_maker_is_registered():
    vendors = yaml.safe_load((SCHEMAS / "vendors.yaml").read_text())
    assert vendors["vendors"]["raritan"]["display"] == "Raritan"
