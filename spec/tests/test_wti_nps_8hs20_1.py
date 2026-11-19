"""The WTI NPS-8HS20-1 network power switch.

The maker's specification table gives the size, the outlets and the breakers, and the NPS Series Hardware Guide draws
the front and the back panel (figures 2.3 and 2.4). One angled photograph of the unit is held. What is true of the library
once the device is in:

  - the model is a device of the registered maker, at the size the table gives for the 8-outlet 1U row;
  - the rear carries one C20 inlet that feeds eight NEMA 5-15R outlets, A1 to A8, and one Ethernet jack;
  - the front carries the RJ45 set-up port, eight output lamps and two breakers, one for A1 to A4 and one for A5 to A8;
  - every face is drawn, or says why it is not;
  - the part number belongs to this device alone, and the estimates and the photograph's limits are declared.

These read the device source and the registry. They read no library/dist and render nothing.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
NAME = "nps-8hs20-1"


def device():
    return yaml.safe_load((LIB / "devices" / "wti" / NAME / "device.yaml").read_text())


def placements(view):
    comps = device()["views"][view].get("components") or {}
    return {p["id"]: p for p in (comps.get("placements") or [])}


def decor(view):
    return {d["id"]: d for d in (device()["views"][view].get("panel") or {}).get("decor") or []}


def test_the_model_is_a_device_of_the_maker_at_the_size_the_table_gives():
    d = device()
    assert (d["manufacturer"], d["model"]) == ("WTI", "NPS-8HS20-1")
    ch = d["chassis"]
    assert (ch["width"], ch["height"], ch["depth"], ch["ru"]) == (482.6, 44.45, 220.98, 1)


def test_the_rear_has_one_inlet_feeding_eight_nema_outlets_and_one_ethernet_jack():
    ps = placements("rear")
    refs = [p["ref"] for p in ps.values()]
    assert refs.count("std/c20-inlet@1") == 1
    assert refs.count("std/nema-5-15r@1") == 8
    assert refs.count("common/rj45-eth@1") == 1
    inlet = next(i for i, p in ps.items() if p["ref"] == "std/c20-inlet@1")
    outlets = [p for p in ps.values() if p["ref"] == "std/nema-5-15r@1"]
    assert {p["fed-by"] for p in outlets} == {inlet}
    assert sorted(p["rel-pos"] for p in outlets) == list(range(1, 9))


def test_the_outlets_sit_in_one_row_left_to_right_in_the_order_of_their_numbers():
    outlets = sorted((p for p in placements("rear").values() if p["ref"] == "std/nema-5-15r@1"), key=lambda p: p["rel-pos"])
    xs = [p["at"][0] for p in outlets]
    assert xs == sorted(xs)
    assert len({p["at"][1] for p in outlets}) == 1


def test_the_front_has_the_setup_port_eight_output_lamps_and_two_breakers():
    assert [p["ref"] for p in placements("front").values()] == ["std/rj45-ganged@2"]
    lamps = [d for i, d in decor("front").items() if i.startswith("lamp-out-")]
    assert len(lamps) == 8
    breakers = [i for i, d in decor("front").items() if d["kind"] == "breaker"]
    assert sorted(breakers) == ["breaker-a1-a4", "breaker-a5-a8"]


def test_every_face_is_drawn_or_says_why_it_is_not():
    views = device()["views"]
    assert sorted(views) == ["bottom", "front", "left", "rear", "right", "top"]
    for name, v in views.items():
        drawn = (v.get("components") or {}).get("placements") or (v.get("panel") or {}).get("decor")
        assert drawn or len(str(v.get("empty", ""))) > 40, f"{name}: neither drawn nor an `empty:` sentence"


def test_the_estimates_and_the_limits_of_the_photograph_are_declared():
    d = device()
    prov = d["provenance"]
    assert prov["method"]["confidence"] == "estimated"
    assert "NO CONNECTOR DIMENSION" in prov["method"]["note"]
    assert prov["colour"]["confidence"] == "photo-measured"
    gaps = {g["what"] for g in d["gaps"]}
    assert {"straight-on-photographs", "breaker-size", "sides"} <= gaps


def test_the_part_number_belongs_to_this_device_alone():
    holders = [p.parent.name for p in sorted((LIB / "devices").glob("*/*/device.yaml"))
               if re.search(r"^\s+NPS-8HS20-1:", p.read_text(), re.M)]
    assert holders == [NAME]
