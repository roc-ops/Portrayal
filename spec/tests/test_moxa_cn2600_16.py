"""The Moxa CN2600 16-port terminal servers are in the library: six faces, the ears and their parts.

The four models share one body and one front. They differ in the serial standard, the weight and the number of AC inlets: the
-2AC models have two, the others one. The rear has a ground screw, a console jack, two LAN jacks and sixteen RJ45 serial ports in
two groups of eight. The sides, the underside and the ears are read from the maker's CAD sheet and declared estimates.

These read the library and the registry and render nothing; they read no library/dist, except the device-type exports.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

MODELS = {"cn2610-16-2ac": ("CN2610-16-2AC", 2), "cn2650-16-2ac": ("CN2650-16-2AC", 2),
          "cn2610-16": ("CN2610-16", 1), "cn2650-16": ("CN2650-16", 1)}
WEIGHT = {"cn2610-16-2ac": 2.64, "cn2650-16-2ac": 2.64, "cn2610-16": 2.46, "cn2650-16": 2.46}


def device(slug):
    return yaml.safe_load((LIB / "devices" / "moxa" / slug / "device.yaml").read_text())


def placements(dev, view):
    return {p["id"]: p for p in dev["views"][view]["components"].get("placements", [])}


def decor(dev, view):
    return {x["id"]: x for x in dev["views"][view]["panel"]["decor"]}


@pytest.mark.parametrize("slug", MODELS)
def test_the_body_is_the_one_the_data_sheet_dimensions(slug):
    d = device(slug)
    assert d["manufacturer"] == "Moxa" and d["model"] == MODELS[slug][0]
    c = d["chassis"]
    assert (c["width"], c["height"], c["depth"]) == (440, 45.5, 198)
    for face, size in {"front": (440, 45.5), "rear": (440, 45.5), "top": (440, 198),
                       "bottom": (440, 198), "left": (198, 45.5), "right": (198, 45.5)}.items():
        assert (d["views"][face]["size"]["w"], d["views"][face]["size"]["h"]) == size, face
    assert d["attrs"]["physical"]["weight-kg"] == WEIGHT[slug]


@pytest.mark.parametrize("slug", MODELS)
def test_the_rear_has_sixteen_numbered_serial_ports_a_console_jack_and_two_lan_jacks(slug):
    d = device(slug)
    rear = placements(d, "rear")
    ports = [p for p in rear.values() if p.get("group") == "serial"]
    assert sorted(p["rel-pos"] for p in ports) == list(range(1, 17))
    assert {p["attrs"]["role"] for p in ports} == {"console-server"}
    assert rear["console"]["ref"] == "std/rj45@2" and rear["console"]["attrs"]["role"] == "console"
    assert [rear[i]["ref"] for i in ("lan-1", "lan-2")] == ["common/rj45-eth@1"] * 2
    assert rear["console"]["at"][0] < rear["lan-1"]["at"][0] < rear["lan-2"]["at"][0]


@pytest.mark.parametrize("slug,spec", MODELS.items())
def test_the_two_ac_models_have_two_inlets_with_a_switch_each_and_the_others_one(slug, spec):
    rear = placements(device(slug), "rear")
    inlets = {i for i in rear if i.startswith("inlet")}
    assert inlets == ({"inlet-1", "inlet-2"} if spec[1] == 2 else {"inlet"})
    for i in inlets:
        assert rear[i]["ref"] == "std/c14-inlet@1"
    switches = {i: p for i, p in rear.items() if p["ref"] == "moxa/nport-5600-power-rocker@1"}
    assert sorted(p["for"] for p in switches.values()) == sorted(inlets)
    assert "ground" in rear


@pytest.mark.parametrize("slug", MODELS)
def test_each_front_has_the_lcd_keys_and_two_lamps_per_serial_port_and_the_system_lamps(slug):
    front = placements(device(slug), "front")
    assert front["lcm"]["ref"] == "moxa/nport-5600-lcm@1" and front["keys"]["ref"] == "moxa/nport-5600-keys@1"
    assert {i for i in front if i.startswith("led-tx-")} == {f"led-tx-{n}" for n in range(1, 17)}
    assert {i for i in front if i.startswith("led-rx-")} == {f"led-rx-{n}" for n in range(1, 17)}
    for lamp in ("led-ready", "led-lan1", "led-lan2", "led-pwr1", "led-pwr2", "reset"):
        assert lamp in front
    assert all(p["states"] == ["off", "on"] for i, p in front.items() if i.startswith("led-"))


@pytest.mark.parametrize("slug", MODELS)
def test_the_ears_are_stated_once_and_the_sides_and_underside_are_drawn(slug):
    d = device(slug)
    ears = d["chassis"]["ears"]["positions"]
    assert len(ears) == 1 and ears[0]["default"] is True
    left, right, bottom = decor(d, "left"), decor(d, "right"), decor(d, "bottom")
    for side in (left, right):
        assert sum(1 for i in side if i.startswith("body-hole-") and not i.endswith("-centre")) == 4
        assert sum(1 for i in side if i.startswith("front-hole-") and not i.endswith("-centre")) == 6
        assert "front-plate" in side and "front-fold" in side
    assert sum(1 for i in bottom if i.startswith("round-hole-")) == 4
    assert sum(1 for i in bottom if i.startswith("tab-") and not i.endswith("-bar")) == 6
    assert "rear-plate" in bottom


@pytest.mark.parametrize("slug", MODELS)
def test_the_notes_state_the_latch_side_down_and_the_environment_on_page_five(slug):
    notes = device(slug)["provenance"]
    assert "latch side is down" in notes["serial-ports"]["note"]
    assert "page 5 power, dimensions and environment" in notes["sources"]["note"]
    assert "page 6 safety and package" in notes["sources"]["note"]


@pytest.mark.parametrize("slug", MODELS)
def test_the_rear_inlets_gap_covers_the_four_views_that_show_the_inlet_strip(slug):
    gap = {g["what"]: g for g in device(slug)["gaps"]}["rear-inlets"]
    assert gap["reason"] == "needs-drawing"
    assert sorted(gap["scope"]) == ["bottom", "left", "right", "top"]
    assert "left and right" in gap["note"]


@pytest.mark.parametrize("slug", MODELS)
def test_the_right_side_is_the_left_mirrored_in_depth(slug):
    d = device(slug)
    left, right = decor(d, "left"), decor(d, "right")
    for ident, item in left.items():
        if ident == "side-plate":
            continue
        other = right[ident]
        assert abs(other["at"][0] + other["size"][0] - (198 - item["at"][0])) < 0.02, ident
        assert other["at"][1] == item["at"][1], ident


@pytest.mark.parametrize("slug,spec", MODELS.items())
@pytest.mark.parametrize("export", ["netbox", "nautobot"])
def test_each_device_type_is_exported_under_the_model_name(slug, spec, export):
    path = LIB / "exports" / export / "device-types" / "Moxa" / f"{spec[0]}.yaml"
    doc = yaml.safe_load(path.read_text())
    assert doc["model"] == spec[0]
    names = [p["name"] for p in doc["console-server-ports"]]
    assert [f"port-{n}" for n in range(1, 17)] == [n for n in names if n.startswith("port-")]
