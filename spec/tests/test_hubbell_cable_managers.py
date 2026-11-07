"""Hubbell Premise Wiring's horizontal cable managers (P-0120, #1101, part of #1091).

Six parts, each from the maker's own spec sheet on hubbellcdn.com: the M-Series
HM14C, HM24C, HM34C and HM144C (wire rings, a centre plate with windows, a hinged
cover), the S-Series HS23C (steel fingers, a lift-off cover) and the SD-Series
HSD13 (plastic fingers, a press-on cover). What each advertises has to WORK in the
library and the rack kit, not only be drawn: a ring a cable can be laid through, a
finger duct a cable runs along, a window it crosses by, a cover that comes off.

These read the build, library/dist and library/exports. The cable laid through a
ring, along a duct and across a window is in spec/tests/js/rack-hubbell-managers.mjs.
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
EXPORTS = ROOT / "library" / "exports"
COMPONENTS = ROOT / "library" / "components"
SVG = "{http://www.w3.org/2000/svg}"
IN = 25.4
WIRE = 0.225 * IN                      # the M-Series sheets: "Wire Diameter 0.225""
THICK = 1.5                            # the M-Series plate, estimated

# The sheets' own dimensions table, inches, with the millimetres each prints:
# (ru, A in, A mm, C in, C mm). B is 19 in (483 mm) on every sheet. The HM144C
# sheet has no table: its 1 RU and 19 in are the HM14C's.
SHEETS = {
    "hm14c": dict(ru=1, a=(1.75, 44), c=(4.0, 102), series="M"),
    "hm24c": dict(ru=2, a=(3.5, 89), c=(4.0, 102), series="M"),
    "hm34c": dict(ru=3, a=(4.6, 117), c=(4.0, 102), series="M"),
    "hm144c": dict(ru=1, a=(1.75, 44), c=(4.0, 102), series="M"),
    "hs23c": dict(ru=2, a=(3.5, 89), c=(3.0, 76), series="S"),
    "hsd13": dict(ru=1, a=(1.6, 41), c=(3.2, 81), series="SD"),
}
M = [n for n, s in SHEETS.items() if s["series"] == "M"]
FINGERED = [n for n, s in SHEETS.items() if s["series"] != "M"]
WINDOWED = M + ["hs23c"]
COVERS = {"hm14c": "hm1c", "hm24c": "hm2c", "hm34c": "hm3c", "hm144c": "hm1c",
          "hs23c": "hs2c", "hsd13": "hsd13-cover"}

needs_build = pytest.mark.skipif(not (DIST / "rack.json").is_file(), reason="library/dist not built - run ./build.sh")


def rack(name):
    return json.loads((DIST / "rack.json").read_text())["devices"][name]


def face(name, view, config="base"):
    """The drawing of one view of one configuration, as the build wrote it."""
    idx = json.loads((DIST / f"{name}.configs.json").read_text())
    cfg = next(c for c in idx["configs"] if c["name"] == config)
    f = (cfg.get("files") or {}).get(view) or f"{name}.{config}.{view}.svg"
    return ET.parse(DIST / f).getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def centre_x(el):
    """The middle of a placed ring along the face: its translate and half its width."""
    tx = float(re.search(r"translate\(([-\d.]+)", el.get("transform")).group(1))
    return tx


@needs_build
@pytest.mark.parametrize("name", SHEETS)
def test_envelope_is_the_sheets_a_b_and_c(name):
    s = SHEETS[name]
    e = rack(name)
    a_in, a_mm = s["a"]
    c_in, c_mm = s["c"]
    # B 19 in, 483 mm printed; A and C in inches, with the millimetres the sheet prints
    assert e["w"] == pytest.approx(19 * IN, abs=0.01) and abs(e["w"] - 483) < 0.5
    assert e["h"] == pytest.approx(a_in * IN, abs=0.01) and abs(e["h"] - a_mm) < 0.5
    assert e["ru"] == s["ru"]
    # the ears bolt C behind the front of the part (an S part: the plate is the back), and an
    # M part has the plate's thickness and the rear extension D, estimated as C, behind that
    assert e["ears"]["default"]["at"] == pytest.approx(c_in * IN + (THICK if s["series"] == "M" else 0), abs=0.01)
    assert abs(c_in * IN - c_mm) < 0.5
    if s["series"] == "M":
        assert e["d"] == pytest.approx(2 * c_in * IN + THICK, abs=0.01)
    else:
        assert e["d"] == pytest.approx(c_in * IN, abs=0.01)
    # a rail-mounted part on the rails (the default mount, as the FS 1 RU managers) taking its units
    assert e["kind"] == "cable manager" and "mount" not in e


@needs_build
def test_the_3_ru_part_keeps_the_sheets_a_and_says_it_is_short_of_3_ru():
    """HM34C: A reads 4.6 in (117 mm) for 3 RU, short of 3 RU's 5.25 in. The sheet's figure is the
    envelope; the part is not 'corrected' to 133.35."""
    e = rack("hm34c")
    assert e["h"] == pytest.approx(4.6 * IN, abs=0.01) and e["h"] < 3 * 44.45 - 10
    assert e["ru"] == 3
    doc = yaml.safe_load((ROOT / "library/devices/hubbell/hm34c/device.yaml").read_text())
    assert "a-is-not-3-ru" in doc["provenance"]
    assert any(g["what"] == "plate-height" for g in doc["gaps"])


@needs_build
@pytest.mark.parametrize("name", M)
def test_m_series_publishes_five_rings_a_side_and_four_windows(name):
    e = rack(name)
    assert e["guides"]["front"] == [f"guide-{i}" for i in range(1, 6)]
    assert e["guides"]["rear"] == [f"rear-{i}" for i in range(1, 6)]
    assert e["passes"]["front"] == e["passes"]["rear"] == [f"pass-through-{i}" for i in range(1, 5)]
    # every ring is a place a cable meets at its own depth and band
    assert sorted(e["rings"]) == sorted(e["guides"]["front"] + e["guides"]["rear"])
    assert all(r["depth"] == pytest.approx(WIRE, abs=0.001) for r in e["rings"].values())


@needs_build
@pytest.mark.parametrize("name", M)
def test_each_ring_states_its_aperture_from_the_wire_and_the_figure(name):
    s = SHEETS[name]
    a, c = s["a"][0] * IN, s["c"][0] * IN
    for view, ids in (("front", "guide-{}"), ("rear", "rear-{}")):
        els = by_id(face(name, view))
        xs = []
        for i in range(1, 6):
            g = els[ids.format(i)]
            assert g.get("data-guide") == "ring" and g.get("data-guide-run") == "x"
            w, h = (float(v) for v in g.get("data-guide-aperture").split())
            # a loop of 0.225 in wire: the opening is the plate's height less a wire top and
            # bottom, and the depth less a wire at each end
            assert w == pytest.approx(a - 2 * WIRE, abs=0.01) and h == pytest.approx(c - 2 * WIRE, abs=0.01)
            assert float(g.get("data-guide-depth")) == pytest.approx(WIRE, abs=0.001)
            xs.append(centre_x(g) + WIRE / 2)
        # five rings, a window between each pair, symmetric about the middle
        assert xs[2] == pytest.approx(19 * IN / 2, abs=0.01)
        pitches = [round(b - a_, 3) for a_, b in zip(xs, xs[1:])]
        assert len(set(pitches)) == 1


@needs_build
@pytest.mark.parametrize("name", FINGERED)
def test_s_and_sd_series_publish_a_duct_with_their_finger_pitch_and_gap(name):
    e = rack(name)
    assert e["guides"]["front"] == ["duct"]
    duct = by_id(face(name, "front"))["guide--duct"]
    assert duct.get("data-guide") == "duct" and duct.get("data-guide-run") == "x"
    pitch, gap = float(duct.get("data-guide-finger-pitch")), float(duct.get("data-guide-finger-gap"))
    assert 0 < gap < pitch
    # the channel is as wide as the part and lies between the finger walls, inside its height
    assert float(duct.get("width")) == pytest.approx(e["w"], abs=0.01)
    assert 0 < float(duct.get("y")) and float(duct.get("y")) + float(duct.get("height")) < e["h"]


@needs_build
@pytest.mark.parametrize("name", WINDOWED)
def test_the_plate_has_four_windows_declared_as_pass_throughs_both_sides(name):
    e = rack(name)
    assert e["passes"]["front"] == e["passes"]["rear"] == [f"pass-through-{i}" for i in range(1, 5)]
    # and the plate is solid but for them: each window is a hole in a floor of the rack's solids
    holed = [s for s in e["solids"] if s.get("holes")]
    assert holed, "no plate of the part carries a window"
    for s in holed:
        assert sorted({h["via"] for h in s["holes"]}) == [f"pass-through-{i}" for i in range(1, 5)]


@needs_build
def test_the_sd_series_advertises_no_pass_through_so_declares_none():
    assert "passes" not in rack("hsd13")


@needs_build
@pytest.mark.parametrize("name", SHEETS)
def test_the_cover_is_a_removable_part_that_ships_fitted(name):
    ref = f"hubbell/{COVERS[name]}@1"
    contract = yaml.safe_load((COMPONENTS / "hubbell" / COVERS[name] / "v1" / "contract.yaml").read_text())
    # a part the explorer can take off (`behaviour: mounts`) and a lid a pass-through may lie under
    assert contract["behaviour"] == "mounts" and contract["lid"] is True
    on = by_id(face(name, "front"))
    assert on["cover"].get("data-ref", "").startswith(ref)
    assert on["cover"].get("data-behaviour") == "mounts"
    # the drawing with it off is a configuration of its own, and the cover is not in it
    off = by_id(face(name, "front", "cover-off"))
    assert "cover" not in off
    # ... and shows what the cover hid: every ring, finger and tab of the drawing with it on
    hidden = [i for i, el in on.items() if el.get("data-ref") and i != "cover" and el.get("data-behaviour") == "mounts"]
    assert hidden and all(i in off for i in hidden)
    # the cover is the last thing drawn on the front, over what it closes
    order = [el.get("id") for el in face(name, "front").iter() if el.get("data-ref")]
    assert order.index("cover") > max(order.index(i) for i in hidden)


@needs_build
@pytest.mark.parametrize("name", M)
def test_the_rings_are_what_a_cover_lies_over(name):
    """Selecting a ring in the explorer takes the cover off to show it: `under: cover` on each."""
    on = by_id(face(name, "front"))
    assert all(on[f"guide-{i}"].get("data-under") == "cover" for i in range(1, 6))


@needs_build
def test_the_sd_series_fingers_are_parts_that_can_each_be_taken_out():
    """'Plastic fingers can be removed where needed for cable entrance': 44 fingers, each its own
    pullable part, and four end blocks. The format has no way to say which one is gone in a rack
    file, and the device says so in a gap."""
    on = by_id(face("hsd13", "front"))
    fingers = [i for i in on if i.startswith("finger-") and "--" not in i]
    assert len(fingers) == 48
    assert all(on[i].get("data-behaviour") == "mounts" for i in fingers)
    doc = yaml.safe_load((ROOT / "library/devices/hubbell/hsd13/device.yaml").read_text())
    assert any(g["what"] == "finger-removal" for g in doc["gaps"])


@pytest.mark.parametrize("name", SHEETS)
def test_no_cable_capacity_is_stated_for_any_part(name):
    """No Hubbell sheet states a cable count, so none is recorded and none estimated."""
    doc = yaml.safe_load((ROOT / "library/devices" / "hubbell" / name / "device.yaml").read_text())
    perf = (doc.get("attrs") or {}).get("performance") or {}
    assert not any(k.startswith("cable-capacity") for k in perf)
    assert any(g["what"] == "cable-capacity" and g["reason"] == "vendor-silent" for g in doc["gaps"])


@pytest.mark.parametrize("name", SHEETS)
def test_every_figure_read_off_a_drawing_says_it_is_estimated(name):
    """Anything read off the sheets' figure and not their table carries `estimated`."""
    doc = yaml.safe_load((ROOT / "library/devices" / "hubbell" / name / "device.yaml").read_text())
    prov = doc["provenance"]
    assert prov["front"]["confidence"] == "estimated"
    if name != "hm144c":
        assert prov["method"]["confidence"] == "datasheet"


def _panel_24_ports():
    """The library's 24-port 1U patch panel: the FS FHD-1UFCE enclosure with four FHD-FAPM6-RJ45
    modules, six RJ45 jacks each. Its bays (the module's edges) and its jacks (their left and right
    edges), as rack x from the middle of the enclosure."""
    dev = yaml.safe_load((ROOT / "library/devices/fs/fhd-1ufce/device.yaml").read_text())
    mod = yaml.safe_load((COMPONENTS / "fs/fhd-fapm6-rj45/v1/contract.yaml").read_text())
    jack = yaml.safe_load((COMPONENTS / "std/rj45/v2/contract.yaml").read_text())["size"]["w"]
    mid = dev["chassis"]["width"] / 2
    bays = [(b["at"][0] - mid, b["at"][0] + b["size"]["w"] - mid) for b in dev["views"]["front"]["components"]["bays"]]
    jacks = [(b[0] + p["at"][0], b[0] + p["at"][0] + jack) for b in bays for p in mod["parts"]]
    return sorted(bays), sorted(jacks)


def test_the_panel_the_library_holds_is_24_ports_in_one_unit():
    bays, jacks = _panel_24_ports()
    assert len(bays) == 4 and len(jacks) == 24
    assert {round(b[1] - b[0], 2) for b in bays} == {108.97}


@needs_build
@pytest.mark.parametrize("name", M)
def test_m_series_rings_stand_between_the_ports_of_a_24_port_panel(name):
    """'Cable rings align with patch panel adaptors to prevent patch cord kinks': the five rings are
    112 mm apart (estimated, off the figure) and the panel's four modules 108.97, so each ring stands
    within 6.1 mm of a module's edge, and none stands in front of a jack."""
    bays, jacks = _panel_24_ports()
    edges = sorted({e for b in bays for e in b})
    els = by_id(face(name, "front"))
    for i in range(1, 6):
        x = centre_x(els[f"guide-{i}"]) + WIRE / 2 - 19 * IN / 2
        band = (x - WIRE / 2, x + WIRE / 2)
        assert min(abs(x - e) for e in edges) < 6.2, (i, x)
        assert not any(band[0] < j1 and j0 < band[1] for j0, j1 in jacks), (i, x)


@needs_build
def test_the_hs23c_fingers_against_the_same_panel_are_recorded_as_found():
    """The S-Series makes the same claim for its fingers. The five are 104 mm apart (estimated) and
    24 wide, so the outer two stand 10 mm from the panel's outer module edges and overlap the
    outermost jack by 1.4 mm each: the claim is not borne out by the estimate, which a drawing could
    close."""
    bays, jacks = _panel_24_ports()
    edges = sorted({e for b in bays for e in b})
    xs = [-208.0, -104.0, 0.0, 104.0, 208.0]
    offs = [min(abs(x - e) for e in edges) for x in xs]
    assert [round(o, 1) for o in offs] == [9.9, 5.0, 0.0, 5.0, 9.9]
    columns = sorted({(round(j0, 3), round(j1, 3)) for j0, j1 in jacks})     # two jacks stand in a column
    over = [sum(max(0.0, min(x + 12, j1) - max(x - 12, j0)) for j0, j1 in columns) for x in xs]
    assert [round(o, 1) for o in over] == [1.4, 0.0, 0.0, 0.0, 1.4]
    # and the figure's fingers are where this reads them
    els = by_id(face("hs23c", "front"))
    got = [centre_x(els[f"finger-{i}"]) + 12 - 19 * IN / 2 for i in range(1, 6)]
    assert [round(g, 1) for g in got] == xs


def test_the_maker_is_in_the_registry_with_its_source():
    reg = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]["hubbell"]
    assert reg["display"] == "Hubbell" and reg["role"] == "hardware"
    assert "Hubbell Premise Wiring" in reg["source"] and "Hubbell Incorporated" in reg["source"]


@pytest.mark.parametrize("name", SHEETS)
def test_dcim_device_types_export_the_rack_units_and_not_full_depth(name):
    """A rail-mounted cable manager takes its rack units on the rail and is not full depth. (The
    FS 1 RU managers are `mount: rack`; only the 0U lacer and the 5U bracket are `rack-face`.)"""
    model = name.upper()
    for tool in ("netbox", "nautobot"):
        f = EXPORTS / tool / "device-types" / "Hubbell" / f"{model}.yaml"
        assert f.is_file(), f"{f} is not exported: run dcim_export.py for {name}"
        doc = yaml.safe_load(f.read_text())
        assert doc["u_height"] == SHEETS[name]["ru"]
        assert doc["is_full_depth"] is False
