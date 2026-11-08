"""The Opengear CM8100-10G console managers with USB-C serial ports: two SKUs,
the 16 and the 48 port, each with a front and a rear drawn from its own
photographs.

What is true of the library once they are in: each SKU is a device of its own,
the serial block, the USB-C serial ports and the dual AC inlets are as the data
sheet and the photographs say, every position read off a photograph is declared
an estimate with its method, the envelope the data sheet does not give for the
-USB models is declared borrowed, and no rack kit is invented.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "opengear"
EXPORTS = ROOT / "library" / "exports"

# name: (model, serial ports, power-max-w the data sheet states or None)
SKUS = {
    "cm8116-10g-usb": ("CM8116-10G-USB", 16, None),
    "cm8148-10g-usb": ("CM8148-10G-USB", 48, 48),
}


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(name, view):
    d = device(name)
    return (d["views"][view].get("components") or {}).get("placements") or []


def refs(name, view, ref):
    return [p for p in placements(name, view) if p["ref"] == ref]


@pytest.mark.parametrize("name", SKUS)
def test_each_sku_is_a_device_of_its_own(name):
    model, _, _ = SKUS[name]
    d = device(name)
    assert d["manufacturer"] == "Opengear" and d["model"] == model
    assert d["name"] == name
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"], c["power"]) == (440.0, 44.0, 265.0, 1, "ac")


@pytest.mark.parametrize("name", SKUS)
def test_all_six_faces_are_present(name):
    assert set(device(name)["views"]) == {"front", "rear", "top", "bottom", "left", "right"}


@pytest.mark.parametrize("name", SKUS)
def test_serial_block_has_the_skus_ports_numbered_as_printed(name):
    _, n, _ = SKUS[name]
    serial = [p for p in placements(name, "front") if p.get("group") == "serial"]
    assert [p["id"] for p in sorted(serial, key=lambda p: p["rel-pos"])] == [f"serial-{i}" for i in range(1, n + 1)]
    assert {p["ref"] for p in serial} == {"std/rj45-ganged@2"}
    assert all(p["attrs"]["media"] == "rj45-serial" for p in serial)
    # odd numbers on the upper row, even on the lower: the printed 1 3 / 2 4
    for p in serial:
        upper = int(p["id"].split("-")[1]) % 2 == 1
        assert (p.get("rotate") == 180) == upper


@pytest.mark.parametrize("name", SKUS)
def test_the_serial_lines_are_console_server_ports(name):
    attrs = device(name)["groups"]["serial"]["attrs"]
    assert attrs["media"] == "rj45-serial" and attrs["role"] == "console-server"


@pytest.mark.parametrize("name", SKUS)
def test_front_has_two_sfp_plus_cages_and_two_rj45_ports(name):
    sfp = refs(name, "front", "std/sfp@1")
    assert [p["id"] for p in sfp] == ["net1-sfp", "net2-sfp"]
    groups = device(name)["groups"]
    assert groups["net-sfp"]["attrs"]["speed"] == "10g"
    rj45 = [p for p in refs(name, "front", "common/rj45-eth@1") if p["group"] == "net-rj45"]
    assert [p["id"] for p in rj45] == ["net3-rj45", "net4-rj45"]
    assert groups["net-rj45"]["attrs"]["speed"] == "1g"


@pytest.mark.parametrize("name", SKUS)
def test_front_has_the_rj45_console_two_usb_erase_and_four_lamps(name):
    front = placements(name, "front")
    console = [p for p in front if p.get("group") == "console"]
    assert len(console) == 1 and console[0]["attrs"] == {"media": "rj45-serial", "role": "console"}
    assert len([p for p in front if p["ref"] == "std/usb-a@1"]) == 2
    assert [p["id"] for p in front if p["ref"] == "common/reset-button@1"] == ["erase"]
    assert len([p for p in front if p["ref"] == "common/led-dot@1"]) == 4


@pytest.mark.parametrize("name", SKUS)
def test_rear_has_eight_usb_c_serial_ports_and_two_ac_inlets(name):
    usb = refs(name, "rear", "std/usb-c@1")
    assert [p["id"] for p in usb] == [f"usb-c-{c}" for c in "abcdefgh"]
    inlets = refs(name, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]
    assert device(name)["groups"]["inlets"]["attrs"]["input-voltage"] == "100-240 V AC"


@pytest.mark.parametrize("name", SKUS)
def test_positions_read_off_a_photograph_are_declared_estimates_with_the_method(name):
    prov = device(name)["provenance"]
    for key in ("front-layout", "rear-layout"):
        assert prov[key]["confidence"] == "estimated"
        assert "px/mm" in prov[key]["note"]


@pytest.mark.parametrize("name", SKUS)
def test_the_envelope_the_data_sheet_does_not_give_for_the_usb_models_is_declared_borrowed(name):
    d = device(name)
    assert d["provenance"]["chassis"]["confidence"] == "borrowed"
    assert any(g["what"] == "usb-model-envelope" for g in d["gaps"])
    assert "weight-kg" not in (d.get("attrs") or {}).get("physical", {})


@pytest.mark.parametrize("name", SKUS)
def test_power_draw_is_stated_only_where_the_data_sheet_states_it(name):
    _, _, watts = SKUS[name]
    power = (device(name).get("attrs") or {}).get("power") or {}
    assert power.get("power-max-w") == watts


@pytest.mark.parametrize("name", SKUS)
def test_no_rack_kit_is_invented_where_no_document_dimensions_one(name):
    d = device(name)
    assert "ears" not in d["chassis"] and "kits" not in d["chassis"]
    assert any(g["what"] == "rack-kit" for g in d["gaps"])


@pytest.mark.parametrize("name", SKUS)
@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_exports_list_each_serial_line_as_a_console_server_port(name, target):
    model, n, _ = SKUS[name]
    doc = yaml.safe_load((EXPORTS / target / "device-types" / "Opengear" / f"{model}.yaml").read_text())
    assert [r["name"] for r in doc["console-server-ports"]] == [f"serial-{i}" for i in range(1, n + 1)]
    assert {r["type"] for r in doc["console-server-ports"]} == {"rj-45"}
