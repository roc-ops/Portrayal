"""The Opengear OM1300 operations managers: four SKUs, two sizes (four and eight
serial jacks with as many switch jacks) and a cellular rear on the -C models.

What is true of the library once they are in: each SKU has its own device, the
serial and switch blocks differ by size as the data sheet and the photographs
say, the cellular rear reuses the SIM slot and antenna jacks the CM8000 uses,
every position read off a photograph is declared an estimate with its method,
and the serial lines are stated as console server ports.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "opengear"

# name: (model, serial and switch jacks, cellular, depth, power-max-w)
SKUS = {
    "om1304-4e": ("OM1304-4E", 4, False, 177.0, 32),
    "om1304-4e-c": ("OM1304-4E-C", 4, True, 189.0, 38),
    "om1308-8e": ("OM1308-8E", 8, False, 177.0, 32),
    "om1308-8e-c": ("OM1308-8E-C", 8, True, 189.0, 38),
}


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(name, view):
    d = device(name)
    return (d["views"][view].get("components") or {}).get("placements") or []


def refs(name, view, ref):
    return [p for p in placements(name, view) if p["ref"] == ref]


def block(name, group):
    return sorted((p for p in placements(name, "front") if p.get("group") == group),
                  key=lambda p: p["rel-pos"])


@pytest.mark.parametrize("name", SKUS)
def test_each_sku_is_a_device_of_its_own(name):
    model, _, _, depth, pmax = SKUS[name]
    d = device(name)
    assert d["manufacturer"] == "Opengear" and d["model"] == model
    assert d["name"] == name
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (220.0, 44.0, depth, 1)
    assert d["attrs"]["power"]["power-max-w"] == pmax


@pytest.mark.parametrize("name", SKUS)
def test_all_six_faces_are_present(name):
    assert set(device(name)["views"]) == {"front", "rear", "top", "bottom", "left", "right"}


@pytest.mark.parametrize("name", SKUS)
def test_serial_block_has_the_skus_ports_numbered_as_printed(name):
    _, n, _, _, _ = SKUS[name]
    serial = block(name, "serial")
    assert [p["id"] for p in serial] == [f"serial-{i}" for i in range(1, n + 1)]
    assert {p["ref"] for p in serial} == {"std/rj45-ganged@2"}
    # odd numbers on the upper row, even on the lower: the printed 1 3 / 2 4
    for p in serial:
        upper = int(p["id"].split("-")[1]) % 2 == 1
        assert (p.get("rotate") == 180) == upper


@pytest.mark.parametrize("name", SKUS)
def test_serial_lines_are_console_server_ports(name):
    groups = device(name)["groups"]
    assert groups["serial"]["attrs"] == {"media": "rj45-serial", "role": "console-server"}
    assert groups["console"]["attrs"] == {"media": "usb-c"}


@pytest.mark.parametrize("name", SKUS)
def test_switch_block_matches_the_serial_block_in_size(name):
    _, n, _, _, _ = SKUS[name]
    switch = block(name, "switch")
    assert [p["id"] for p in switch] == [f"switch-{i}" for i in range(1, n + 1)]
    assert {p["ref"] for p in switch} == {"common/rj45-ganged-eth@1"}
    serial = block(name, "serial")
    # the two blocks share their rows
    assert {p["at"][1] for p in switch} == {p["at"][1] for p in serial}
    # the eight-jack block is two housings of four, with a gap between them
    xs = sorted({p["at"][0] for p in switch})
    gaps = {round(b - a, 2) for a, b in zip(xs, xs[1:])}
    assert gaps == ({13.97} if n == 4 else {13.97, 17.23})


@pytest.mark.parametrize("name", SKUS)
def test_each_network_port_is_a_combo_with_both_halves_placed(name):
    ids = {p["id"] for p in placements(name, "front")}
    assert {"net1-sfp", "net2-sfp", "net1-rj45", "net2-rj45"} <= ids


@pytest.mark.parametrize("name", SKUS)
def test_front_has_the_usb_console_erase_and_six_lamps(name):
    front = placements(name, "front")
    assert len([p for p in front if p["ref"] == "std/usb-a@1"]) == 2
    console = [p for p in front if p["ref"] == "std/usb-c@1"]
    assert len(console) == 1 and console[0]["attrs"]["role"] == "console"
    assert [p["id"] for p in front if p["ref"] == "common/reset-button@1"] == ["erase"]
    assert len([p for p in front if p["ref"] == "common/led-dot@1"]) == 6


@pytest.mark.parametrize("name", SKUS)
def test_rear_has_two_12vdc_jacks_and_no_cable_retention_openings(name):
    jacks = refs(name, "rear", "common/dc-barrel@1")
    assert [p["id"] for p in jacks] == ["dc-in-1", "dc-in-2"]
    decor = device(name)["views"]["rear"]["panel"]["decor"]
    assert not [e for e in decor if e["kind"] == "cable-retention-insert"]


@pytest.mark.parametrize("name", SKUS)
def test_cellular_rear_adds_four_antenna_jacks_and_two_sim_slots(name):
    _, _, cellular, _, _ = SKUS[name]
    sma = refs(name, "rear", "common/sma-jack@1")
    sim = refs(name, "rear", "opengear/sim-slot-4ff@1")
    assert (len(sma), len(sim)) == ((4, 2) if cellular else (0, 0))
    if cellular:
        assert [p["id"] for p in sma] == ["wwan1", "wwan2", "wwan3", "wwan4"]
        assert [p["id"] for p in sim] == ["sim1", "sim2"]


@pytest.mark.parametrize("name", SKUS)
def test_positions_read_off_a_photograph_are_declared_estimates_with_the_method(name):
    prov = device(name)["provenance"]
    for key in ("front-layout", "rear-layout"):
        assert prov[key]["confidence"] == "estimated"
        assert "px/mm" in prov[key]["note"]


@pytest.mark.parametrize("name", SKUS)
def test_no_rack_kit_is_invented_where_no_document_dimensions_one(name):
    d = device(name)
    assert "ears" not in d["chassis"] and "kits" not in d["chassis"]
    assert any(g["what"] == "rack-kit" for g in d["gaps"])


@pytest.mark.parametrize("name", SKUS)
def test_no_login_is_written_into_a_device_file(name):
    for fname in ("layout.yaml", "device.yaml"):
        text = (DEVICES / name / fname).read_text().lower()
        assert "password" not in text and "192.168" not in text
