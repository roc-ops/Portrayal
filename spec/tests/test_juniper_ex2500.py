"""The Juniper EX2500 fixed 10 GbE top-of-rack switch: EX2500-24F-FB and EX2500-24F-BF.

One device, because the two models share one front and one rear and differ only in the direction the
air moves; each model is a `kind: orderable` configuration that carries its own part number. The expected
figures are Juniper's: the EX2500 Ethernet Switch Hardware Guide (Table 12 for the envelope, Table 14 for
the power, Table 15 for the part numbers, Figures 1 and 2 for the two panels, Tables 8 to 11 for the
lamps) and the EX2500 Ethernet Switches datasheet (Apr 2009). Each test reads the YAML a contributor
edits, or the generated export a DCIM user imports.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEV = LIB / "devices/juniper/ex2500-24f"
INCH = 25.4


def load():
    return yaml.safe_load((DEV / "device.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def by_ref(d, view, ref):
    return [p for p in placements(d, view) if p["ref"] == ref]


def export(part):
    path = LIB / "exports/netbox/device-types/Juniper" / f"{part}.yaml"
    return yaml.safe_load(path.read_text())


def test_the_device_has_a_layout_a_device_and_a_lock():
    for name in ("layout.yaml", "device.yaml", "device.lock.json"):
        assert (DEV / name).is_file(), name


def test_the_maker_and_the_names_are_as_printed():
    d = load()
    assert d["manufacturer"] == "Juniper"
    assert d["model"] == "EX2500-24F"
    assert d["portfolio"] == {"line": "EX Series", "family": "EX2500"}
    assert d["maturity"] == "modelled"


def test_the_envelope_is_table_12():
    """Table 12: 1.73 x 17.3 x 15.0 in (4.4 x 43.9 x 38.1 cm), 6.4 kg, the same for both models."""
    c = load()["chassis"]
    assert c["ru"] == 1
    assert c["height"] == pytest.approx(1.73 * INCH, abs=0.2)
    assert c["width"] == pytest.approx(43.9 * 10, abs=0.3)
    assert c["depth"] == pytest.approx(38.1 * 10, abs=0.3)
    assert c["weight-kg"] == pytest.approx(6.4)
    assert c["airflow"] == "front-to-back"
    assert c["power"] == "ac"


def test_the_front_has_the_24_sfp_plus_ports_numbered_as_printed():
    d = load()
    ports = by_ref(d, "front", "std/sfp-ganged@1")
    assert sorted(int(p["id"].split("-")[1]) for p in ports) == list(range(1, 25))
    assert {p["group"] for p in ports} == {"sfp-plus"}
    g = d["groups"]["sfp-plus"]
    assert g["attrs"] == {"media": "sfp-plus", "speed": "10g"}
    assert g["index-origin"] == 1
    numerals = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
                if (s.get("for") or "").startswith("port-")}
    assert numerals == {f"port-{k}": str(k) for k in range(1, 25)}


def test_the_ports_stand_in_six_gangs_of_four():
    xs = [p["at"][0] for p in sorted(by_ref(load(), "front", "std/sfp-ganged@1"),
                                     key=lambda p: int(p["id"].split("-")[1]))]
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    within = {s for i, s in enumerate(steps, 1) if i % 4}
    between = {s for i, s in enumerate(steps, 1) if not i % 4}
    assert len(within) == 1 and len(between) == 1
    assert between.pop() > within.pop()


def test_each_port_has_a_speed_lamp_and_a_link_activity_lamp():
    d = load()
    lamps = {p["id"]: p for p in by_ref(d, "front", "common/led-dot@1")}
    for k in range(1, 25):
        assert f"led-port-{k}" in lamps, k
        assert f"led-port-{k}-speed" in lamps, k
    # Table 10: L/A is green with a link and blinks with traffic; SP is green at 10 Gbps, off at 1 Gbps
    link = {s["name"] if isinstance(s, dict) else s for s in d["groups"]["sfp-plus-activity-leds"]["states"]}
    assert link == {"off", "link", "activity"}
    speed = {s["name"] if isinstance(s, dict) else s for s in d["groups"]["sfp-plus-speed-leds"]["states"]}
    assert speed == {"off", "10g"}


def test_the_front_carries_two_management_jacks_a_mini_usb_console_and_a_reset_button():
    d = load()
    jacks = by_ref(d, "front", "common/rj45-ganged-eth@1")
    assert sorted(p["id"] for p in jacks) == ["mgmt-a", "mgmt-b"]
    for p in jacks:
        assert p["attrs"] == {"media": "rj45", "speed": "1g", "role": "mgmt"}
    # the figure prints B over A, and the jack of the upper port is turned so its lamps are on top
    assert {p["id"]: p.get("rotate", 0) for p in jacks} == {"mgmt-a": 0, "mgmt-b": 180}
    top = {p["id"]: p["at"][1] for p in jacks}
    assert top["mgmt-b"] < top["mgmt-a"]
    (console,) = by_ref(d, "front", "std/mini-usb@1")
    assert console["attrs"] == {"role": "console"}
    (reset,) = by_ref(d, "front", "common/reset-button@1")
    assert reset["id"] == "btn-reset"


def test_the_four_chassis_lamps_are_the_guides_table_8():
    d = load()
    lamps = {p["id"]: p for p in by_ref(d, "front", "common/led-dot@1") if p["group"] == "status-leds"}
    assert set(lamps) == {"led-sys", "led-fan", "led-st-a", "led-st-b"}
    assert sorted(p["at"][1] for p in lamps.values()) == [p["at"][1] for p in sorted(
        lamps.values(), key=lambda p: ["led-sys", "led-fan", "led-st-a", "led-st-b"].index(p["id"]))]


def test_the_rear_has_two_ac_inlets_and_the_supplies_and_fans_are_built_in():
    d = load()
    inlets = by_ref(d, "rear", "std/c14-inlet@1")
    assert len(inlets) == 2
    assert {p["group"] for p in inlets} == {"power-input"}
    # the guide: two internal supplies with an IEC 320 inlet each, six internal fans that are not
    # customer replaceable, so no view has a bay
    for view in d["views"].values():
        assert not (view.get("components") or {}).get("bays")
    assert {"fans", "psus"}.isdisjoint(d["groups"])


def test_the_rear_carries_the_earth_symbol_the_guide_draws_and_no_invented_hardware():
    """Figure 2 draws a circled earth symbol at the left of the left inlet on the bare panel, and no lug,
    stud or screw at it."""
    d = load()
    (mark,) = by_ref(d, "rear", "common/ground-symbol@1")
    assert mark["for"] == "chassis"
    left_inlet = min(by_ref(d, "rear", "std/c14-inlet@1"), key=lambda p: p["at"][0])
    assert mark["at"][0] + 3.0 < left_inlet["at"][0]
    earth_hardware = [p["ref"] for p in placements(d, "rear") if "ground" in p["ref"] and p is not mark]
    assert earth_hardware == []


def test_the_two_models_are_configurations_that_differ_in_airflow():
    d = load()
    cfg = d["configurations"]
    assert {k: v["kind"] for k, v in cfg.items()} == {"fb": "base", "bf": "orderable"}
    assert cfg["fb"].get("default") is True
    assert set(cfg["fb"]["part-numbers"]) == {"EX2500-24F-FB"}
    assert set(cfg["bf"]["part-numbers"]) == {"EX2500-24F-BF"}
    assert cfg["bf"]["airflow"] == "back-to-front"
    assert "airflow" not in cfg["fb"]


@pytest.mark.parametrize("part,airflow", [("EX2500-24F-FB", "front-to-rear"), ("EX2500-24F-BF", "rear-to-front")])
def test_each_model_is_exported_with_its_airflow(part, airflow):
    e = export(part)
    assert e["manufacturer"] == "Juniper"
    assert e["model"] == part
    assert e["u_height"] == 1.0
    assert e["airflow"] == airflow
    sfp = [i for i in e["interfaces"] if i["type"] == "10gbase-x-sfpp"]
    assert len(sfp) == 24
    assert sum(1 for i in e["interfaces"] if i.get("mgmt_only")) == 2
    assert "module-bays" not in e
