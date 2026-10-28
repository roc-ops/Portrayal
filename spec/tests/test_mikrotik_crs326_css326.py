"""MikroTik's CRS326-24G-2S+RM and CSS326-24G-2S+RM: the maker, the envelope and the faces.

Both devices come from one MikroTik dimensions drawing ("CRS/CSS326-24G-2S+ dimensions", printed
19.09.2023: 443 wide, 44.5 high, 144.6 deep) and from each model's brochure (24 10/100/1000
ports, two SFP+ cages; a serial RJ45 on the CRS only). The device name spells the + as `-plus`;
`model:` keeps it as printed.
"""
import json
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/mikrotik"
NAMES = ["crs326-24g-2s-plus-rm", "css326-24g-2s-plus-rm"]
MODELS = {"crs326-24g-2s-plus-rm": "CRS326-24G-2S+RM", "css326-24g-2s-plus-rm": "CSS326-24G-2S+RM"}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


# the rear legend each model prints, as the placement's input-voltage
RATED = {"crs326-24g-2s-plus-rm": ("10-28 VDC",), "css326-24g-2s-plus-rm": ("8-30 VDC",)}
# port 1's passive PoE input, from each model's brochure (CRS) and quick guide (CSS)
POE_IN = {"crs326-24g-2s-plus-rm": "passive PD (in), 9 - 30 V",
          "css326-24g-2s-plus-rm": "passive PD (in), 11 - 30 V"}


def d_cutouts(name):
    return load(name)["views"]["front"]["panel"]["cutouts"]


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def test_mikrotik_resolves_in_the_vendor_registry():
    reg = yaml.safe_load((ROOT / "spec/schemas/vendors.yaml").read_text())["vendors"]
    assert reg["mikrotik"]["display"] == "MikroTik"
    assert reg["mikrotik"]["role"] == "both"
    assert str(reg["mikrotik"]["source"]).strip()
    # the entry sits directly after cisco's
    order = list(reg)
    assert order[order.index("cisco") + 1] == "mikrotik"


@pytest.mark.parametrize("name", NAMES)
def test_the_device_is_named_as_the_maker_prints_it(name):
    d = load(name)
    assert d["name"] == name
    assert d["manufacturer"] == "MikroTik"
    assert d["model"] == MODELS[name]
    assert "+" not in name


@pytest.mark.parametrize("name", NAMES)
def test_envelope_matches_the_dimensions_drawing(name):
    """443 x 44.5 x 144.6, one rack unit; the brochure's 443 x 144 x 44 is the same box rounded."""
    d = load(name)
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"], c["ru"]) == (443.0, 44.5, 144.6, 1)
    assert d["views"]["front"]["size"] == {"w": 443.0, "h": 44.5}
    assert d["views"]["rear"]["size"] == {"w": 443.0, "h": 44.5}
    assert d["views"]["top"]["size"] == {"w": 443.0, "h": 144.6}


@pytest.mark.parametrize("name", NAMES)
def test_ears_are_in_the_box_and_flush(name):
    ears = load(name)["chassis"]["ears"]
    default = [p for p in ears["positions"] if p.get("default")]
    assert [(p["name"], p["at"]) for p in default] == [("flush", 0)]


@pytest.mark.parametrize("name", NAMES)
def test_twenty_four_gigabit_ports_numbered_as_printed(name):
    d = load(name)
    jacks = [p for p in placements(d, "front") if p["ref"] == "common/rj45-ganged-eth-plain@1"]
    assert sorted(p["rel-pos"] for p in jacks) == list(range(1, 25))
    assert {p["id"] for p in jacks} == {f"port-{n}" for n in range(1, 25)}
    by_id = {p["id"]: p for p in jacks}
    # the lower jack of a column takes the odd number; port 1 is the POE IN jack
    for n in range(1, 25, 2):
        lower, upper = by_id[f"port-{n}"], by_id[f"port-{n + 1}"]
        assert lower["at"][1] > upper["at"][1]
        assert lower["at"][0] == upper["at"][0]
        assert "rotate" not in lower and upper["rotate"] == 180
    # three blocks of four columns on the 13.97 pitch with the drawing's 63.5 step
    xs = sorted({by_id[f"port-{n}"]["at"][0] for n in range(1, 25, 2)})
    assert len(xs) == 12
    assert xs[4] - xs[0] == pytest.approx(63.5, abs=0.05)
    assert xs[1] - xs[0] == pytest.approx(13.97, abs=0.01)
    # one lamp per port
    lamps = {p["for"] for p in placements(d, "front") if p["ref"] == "common/led-sq@1" and p["id"].startswith("led-port-")}
    assert lamps == set(by_id)


@pytest.mark.parametrize("name", NAMES)
def test_two_sfp_plus_cages(name):
    d = load(name)
    cages = [p for p in placements(d, "front") if p["ref"] == "std/sfp@1"]
    assert len(cages) == 2
    assert [p["rel-pos"] for p in cages] == [1, 2]
    assert d["groups"]["sfp-plus"]["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    texts = {s.get("text") for s in d["views"]["front"]["silkscreen"]}
    assert {"SFP+ 1", "SFP+ 2", "ACT/LINK", "10G"} <= texts


def test_only_the_crs_has_the_rj45_console():
    crs, css = load(NAMES[0]), load(NAMES[1])
    assert [p["id"] for p in placements(crs, "front") if p["ref"] == "std/rj45@2"] == ["console"]
    assert not [p for p in placements(css, "front") if p["ref"] == "std/rj45@2"]


@pytest.mark.parametrize("name", NAMES)
def test_power_is_a_dc_jack_not_a_built_in_supply(name):
    d = load(name)
    # the jack is the placed common/dc-barrel, as on every other device with one, not chassis art
    jack = [p for p in placements(d, "rear") if p["ref"] == "common/dc-barrel@1"]
    assert [p["id"] for p in jack] == ["dc-in"]
    assert jack[0]["attrs"] == {"input-voltage": RATED[name][0], "current-max-a": 1.2}
    decor = {x.get("id") for x in d["views"]["rear"]["panel"]["decor"]}
    assert not {"dc-jack-ring", "dc-jack-bore", "dc-jack-pin"} & decor
    assert d["provenance"]["dc-in-rating"]["confidence"] == "datasheet"
    assert not (d["views"]["front"].get("components") or {}).get("bays")
    assert not (d["views"]["rear"].get("components") or {}).get("bays")
    assert d["chassis"]["power"] == "dc"


@pytest.mark.parametrize("name", NAMES)
def test_port_1_carries_the_passive_poe_input_as_an_attr(name):
    d = load(name)
    jacks = {p["id"]: p for p in placements(d, "front") if p["ref"] == "common/rj45-ganged-eth-plain@1"}
    assert jacks["port-1"]["attrs"] == {"media": "rj45", "speed": "1g", "poe": POE_IN[name]}
    assert all("poe" not in jacks[f"port-{n}"]["attrs"] for n in range(2, 25))


@pytest.mark.parametrize("name", NAMES)
def test_the_lamp_cutouts_are_square_as_the_lamp_part_is(name):
    cut = {c["id"]: c for c in d_cutouts(name)}
    for n in range(1, 25):
        assert cut[f"led-port-{n}"]["shape"] == "rect"


@pytest.mark.parametrize("name", NAMES)
def test_the_rear_opening_is_a_fan_guard_grille_with_no_fan(name):
    d = load(name)
    text = " ".join(d["description"].split())
    assert "fan-guard grille with four fan-mount holes and no fan fitted" in text
    assert "passive cooling" in text and "is a vent" not in text
    assert d["attrs"]["thermal"]["cooling"].startswith("passive")


@pytest.mark.parametrize("name", NAMES)
def test_the_earth_stud_is_chassis_art_with_a_gap_for_its_part(name):
    d = load(name)
    gap = [g for g in d["gaps"] if g["what"] == "earth-stud-part"]
    assert len(gap) == 1 and gap[0]["scope"] == ["rear"]
    assert "wing-nut" in gap[0]["wanted"]
    decor = {x.get("id") for x in d["views"]["rear"]["panel"]["decor"]}
    assert {"earth-stud-base", "earth-stud-nut"} <= decor


def test_the_css_quick_guide_is_cited_with_its_document_number_and_date():
    d = load(NAMES[1])
    assert "Document #49066 Modified on: 26.APR.2019" in " ".join(d["provenance"]["sources"]["note"].split())
    quick = [r for r in d["references"] if "quick guide" in r["title"]]
    assert len(quick) == 1
    assert "Document #49066 Modified on: 26.APR.2019" in quick[0]["title"]
    assert "no date" not in quick[0]["title"]


def test_the_css_rear_is_estimated_like_the_crs():
    assert load(NAMES[0])["provenance"]["rear-layout"]["confidence"] == "estimated"
    assert load(NAMES[1])["provenance"]["rear-layout"]["confidence"] == "estimated"


def test_the_two_devices_differ_where_their_brochures_do():
    """Switch chip, flash, temperature, power, VLANs, OS, console and the rear legend."""
    got = {}
    for name in NAMES:
        d = load(name)
        legends = [s["text"] for s in d["views"]["rear"]["silkscreen"] if str(s.get("text", "")).startswith("DC")]
        got[name] = (
            d["attrs"]["platform"]["switch-chip"], d["attrs"]["platform"]["storage"],
            d["attrs"]["platform"]["os"], d["attrs"]["environmental"]["operating-temp-c"],
            d["attrs"]["power"]["power-max-w"], d["attrs"]["features"]["vlan-limit"], legends,
        )
    assert got[NAMES[0]] == ("98DX3236A1", "16 MB flash", "SwOS / RouterOS (dual boot)", "-40 to 60 (tested)",
                             24, "IEEE 802.1Q, up to 4K VLANs", ["DC 10-28V"])
    assert got[NAMES[1]] == ("98DX3216A1", "2 MB flash", "SwOS", "-20 to 70 (tested)",
                             19, "IEEE 802.1Q, up to 250 VLANs", ["DC 8 - 30V"])
    assert load(NAMES[0])["attrs"]["platform"]["ram"] == "512 MB"
    assert "ram" not in load(NAMES[1])["attrs"]["platform"]


@pytest.mark.parametrize("name", NAMES)
def test_the_logo_is_reserved_not_drawn(name):
    front = load(name)["views"]["front"]
    assert [r["id"] for r in front["regions"]] == ["logo-zone"]
    assert not [s for s in front["silkscreen"] if "mikrotik" in str(s.get("text", "")).lower()]


@pytest.mark.parametrize("name", NAMES)
def test_dcim_device_type_exports_one_per_device(name):
    """One orderable configuration, one exported device type, u_height 1, the DC jack as `dc-in`."""
    docs = [
        yaml.safe_load(f.read_text())
        for f in (ROOT / "library/exports/netbox/device-types/MikroTik").glob("*.yaml")
    ]
    mine = [d for d in docs if d["model"] == MODELS[name]]
    assert len(mine) == 1
    assert mine[0]["u_height"] == 1
    assert mine[0]["manufacturer"] == "MikroTik"
    assert sum(1 for i in mine[0]["interfaces"] if i["type"] == "1000base-t") == 24
    assert len(mine[0]["interfaces"]) == 26
    assert [p["name"] for p in mine[0]["power-ports"]] == ["dc-in"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", NAMES)
def test_the_committed_exports_are_what_the_exporter_writes_now(name, target, tmp_path, monkeypatch):
    """Runs the exporter on the build and compares its file with the committed one, so a device
    edited without regenerating its export fails here and not only in CI's "exports are current"."""
    dist = ROOT / "library/dist"
    assert (dist / "devices.json").exists(), "run ./build.sh first: this reads library/dist"
    monkeypatch.setattr(dx, "RASTER", False)
    dx.export_device(dx.Dist(str(dist)), name, str(tmp_path), str(dist))
    rel = Path(target) / "device-types" / "MikroTik" / f"{MODELS[name]}.yaml"
    assert (tmp_path / rel).read_text() == (ROOT / "library/exports" / rel).read_text()


def test_the_lock_files_match_the_devices():
    """The lock entry of each device is what devicelock computes from it now, at its own version."""
    lib = ROOT / "library"
    assert not [f for f in devicelock.check(lib) if f[0].startswith("mikrotik/")]
    known = devicelock.load_lock(lib)["devices"]
    for name in NAMES:
        entry = known[f"mikrotik/{name}"]
        assert entry["version"] == load(name)["version"]
        per_device = json.loads((DEVICES / name / "device.lock.json").read_text())
        assert per_device["gaps"] == entry["gaps"]
        assert "dc-in" in " ".join(per_device["ids"])
