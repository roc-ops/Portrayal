"""The USB and mixed forms of the Perle IOLAN SCG expandable chassis.

Each of the six devices fills the rear bays with 16-port modules. A USB module is 16 USB-A ports in two bands of
four columns, as the installation guide's page 9 photograph shows. The tests read each device file and its layout.
They read no built library, and they state what holds of the devices and nothing about any other part.
"""
from pathlib import Path

import pytest
import yaml

DEVICES = Path(__file__).resolve().parents[2] / "library" / "devices" / "perle"
BAY_LEFT = {1: 39.0, 2: 155.4, 3: 271.8}
MODULE_W = 116.4
USB_W = 12.0

# device: (the module in each bay, in order; "usb", "rj45" or "-" for an empty bay)
FORMS = {
    "iolan-scg18-u": ("usb", "-", "-"),
    "iolan-scg34-u": ("usb", "usb", "-"),
    "iolan-scg34-ru": ("rj45", "usb", "-"),
    "iolan-scg50-u": ("usb", "usb", "usb"),
    "iolan-scg50-rru": ("rj45", "usb", "rj45"),
    "iolan-scg50-ruu": ("rj45", "usb", "usb"),
}


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def rear_parts(name):
    comp = load(name)["views"]["rear"]["components"]
    return comp.get("placements", []), comp.get("blocks", []), comp.get("bays", [])


def usb_ports(name):
    placements, _, _ = rear_parts(name)
    return [p for p in placements if str(p.get("ref", "")).startswith("std/usb-a@")]


def bay_of(x):
    for bay, left in BAY_LEFT.items():
        if left <= x < left + MODULE_W:
            return bay
    return None


@pytest.mark.parametrize("name", FORMS)
def test_the_device_exists_with_its_layout(name):
    assert (DEVICES / name / "device.yaml").exists()
    assert (DEVICES / name / "layout.yaml").exists()


@pytest.mark.parametrize("name", FORMS)
def test_the_usb_ports_are_sixteen_to_a_usb_module(name):
    want = 16 * FORMS[name].count("usb")
    assert len(usb_ports(name)) == want


@pytest.mark.parametrize("name", FORMS)
def test_each_usb_module_holds_its_sixteen_ports_in_its_own_bay(name):
    per_bay = {}
    for p in usb_ports(name):
        per_bay.setdefault(bay_of(p["at"][0]), []).append(p)
    for bay, kind in enumerate(FORMS[name], start=1):
        assert len(per_bay.get(bay, [])) == (16 if kind == "usb" else 0), (name, bay)
    assert None not in per_bay


@pytest.mark.parametrize("name", FORMS)
def test_a_usb_module_has_two_bands_of_four_columns_of_pairs(name):
    for bay, kind in enumerate(FORMS[name], start=1):
        if kind != "usb":
            continue
        ports = [p for p in usb_ports(name) if bay_of(p["at"][0]) == bay]
        upper = {p["at"][0] for p in ports if p["at"][1] < 20}
        lower = {p["at"][0] for p in ports if p["at"][1] >= 20}
        assert len(upper) == 4 and len(lower) == 4, (name, bay)
        assert all(abs(b - a - 14.0) < 0.5 for a, b in zip(sorted(upper), sorted(lower))), (name, bay)


@pytest.mark.parametrize("name", FORMS)
def test_the_usb_ports_are_numbered_in_one_run_and_never_overlap(name):
    ports = usb_ports(name)
    assert sorted(p["rel-pos"] for p in ports) == list(range(1, len(ports) + 1))
    ids = [p["id"] for p in ports]
    assert len(ids) == len(set(ids))
    boxes = [(p["at"][0], p["at"][1], p["at"][0] + USB_W, p["at"][1] + 4.5) for p in ports]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]


@pytest.mark.parametrize("name", FORMS)
def test_every_usb_port_has_a_cutout_on_the_rear_panel(name):
    cut = {c["id"] for c in load(name)["views"]["rear"]["panel"].get("cutouts", []) if "id" in c}
    assert {p["id"] for p in usb_ports(name)} <= cut


@pytest.mark.parametrize("name", FORMS)
def test_the_rj45_modules_hold_sixteen_jacks_each(name):
    placements, _, _ = rear_parts(name)
    jacks = [p for p in placements if "rj45-ganged" in str(p.get("ref", ""))]
    assert len(jacks) == 16 * FORMS[name].count("rj45")


@pytest.mark.parametrize("name", FORMS)
def test_each_rj45_module_sits_in_the_bay_the_photograph_shows(name):
    placements, _, _ = rear_parts(name)
    per_bay = {}
    for p in placements:
        if "rj45-ganged" in str(p.get("ref", "")):
            per_bay.setdefault(bay_of(p["at"][0]), []).append(p)
    for bay, kind in enumerate(FORMS[name], start=1):
        assert len(per_bay.get(bay, [])) == (16 if kind == "rj45" else 0), (name, bay)


@pytest.mark.parametrize("name", FORMS)
def test_each_fitted_module_has_two_thumbscrews_in_its_own_bay(name):
    decor = load(name)["views"]["rear"]["panel"]["decor"]
    screws = [d for d in decor if d.get("kind") == "thumbscrew"]
    per_bay = {}
    for d in screws:
        per_bay.setdefault(bay_of(d["at"][0] + d["size"][0] / 2), []).append(d)
    for bay, kind in enumerate(FORMS[name], start=1):
        assert len(per_bay.get(bay, [])) == (0 if kind == "-" else 2), (name, bay)
    seams = [d for d in decor if d.get("kind") == "seam" and d["at"][1] < 10 and d["size"][1] > 40]
    assert len(seams) == 2


@pytest.mark.parametrize("name", FORMS)
def test_the_empty_bays_are_declared_and_the_fitted_ones_are_not(name):
    _, _, bays = rear_parts(name)
    declared = {b["id"] for b in bays}
    empty = {f"bay-{i}" for i, kind in enumerate(FORMS[name], start=1) if kind == "-"}
    assert declared == empty


@pytest.mark.parametrize("name", FORMS)
def test_the_face_sizes_are_the_chassis(name):
    views = load(name)["views"]
    assert views["rear"]["size"] == {"w": 436, "h": 44}
    assert views["front"]["size"]["h"] == 44
    assert views["top"]["size"] == {"w": 436, "h": 262}


@pytest.mark.parametrize("name", FORMS)
def test_no_cellular_part_is_drawn_on_a_non_cellular_form(name):
    text = (DEVICES / name / "device.yaml").read_text()
    assert "sma-jack" not in text and "scg-sim-slot" not in text
