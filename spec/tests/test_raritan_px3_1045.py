"""The Raritan PX3-1045, a 0U rack PDU with 36 IEC C13 outlets in two circuits of 18.

What is true of the library once the device is in it: the device exists under its
maker, its outline is the printed unit size, its 36 outlets are C13, each runs through
one of two breakers (18 each), the outlets stand 24.0 mm apart inside a group of three,
the rear carries two mounting buttons 1244.0 apart, every side is drawn or says why not,
the controller's two Ethernet jacks are the device's interfaces, and every estimate or
borrowed shape is declared in the device's provenance, its gaps or the part's contract.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "raritan" / "px3-1045" / "device.yaml"
COMPONENTS = ROOT / "library" / "components" / "raritan"
C13 = "std/c13-outlet"
NEW_PARTS = ("px3-breaker", "px3-mounting-button", "px3-cord-60309")


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _device():
    return _load(DEVICE)


def _placements(dev, view=None):
    out = []
    for name, v in dev.get("views", {}).items():
        if view and name != view:
            continue
        out.extend((v.get("components") or {}).get("placements") or [])
    return out


def _outlets(dev):
    return [p for p in _placements(dev) if p["ref"].split("@")[0] == C13]


def test_the_device_exists_under_its_maker_and_is_modelled():
    dev = _device()
    assert dev["manufacturer"] == "Raritan"
    assert dev["model"] == "PX3-1045"
    assert dev["maturity"] == "modelled"


def test_the_outline_is_the_printed_unit_size():
    chassis = _device()["chassis"]
    assert (chassis["width"], chassis["depth"], chassis["height"]) == (52, 55, 1780)
    assert chassis["mount"] == "rack-side"


def test_every_side_is_drawn_or_says_why_it_is_not():
    views = _device()["views"]
    assert set(views) == {"front", "rear", "top", "bottom", "left", "right"}
    for name in ("top", "bottom", "left", "right"):
        view = views[name]
        assert view.get("panel") or view.get("components") or view.get("empty"), name


def test_the_outlets_are_thirty_six_c13_numbered_one_to_thirty_six():
    ids = sorted(int(p["id"].rsplit("-", 1)[1]) for p in _outlets(_device()))
    assert ids == list(range(1, 37))


def test_each_circuit_of_eighteen_outlets_runs_through_its_own_breaker():
    dev = _device()
    breakers = [p["id"] for p in _placements(dev) if p["ref"].startswith("raritan/px3-breaker")]
    assert len(breakers) == 2
    per = {b: 0 for b in breakers}
    for outlet in _outlets(dev):
        assert outlet["through"] in per, outlet["id"]
        per[outlet["through"]] += 1
    assert sorted(per.values()) == [18, 18]


def test_neighbouring_outlets_of_a_group_stand_24_mm_apart():
    outlets = sorted(_outlets(_device()), key=lambda p: p["at"][1])
    ys = [p["at"][1] for p in outlets]
    steps = [round(b - a, 2) for a, b in zip(ys, ys[1:])]
    assert steps.count(24.0) == 24, steps
    # groups of three: after two 24.0 steps comes a wider gap, never a third 24.0
    for i in range(0, 34, 3):
        assert steps[i:i + 2] == [24.0, 24.0], i
    assert all(step > 24.0 for step in steps[2::3])


def test_the_rear_carries_two_buttons_1244_apart():
    buttons = [p for p in _placements(_device(), "rear") if p["ref"].startswith("raritan/px3-mounting-button")]
    assert len(buttons) == 2
    ys = sorted(p["at"][1] for p in buttons)
    assert round(ys[1] - ys[0], 2) == 1244.0


def test_the_two_ethernet_jacks_are_the_interfaces():
    interfaces = _device()["interfaces"]
    physical = [i["physical"] for i in interfaces]
    assert "eth-1" in physical and "eth-2" in physical
    placed = {p["id"] for p in _placements(_device(), "front")}
    assert {"eth-1", "eth-2"} <= placed


def test_the_new_parts_declare_what_is_estimated():
    for name in NEW_PARTS:
        contract = _load(COMPONENTS / name / "v1" / "contract.yaml")
        assert contract["version"] == "1.0.0", name
        text = yaml.safe_dump(contract.get("provenance") or {})
        assert "estimated" in text.lower() or "borrowed" in text.lower() or "drawing" in text.lower(), name


def test_positions_read_off_a_photograph_are_marked_as_such():
    dev = _device()
    assert dev["provenance"]["front"]["confidence"] in ("photo-measured", "estimated")
    gaps = {g["what"] for g in dev.get("gaps", [])}
    assert "controller-layout" in gaps and "numbering-direction" in gaps, gaps
