"""The JNP10K-PWR-AC2 is drawn to the guides' 91.4 x 88.9 mm in every chassis that seats it.

Every Juniper hardware guide that lists the supply gives it as 3.5 in. high by 3.6 in. wide
(8.89 x 9.14 cm): the MX10004 guide's Table 22, the MX10008 guide's Table 55, the MX10016 guide's
Table 39 and the QFX10008 and QFX10016 guides' Table 16. Version 1 of `juniper/jnp10k-pwr-ac2` drew
84.0 x 97.0 mm from a photograph, and the MX10004, MX10008, MX10016 and QFX10016 seated it; version 2
is the guides' size. These tests keep all five chassis on version 2 and version 1 retired.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

V1, V2 = "juniper/jnp10k-pwr-ac2@1", "juniper/jnp10k-pwr-ac2@2"
BLNK1, BLNK2 = "juniper/jnp10k-pwr-blnk@1", "juniper/jnp10k-pwr-blnk@2"
FACE = {"w": 91.4, "h": 88.9}
# device -> supply bays in the rear, and what the guide lists the supply as
DEVICES = {"mx10004": 3, "mx10008": 6, "mx10016": 10, "qfx10008": 6, "qfx10016": 10}
MOVED = ["mx10004", "mx10008", "mx10016", "qfx10016"]


def load_device(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def load_contract(name, major):
    return yaml.safe_load((LIB / "components/juniper" / name / f"v{major}" / "contract.yaml").read_text())


def rear_bays(dev):
    return (dev["views"]["rear"].get("components") or {}).get("bays") or []


def supply_bays(dev):
    return [b for b in rear_bays(dev) if b["id"].startswith("psu")]


def box(b):
    x, y = b["at"]
    return x, y, x + b["size"]["w"], y + b["size"]["h"]


def overlap(a, b):
    ax0, ay0, ax1, ay1 = box(a)
    bx0, by0, bx1, by1 = box(b)
    return min(ax1, bx1) - max(ax0, bx0) > 1e-6 and min(ay1, by1) - max(ay0, by0) > 1e-6


@pytest.mark.parametrize("name", MOVED)
def test_every_supply_bay_is_the_guides_size_and_seats_version_2(name):
    bays = supply_bays(load_device(name))
    assert len(bays) == DEVICES[name]
    for b in bays:
        assert b["size"] == FACE, (name, b["id"])
        assert V2 in b["accepts"] and V1 not in b["accepts"], (name, b["id"])
        if "default" in b and b["default"].startswith("juniper/jnp10k-pwr-ac2"):
            assert b["default"] == V2, (name, b["id"])


@pytest.mark.parametrize("name", MOVED)
def test_a_supply_that_is_fitted_is_version_2(name):
    dev = load_device(name)
    for cid, cfg in dev["configurations"].items():
        for bay, ref in (cfg.get("bays") or {}).items():
            assert ref not in (V1, BLNK1), (name, cid, bay)


@pytest.mark.parametrize("name", ["mx10004", "mx10008", "mx10016"])
def test_the_mx_supply_cover_is_version_2_so_it_fills_the_bay_the_supply_does(name):
    """The cover takes the supply's own size (jnp10k-pwr-blnk, `derived`), so it follows it."""
    for b in supply_bays(load_device(name)):
        assert BLNK2 in b["accepts"] and BLNK1 not in b["accepts"], (name, b["id"])
    assert load_contract("jnp10k-pwr-blnk", 1)["superseded-by"] == BLNK2
    assert "superseded-by" not in load_contract("jnp10k-pwr-blnk", 2)
    assert load_contract("jnp10k-pwr-blnk", 2)["size"] == FACE


@pytest.mark.parametrize("name", sorted(DEVICES))
def test_the_supply_bays_clear_each_other_the_fan_trays_and_the_rear_face(name):
    dev = load_device(name)
    face = dev["views"]["rear"]["size"]
    bays = rear_bays(dev)
    for b in bays:
        x0, y0, x1, y1 = box(b)
        assert x0 >= 0 and y0 >= 0 and x1 <= face["w"] + 1e-6 and y1 <= face["h"] + 1e-6, (name, b["id"])
    for i, a in enumerate(bays):
        for b in bays[i + 1:]:
            assert not overlap(a, b), (name, a["id"], b["id"])


@pytest.mark.parametrize("name", sorted(DEVICES))
def test_the_supply_bays_stack_at_the_supplys_own_height(name):
    """Table 22, 55, 39 and 16 give the height, 3.5 in.: the supplies sit one above the next with no gap wider than a fraction of it."""
    bays = sorted(supply_bays(load_device(name)), key=lambda b: b["at"][1])
    for above, below in zip(bays, bays[1:]):
        gap = below["at"][1] - (above["at"][1] + above["size"]["h"])
        assert -1e-6 <= gap <= 1.0, (name, above["id"], below["id"], gap)


def test_version_1_is_retired_by_version_2():
    v1, v2 = load_contract("jnp10k-pwr-ac2", 1), load_contract("jnp10k-pwr-ac2", 2)
    assert v1["superseded-by"] == "juniper/jnp10k-pwr-ac2@2"
    assert "superseded-by" not in v2
    assert (v1["size"]["w"], v1["size"]["h"]) == (84.0, 97.0), "version 1 is kept as it was drawn, not edited"
    assert (v2["size"]["w"], v2["size"]["h"]) == (91.4, 88.9)


def strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from strings(k)
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)


@pytest.mark.heavy
def test_nothing_in_the_library_seats_version_1_of_the_supply_or_its_cover():
    """A whole-string match: a note may name a retired part in a sentence, and no list or field may name it alone."""
    files = sorted((LIB / "devices").glob("*/*/device.yaml")) + sorted((LIB / "devices").glob("*/*/layout.yaml"))
    files += sorted((LIB / "components").glob("*/*/v*/contract.yaml"))
    assert len(files) > 400
    for path in files:
        doc = yaml.safe_load(path.read_text()) or {}
        named = set(strings(doc))
        assert V1 not in named and BLNK1 not in named, path
