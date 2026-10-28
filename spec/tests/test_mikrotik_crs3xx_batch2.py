"""MikroTik's second Cloud Router Switch batch: the CRS328-24P-4S+RM, CRS354-48G-4S+2Q+RM, CRS354-48P-4S+2Q+RM and
CRS326-24S+2Q+RM.

The CRS328-24P-4S+RM's envelope comes from MikroTik's dimensions drawing for the model (printed 19.09.2023: 443 wide,
298 deep; the drawing prints no height, the side view reads 44.3) and the counts from the brochure. The device name
spells the + as `-plus`; `model:` keeps it as printed. The pilot (CRS326-24G and CSS326-24G) is in its own test module.

The two CRS354 come from MikroTik's dimensions drawings printed 20.09.2023 (48G: 443 wide, 44.3 high, 297 deep;
48P: 443, 44.3, 380) and each model's brochure; the brochure's "297 x 443 x 44" (48G, reordered) and "443 x 382 x 44"
(48P) are the same boxes, rounded or 2 mm longer. The CRS326-24S+2Q has no drawing: its 200 deep is the brochure's
and the product page's.

The CRS328-24P's helpers and tests carry a `crs328` name; the other three devices' keep the plain names.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/mikrotik"
NAMES_CRS328 = ["crs328-24p-4s-plus-rm"]
MODELS_CRS328 = {"crs328-24p-4s-plus-rm": "CRS328-24P-4S+RM"}
POE_OUT = "802.3af/at or 26 V / 53 V passive (out)"
G48, P48, S24 = "crs354-48g-4s-plus-2q-plus-rm", "crs354-48p-4s-plus-2q-plus-rm", "crs326-24s-plus-2q-plus-rm"
NAMES = [G48, P48, S24]
MODELS = {G48: "CRS354-48G-4S+2Q+RM", P48: "CRS354-48P-4S+2Q+RM", S24: "CRS326-24S+2Q+RM"}
SERIES = {G48: "CRS354", P48: "CRS354", S24: "CRS326"}
# width, height, depth, rack units: the drawings (48G, 48P) and the brochure's 443 x 200 x 44 (24S, no drawing held)
ENVELOPE = {G48: (443.0, 44.3, 297.0, 1), P48: (443.0, 44.3, 380.0, 1), S24: (443.0, 44.45, 200.0, 1)}
# AC inlets: the product page's "Number of AC inputs"
INLETS = {G48: ["ac-inlet-1", "ac-inlet-2"], P48: ["ac-inlet"], S24: ["ac-inlet-1", "ac-inlet-2"]}
# the product page's fan count against the fans a held document places (48P: the drawing shows two rings of four)
FANS_PAGE = {G48: 3, P48: 4, S24: 3}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def refs(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


def decor(d, view):
    return (d["views"][view].get("panel") or {}).get("decor") or []


# --- CRS328-24P-4S+RM ---


@pytest.mark.parametrize("name", NAMES_CRS328)
def test_crs328_device_is_named_as_the_maker_prints_it(name):
    d = load(name)
    assert d["name"] == name
    assert d["manufacturer"] == "MikroTik"
    assert d["model"] == MODELS_CRS328[name]
    assert d["portfolio"] == {"line": "Switches", "family": "Cloud Router Switch", "series": "CRS328"}
    assert "+" not in name


def test_crs328_envelope_matches_the_dimensions_drawing():
    """443 x 298 from the drawing; the brochure's 300 is declared; the height is the side view's 44.3."""
    d = load("crs328-24p-4s-plus-rm")
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (443.0, 44.3, 298.0, 1)
    assert d["views"]["front"]["size"] == {"w": 443.0, "h": 44.3}
    assert d["views"]["top"]["size"] == {"w": 443.0, "h": 298.0}
    assert d["views"]["right"]["size"] == {"w": 298.0, "h": 44.3}
    assert "300" in d["provenance"]["chassis"]["note"] and "298" in d["provenance"]["chassis"]["note"]


def test_crs328_has_24_poe_out_ports_numbered_as_printed():
    d = load("crs328-24p-4s-plus-rm")
    jacks = [p for p in placements(d, "front") if p["ref"] == "common/rj45-ganged-eth-plain@1"]
    assert sorted(p["rel-pos"] for p in jacks) == list(range(1, 25))
    assert all(p["attrs"]["poe"] == POE_OUT for p in jacks)
    assert d["groups"]["rj45"]["attrs"]["poe"] == POE_OUT
    by_id = {p["id"]: p for p in jacks}
    xs = sorted({by_id[f"port-{n}"]["at"][0] for n in range(1, 25, 2)})
    assert len(xs) == 12
    # three blocks of four columns on the 13.97 pitch; the drawing's block step is 70.3
    assert xs[1] - xs[0] == pytest.approx(13.97, abs=0.01)
    assert xs[4] - xs[0] == pytest.approx(70.4, abs=0.15)
    # every port has a lamp above its column and one below, both numbered with the port
    lamps = [p for p in placements(d, "front") if p["ref"] == "common/led-sq@1" and p["id"].startswith("led-port-")]
    assert len(lamps) == 48
    assert {p["for"] for p in lamps} == set(by_id)
    assert sorted(p["rel-pos"] for p in lamps) == list(range(1, 49))


def test_crs328_has_four_sfp_plus_cages_one_console_and_no_management_port():
    d = load("crs328-24p-4s-plus-rm")
    cages = [p for p in placements(d, "front") if p["ref"] == "std/sfp@1"]
    assert [p["rel-pos"] for p in cages] == [1, 2, 3, 4]
    assert d["groups"]["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert [p["id"] for p in placements(d, "front") if p["ref"] == "std/rj45@2"] == ["console"]
    texts = {s.get("text") for s in d["views"]["front"]["silkscreen"]}
    assert {"CONSOLE", "RESET", "MODE", "PWR", "USR", "FAN", "PoE", "SFP+"} <= texts


def test_crs328_has_two_buttons_reset_and_mode():
    d = load("crs328-24p-4s-plus-rm")
    buttons = {p["id"]: p["attrs"]["function"] for p in placements(d, "front") if p["ref"] == "common/reset-button@1"}
    assert buttons == {"btn-reset": "reset", "btn-mode": "mode"}


def test_crs328_power_is_built_in_and_figures_are_filed_as_worded():
    d = load("crs328-24p-4s-plus-rm")
    assert not (d["views"]["front"].get("components") or {}).get("bays")
    assert d["chassis"]["power"] == "ac"
    p = d["attrs"]["power"]
    # the page's maximum, the brochure's 44 W only without PoE devices, the 450 W guaranteed for PoE
    assert (p["power-max-w"], p["poe-budget-w"], p["power-envelope"]) == (494, 450, "fully-configured")
    assert "without PoE devices connected" in p["power-without-attachments"]


def test_crs328_rear_is_empty_and_no_inlet_is_placed():
    """No held document shows the rear: it is not drawn from another model, and no power port is exported."""
    d = load("crs328-24p-4s-plus-rm")
    assert d["views"]["rear"].get("empty")
    assert not placements(d, "rear")
    assert not [p for v in d["views"].values() for p in (v.get("components") or {}).get("placements") or []
                if p["ref"] == "std/c14-inlet@1"]
    gap = [g for g in d["gaps"] if g["what"] == "rear-face"]
    assert len(gap) == 1 and gap[0]["scope"] == ["rear"]


def test_crs328_two_fans_are_drawn_on_the_right_wall():
    d = load("crs328-24p-4s-plus-rm")
    fans = [x["id"] for x in d["views"]["right"]["panel"]["decor"] if x.get("kind") == "fan-grille"]
    assert fans == ["fan-0", "fan-1"]
    assert d["views"]["left"].get("empty")
    assert d["attrs"]["thermal"]["cooling"].startswith("two built-in fans")


def test_crs328_ears_are_in_the_box_and_flush():
    ears = load("crs328-24p-4s-plus-rm")["chassis"]["ears"]
    default = [p for p in ears["positions"] if p.get("default")]
    assert [(p["name"], p["at"]) for p in default] == [("flush", 0)]


@pytest.mark.parametrize("name", NAMES_CRS328)
def test_crs328_logo_is_reserved_not_drawn(name):
    front = load(name)["views"]["front"]
    assert [r["id"] for r in front["regions"]] == ["logo-zone"]
    assert not [s for s in front["silkscreen"] if "mikrotik" in str(s.get("text", "")).lower()]


@pytest.mark.parametrize("name", NAMES_CRS328)
def test_crs328_dcim_device_type_exports_one_per_device(name):
    """One orderable configuration, one exported device type, u_height 1."""
    docs = [
        yaml.safe_load(f.read_text())
        for f in (ROOT / "library/exports/netbox/device-types/MikroTik").glob("*.yaml")
    ]
    mine = [d for d in docs if d["model"] == MODELS_CRS328[name]]
    assert len(mine) == 1
    assert mine[0]["u_height"] == 1
    assert mine[0]["manufacturer"] == "MikroTik"
    assert sum(1 for i in mine[0]["interfaces"] if i["type"] == "1000base-t") == 24
    assert sum(1 for i in mine[0]["interfaces"] if i["type"] == "10gbase-x-sfpp") == 4
    assert not mine[0].get("power-ports")


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", NAMES_CRS328)
def test_crs328_committed_exports_are_what_the_exporter_writes_now(name, target, tmp_path, monkeypatch):
    dist = ROOT / "library/dist"
    assert (dist / "devices.json").exists(), "run the build first: this reads library/dist"
    monkeypatch.setattr(dx, "RASTER", False)
    dx.export_device(dx.Dist(str(dist)), name, str(tmp_path), str(dist))
    rel = Path(target) / "device-types" / "MikroTik" / f"{MODELS_CRS328[name]}.yaml"
    assert (tmp_path / rel).read_text() == (ROOT / "library/exports" / rel).read_text()


def test_crs328_lock_files_match_the_devices():
    lib = ROOT / "library"
    assert not [f for f in devicelock.check(lib) if f[0].startswith("mikrotik/")]
    known = devicelock.load_lock(lib)["devices"]
    for name in NAMES_CRS328:
        entry = known[f"mikrotik/{name}"]
        assert entry["version"] == load(name)["version"]
        per_device = json.loads((DEVICES / name / "device.lock.json").read_text())
        assert per_device["gaps"] == entry["gaps"]


# --- CRS354-48G-4S+2Q+RM, CRS354-48P-4S+2Q+RM and CRS326-24S+2Q+RM ---


@pytest.mark.parametrize("name", NAMES)
def test_the_device_is_named_as_the_maker_prints_it(name):
    d = load(name)
    assert d["name"] == name
    assert d["manufacturer"] == "MikroTik"
    assert d["model"] == MODELS[name]
    assert "+" not in name
    assert d["portfolio"] == {"line": "Switches", "family": "Cloud Router Switch", "series": SERIES[name]}
    assert list(d["configurations"]["base"]["part-numbers"]) == [MODELS[name]]


@pytest.mark.parametrize("name", NAMES)
def test_envelope_matches_the_drawing_or_the_brochure(name):
    """48G 443 x 44.3 x 297 and 48P 443 x 44.3 x 380 (drawings); 24S 443 x 44.45 x 200 (brochure, no drawing)."""
    d = load(name)
    c = d["chassis"]
    w, h, depth, ru = ENVELOPE[name]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (w, h, depth, ru)
    assert d["views"]["front"]["size"] == {"w": w, "h": h}
    assert d["views"]["rear"]["size"] == {"w": w, "h": h}
    assert d["views"]["top"]["size"] == {"w": w, "h": depth}
    assert d["views"]["left"]["size"] == {"w": depth, "h": h}


def test_the_brochure_conflicts_are_declared_in_provenance():
    g, p, s = (" ".join(load(n)["provenance"]["chassis"]["note"].split()) for n in NAMES)
    assert '"297 x 443 x 44 mm"' in g and "depth first" in g
    assert '"443 x 382 x 44 mm"' in p and "2 mm longer" in p
    assert "No drawing is held" in s and load(S24)["provenance"]["chassis"]["confidence"] == "datasheet"


@pytest.mark.parametrize("name", NAMES)
def test_ears_are_in_the_box_and_flush(name):
    default = [p for p in load(name)["chassis"]["ears"]["positions"] if p.get("default")]
    assert [(p["name"], p["at"]) for p in default] == [("flush", 0)]
    assert not refs(load(name), "front", "common/rack-ear@1")


@pytest.mark.parametrize("name", [G48, P48])
def test_forty_eight_gigabit_ports_numbered_as_printed(name):
    d = load(name)
    jacks = [p for p in placements(d, "front") if p["ref"] == "common/rj45-ganged-eth@1"]
    assert sorted(p["rel-pos"] for p in jacks) == list(range(1, 49))
    by_id = {p["id"]: p for p in jacks}
    assert set(by_id) == {f"port-{n}" for n in range(1, 49)}
    # the lower jack of a column takes the odd number, the upper is turned and takes the even
    for n in range(1, 49, 2):
        lower, upper = by_id[f"port-{n}"], by_id[f"port-{n + 1}"]
        assert lower["at"][1] > upper["at"][1] and lower["at"][0] == upper["at"][0]
        assert "rotate" not in lower and upper["rotate"] == 180
    # four blocks of six columns on the 13.97 pitch, 88.4 mm apart (the drawing's)
    xs = sorted({by_id[f"port-{n}"]["at"][0] for n in range(1, 49, 2)})
    assert len(xs) == 24
    assert xs[1] - xs[0] == pytest.approx(13.97, abs=0.01)
    assert xs[6] - xs[0] == pytest.approx(88.4, abs=0.05)
    assert xs[0] + 6.35 == pytest.approx(16.45, abs=0.05)


@pytest.mark.parametrize("name", [G48, P48])
def test_the_cages_and_the_two_management_jacks(name):
    d = load(name)
    sfp = refs(d, "front", "std/sfp-ganged@1")
    assert sorted(p["rel-pos"] for p in sfp) == [1, 2, 3, 4]
    assert {p["id"] for p in sfp} == {f"uplink-{n}" for n in range(1, 5)}
    qsfp = refs(d, "front", "std/qsfp-ganged@1")
    assert sorted(p["rel-pos"] for p in qsfp) == [1, 2]
    assert d["groups"]["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert d["groups"]["qsfp-plus"]["attrs"] == {"media": "qsfp", "speed": "40g"}
    # odd numbers below, even above (the photograph's printing)
    by = {p["rel-pos"]: p for p in sfp}
    assert by[1]["at"][1] > by[2]["at"][1] and by[3]["at"][1] > by[4]["at"][1]
    assert by[1]["at"][0] == by[2]["at"][0] and by[3]["at"][0] > by[1]["at"][0]
    q = {p["rel-pos"]: p for p in qsfp}
    assert q[1]["at"][1] > q[2]["at"][1]
    console = [p for p in refs(d, "front", "std/rj45@2")]
    assert [(p["id"], p["attrs"]["media"]) for p in console] == [("console", "rj45-serial")]
    mgmt = refs(d, "front", "common/rj45-eth@1")
    assert [(p["id"], p["attrs"]["speed"]) for p in mgmt] == [("mgmt-eth", "100m")]
    texts = {s.get("text") for s in d["views"]["front"]["silkscreen"]}
    assert {"CONSOLE", "MGMT", "SFP+", "40G QSFP+", "RESET", "GIGABIT ETHERNET", "FAULT"} <= texts


def test_the_24s_has_24_sfp_plus_two_qsfp_the_usb_and_the_two_rj45():
    d = load(S24)
    sfp = refs(d, "front", "std/sfp-ganged@1")
    assert sorted(p["rel-pos"] for p in sfp) == list(range(1, 25))
    by = {p["rel-pos"]: p for p in sfp}
    for n in range(1, 25, 2):
        assert by[n]["at"][1] > by[n + 1]["at"][1] and by[n]["at"][0] == by[n + 1]["at"][0]
        assert "rotate" in by[n] and "rotate" not in by[n + 1]
    xs = sorted({by[n]["at"][0] for n in range(1, 25, 2)})
    assert len(xs) == 12
    assert xs[4] - xs[0] == pytest.approx(63.2, abs=0.05)
    assert sorted(p["rel-pos"] for p in refs(d, "front", "std/qsfp-ganged@1")) == [1, 2]
    assert not refs(d, "front", "common/rj45-ganged-eth@1")
    assert [p["id"] for p in refs(d, "front", "std/rj45@2")] == ["console"]
    assert [p["id"] for p in refs(d, "front", "common/rj45-eth@1")] == ["mgmt-boot"]
    usb = refs(d, "front", "std/usb-a@1")
    assert [p["id"] for p in usb] == ["usb"] and usb[0]["rotate"] == 90
    # USER, FAULT, PWR 2 and PWR 1 lamps, top to bottom
    lamps = [p["id"] for p in placements(d, "front") if p["ref"] == "common/led-dot@1"]
    assert lamps == ["led-user", "led-fault", "led-pwr2", "led-pwr1"]
    texts = {s.get("text") for s in d["views"]["front"]["silkscreen"]}
    assert {"CONSOLE", "MGMT/BOOT", "RESET", "USER", "FAULT", "PWR 2", "PWR 1"} <= texts


def test_poe_out_is_on_every_ethernet_port_of_the_48p_and_none_of_the_48g():
    for name, expect in ((P48, True), (G48, False)):
        jacks = [p for p in refs(load(name), "front", "common/rj45-ganged-eth@1")]
        assert len(jacks) == 48
        has = [("poe" in p["attrs"]) for p in jacks]
        assert all(has) if expect else not any(has)
    poe = {p["attrs"]["poe"] for p in refs(load(P48), "front", "common/rj45-ganged-eth@1")}
    assert poe == {"IEEE 802.3af/at out; 26 V or 53 V passive out"}
    p = load(P48)["attrs"]["power"]
    assert (p["power-max-w"], p["power-without-attachments-w"], p["poe-budget-w"], p["power-supply-w"]) == (800, 85, 700, 750)


@pytest.mark.parametrize("name", NAMES)
def test_the_inlets_are_c14_placements_for_the_pages_ac_inputs(name):
    d = load(name)
    inlets = refs(d, "rear", "std/c14-inlet@1")
    assert [p["id"] for p in inlets] == INLETS[name]
    assert all(p["group"] == "inlets" for p in inlets)
    assert not (d["views"]["rear"].get("components") or {}).get("bays")
    assert not (d["views"]["front"].get("components") or {}).get("bays")
    assert d["chassis"]["power"] == "ac"
    assert "dc-barrel" not in json.dumps(d)
    note = " ".join(d["provenance"]["built-in-power-and-fans"]["note"].split())
    assert "built in" in note and ("not a bay" in note or "not bays" in note)


def test_the_48p_inlet_is_turned_a_quarter_turn_as_the_photograph_shows():
    d = load(P48)
    (inlet,) = refs(d, "rear", "std/c14-inlet@1")
    assert inlet["rotate"] == 90
    cut = {c["id"]: c for c in d["views"]["rear"]["panel"]["cutouts"]}["ac-inlet"]
    assert cut["size"] == [20.0, 28.0]


def test_the_differences_between_the_two_354_are_pinned_to_their_brochures():
    g, p = load(G48), load(P48)
    assert (g["chassis"]["depth"], p["chassis"]["depth"]) == (297.0, 380.0)
    assert (g["attrs"]["power"]["power-max-w"], g["attrs"]["power"]["power-without-attachments-w"]) == (60, 50)
    assert g["attrs"]["thermal"]["cooling"].startswith("3 fans") and p["attrs"]["thermal"]["cooling"].startswith("4 fans")
    assert "two inputs" in g["attrs"]["power"]["power-input"] and "one input" in p["attrs"]["power"]["power-input"]
    assert len(refs(g, "rear", "std/c14-inlet@1")) == 2 and len(refs(p, "rear", "std/c14-inlet@1")) == 1
    assert "poe-budget-w" not in g["attrs"]["power"]
    assert g["attrs"]["platform"]["switch-chip"] == p["attrs"]["platform"]["switch-chip"] == "98DX3257"
    # the 48P's brochure lists rear support ears the format cannot place: a gap, not an ear
    assert [x for x in p["gaps"] if x["what"] == "rear-support-ears"]
    assert not [x for x in g["gaps"] if x["what"] == "rear-support-ears"]
    assert (load(S24)["attrs"]["power"]["power-max-w"], load(S24)["attrs"]["platform"]["switch-chip"]) == (69, "98DX8332")


def fan_rings(d, view):
    return [x for x in decor(d, view) if x.get("kind") == "fan-grille"]


def test_fans_are_openings_of_the_chassis_where_a_document_places_them():
    assert [len(fan_rings(load(G48), "rear")), len(fan_rings(load(S24), "rear"))] == [3, 3] == [FANS_PAGE[G48], FANS_PAGE[S24]]
    p = load(P48)
    # two rings in the left wall; the page's other two fans are placed by nothing held, and a gap says so
    assert len(fan_rings(p, "left")) == 2 and not fan_rings(p, "rear")
    assert [x for x in p["gaps"] if x["what"] == "fans-three-and-four"]
    for name in NAMES:
        assert not refs(load(name), "rear", "common/fan@1")


def test_the_side_walls_are_drawn_only_where_a_view_shows_them():
    g = load(G48)
    assert [x["id"] for x in decor(g, "left")] == ["side-vent"] and [x["id"] for x in decor(g, "right")] == ["side-vent"]
    # the 48G left vent is 232.7 from the rear, the right one the same distance from the front (297 - 267.2 = 29.7)
    assert decor(g, "left")[0]["at"][0] + decor(g, "left")[0]["size"][0] + decor(g, "right")[0]["at"][0] == pytest.approx(297.0, abs=0.5)
    assert [x["id"] for x in decor(load(P48), "right")] == ["side-vent"]
    assert len(decor(load(P48), "left")) == 4
    s = load(S24)
    assert "empty" in s["views"]["left"] and "empty" in s["views"]["right"]


def test_the_24s_positions_are_estimated_because_the_photograph_is_not_orthographic():
    s = load(S24)
    assert s["provenance"]["front-layout"]["confidence"] == "estimated"
    assert s["provenance"]["gate-1"]["confidence"] == "estimated"
    assert [x for x in s["gaps"] if x["what"] == "dimensions-drawing"]
    for name in NAMES:
        assert load(name)["provenance"]["rear-layout"]["confidence"] == "estimated"


@pytest.mark.parametrize("name", NAMES)
def test_the_logo_is_reserved_not_drawn(name):
    front = load(name)["views"]["front"]
    assert [r["id"] for r in front["regions"]] == ["logo-zone"]
    assert not [s for s in front["silkscreen"] if "mikrotik" in str(s.get("text", "")).lower()]


@pytest.mark.parametrize("name", NAMES)
def test_every_gap_has_its_wanted_line(name):
    assert all(g.get("wanted") for g in load(name)["gaps"])
    assert [g for g in load(name)["gaps"] if g["what"] == "led-states"]


def device_type(name):
    docs = [yaml.safe_load(f.read_text()) for f in (ROOT / "library/exports/netbox/device-types/MikroTik").glob("*.yaml")]
    mine = [d for d in docs if d["model"] == MODELS[name]]
    assert len(mine) == 1
    return mine[0]


# (interfaces, power ports): every cage and jack is one interface, the console included, each inlet one power port
EXPORT = {G48: (55, 2), P48: (55, 1), S24: (27, 2)}


@pytest.mark.parametrize("name", NAMES)
def test_dcim_device_type_exports_one_per_device(name):
    mine = device_type(name)
    assert mine["u_height"] == 1
    assert mine["manufacturer"] == "MikroTik"
    n_if, n_pw = EXPORT[name]
    assert len(mine["interfaces"]) == n_if
    assert [p["name"] for p in mine["power-ports"]] == INLETS[name]
    assert len(mine["power-ports"]) == n_pw


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", NAMES)
def test_the_committed_exports_are_what_the_exporter_writes_now(name, target, tmp_path, monkeypatch):
    dist = ROOT / "library/dist"
    assert (dist / "devices.json").exists(), "run a build first: this reads library/dist"
    monkeypatch.setattr(dx, "RASTER", False)
    dx.export_device(dx.Dist(str(dist)), name, str(tmp_path), str(dist))
    rel = Path(target) / "device-types" / "MikroTik" / f"{MODELS[name]}.yaml"
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
