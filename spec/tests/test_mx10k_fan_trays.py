"""The MX10000-line fan trays are drawn to the hardware guides' size, and the bays are cut to fit them.

The four Juniper guides give the tray 6.6 in. (16.8 cm) wide: the MX10004 guide's Table 9, the MX10008
guide's Table 12, the MX10016 guide's Table 7 and the QFX10016 guide's Table 8. The same tables give the
height (12.08 in. on the MX10004, 22.4 in. on the MX10008, 36.6 in. on the MX10016, where the FAN2's
inch column says 36.5 and its centimetre column the same 92.97 cm) and the depth without handles.
Version 1 of the six parts was drawn 176 mm wide from a photograph and two line drawings, which is wider
than the guides' tray and wider than the 175 mm bay it was seated in. Version 2 is the guides' size.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

GUIDE_WIDTH = 167.6  # 6.6 in. (16.8 cm), the same in all four guides' tables

# part -> (w, h, d) from the guide's table; d is the depth without handles
GUIDE = {
    "jnp10004-fan2": (167.6, 306.8, 139.7),  # MX10004 Table 9: 12.08 in. (30.68 cm), 5.5 in. (13.97 cm)
    "jnp10008-fan": (167.6, 569.0, 102.0),  # MX10008 Table 12: 22.4 in. (56.9 cm), 4.0 in. (10.2 cm)
    "jnp10008-fan2": (167.6, 569.0, 139.7),  # 5.5 in. (13.97 cm)
    "jnp10008-fan3": (167.6, 569.0, 147.3),  # 5.8 in. (14.73 cm)
    "jnp10016-fan": (167.6, 929.6, 102.0),  # MX10016 Table 7: 36.6 in. (92.97 cm), 4.0 in. (10.2 cm)
    "jnp10016-fan2": (167.6, 929.6, 139.7),  # 36.5 in. but 92.97 cm; 5.5 in. (13.97 cm)
}
MX = ["mx10004", "mx10008", "mx10016"]
SEATED_IN = MX + ["qfx10008"]  # the QFX10008 accepts the MX10008 trays in its own bays


def load_device(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    path = LIB / "components" / ns / name / f"v{major}" / "contract.yaml"
    return yaml.safe_load(path.read_text())


def fan_bays(dev):
    bays = (dev["views"]["rear"].get("components") or {}).get("bays") or []
    return [b for b in bays if b["id"].startswith("fan")]


def seated_trays(name):
    """Every MX-line tray a device's fan bays accept, with the bay."""
    for b in fan_bays(load_device(name)):
        for ref in b["accepts"]:
            if ref.split("/")[1].split("@")[0] in GUIDE:
                yield b, ref


@pytest.mark.parametrize("name", SEATED_IN)
def test_no_fan_tray_is_wider_than_the_guides_or_its_bay(name):
    seen = 0
    for b, ref in seated_trays(name):
        seen += 1
        size = contract(ref)["size"]
        assert size["w"] <= GUIDE_WIDTH + 0.05, (name, b["id"], ref, size["w"])
        assert size["w"] <= b["size"]["w"] + 1e-6, (name, b["id"], ref, size["w"], b["size"]["w"])
        assert size["h"] <= b["size"]["h"] + 1e-6, (name, b["id"], ref, size["h"], b["size"]["h"])
    assert seen


@pytest.mark.parametrize("part", sorted(GUIDE))
def test_version_2_is_the_guides_size_and_version_1_is_retired(part):
    w, h, d = GUIDE[part]
    v2 = contract(f"juniper/{part}@2")
    assert (v2["size"]["w"], v2["size"]["h"], v2["size"]["d"]) == (w, h, d)
    assert "superseded-by" not in v2
    v1 = contract(f"juniper/{part}@1")
    assert v1["superseded-by"] == f"juniper/{part}@2"
    assert v1["size"]["w"] == 176.0, "version 1 is kept as it was drawn, not edited"


@pytest.mark.parametrize("name", SEATED_IN)
def test_every_fan_bay_accepts_version_2_and_no_version_1(name):
    for b, ref in seated_trays(name):
        assert ref.endswith("@2"), (name, b["id"], ref)
        if "default" in b and b["default"].split("/")[1].split("@")[0] in GUIDE:
            assert b["default"].endswith("@2"), (name, b["id"])


@pytest.mark.parametrize("name", SEATED_IN)
def test_a_fan_tray_that_is_fitted_is_version_2(name):
    dev = load_device(name)
    for cid, cfg in dev["configurations"].items():
        for bay, ref in (cfg.get("bays") or {}).items():
            if bay.startswith("fan") and ref.split("/")[1].split("@")[0] in GUIDE:
                assert ref.endswith("@2"), (name, cid, bay, ref)


@pytest.mark.parametrize("name", MX)
def test_the_mx_fan_bays_are_the_trays_size_and_sit_beside_the_supplies(name):
    """Figure 3 and Figure 21 (MX10004) and the other guides' rears: two trays side by side, against the supply column."""
    dev = load_device(name)
    face = dev["views"]["rear"]["size"]
    bays = sorted(fan_bays(dev), key=lambda b: b["at"][0])
    assert len(bays) == 2
    supplies = [b for b in dev["views"]["rear"]["components"]["bays"] if b["id"].startswith("psu")]
    column_right = max(b["at"][0] + b["size"]["w"] for b in supplies)
    for b in bays:
        w, h = b["size"]["w"], b["size"]["h"]
        for ref in b["accepts"]:
            part = contract(ref)["size"]
            assert (w, h) == (part["w"], part["h"]), (name, b["id"], ref)
        assert b["at"][0] + w <= face["w"] + 1e-6 and b["at"][1] + h <= face["h"] + 1e-6, (name, b["id"])
    left, right = bays
    assert left["at"][0] - column_right == pytest.approx(0.0, abs=1.0), name
    assert right["at"][0] - (left["at"][0] + left["size"]["w"]) == pytest.approx(0.0, abs=1.0), name
    assert left["at"][1] == right["at"][1]


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


def test_nothing_in_the_library_seats_version_1_of_a_fan_tray():
    """A whole-string match: a note may name a retired part in a sentence, and no list or field may name it alone."""
    retired = {f"juniper/{p}@1" for p in GUIDE}
    files = sorted((LIB / "devices").glob("*/*/device.yaml")) + sorted((LIB / "devices").glob("*/*/layout.yaml"))
    files += sorted((LIB / "components").glob("*/*/v*/contract.yaml"))
    assert len(files) > 400
    for path in files:
        doc = yaml.safe_load(path.read_text()) or {}
        if path.parts[-3] in GUIDE and path.parts[-2] == "v1":
            continue
        for s in strings(doc):
            assert not ({p.strip() for p in s.split(",")} & retired), (path, s)
