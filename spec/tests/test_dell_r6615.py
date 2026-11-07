"""The Dell PowerEdge R6615 (1U, one AMD EPYC socket), against Dell's Installation
and Service Manual (ISM) and Technical Guide (TG).

The device is `library/devices/dell/r6615`. Its figures come from the ISM: the
chassis table (table 10), the five front figures (1 to 5), the rear figures (6 to
9), the riser tables (16, 17, 97 and 98) and the interior view (figure 10). These
tests hold the shape the ISM states - the envelope, which fronts exist and how many
bays each has, which slots each riser configuration's rear carries and how Dell
numbers them, the supplies, the fans, heatsink and DIMM slots of the top view, and
the DCIM device types - so a later edit cannot move one without saying so.

The rear and top-view checks read `library/dist`, so run a build first, as
test_hides.py does; the DCIM check reads `library/exports`.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEV = LIB / "devices" / "dell" / "r6615" / "device.yaml"
DIST = LIB / "dist"
EXPORTS = LIB / "exports"


def _device():
    return yaml.safe_load(DEV.read_text())


def _contract(ref):
    """The component contract a `vendor/name@N` ref names."""
    vendor, rest = ref.split("/")
    name, ver = rest.split("@")
    return yaml.safe_load((LIB / "components" / vendor / name / f"v{ver}" / "contract.yaml").read_text())


def _bays(view):
    return _device()["views"][view]["components"]["bays"]


def _placements(view):
    return _device()["views"][view]["components"].get("placements", [])


# --- the envelope (ISM table 10) ----------------------------------------------------------------

def test_the_chassis_is_the_isms_434_by_42_8_by_ear_plus_rear_wall():
    ch = _device()["chassis"]
    assert (ch["width"], ch["height"], ch["ru"]) == (434.0, 42.8, 1)
    # ISM table 10: 22.0 from the front face to the ears without the bezel, then
    # 751.48 from the ears to the rear wall for the 4, 8 and 10 drive builds.
    assert ch["depth"] == pytest.approx(22.0 + 751.48, abs=0.05)


def test_the_front_is_the_482_6_rack_face_and_the_rear_is_the_434_body():
    views = _device()["views"]
    for name in ("front", "front-sff8", "front-lff4", "front-e3s14", "front-e3s16"):
        # the ears carry both control panels, so the face is 482.6 wide (ISM table 10:
        # 482.0 across the ears, 434.0 between them)
        assert views[name]["size"] == {"w": 482.6, "h": 42.8}, name
    assert views["rear"]["size"] == {"w": 434.0, "h": 42.8}
    assert views["top"]["size"] == {"w": 434.0, "h": 773.5}
    assert views["left"]["size"] == {"w": 773.5, "h": 42.8}


def test_the_depth_is_not_the_technical_guides_758_29_nor_the_spec_sheets_809_05():
    # the TG's overview gives 758.29, which no row of ISM table 10 agrees with, and
    # the spec sheet's 809.05 is the front face to the PSU handle (22.0 + 787.05)
    depth = _device()["chassis"]["depth"]
    assert abs(depth - 758.29) > 10 and abs(depth - 809.05) > 10


# --- the fronts (ISM figures 1 to 5) ------------------------------------------------------------

FRONTS = {
    # view -> (bay prefix, bays, group)
    "front": ("drive-", 10, "drives"),
    "front-sff8": ("drive-", 8, "drives"),
    "front-lff4": ("lff-drive-", 4, "drives-lff"),
    "front-e3s14": ("e3s-", 14, "drives-e3s"),
    "front-e3s16": ("e3s-", 16, "drives-e3s"),
}


@pytest.mark.parametrize("view", FRONTS)
def test_each_front_is_a_view_with_its_bay_count_and_numbering(view):
    prefix, count, group = FRONTS[view]
    bays = [b for b in _bays(view) if b["id"].startswith(prefix) and b.get("group") == group]
    assert len(bays) == count, view
    # numbered from 0, in the order the bays are listed
    assert [b["rel-pos"] for b in bays] == list(range(count))
    assert [b["id"] for b in bays] == [f"{prefix}{n}" for n in range(count)]


def test_the_two_and_a_half_inch_fronts_number_down_each_column():
    # the upper bay of a column is even and the lower is odd (the R660's numbering of
    # the same chassis; no R6615 document prints the numbers)
    for view in ("front", "front-sff8"):
        for b in _bays(view):
            if b["id"].startswith("drive-"):
                n = int(b["id"].split("-")[1])
                upper = b["at"][1] < 20
                assert upper == (n % 2 == 0), (view, b["id"])


def test_the_14_drive_e3s_front_ends_in_a_two_slot_filler():
    bays = {b["id"]: b for b in _bays("front-e3s14")}
    assert "e3s-13" in bays and "e3s-14" not in bays
    assert bays["e3s-filler-14"]["accepts"] == ["dell/e3s-filler-2slot-1u@1"]


def test_every_drive_bay_defaults_to_a_blank_and_the_bezel_hides_the_drives():
    for view, (prefix, count, group) in FRONTS.items():
        drives = [b for b in _bays(view) if b.get("group") == group]
        assert all("blank" in b["default"] for b in drives), view
        bezel = next(p for p in _placements(view) if p["id"] == "bezel")
        assert bezel["ref"] == "dell/bezel-1u-16g@1"
        assert bezel["hides"] == [b["id"] for b in drives], view


def test_the_3_5_inch_front_puts_the_vga_above_the_fourth_bay():
    vga = next(p for p in _placements("front-lff4") if p["id"] == "vga")
    fourth = next(b for b in _bays("front-lff4") if b["id"] == "lff-drive-3")
    centre = vga["at"][0] + 20.47 / 2
    assert fourth["at"][0] <= centre <= fourth["at"][0] + fourth["size"]["w"]
    assert vga["at"][1] + 11.4 <= fourth["at"][1] + 1.0


# --- the rear for each riser configuration (ISM tables 16, 17, 97 and 98) -----------------------

# configuration -> (the slots Dell numbers on the rear, the rear drive bays)
REAR = {
    0: ({}, set()),
    1: ({1, 2, 3}, set()),
    2: ({1, 2, 3}, set()),
    3: ({1, 2}, set()),
    4: ({1, 2}, set()),
    5: ({3}, set()),
    6: ({1, 2}, set()),
    7: ({1, 3}, {"e3s-0", "e3s-1"}),
    8: ({1, 2, 3}, set()),
}


def _configs():
    return _device()["configurations"]


def _active_bays(name):
    return [b for b in _device()["views"]["rear"]["components"]["bays"]
            if "only-in" not in b or name in b["only-in"]]


def _slots(name):
    """The slot numbers and rear drive ids the configuration's risers carry."""
    cfg = _configs()[name]
    slots, drives = set(), set()
    for bay in _active_bays(name):
        if not bay["id"].startswith("riser-"):
            continue
        ref = (cfg.get("bays") or {}).get(bay["id"]) or bay["default"]
        contract = _contract(ref)
        for sid in (contract.get("bays") or {}):
            if sid.startswith("slot-"):
                slots.add(int(sid.split("-")[1]))
            elif sid.startswith("e3s-"):
                drives.add(sid)
    return slots, drives


@pytest.mark.heavy
@pytest.mark.parametrize("rc", REAR)
def test_each_riser_configurations_rear_has_the_slots_the_isms_table_lists(rc):
    names = [n for n in _configs() if re.search(rf"-rc{rc}-", n) and _configs()[n]["kind"] == "orderable"]
    assert names, f"no build for riser configuration {rc}"
    want, drives = REAR[rc]
    for name in names:
        slots, got_drives = _slots(name)
        assert slots == set(want), name
        assert got_drives == drives, name


def test_the_slots_are_numbered_as_dell_prints_them_on_the_rear_face():
    # the cages print the numbers; read them off the built rear of each configuration
    # (the Gen5 cages print a number and 'GEN 5' strip over each Gen5 slot)
    cfgs = {c["name"]: c for c in _configs_json()}

    def printed(rc):
        name = next(n for n in cfgs if re.search(rf"-rc{rc}-", n) and cfgs[n]["kind"] == "orderable")
        svg = DIST / cfgs[name]["files"]["rear"]
        texts = [t.text.strip() for t in ET.parse(svg).iter()
                 if t.tag.endswith("text") and (t.text or "").strip() in {"1", "2", "3", "4"}]
        return name, {d: texts.count(d) for d in "1234"}

    # the supplies and the LOM window print 1 and 2 twice each (the chassis print);
    # the risers' cages print the rest, one number a slot
    _, base = printed(0)
    assert base == {"1": 2, "2": 2, "3": 0, "4": 0}
    for rc, (slots, _) in REAR.items():
        name, got = printed(rc)
        for n in "1234":
            assert got[n] == base[n] + (1 if int(n) in slots else 0), \
                f"{name}: slot {n} printed {got[n] - base[n]} times, want {1 if int(n) in slots else 0}"


def _configs_json():
    import json
    path = DIST / "r6615.configs.json"
    assert path.exists(), "library/dist has no r6615.configs.json: these read the build, so run ./build.sh first"
    return json.loads(path.read_text())["configs"]


def test_a_rear_slot_takes_the_connector_width_and_processor_the_ism_gives():
    # ISM table 16: every slot is on processor 1, R2A's two slots are x8 Gen4,
    # R2T's are x16 Gen5 and x16 Gen4, the full-height R1Q and R4P are Gen5
    want = {
        "r6615-riser-2a": {"slot-1": (8, 4), "slot-2": (8, 4)},
        "r6615-riser-2t": {"slot-1": (16, 5), "slot-2": (16, 4)},
        "r6615-riser-2u": {"slot-1": (16, 5)},
        "r6615-riser-3a": {"slot-3": (16, 4)},
        "r6615-riser-3p": {"slot-3": (16, 5)},
        "r6615-riser-3s": {"slot-3": (16, 5)},
        "r6615-riser-1q": {"slot-1": (16, 5)},
        "r6615-riser-4p": {"slot-2": (16, 5)},
    }
    for name, slots in want.items():
        bays = _contract(f"dell/{name}@1")["bays"]
        for sid, (lanes, gen) in slots.items():
            slot = bays[sid]["slot"]
            assert (slot["lanes"], slot["generation"], slot["processor"]) == (lanes, gen, 1), (name, sid)


def test_the_rear_drive_modules_are_the_ism_s_2_5_inch_and_e3s_pairs():
    rear2 = _configs()["sff10-rc5-3p-rear2"]
    ids = {b["id"] for b in _active_bays("sff10-rc5-3p-rear2") if b["id"].startswith("rear-drive")}
    assert ids == {"rear-drive-0", "rear-drive-1"} and rear2["kind"] == "orderable"
    for name in ("lff4-rc7-2u3s", "sff10-rc7-2u3s"):
        assert _slots(name)[1] == {"e3s-0", "e3s-1"}


def test_a_rear_drive_module_is_paired_only_with_the_fronts_the_tg_lists():
    names = set(_configs())
    assert {n for n in names if n.endswith("rc7-2u3s")} == {"lff4-rc7-2u3s", "sff10-rc7-2u3s"}
    assert {n for n in names if n.endswith("rear2")} == {"sff10-rc5-3p-rear2"}


def test_every_front_has_a_build_for_every_riser_configuration_but_the_rear_storage_ones():
    names = set(_configs())
    for front in ("lff4", "sff8", "sff10", "e3s14", "e3s16"):
        for rc in (0, 1, 2, 3, 4, 5, 6, 8):
            assert any(n.startswith(f"{front}-rc{rc}-") for n in names), (front, rc)


# --- the supplies (ISM tables 13 and 14) --------------------------------------------------------

def test_the_supply_bays_accept_the_four_60mm_ac_supplies_the_ism_lists():
    want = {"dell/psu-1400w-ac-60mm@1", "dell/psu-1100w-ac-60mm@1",
            "dell/psu-800w-ac-60mm@1", "dell/psu-700w-ac-60mm@1"}
    bays = {b["id"]: b for b in _bays("rear") if b["id"].startswith("psu-")}
    assert set(bays) == {"psu-1", "psu-2"}
    for b in bays.values():
        assert set(b["accepts"]) == want


# --- the top view (ISM figures 10 and 17, tables 15 and 19) -------------------------------------

def test_the_top_view_has_four_fans_one_heatsink_and_twelve_dimm_slots_named_a1_to_a12():
    top = _device()["views"]["top"]["components"]
    fans = [b for b in top["bays"] if b["id"].startswith("fan-")]
    dimms = [b["id"] for b in top["bays"] if b["id"].startswith("dimm-")]
    sinks = [p for p in top["placements"] if p["id"].startswith("heatsink")]
    assert len(fans) == 4 and len(sinks) == 1
    assert sorted(dimms) == sorted(f"dimm-a{n}" for n in range(1, 13))
    # ISM figure 17: the memory label's order, left to right, six either side of the processor
    ordered = [d.split("-")[1].upper() for d in sorted(dimms, key=lambda i: next(
        b["at"][0] for b in top["bays"] if b["id"] == i))]
    assert ordered == ["A12", "A8", "A10", "A4", "A6", "A2", "A1", "A5", "A3", "A9", "A7", "A11"]


def test_the_built_top_view_carries_them_and_the_covers_over_them():
    path = DIST / "r6615.top.svg"
    assert path.exists(), "library/dist has no r6615.top.svg: these read the build, so run ./build.sh first"
    paths = {n.get("data-path") for n in ET.parse(path).iter() if n.get("data-path")}
    for want in ["heatsink-1", "system-cover", "backplane-cover", "fan-bracket", "system-board",
                 *[f"fan-{n}" for n in range(1, 5)], *[f"dimm-a{n}" for n in range(1, 13)]]:
        assert want in paths, want


# --- the DCIM device types ----------------------------------------------------------------------

@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_dcim_device_types_export_one_rack_unit_and_full_depth(target):
    found = sorted((EXPORTS / target / "device-types" / "Dell").glob("PowerEdge R6615 *.yaml"))
    assert found, f"{target} has no PowerEdge R6615 device type: run dcim_export.py --device r6615"
    for path in found:
        doc = yaml.safe_load(path.read_text())
        assert doc["manufacturer"] == "Dell" and doc["model"].startswith("PowerEdge R6615 ")
        assert doc["u_height"] == 1.0 and doc["is_full_depth"] is True, path.name
    # one for each front at least: the configuration names lead with the front
    for front in ("lff4", "sff8", "sff10", "e3s14", "e3s16"):
        assert any(f" {front}-rc" in p.name for p in found), (target, front)
