"""The Raritan PX4-132AWA-E7M26V2, PX4-5551WA-E7M26V2 and PX3-5469R rack PDUs.

What is true of the library once the three devices are in it: each exists under its maker with
the printed unit size, the PX4 pair carry C13 outlets first and the locking Cx outlet last in
every group at the printed 26.6 mm pitch, the PX3-5469R carries two rows of ten outlets (eight
C13 and two C19 in each), every side is drawn or says why not, the Cx outlet presents no
interface key, and every colour and every borrowed or estimated figure is declared as such.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "raritan"
COMPONENTS = ROOT / "library" / "components" / "raritan"
C13 = "std/c13-outlet"
C19 = "std/c19-outlet"
CX = "raritan/px4-cx-outlet"
PX4 = {"px4-132awa-e7m26v2": ("PX4-132AWA-E7M26V2", 18, 6), "px4-5551wa-e7m26v2": ("PX4-5551WA-E7M26V2", 12, 4)}
NEW_PARTS = ("px4-cx-outlet", "px4-breaker", "px4-universal-input", "px4-mounting-button", "px3-rear-cord-60309")
SIDES = {"front", "rear", "top", "bottom", "left", "right"}


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _device(name):
    return _load(DEVICES / name / "device.yaml")


def _placements(dev, view=None):
    out = []
    for name, v in dev.get("views", {}).items():
        if view and name != view:
            continue
        out.extend((v.get("components") or {}).get("placements") or [])
    return out


def _of(dev, ref, view="front"):
    return [p for p in _placements(dev, view) if p["ref"].split("@")[0] == ref]


def _text(node):
    return yaml.safe_dump(node).lower()


def test_each_device_exists_under_its_maker_and_is_modelled():
    for name, model in [(n, m[0]) for n, m in PX4.items()] + [("px3-5469r", "PX3-5469R")]:
        dev = _device(name)
        assert dev["manufacturer"] == "Raritan", name
        assert dev["model"] == model, name
        assert dev["maturity"] == "modelled", name


def test_the_outlines_are_the_printed_unit_sizes():
    for name in PX4:
        chassis = _device(name)["chassis"]
        assert (chassis["width"], chassis["depth"], chassis["height"]) == (56, 65, 1780), name
        assert chassis["mount"] == "rack-side", name
    chassis = _device("px3-5469r")["chassis"]
    assert (chassis["width"], chassis["depth"], chassis["height"]) == (440, 293, 88)
    assert chassis["mount"] == "rack"
    assert chassis["ru"] == 2


def test_every_side_is_drawn_or_says_why_it_is_not():
    for name in list(PX4) + ["px3-5469r"]:
        views = _device(name)["views"]
        assert set(views) == SIDES, name
        for side, view in views.items():
            assert view.get("panel") or view.get("components") or view.get("empty"), (name, side)


def test_each_px4_has_c13_outlets_first_and_cx_outlets_last_in_every_group():
    for name, (_, per_type, group) in PX4.items():
        dev = _device(name)
        outlets = sorted(
            (p for p in _placements(dev, "front") if p["id"].startswith("outlet-")),
            key=lambda p: int(p["id"].split("-")[1]),
        )
        assert len(outlets) == 2 * per_type, name
        refs = [p["ref"].split("@")[0] for p in outlets]
        assert refs.count(C13) == per_type and refs.count(CX) == per_type, name
        half = group // 2
        for g in range(0, len(refs), group):
            assert refs[g:g + group] == [C13] * half + [CX] * half, (name, g)


def test_outlets_of_a_px4_group_stand_26_6_mm_apart():
    for name, (_, per_type, group) in PX4.items():
        outlets = [p for p in _placements(_device(name), "front") if p["id"].startswith("outlet-")]
        outlets.sort(key=lambda p: -p["at"][1])  # from the cord end, which is drawn at the bottom
        for g in range(0, len(outlets), group):
            starts = [p["at"][1] + (22.0 if p["ref"].startswith(C13) else 24.0) for p in outlets[g:g + group]]
            steps = [round(a - b, 2) for a, b in zip(starts, starts[1:])]
            assert all(abs(s - 26.6) < 0.01 for s in steps[:2]), (name, g, steps)


def test_each_px4_has_six_breakers_and_a_controller_with_the_named_ports():
    for name in PX4:
        dev = _device(name)
        front = _placements(dev, "front")
        assert len([p for p in front if p["ref"].startswith("raritan/px4-breaker")]) == 6, name
        ids = {p["id"] for p in front}
        assert {"eth-1", "eth-2", "usb-a-1", "usb-a-2", "usb-b", "link", "sensor"} <= ids, name
        assert any(p["ref"].startswith("raritan/px4-universal-input") for p in front), name


def test_each_px4_rear_carries_two_mounting_buttons_1244_apart():
    for name in PX4:
        buttons = _of(_device(name), "raritan/px4-mounting-button", "rear")
        assert len(buttons) == 2, name
        ys = sorted(p["at"][1] for p in buttons)
        assert round(ys[1] - ys[0], 2) == 1244.0, name


def test_the_cx_outlet_presents_no_interface_key_and_says_what_is_estimated():
    contract = _load(COMPONENTS / "px4-cx-outlet" / "v1" / "contract.yaml")
    assert "interface" not in contract
    assert "estimate" in _text(contract["provenance"])


def test_the_px3_5469r_has_two_rows_of_ten_with_eight_c13_and_two_c19_in_each():
    dev = _device("px3-5469r")
    outlets = [p for p in _placements(dev, "front") if p["id"].startswith("outlet-")]
    assert len(outlets) == 20
    rows = {}
    for p in outlets:
        rows.setdefault(round(p["at"][1] + (22.0 if p["ref"].startswith(C13) else 27.7) / 2, 1), []).append(p)
    assert len(rows) == 2
    top, bottom = [sorted(r, key=lambda p: p["at"][0]) for _, r in sorted(rows.items())]
    for row in (top, bottom):
        assert [p["ref"].split("@")[0] for p in row] == [C13] * 8 + [C19] * 2
    gap = sorted(rows)[1] - sorted(rows)[0]
    assert 40 <= gap <= 46, gap


def test_the_px3_5469r_controller_panel_and_rear_panel_are_drawn():
    dev = _device("px3-5469r")
    front = {p["id"] for p in _placements(dev, "front")}
    assert {"display", "console", "usb-b", "usb-a", "button-up", "button-down", "button-ok", "button-back", "reset"} <= front
    rear = _placements(dev, "rear")
    assert {"sensor", "expansion", "eth", "feature"} <= {p["id"] for p in rear}
    assert any(p["ref"].startswith("raritan/px3-rear-cord") for p in rear)


def test_every_colour_and_borrowed_figure_is_declared_unchecked():
    for name in list(PX4) + ["px3-5469r"]:
        dev = _device(name)
        text = _text(dev["provenance"])
        assert "unchecked" in text and "colour" in text, name
        assert {"estimated", "photo-measured", "drawing"} & {v["confidence"] for v in dev["provenance"].values()}, name
    for part in NEW_PARTS:
        contract = _load(COMPONENTS / part / "v1" / "contract.yaml")
        assert contract["kind"] == "component", part
        assert "unchecked" in _text(contract["provenance"]), part


def test_what_no_source_places_is_a_gap_and_not_a_guess():
    for name in PX4:
        gaps = {g["what"] for g in _device(name).get("gaps", [])}
        assert {"breaker-feed", "controller-layout", "mount-marks", "sides"} <= gaps, (name, gaps)
    gaps = {g["what"] for g in _device("px3-5469r").get("gaps", [])}
    assert {"breakers", "rear-panel", "rack-kit", "numbering"} <= gaps, gaps
