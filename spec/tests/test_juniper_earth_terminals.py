"""The earthing terminals of 23 Juniper switches are placed parts a lug lands on, not panel art.

Twenty-two switches drew their earthing terminal as panel decor (two holes, or one stud), so nothing a ground lug
could land on was placed. Each is now one placement of a part that presents a lug seat: a pair of bare tapped holes on
the pitch of the lug the guide names (a two-hole lug lands across them, a ring lug still landing on either), or, on the
two EX2300 MP models, the one M4 screw the guide says is provided. The QFX5210-64C's plate is the same, as a pair host of
its own. The holes stay bare, as the photographs show them. The pitch is never stated by the guides, so every pair
carries a declared gap and a provenance note that says how it was read.

This module pins each switch's placement, what the decor became, the gap and the note, the five new components, the
plate, and that the records file holds no row for the plate. The census of lug seats is pinned in test_occupant_turn.py.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RECORDS = LIB / "conformance-exceptions.yaml"

H58_M5 = "common/ground-hole-pair-5-8-m5@1"
H58_1032 = "common/ground-hole-pair-5-8-10-32@1"
H34_1032 = "common/ground-hole-pair-3-4-10-32@1"
M4 = "common/ground-screw-m4@1"

# device -> {view: (placement id, host, at, rotate)}: the host stands on the midpoint of the two holes (or on the
# centre of the one ring) that the decor drew
PLACED = {
    "ex2200-24p": {"rear": ("ground-pair", H34_1032, [44.362, 8.287], None)},
    "ex2200-24t": {"rear": ("ground-pair", H34_1032, [44.362, 8.287], None),
                   "rear-dc": ("ground-pair", H34_1032, [44.362, 8.287], None)},
    "ex2200-48p": {"rear": ("ground-pair", H34_1032, [44.362, 8.287], None)},
    "ex2200-48t": {"rear": ("ground-pair", H34_1032, [44.362, 8.287], None)},
    "ex2200-c-12p": {"rear": ("ground-pair", H34_1032, [16.262, 29.487], None)},
    "ex2200-c-12t": {"rear": ("ground-pair", H34_1032, [16.262, 29.487], None)},
    "ex2300-24mp": {"rear": ("earth-screw", M4, [216.3, 12.4], None)},
    "ex2300-48mp": {"rear": ("earth-screw", M4, [419.6, 16.3], None)},
    "ex2300-24p": {"rear": ("ground-pair", H58_1032, [59.3995, 5.387], None)},
    "ex2300-24t": {"rear": ("ground-pair", H58_1032, [59.3995, 5.387], None),
                   "rear-dc": ("ground-pair", H58_1032, [59.3995, 5.387], None)},
    "ex2300-48p": {"rear": ("ground-pair", H58_1032, [59.3995, 5.387], None)},
    "ex2300-48t": {"rear": ("ground-pair", H58_1032, [59.3995, 5.387], None)},
    "ex2300-c-12p": {"rear": ("ground-pair", H58_1032, [23.5995, 30.987], None)},
    "ex2300-c-12t": {"rear": ("ground-pair", H58_1032, [23.5995, 30.987], None)},
    "ex4100-f-24p": {"rear": ("ground-pair", H58_M5, [59.6125, 5.6], None)},
    "ex4100-f-24t": {"rear": ("ground-pair", H58_M5, [59.4125, 5.7], None)},
    "ex4100-f-48p": {"rear": ("ground-pair", H58_M5, [59.6125, 5.6], None)},
    "ex4100-f-48t": {"rear": ("ground-pair", H58_M5, [59.4125, 5.7], None)},
    "ex4100-h-12mp": {"front": ("ground-pair", H58_M5, [90.0625, 110.3], 90)},
    "ex4100-h-24f": {"rear": ("ground-pair", H58_M5, [419.2625, 12.85], 90)},
    "ex4100-h-24mp": {"rear": ("ground-pair", H58_M5, [21.8625, 12.9], 90)},
    "qfx5220-128c": {"rear": ("ground-pair", H58_1032, [17.9995, 149.937], None)},
}
# decor kinds the L197 list names for an earthing point: none may be left on these devices
EARTH_KINDS = {"earth-hole", "earth-stud", "earth-ring", "earthing-terminal"}
# what the decor that frames the part is called now, where it was renamed
RENAMED = {"ex4100-h-12mp": {"earth-ring-1": "earth-boss", "earth-ring-2": "earth-boss"},
           "qfx5220-128c": {"pad-earth": "earth-plate"}}
# the bare hole -> (the thread's nominal diameter)
HOLES = {"common/ground-hole-m5@1": 5.0, "common/ground-hole-10-32@1": 4.826}
# the pair host -> (interface, pitch, its hole, the lug that mates it)
HOSTS = {
    H58_M5: ("stud-pair-5-8", 15.875, "common/ground-hole-m5@1", "generic/two-hole-lug-5-8@1"),
    H58_1032: ("stud-pair-5-8", 15.875, "common/ground-hole-10-32@1", "generic/two-hole-lug-5-8@1"),
    H34_1032: ("stud-pair-3-4", 19.05, "common/ground-hole-10-32@1", "generic/two-hole-lug-3-4@1"),
}
STALE_WORDS = ("no lug seat is offered", "no two-hole seat is offered", "The two holes are not", "no pair part for M5")
CLOSED_GAPS = {"ground-hole-seat", "earthing-terminal-holes"}


def _yaml(path):
    return yaml.safe_load(pathlib.Path(path).read_text())


def _device(name):
    return _yaml(LIB / "devices/juniper" / name / "device.yaml")


def _contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return _yaml(LIB / "components" / ns / name / f"v{major}" / "contract.yaml")


def _placements(device, view):
    return {p["id"]: p for p in ((device["views"][view].get("components") or {}).get("placements") or [])}


def test_each_switch_places_its_earthing_terminal_where_the_decor_drew_it():
    bad = []
    for name, views in PLACED.items():
        d = _device(name)
        group = d["groups"].get("grounding")
        if not group or group.get("role") != "furniture" or group.get("term") != "Point":
            bad.append(f"{name}: no `grounding` group of furniture points")
        for view, (pid, host, at, rotate) in views.items():
            p = _placements(d, view).get(pid)
            if not p:
                bad.append(f"{name} {view}: no placement {pid}")
                continue
            if p["ref"] != host or p["at"] != at or p.get("rotate") != rotate or p.get("group") != "grounding":
                bad.append(f"{name} {view}: {pid} is {p['ref']} at {p['at']} rotate {p.get('rotate')} group {p.get('group')}")
    assert not bad, bad


def test_no_earthing_decor_that_names_a_connector_is_left():
    bad = []
    for name in PLACED:
        d = _device(name)
        for view, v in d["views"].items():
            for x in (v.get("panel") or {}).get("decor") or []:
                if x.get("kind") in EARTH_KINDS:
                    bad.append(f"{name} {view}: decor {x.get('id')} is kind {x.get('kind')}")
    assert not bad, bad


def test_the_decor_that_frames_a_placed_part_is_kept_and_named_for_what_it_is():
    bad = []
    for name, renames in RENAMED.items():
        decor = {x["id"]: x for x in (_device(name)["views"]["front" if name == "ex4100-h-12mp" else "rear"]["panel"]["decor"])}
        for ident, kind in renames.items():
            if decor.get(ident, {}).get("kind") != kind:
                bad.append(f"{name}: decor {ident} is not kind {kind}")
    # the plate behind the holes of the other switches is still drawn
    for name in ("ex2200-24p", "ex2300-24p", "ex4100-f-24p", "ex4100-h-24f", "ex4100-h-24mp"):
        ids = {x["id"] for x in _device(name)["views"]["rear"]["panel"]["decor"]}
        if not ids & {"earth-terminal", "earth-plate"}:
            bad.append(f"{name}: the earthing plate is not drawn")
    assert not bad, bad


def test_each_pair_declares_how_its_pitch_was_read_and_each_single_screw_where_it_stands():
    bad = []
    for name, views in PLACED.items():
        d = _device(name)
        gaps = {g["what"]: g for g in d.get("gaps") or []}
        single = name in ("ex2300-24mp", "ex2300-48mp")
        want = "earthing-terminal-position" if single else "ground-pair-pitch"
        if want not in gaps or not gaps[want].get("wanted"):
            bad.append(f"{name}: no gap {want}")
        if gaps.get(want, {}).get("reason") != ("needs-photo" if single else "vendor-silent"):
            bad.append(f"{name}: gap {want} has reason {gaps.get(want, {}).get('reason')}")
        if CLOSED_GAPS & set(gaps):
            bad.append(f"{name}: still carries {sorted(CLOSED_GAPS & set(gaps))}")
        note = (d.get("provenance") or {}).get("ground-stud-pitch")
        if not note or note.get("confidence") != "estimated" or len(" ".join(note["note"].split())) < 200:
            bad.append(f"{name}: no estimated `ground-stud-pitch` note")
        if not single and "INFERRED, NOT STATED" not in (note or {}).get("note", ""):
            bad.append(f"{name}: the pitch note does not say it is inferred")
        if not single and "bare" not in (note or {}).get("note", ""):
            bad.append(f"{name}: the pitch note does not say the holes are bare")
    assert not bad, bad


def test_no_provenance_note_still_says_a_lug_seat_is_not_offered():
    bad = []
    for name in PLACED:
        text = " ".join(" ".join(str(e.get("note", "")).split()) for e in (_device(name).get("provenance") or {}).values()
                        if isinstance(e, dict))
        for words in STALE_WORDS:
            if words in text:
                bad.append(f"{name}: a provenance note still says {words!r}")
    assert not bad, bad


def test_the_two_bare_holes_are_dark_discs_of_the_threads_nominal_size_with_the_seat_on_the_face():
    bad = []
    for ref, d in HOLES.items():
        c = _contract(ref)
        if c["class"] != "ground" or c["interface"] != "terminal-stud" or c["size"] != {"w": d, "h": d}:
            bad.append(f"{ref}: class {c['class']}, interface {c['interface']}, size {c['size']}")
        mate = c["connection-points"]["mate"]
        if mate["at"] != [round(d / 2, 4), round(d / 2, 4)] or "seat-out" in mate or "on" in mate:
            bad.append(f"{ref}: mate is {mate}, expected the centre of the hole and no height")
        if c.get("relief"):
            bad.append(f"{ref}: a bare hole builds no solid")
        skin = (LIB / "components" / ref.split("/")[0] / ref.split("/")[1].split("@")[0] / "v1/skins/default.svg").read_text()
        if skin.count("<circle") != 1 or "#2a2d31" not in skin:
            bad.append(f"{ref}: its skin is not one dark disc")
    assert not bad, bad


def test_the_three_pair_hosts_are_on_the_pitch_of_their_lug_with_the_midpoint_between_the_holes():
    bad = []
    for ref, (iface, pitch, hole, lug) in HOSTS.items():
        c = _contract(ref)
        d = HOLES[hole]
        if c["class"] != "ground" or c["interface"] != iface or c["behaviour"] != "mounts":
            bad.append(f"{ref}: class {c['class']}, interface {c['interface']}, behaviour {c['behaviour']}")
        parts = c["parts"]
        if [q["ref"] for q in parts] != [hole, hole] or [q["id"] for q in parts] != ["1", "2"] \
                or [q["at"][0] for q in parts] != [0, pitch] or any(q["at"][1] != 0 for q in parts):
            bad.append(f"{ref}: the holes are {parts}")
        mate = c["connection-points"]["mate"]
        if mate["at"] != [round((pitch + d) / 2, 4), round(d / 2, 4)] or "seat-out" in mate:
            bad.append(f"{ref}: mate is {mate}")
        if c["size"] != {"w": round(pitch + d, 3), "h": d}:
            bad.append(f"{ref}: size is {c['size']}")
        if _contract(lug).get("mates") != iface:
            bad.append(f"{ref}: {lug} does not mate {iface}")
    assert not bad, bad


def test_the_qfx5210_plate_is_a_pair_host_of_two_bare_10_32_holes_on_the_pitch_of_a_two_hole_lug():
    c = _contract("juniper/qfx5210-ground-plate@1")
    assert c["version"] == "1.1.0" and c["interface"] == "stud-pair-5-8" and c["class"] == "ground"
    parts = c["parts"]
    assert [q["ref"] for q in parts] == ["common/ground-hole-10-32@1"] * 2 and [q["id"] for q in parts] == ["1", "2"]
    assert abs(parts[1]["at"][0] - parts[0]["at"][0] - 15.875) < 1e-9 and parts[0]["at"][1] == parts[1]["at"][1]
    mid = (parts[0]["at"][0] + 2.413 + parts[1]["at"][0] + 2.413) / 2
    mate = c["connection-points"]["mate"]
    assert mate["at"] == [round(mid, 4), round(parts[0]["at"][1] + 2.413, 4)] and "seat-out" not in mate
    seat = " ".join(c["provenance"]["seat"].split())
    assert "NOT A LUG SEAT" not in seat and "LCD10-10A-L" in seat and "15.875" in seat and "bare" in seat
    svg = (LIB / "components/juniper/qfx5210-ground-plate/v1/skins/default.svg").read_text()
    assert "circle" not in svg, "the holes are composed parts now, not art in the skin"
    d = _device("qfx5210-64c")
    assert _placements(d, "rear")["ground-plate"]["ref"] == "juniper/qfx5210-ground-plate@1"


def test_the_records_file_holds_no_row_for_the_plate_and_its_cap_is_its_row_count():
    doc = _yaml(RECORDS)
    assert not [r for r in doc["rows"] if r["part"] == "juniper/qfx5210-ground-plate@1"]
    assert doc["cap"] == len(doc["rows"])
