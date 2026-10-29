"""MikroTik's Cloud Router Switch CRS5xx, batch 1: the 25G and 100G models.

The CRS518-16XS-2XQ-RM takes its envelope from MikroTik's dimensions drawing (printed 20.09.2023): 443 wide, 44 high and
268 deep, where the brochure prints 443 x 265 x 44.5. Its two supplies and four fans are hot-swap modules in the
brochure and the photograph, but no held document prints a part number for either, so they are drawn as part of the
chassis (two C14 inlets, four fan openings) and no bay is added. The device names are lower case with no +.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/mikrotik"
MODELS = {
    "crs518-16xs-2xq-rm": ("CRS518-16XS-2XQ-RM", "CRS518"),
    "crs510-8xs-2xq-in": ("CRS510-8XS-2XQ-IN", "CRS510"),
}
NAMES = sorted(MODELS)
ENVELOPE = {  # width, height, depth
    "crs518-16xs-2xq-rm": (443.0, 44.0, 268.0),
    "crs510-8xs-2xq-in": (320.0, 44.0, 185.0),
}
CRS518 = "crs518-16xs-2xq-rm"
CRS510 = "crs510-8xs-2xq-in"


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return (d["views"][view].get("components") or {}).get("bays") or []


def refs(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


def text_of(d, view):
    return {s.get("text") for s in d["views"][view]["silkscreen"]}


@pytest.mark.parametrize("name", NAMES)
def test_the_device_is_named_as_the_maker_prints_it(name):
    d = load(name)
    model, series = MODELS[name]
    assert d["name"] == name
    assert d["manufacturer"] == "MikroTik"
    assert d["model"] == model
    assert d["portfolio"] == {"line": "Switches", "family": "Cloud Router Switch", "series": series}
    assert "+" not in name
    assert d["version"] == "1.0.0"
    assert list(d["configurations"]["base"]["part-numbers"]) == [model]


@pytest.mark.parametrize("name", NAMES)
def test_the_envelope_is_the_drawings(name):
    d = load(name)
    w, h, depth = ENVELOPE[name]
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, depth, 1)
    assert d["views"]["front"]["size"] == {"w": w, "h": h}
    assert d["views"]["top"]["size"] == {"w": w, "h": depth}
    assert d["views"]["left"]["size"] == {"w": depth, "h": h}
    assert d["views"]["right"]["size"] == {"w": depth, "h": h}


# --- CRS518-16XS-2XQ-RM ------------------------------------------------------------------------------------------

def test_crs518_brochure_and_drawing_differences_are_declared():
    d = load(CRS518)
    note = d["provenance"]["chassis"]["note"]
    assert "268" in note and "265" in note and "44.5" in note
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["size-figures"]["reason"] == "sources-disagree"


def test_crs518_has_sixteen_sfp28_cages_in_eight_stacked_pairs():
    d = load(CRS518)
    cages = [p for p in placements(d, "front") if p.get("group") == "sfp28"]
    assert [p["id"] for p in cages] == [f"cage-{n}" for n in range(1, 17)]
    assert [p["rel-pos"] for p in cages] == list(range(1, 17))
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp28", "speed": "25g"} for p in cages)
    by_id = {p["id"]: p for p in cages}
    for n in range(1, 17, 2):  # the metal prints 1 and 2 under a stack: 1 is the lower cage
        assert by_id[f"cage-{n}"]["at"][1] > by_id[f"cage-{n + 1}"]["at"][1]
        assert by_id[f"cage-{n}"]["at"][0] == by_id[f"cage-{n + 1}"]["at"][0]
    assert by_id["cage-3"]["at"][0] - by_id["cage-1"]["at"][0] == pytest.approx(21.2, abs=0.05)


def test_crs518_has_two_qsfp28_cages_each_with_two_lamps():
    d = load(CRS518)
    cages = [p for p in placements(d, "front") if p.get("group") == "qsfp28"]
    assert [p["id"] for p in cages] == ["qsfp-1", "qsfp-2"]
    assert all(p["ref"] == "std/qsfp28@1" and p["attrs"] == {"media": "qsfp28", "speed": "100g"} for p in cages)
    assert cages[1]["at"][0] - cages[0]["at"][0] == pytest.approx(26.0, abs=0.05)
    assert len([p for p in placements(d, "front") if p.get("group") == "qsfp-leds"]) == 4
    assert len([p for p in placements(d, "front") if p.get("group") == "sfp-leds"]) == 32  # four per stack


def test_crs518_has_management_console_usb_reset_and_four_lamps():
    d = load(CRS518)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "100m")]
    assert [p["id"] for p in refs(d, "front", "std/usb-a@1")] == ["usb"]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    assert len([p for p in placements(d, "front") if p.get("group") == "status-leds"]) == 4
    assert {"CONSOLE", "ETH / BOOT", "MANAGEMENT", "RESET", "USER", "FAULT", "PWR 2", "PWR 1", "1", "2",
            "40G/100G", "1G/10G/25G", "CRS518-16XS-2XQ"} <= text_of(d, "front")
    ports = [p for p in placements(d, "front") if p.get("group") in {"sfp28", "qsfp28", "mgmt", "console", "usb"}]
    assert len(ports) == 16 + 2 + 1 + 1 + 1  # page: 16 SFP28, 2 QSFP28, 1 x 100M, one USB, one console


def test_crs518_supplies_and_fans_are_part_of_the_chassis_with_no_part_number():
    d = load(CRS518)
    assert not bays(d, "rear")
    assert d["chassis"]["power"] == "ac"
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]  # the page: 2 AC inputs
    assert all(p["group"] == "inlets" for p in inlets)
    fans = [x["id"] for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert fans == ["fan-0", "fan-1", "fan-2", "fan-3"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert {"hot-swap-supplies", "hot-swap-fans"} <= set(gaps)
    assert "fan-redundancy" not in json.dumps(d["groups"])
    p = d["attrs"]["power"]
    assert p["power-max-w"] == 77 and p["power-without-attachments-w"] == 45


def _decor(d, view):
    return {x["id"]: x for x in d["views"][view]["panel"]["decor"]}


def _render_decor(decor, w=443.0, h=44.0):
    import re
    from portrayal import render
    view = {"size": {"w": w, "h": h}, "panel": {"decor": decor}}
    dev = {"name": "f", "manufacturer": "F", "model": "F", "version": "0.1.0",
           "chassis": {"width": w, "height": h, "depth": 100.0}, "views": {"front": view}}
    out = render.render_view(dev, "front", view, render.Library([str(ROOT / "library")]), config={})
    return out if isinstance(out, str) else render.ET.tostring(out, encoding="unicode")


def test_crs518_front_vent_band_is_chevrons_along_the_top_edge():
    """The drawing and photograph 2196 show a zigzag of V shapes, not perforations. Read off the drawing at 2.63 px
    per mm (the 443 mm body is 1164 px): the band runs 2.3 to 440.3 mm, 2.7 to 9.5 mm down, one V every 16.7 mm
    (autocorrelation of the ink, peak at 44 px), so 26 V shapes with a peak between each pair."""
    d = load(CRS518)
    band = _decor(d, "front")["vent-field"]
    assert band["pattern"] == "chevrons" and band["vent"]
    assert band["at"] == [2.3, 2.7] and band["size"] == [438.0, 6.8]
    assert band["pattern-offset"] == band["at"]  # the first stroke starts at the band's left end, at the bottom
    assert band["pattern-pitch"][0] == 16.7
    assert round(band["size"][0] / band["pattern-pitch"][0]) == 26
    svg = _render_decor([band])
    import re
    m = re.search(r'<rect id="vent-field"[^>]*fill="url\(#([^)]+)\)"', svg)
    assert m and "chevrons" in m.group(1), svg[:600]
    pat = re.search(rf'<pattern[^>]*id="{re.escape(m.group(1))}"[^>]*>(.*?)</pattern>', svg, re.S)
    assert pat and "<path" in pat.group(1) and 'fill="none"' in pat.group(1)
    assert 'data-aperture="air"' in svg  # still an opening, not paint


@pytest.mark.parametrize("name, fans", [(CRS518, 4), (CRS510, 2)])
def test_every_fan_opening_has_a_plain_hub_in_its_centre(name, fans):
    """Photographs 2197 and 2233 show each fan as a ring of mesh round a plain hub, not a disc of mesh."""
    decor = _decor(load(name), "rear")
    for i in range(fans):
        g, hub = decor[f"fan-{i}"], decor[f"fan-hub-{i}"]
        centre = lambda x: (round(x["at"][0] + x["size"][0] / 2, 2), round(x["at"][1] + x["size"][1] / 2, 2))
        assert centre(g) == centre(hub)
        assert 0.4 <= hub["size"][0] / g["size"][0] <= 0.6
        assert "pattern" not in hub and not hub.get("vent")


def test_crs510_front_has_no_vent_band_along_the_top():
    """The drawing's front view and photograph 2232 show a plain top edge: no chevrons on this box."""
    d = load(CRS510)
    assert not [x for x in d["views"]["front"]["panel"]["decor"]
                if x.get("pattern") == "chevrons" or x["id"] == "vent-field"]


@pytest.mark.parametrize("psu, left", [("psu-1", 12.6), ("psu-2", 72.0)])
def test_crs510_supply_vent_is_slots_not_perforations(psu, left):
    """Each supply shows six tall slots (three across, two down) and a row of four short ones along its top edge, in
    the drawing's front view and in photograph 2232. Sizes are read off the drawing at 3.94 px per mm and are
    estimates to about 0.4 mm; the photograph, at 8.74 px per mm, agrees on the count."""
    d = load(CRS510)
    decor = _decor(d, "front")
    assert f"{psu}-vent" not in decor  # the round-perforation field is gone
    tall = [decor[f"{psu}-slot-{r}{c}"] for r in "ab" for c in "123"]
    short = [decor[f"{psu}-slot-top-{i}"] for i in range(1, 5)]
    for s in tall + short:
        assert s["kind"] == "vent-field" and s["vent"] and "pattern" not in s
        assert left <= s["at"][0] and s["at"][0] + s["size"][0] <= left + 52.1
    assert {tuple(s["size"]) for s in tall} == {(3.8, 7.6), (3.8, 7.5)}
    xs = sorted({round(s["at"][0] - left, 2) for s in tall})
    assert xs == [3.7, 8.7, 13.7]  # a 5.0 mm pitch
    assert sorted({s["at"][1] for s in tall}) == [20.0, 29.2]
    assert all(s["at"][1] < 12 and s["size"][1] == 2.5 for s in short)
    lay = d["provenance"]["vent-slots"]
    assert lay["confidence"] == "estimated"


def test_crs518_walls():
    d = load(CRS518)
    assert [x["id"] for x in d["views"]["right"]["panel"]["decor"]] == ["side-vent"]
    assert d["views"]["left"].get("empty")
    assert d["views"]["top"].get("empty")


# --- CRS510-8XS-2XQ-IN ------------------------------------------------------------------------------------------

def test_crs510_drawing_and_brochure_agree_and_the_power_figures_conflict_is_declared():
    d = load(CRS510)
    assert "320 x 185 x 44" in d["provenance"]["chassis"]["note"]
    gaps = {g["what"]: g for g in d["gaps"]}
    assert gaps["power-figures"]["reason"] == "sources-disagree"
    assert "27" in gaps["power-figures"]["note"] and "31" in gaps["power-figures"]["note"]
    assert d["attrs"]["power"]["power-without-attachments-w"] == 31 and d["attrs"]["power"]["power-max-w"] == 51


def test_crs510_has_eight_sfp28_and_two_qsfp28_cages_in_stacks():
    d = load(CRS510)
    sfp = [p for p in placements(d, "front") if p.get("group") == "sfp28"]
    assert [p["id"] for p in sfp] == [f"cage-{n}" for n in range(1, 9)]
    assert all(p["ref"] == "std/sfp-ganged@1" and p["attrs"] == {"media": "sfp28", "speed": "25g"} for p in sfp)
    by_id = {p["id"]: p for p in sfp}
    for n in range(1, 9, 2):  # the metal prints 1 3 5 7 under the stacks and 2 4 6 8 over them
        assert by_id[f"cage-{n}"]["at"][1] > by_id[f"cage-{n + 1}"]["at"][1]
        assert by_id[f"cage-{n}"]["at"][0] == by_id[f"cage-{n + 1}"]["at"][0]
    assert by_id["cage-3"]["at"][0] - by_id["cage-1"]["at"][0] == pytest.approx(17.4, abs=0.05)
    assert by_id["cage-5"]["at"][0] - by_id["cage-3"]["at"][0] == pytest.approx(21.1, abs=0.05)  # the gutter
    q = [p for p in placements(d, "front") if p.get("group") == "qsfp28"]
    assert [p["id"] for p in q] == ["qsfp-1", "qsfp-2"] and q[0]["at"][1] > q[1]["at"][1]
    assert all(p["ref"] == "std/qsfp28@1" and p["attrs"] == {"media": "qsfp28", "speed": "100g"} for p in q)
    assert len([p for p in placements(d, "front") if p.get("group") == "sfp-leds"]) == 16 + 4  # four arrows a stack
    assert len([p for p in placements(d, "front") if p.get("group") == "qsfp-leds"]) == 2  # and the QSFP28's two dots
    ports = [p for p in placements(d, "front") if p.get("group") in {"sfp28", "qsfp28", "mgmt", "console"}]
    assert len(ports) == 8 + 2 + 1 + 1


def test_crs510_front_carries_console_management_reset_dc_jack_and_three_lamps():
    d = load(CRS510)
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    mgmt = [p for p in refs(d, "front", "common/rj45-eth@1") if p.get("group") == "mgmt"]
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt", "100m")]
    assert [p["id"] for p in refs(d, "front", "common/reset-button@1")] == ["btn-reset"]
    assert not refs(d, "front", "common/dc-barrel@1")  # drawn as chassis art: the barrel census wants a current
    assert [x["id"] for x in d["views"]["front"]["panel"]["decor"] if x.get("kind") == "dc-jack-art"] == [
        "dc-jack-housing", "dc-jack-bore"]
    assert len([p for p in placements(d, "front") if p.get("group") == "status-leds"]) == 5  # 3 bars, 2 supply lamps
    assert {"CONSOLE", "MGMT/PoE in", "RESET", "USER", "FAULT", "POWER", "36-57 V", "CRS510-8XS-2XQ-IN"} <= text_of(d, "front")
    gaps = {g["what"] for g in d["gaps"]}
    assert {"dc-jack", "dc-terminal", "hot-swap-supplies", "led-states", "left-wall"} <= gaps  # neither DC input is placed
    assert not [p for p in placements(d, "front") if p["ref"].startswith("common/dc-terminal")]


def test_crs510_supplies_are_two_front_modules_with_c14_inlets_and_no_bays():
    d = load(CRS510)
    assert not bays(d, "front") and not bays(d, "rear")
    inlets = refs(d, "front", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == ["ac-inlet-1", "ac-inlet-2"]
    assert all(p["group"] == "inlets" and p["rotate"] in (90, 270, -90) for p in inlets)
    assert {"PSU 1", "PSU 2", "100-240 V 50/60 Hz"} <= text_of(d, "front")
    assert d["chassis"]["power"] == "ac"
    fans = [x["id"] for x in d["views"]["rear"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert fans == ["fan-0", "fan-1"]
    assert d["views"]["right"]["panel"]["decor"] and d["views"]["left"].get("empty")


# --- every device ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", NAMES)
def test_the_ears_are_shipped_flush_and_never_placed(name):
    d = load(name)
    default = [p for p in d["chassis"]["ears"]["positions"] if p.get("default")]
    assert [p["name"] for p in default] == ["flush"]
    assert not [p for v in d["views"].values() for p in (v.get("components") or {}).get("placements") or []
                if p["ref"] == "common/rack-ear@1"]
    assert "kits" not in d["chassis"]


@pytest.mark.parametrize("name", NAMES)
def test_the_logo_is_reserved_not_drawn(name):
    front = load(name)["views"]["front"]
    assert [r["id"] for r in front["regions"]] == ["logo-zone"]
    assert not [s for s in front["silkscreen"] if "mikrotik" in str(s.get("text", "")).lower()]


@pytest.mark.parametrize("name", NAMES)
def test_every_legend_is_readable_at_the_device_pages_scale(name):
    d = load(name)
    for view in d["views"].values():
        for s in view.get("silkscreen") or []:
            if s.get("text"):
                assert s["font-size"] >= 1.5, s


# --- the DCIM export --------------------------------------------------------------------------------------------

def exported(name):
    model = MODELS[name][0]
    docs = [yaml.safe_load(f.read_text()) for f in (ROOT / "library/exports/netbox/device-types/MikroTik").glob("*.yaml")]
    mine = [x for x in docs if x["model"] == model]
    assert len(mine) == 1
    return mine[0]


def count(doc, kind):
    return sum(1 for i in doc["interfaces"] if i["type"] == kind)


@pytest.mark.parametrize("name", NAMES)
def test_dcim_device_type_exports_one_per_device(name):
    doc = exported(name)
    assert doc["u_height"] == 1 and doc["manufacturer"] == "MikroTik"


def test_dcim_crs518_interfaces_and_power_ports_follow_the_faces():
    a = exported(CRS518)
    assert count(a, "25gbase-x-sfp28") == 16 and count(a, "100gbase-x-qsfp28") == 2
    assert count(a, "100base-tx") == 1
    assert len(a["power-ports"]) == 2  # two C14 inlets
    assert len(a["console-ports"]) == 1


def test_dcim_crs510_interfaces_and_power_ports_follow_the_faces():
    a = exported(CRS510)
    assert count(a, "25gbase-x-sfp28") == 8 and count(a, "100gbase-x-qsfp28") == 2
    assert count(a, "100base-tx") == 1
    assert len(a["power-ports"]) == 2  # the two C14 inlets; the DC jack and the terminal are not placed
    assert len(a["console-ports"]) == 1


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", NAMES)
def test_the_committed_exports_are_what_the_exporter_writes_now(name, target, tmp_path, monkeypatch):
    dist = ROOT / "library/dist"
    assert (dist / "devices.json").exists(), "run the build first: this reads library/dist"
    monkeypatch.setattr(dx, "RASTER", False)
    dx.export_device(dx.Dist(str(dist)), name, str(tmp_path), str(dist))
    rel = Path(target) / "device-types" / "MikroTik" / f"{MODELS[name][0]}.yaml"
    assert (tmp_path / rel).read_text() == (ROOT / "library/exports" / rel).read_text()


def test_the_lock_files_match_the_devices():
    lib = ROOT / "library"
    assert not [f for f in devicelock.check(lib) if f[0].startswith("mikrotik/")]
    known = devicelock.load_lock(lib)["devices"]
    for name in NAMES:
        entry = known[f"mikrotik/{name}"]
        assert entry["version"] == load(name)["version"] == "1.0.0"
        per_device = json.loads((DEVICES / name / "device.lock.json").read_text())
        assert per_device["gaps"] == entry["gaps"]
