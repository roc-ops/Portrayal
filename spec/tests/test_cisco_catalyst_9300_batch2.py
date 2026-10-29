"""The Catalyst 9300's second batch: the C9300-24P, C9300-24U and C9300-48U.

Source: Cisco Catalyst 9300 Series Switches Hardware Installation Guide (first published
2017-06-20, last modified 2026-05-15). Table 1 gives each model's ports, Table 42 its envelope,
Table 18 its default power supply and PoE budget, Table 35 the supplies the series takes and
Table 43 the weight. The tests hold each device to the guide's figures, not to what a drawing
happens to say. The C9300-24T is not here: no held source shows its own front.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/cisco"
COMPONENTS = LIB / "components/cisco"
EXPORTS = LIB / "exports"
DIST = LIB / "dist"

IN = 25.4

# model -> the guide's figures: ports (Table 1), default supply and PoE budget (Table 18), weight
# (Table 43, kg)
MODELS = {
    "c9300-24p": {"model": "C9300-24P", "ports": 24, "psu": "pwr-c1-715wac-p", "poe": 445, "weight": 7.4},
    "c9300-24u": {"model": "C9300-24U", "ports": 24, "psu": "pwr-c1-1100wac-p", "poe": 830, "weight": 7.54},
    "c9300-48u": {"model": "C9300-48U", "ports": 48, "psu": "pwr-c1-1100wac-p", "poe": 822, "weight": 7.72},
}

# Table 35 and the Power Supply Modules list: the supplies the C9300 series takes
SUPPLIES = {
    "pwr-c1-350wac", "pwr-c1-350wac-p", "pwr-c1-715wac", "pwr-c1-715wac-p", "pwr-c1-1100wac",
    "pwr-c1-1100wac-p", "pwr-c1-1900wac-p", "pwr-c1-1900whv-t", "pwr-c1-715wdc",
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def placements(d, view):
    comps = d["views"][view]["components"]
    return {p["id"]: p for p in comps.get("placements", [])}


def bays(d, view):
    return {b["id"]: b for b in d["views"][view]["components"].get("bays", [])}


@pytest.fixture(params=sorted(MODELS))
def dev(request):
    return request.param, load(request.param), MODELS[request.param]


# ---------------------------------------------------------------- the envelope


def test_envelope_is_table_42(dev):
    """1.73 x 17.5 x 19.2 in for every model. The height is the rack unit, 44.45 mm; the printed
    1.73 in (43.9 mm) is nominal and within a millimetre."""
    _, d, _ = dev
    ch = d["chassis"]
    assert ch["width"] == pytest.approx(17.5 * IN, abs=0.1)
    assert ch["depth"] == pytest.approx(19.2 * IN, abs=0.5)
    assert ch["height"] == pytest.approx(1.73 * IN, abs=1.0)
    assert ch["ru"] == 1
    assert ch["airflow"] == "front-to-back"


def test_weight_is_table_43(dev):
    _, d, m = dev
    assert d["chassis"]["weight-kg"] == m["weight"]


def test_poe_budget_is_table_18(dev):
    _, d, m = dev
    assert d["attrs"]["power"]["poe-budget-w"] == m["poe"]


def test_every_face_is_sized_from_the_chassis(dev):
    _, d, _ = dev
    ch = d["chassis"]
    for v in ("front", "rear"):
        assert d["views"][v]["size"] == {"w": ch["width"], "h": ch["height"]}
    for v in ("top", "bottom"):
        assert d["views"][v]["size"] == {"w": ch["width"], "h": ch["depth"]}


def test_the_ears_name_the_shipped_position_and_no_kit_is_written(dev):
    _, d, _ = dev
    pos = d["chassis"]["ears"]["positions"]
    assert [p["name"] for p in pos if p.get("default")] == ["flush"]
    assert not [p for p in pos if "at" in p], "the guide prints no setback"
    assert "kits" not in d["chassis"], "no depth range is printed, so no kit is written"
    assert "rack-kit" in {g["what"] for g in d["gaps"]}


def test_the_device_is_named_as_the_pilot_names_its_devices(dev):
    _, d, m = dev
    assert d["manufacturer"] == "Cisco" and d["model"] == m["model"]
    assert d["portfolio"] == {"line": "Catalyst", "family": "Catalyst 9300", "series": "Catalyst 9300"}
    assert d["version"] == "1.0.0"


# ----------------------------------------------------------------------- ports


def test_front_has_the_numbered_rj45_ports_table_1_gives(dev):
    _, d, m = dev
    pl = placements(d, "front")
    ports = {k: v for k, v in pl.items() if re.fullmatch(r"port-\d+", k)}
    assert sorted(int(k.split("-")[1]) for k in ports) == list(range(1, m["ports"] + 1))
    assert {p["ref"] for p in ports.values()} == {"std/rj45-ganged@2"}
    assert {p["group"] for p in ports.values()} == {"rj45"}
    assert d["groups"]["rj45"]["attrs"] == {"media": "rj45", "speed": "1g"}


def test_ports_run_down_each_column_in_blocks_of_six(dev):
    _, d, m = dev
    pl = placements(d, "front")
    n_ports = m["ports"]
    for n in range(1, n_ports, 2):
        top, bottom = pl[f"port-{n}"]["at"], pl[f"port-{n + 1}"]["at"]
        assert top[0] == bottom[0] and top[1] < bottom[1], f"port {n} is over port {n + 1}"
    xs = sorted({pl[f"port-{n}"]["at"][0] for n in range(1, n_ports, 2)})
    assert len(xs) == n_ports // 2
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    gutters = [i for i, s in enumerate(steps) if s > 15]
    assert gutters == list(range(5, len(xs) - 1, 6)), "a gutter after every sixth column"


def test_a_24_port_face_has_its_two_blocks_where_the_merged_48p_has_its_last_two():
    """The 24-port elevations draw the jacks at the x positions of the 48-port picture's third and
    fourth blocks; the merged C9300-48P is the reference for those positions."""
    ref = placements(load("c9300-48p"), "front")
    for name in ("c9300-24p", "c9300-24u"):
        pl = placements(load(name), "front")
        for n in range(1, 25):
            assert pl[f"port-{n}"]["at"][0] == pytest.approx(ref[f"port-{n + 24}"]["at"][0], abs=0.01)
            assert pl[f"port-{n}"]["at"][1] == pytest.approx(ref[f"port-{n + 24}"]["at"][1], abs=0.01)


def test_the_48u_front_ports_sit_where_the_48p_front_ports_sit():
    ref, new = placements(load("c9300-48p"), "front"), placements(load("c9300-48u"), "front")
    for n in range(1, 49):
        assert new[f"port-{n}"]["at"] == ref[f"port-{n}"]["at"]


def test_every_port_has_a_lamp(dev):
    _, d, m = dev
    pl = placements(d, "front")
    n = m["ports"]
    assert {k for k in pl if k.startswith("led-port-")} == {f"led-port-{i}" for i in range(1, n + 1)}
    assert all(pl[f"led-port-{i}"]["for"] == f"port-{i}" for i in range(1, n + 1))


def test_the_legends_are_the_elevations_own(dev):
    _, d, m = dev
    texts = {s["text"] for s in d["views"]["front"]["silkscreen"]}
    if m["ports"] == 24:
        assert {"1X", "12X", "13X", "24X"} <= texts
        assert not {"25X", "48X", "01X"} & texts
    else:
        assert {"01X", "12X", "13X", "24X", "25X", "36X", "37X", "48X"} <= texts


def test_each_name_plate_says_its_own_model():
    plates = {n: [s["text"] for s in load(n)["views"]["front"]["silkscreen"] if s["id"] == "silk-model"][0]
              for n in MODELS}
    assert plates == {
        "c9300-24p": "Catalyst 9300 24 PoE+",
        "c9300-24u": "Catalyst 9300 24 UPOE",
        "c9300-48u": "Catalyst 9300 48 UPOE",
    }


def test_no_logo_or_wordmark_is_drawn(dev):
    _, d, _ = dev
    for v in ("front", "rear"):
        for s in d["views"][v].get("silkscreen", []):
            assert "cisco" not in s["text"].lower()
    zone = [r for r in d["views"]["front"]["regions"] if r["id"] == "logo-zone"]
    assert zone and "not drawn" in zone[0]["label"]


def test_front_console_is_the_registry_mini_usb_b_and_there_is_a_usb_a(dev):
    _, d, _ = dev
    pl = placements(d, "front")
    assert pl["console-usb"]["ref"] == "std/mini-usb@1"
    assert pl["usb-a"]["ref"] == "std/usb-a@1"
    assert d["groups"]["usb-console"]["attrs"] == {"media": "mini-usb-b"}


def test_the_buttons_and_the_mode_button_part_are_reused(dev):
    _, d, _ = dev
    pl = placements(d, "front")
    assert pl["mode-button"]["ref"] == "cisco/c9300-mode-button@1"
    assert pl["uid-button"]["ref"] == "common/button-led-sq@1"


def test_rear_console_management_stack_and_power_stack_connectors(dev):
    _, d, _ = dev
    pl = placements(d, "rear")
    assert pl["console"]["attrs"]["role"] == "console"
    assert pl["mgmt"]["attrs"]["role"] == "mgmt"
    assert pl["console"]["at"][0] < pl["mgmt"]["at"][0]
    assert {k for k in pl if k.startswith("stack-")} == {"stack-1", "stack-2"}
    assert {k for k in pl if k.startswith("spwr-")} == {"spwr-1", "spwr-2"}
    assert pl["usb-ssd"]["attrs"]["usb"] == "3.0"


def test_the_stackwise_ports_reuse_the_three_connector_carrier(dev):
    _, d, _ = dev
    pl = placements(d, "rear")
    assert {pl["stack-1"]["ref"], pl["stack-2"]["ref"]} == {"cisco/stackwise-480-port@1"}
    assert {pl["spwr-1"]["ref"], pl["spwr-2"]["ref"]} == {"cisco/stackpower-port@1"}
    c = contract("stackwise-480-port")
    assert c["version"] == "1.1.0"
    openings = [e["size"] for e in c["elements"].values()]
    assert len(openings) == 3 and all(s == [14.9, 5.2] for s in openings)


def test_the_rear_is_the_merged_series_rear(dev):
    """Every model's rear is placed where the merged C9300-48P's rear is: the 24-port rears agree
    with it to a millimetre on their own elevations, and the 48U's is carried from it."""
    _, d, _ = dev
    ref = load("c9300-48p")
    assert placements(d, "rear") == placements(ref, "rear")
    assert {k: (v["at"], v["size"]) for k, v in bays(d, "rear").items()} == \
        {k: (v["at"], v["size"]) for k, v in bays(ref, "rear").items()}


def test_the_48u_rear_is_marked_estimated_from_the_48p_and_figure_10():
    d = load("c9300-48u")
    note = d["provenance"]["rear-scale"]
    assert note["confidence"] == "estimated"
    assert "cisco/c9300-48p" in note["note"] and "Figure 10" in note["note"]
    assert "rear-drawing" in {g["what"] for g in d["gaps"]}


def test_the_poe_lamp_is_on_every_model(dev):
    _, d, _ = dev
    assert "led-poe" in placements(d, "front")


# ------------------------------------------------- supplies, fans and the bays


def test_three_fan_modules_seat_fan_t2(dev):
    _, d, _ = dev
    fans = {k: v for k, v in bays(d, "rear").items() if k.startswith("fan-")}
    assert sorted(fans) == ["fan-1", "fan-2", "fan-3"]
    assert all(b["accepts"] == ["cisco/fan-t2@1"] and b["default"] == "cisco/fan-t2@1"
               for b in fans.values())


def test_both_supply_bays_accept_what_the_guide_lists_and_the_cover(dev):
    _, d, _ = dev
    fb = bays(d, "rear")
    want = {f"cisco/{n}@1" for n in SUPPLIES} | {"cisco/c9300-psu-blank@1"}
    for bid in ("psu-1", "psu-2"):
        assert set(fb[bid]["accepts"]) == want


def test_the_pwr_c6_supplies_are_not_accepted(dev):
    """Table 35 lists the PWR-C6 supplies for the C9300LM only."""
    _, d, _ = dev
    for bid in ("psu-1", "psu-2"):
        assert not [a for a in bays(d, "rear")[bid]["accepts"] if "pwr-c6" in a]


def test_default_supply_is_table_18_and_the_second_slot_has_the_cover(dev):
    _, d, m = dev
    fb = bays(d, "rear")
    assert fb["psu-1"]["default"] == f"cisco/{m['psu']}@1"
    assert fb["psu-2"]["default"] == "cisco/c9300-psu-blank@1"


def test_the_network_module_bay_takes_only_the_blank(dev):
    _, d, _ = dev
    bay = bays(d, "front")["nm-bay"]
    assert bay["default"] == "cisco/c9300-nm-blank@1" and bay["accepts"] == ["cisco/c9300-nm-blank@1"]


# ------------------------------------------------------------- configurations


def test_the_orderable_configuration_is_the_model_as_shipped(dev):
    name, d, m = dev
    cfgs = d["configurations"]
    orderable = {k: v for k, v in cfgs.items() if v["kind"] == "orderable"}
    assert list(orderable) == [name]
    assert orderable[name]["part-numbers"] == {m["model"]: {}}
    assert orderable[name]["default"] is True and "bays" not in orderable[name]
    assert [k for k, v in cfgs.items() if v.get("default")] == [name]
    assert not [k for k, v in cfgs.items() if v["kind"] == "base"]


def test_every_supply_has_a_configuration_that_seats_it(dev):
    name, d, m = dev
    cfgs = d["configurations"]
    seated = {c["bays"].get("psu-1") for c in cfgs.values() if "bays" in c}
    seated.add(f"cisco/{m['psu']}@1")
    assert {f"cisco/{n}@1" for n in SUPPLIES} <= seated
    assert {c["kind"] for k, c in cfgs.items() if k != name} == {"example"}
    assert "empty-supply-bay" in cfgs
    dual = {k: v for k, v in cfgs.items() if k.startswith("dual-")}
    assert list(dual) == [f"dual-{m['psu'][len('pwr-c1-'):]}"]
    assert dual[next(iter(dual))]["bays"] == {"psu-2": f"cisco/{m['psu']}@1"}


def test_the_dc_supply_feeds_a_dc_configuration(dev):
    _, d, _ = dev
    cfg = d["configurations"]["psu-715wdc"]
    assert cfg["power"] == "dc" and cfg["bays"] == {"psu-1": "cisco/pwr-c1-715wdc@1"}
    assert d["chassis"]["power"] == "ac"


def test_licence_suffix_is_not_a_part_number(dev):
    _, d, m = dev
    pn = d["configurations"][m["model"].lower()]["part-numbers"]
    assert not [k for k in pn if k.endswith(("-A", "-E"))]
    assert "software" in d["provenance"]["the-licence-suffix"]["note"]


# ------------------------------------------------------- the DCIM device types


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_dcim_exports_one_type_per_device(target):
    for name, m in MODELS.items():
        f = EXPORTS / target / "device-types/Cisco" / f"{m['model']}.yaml"
        t = yaml.safe_load(f.read_text())
        assert t["manufacturer"] == "Cisco" and t["model"] == m["model"]
        assert t["u_height"] == 1 == round(1.73 * IN / 44.45)
        assert t["weight"] == m["weight"]
        assert t["front_image"] is True and t["rear_image"] is True, "exported with the image flags"
        ports = [i for i in t["interfaces"] if re.fullmatch(r"port-\d+", i["name"])]
        assert len(ports) == m["ports"]


def test_the_exported_types_carry_no_illustration():
    names = {f.name for f in (EXPORTS / "netbox/device-types/Cisco").glob("C9300*")}
    assert {f"{m['model']}.yaml" for m in MODELS.values()} <= names
    assert not [n for n in names if n.endswith(("-A.yaml", "-E.yaml"))]


@pytest.mark.parametrize("name", sorted(MODELS))
def test_committed_exports_equal_the_exporters_own_output(name, tmp_path):
    """Reads library/dist, so it runs after a build."""
    out = tmp_path / "exports"
    subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/portrayal/dcim_export.py"), "--dist", str(DIST),
         "--out", str(out), "--device", name, "--images", "--no-raster"],
        check=True, capture_output=True, cwd=tmp_path,
        env={"PYTHONPATH": str(ROOT / "spec/tools"), "PATH": "/usr/bin:/bin"},
    )
    fresh = sorted(p.relative_to(out) for p in out.rglob("*.yaml"))
    assert fresh, "the exporter wrote nothing"
    for rel in fresh:
        assert (EXPORTS / rel).read_text() == (out / rel).read_text(), f"{rel} is stale"


# ------------------------------------------------------------------- the lock


def test_the_lock_agrees_with_the_device():
    from portrayal import devicelock

    for name in MODELS:
        lock = json.loads((DEVICES / name / "device.lock.json").read_text())
        assert lock["version"] == "1.0.0"
    mine = {f"cisco/{n}" for n in MODELS}
    assert [f for f in devicelock.check(LIB) if f[0] in mine] == []


def test_the_pilot_devices_stay_at_1_0_0():
    for name in ("c9300-48p", "c9300-48t"):
        assert load(name)["version"] == "1.0.0"
