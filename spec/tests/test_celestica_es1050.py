"""Celestica ES1050: 16 x 2.5GbE + 32 x 1GbE, four SFP28, PoE++ on the -48CP only.

The ES1050 is its own device, not a listing of celestica/es1010: the hardware guide gives
it different ports (Front Panel Table 1), its own front figure, its own link-lamp
meaning, and the datasheet orders four part numbers of its own. These tests read the
device file; they state what the guide and the datasheet print.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
FOLDER = ROOT / "library" / "devices" / "celestica" / "es1050"
SPEC = ROOT / "spec" / "schemas"

from portrayal import capability as C

FACES = ("front", "rear", "left", "right", "top", "bottom")


@pytest.fixture(scope="module")
def dev():
    return yaml.safe_load((FOLDER / "device.yaml").read_text())


def placements(dev, view="front"):
    return (((dev["views"][view].get("components") or {}).get("placements")) or [])


def test_the_device_folder_exists_with_its_lock():
    assert (FOLDER / "device.yaml").is_file()
    assert (FOLDER / "device.lock.json").is_file()


def test_the_chassis_is_the_guides():
    # datasheet PHYSICAL DIMENSIONS: 43.4 x 438.2 x 371.6, 1U
    chassis = yaml.safe_load((FOLDER / "device.yaml").read_text())["chassis"]
    assert (chassis["width"], chassis["height"], chassis["depth"], chassis["ru"]) == (438.2, 43.4, 371.6, 1)


def test_port_counts_per_speed_are_the_guides(dev):
    groups = dev["groups"]
    by_group = {}
    for p in placements(dev):
        if p["ref"].startswith("common/rj45-ganged-eth") and p["id"].startswith("port-"):
            by_group.setdefault(p["group"], []).append(int(p["id"].split("-")[1]))
        if p["ref"] == "std/sfp-ganged@1":
            by_group.setdefault(p["group"], []).append(int(p["id"].split("-")[1]))
    speeds = {g: groups[g]["attrs"]["speed"] for g in by_group}
    count = {}
    for g, ids in by_group.items():
        count[speeds[g]] = count.get(speeds[g], 0) + len(ids)
    # guide Ports Tables 3 and 4: ports 1-16 2.5GbE-capable, 17-48 1GbE; four SFP28
    assert count == {"2.5g": 16, "1g": 32, "25g": 4}
    assert sorted(by_group["rj45-2p5g"]) == list(range(1, 17))
    assert sorted(by_group["rj45-1g"]) == list(range(17, 49))
    assert sorted(by_group["sfp28"]) == [49, 50, 51, 52]


def test_management_console_and_usb_are_present(dev):
    ids = {p["id"] for p in placements(dev)}
    assert {"mgmt", "mgmt-sfp", "console", "usb-1", "usb-2"} <= ids
    assert {"led-stat", "led-fan", "led-pwr", "led-alm"} <= ids
    usb = [p for p in placements(dev) if p["ref"] == "std/usb-a@1"]
    assert len(usb) == 2 and all(p["attrs"]["usb"] == "3.0" for p in usb)


def test_poe_is_on_the_cp_builds_only_and_is_class_8(dev):
    cfgs = dev["configurations"]
    for name, cfg in cfgs.items():
        has_poe = "PoE++" in cfg["description"]
        assert has_poe == ("48cp" in name), name
        assert ("48CP" in cfg["description"]) == has_poe, name
    poe = dev["attrs"]["features"]["poe"]
    assert "Type 4 Class 8" in poe and "90 W" in poe and "-48CP" in poe


def test_the_configurations_carry_the_datasheets_four_part_numbers(dev):
    got = {}
    for name, cfg in dev["configurations"].items():
        for pn in cfg.get("part-numbers") or {}:
            got[pn] = (cfg["airflow"], name)
    assert got == {
        "R4048-F90L2-A1": ("front-to-back", "48c-f2b"),
        "R4048-F91L2-A1": ("back-to-front", "48c-b2f"),
        "R4048-F90L3-A1": ("front-to-back", "48cp-f2b"),
        "R4048-F91L3-A1": ("back-to-front", "48cp-b2f"),
    }
    assert sum(1 for c in dev["configurations"].values() if c.get("default")) == 1
    assert dev["configurations"]["base"]["kind"] == "base"


def test_supplies_follow_the_rating_each_build_names(dev):
    # guide System Overview: ES1050-48C 2 x 550 W, ES1050-48CP 2 x 1600 W
    for name, cfg in dev["configurations"].items():
        if cfg["kind"] == "base":
            continue
        want = "celestica/psu-crps-1600-ac@1" if "48cp" in name else "celestica/psu-crps-550-ac@1"
        assert cfg["bays"] == {"psu-1": want, "psu-2": want}, name


def test_supply_references_resolve(dev):
    refs = set()
    for bay in dev["views"]["rear"]["components"]["bays"]:
        refs.update(bay["accepts"])
        refs.add(bay["default"])
    for cfg in dev["configurations"].values():
        refs.update((cfg.get("bays") or {}).values())
    for ref in refs:
        name, ver = ref.split("@")
        assert (ROOT / "library" / "components" / name / f"v{ver}" / "contract.yaml").is_file(), ref


def test_all_six_faces_exist_and_each_is_drawn_or_says_empty(dev):
    for face in FACES:
        view = dev["views"][face]
        drawn = bool(view.get("panel") or placements(dev, face) or (view.get("components") or {}).get("bays"))
        assert drawn or view.get("empty"), face
        if view.get("empty"):
            assert len(view["empty"].split()) > 10, face


def test_the_front_stripe_and_the_plate_are_the_es1050s(dev):
    decor = {d["id"]: d for d in dev["views"]["front"]["panel"]["decor"]}
    assert "green-stripe" in decor
    lug = [p for p in placements(dev) if p["id"] == "lug-tag"][0]
    assert lug["attrs"]["label"] == "ES1050"


def test_every_placement_names_its_group_and_every_group_its_term(dev):
    for face in FACES:
        for p in placements(dev, face):
            assert "group" in p and "rel-pos" in p, (face, p["id"])
    for name, g in dev["groups"].items():
        assert "term" in g and "index-origin" in g, name


def test_capability_level_is_four(dev):
    profiles = C.load_profiles(SPEC)
    cap, _ = C.assess(dev, profiles=profiles)
    assert cap["level"] == 4, cap.get("blocked")


def test_a_figure_the_documents_do_not_print_is_a_gap(dev):
    gaps = {g["what"] for g in dev["gaps"]}
    # no document names a supply part number, a 1G-port link-lamp colour or the lid and side geometry
    assert {"psu-part-numbers", "port-lamp-meaning-1g-ports", "side-top-bottom-geometry"} <= gaps
    # every estimated mark says where it came from
    # the side screws are estimated, and the provenance entry says so
    assert dev["provenance"]["sides-top-bottom"]["confidence"] == "estimated"
    assert all(len(placements(dev, face)) == 4 for face in ("left", "right"))
    for d in dev["views"]["top"]["panel"]["decor"]:
        assert d["confidence"] == "estimated" and d["source"], d["id"]
    assert dev["maturity"] != "verified"
