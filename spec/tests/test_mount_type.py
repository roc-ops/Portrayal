"""How a box is installed, and what its DCIM export says about it (#734).

`ru` was the only mounting fact a device could state, and the export read it
as `ch.get("ru", 1)`. Every device that left it out exported as a 1U,
full-depth rack device:

    readylinks/gl-8xep   wall-mount unit        u_height 1.0, full depth
    halny/hlx-tgv        desktop ONT            u_height 1.0, full depth
    dell/r740xd          2U rack server         u_height 1.0

An omission and a box that is not racked looked the same. `chassis.mount`
makes the difference a statement - absent means `rack` - and L125 holds `ru`
to it. A box that is not racked exports `u_height: 0` and
`is_full_depth: false`, which is how the NetBox and Nautobot community
libraries write wall and desktop hardware.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

from portrayal import dcim_export as dx   # noqa: E402
from portrayal import libwalk             # noqa: E402
from portrayal import lint                # noqa: E402

NOT_RACKED = ("din-rail", "wall", "desktop")
# occupies no rack unit, but bolts to rack holes and so still states `ru`
ON_THE_RAIL_FACE = "rack-face"
NO_RACK_UNIT = NOT_RACKED + (ON_THE_RAIL_FACE,)


# --- the export --------------------------------------------------------------

def test_a_rack_device_exports_its_rack_units_and_full_depth():
    assert dx.u_height({"ru": 2}) == 2.0
    assert dx.u_height({"ru": 2, "mount": "rack"}) == 2.0
    assert dx.is_full_depth({"ru": 2}) is True


@pytest.mark.parametrize("mount", NO_RACK_UNIT)
def test_a_box_that_is_not_racked_exports_no_rack_units(mount):
    ch = {"mount": mount}
    assert dx.u_height(ch) == 0.0
    assert dx.is_full_depth(ch) is False


@pytest.mark.parametrize("mount", NO_RACK_UNIT)
def test_the_mount_is_said_in_the_comments(mount):
    """Neither DCIM has a field for it, and `u_height: 0` alone does not tell a
    DIN-rail switch from a desktop ONT."""
    dev = {"chassis": {"mount": mount}}
    assert dx.MOUNT_PROSE[mount] in dx.comments_for(dev, "base", {})


def test_a_rack_face_part_exports_no_rack_units_though_it_states_some():
    ch = {"mount": "rack-face", "ru": 1}
    assert dx.u_height(ch) == 0.0
    assert dx.is_full_depth(ch) is False


def test_the_rack_face_mount_is_said_in_the_comments():
    dev = {"chassis": {"mount": "rack-face", "ru": 1}}
    assert dx.MOUNT_PROSE["rack-face"] in dx.comments_for(dev, "base", {})


def test_a_rack_device_says_nothing_about_mounting():
    body = dx.comments_for({"chassis": {"ru": 1}}, "base", {})
    assert not any(p in body for p in dx.MOUNT_PROSE.values())


def test_every_mount_the_schema_allows_is_handled():
    """A value added to the enum without prose would export silently."""
    import json
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    enum = _find_mount_enum(schema)
    assert enum and "rack" in enum
    assert set(enum) - {"rack"} == set(dx.MOUNT_PROSE)


def _find_mount_enum(node):
    if isinstance(node, dict):
        if "mount" in node and isinstance(node["mount"], dict) and "enum" in node["mount"]:
            return node["mount"]["enum"]
        for v in node.values():
            got = _find_mount_enum(v)
            if got:
                return got
    return None


# --- L125 --------------------------------------------------------------------

def findings(doc):
    with lint.collecting() as found:
        lint.lint_device_mount("device.yaml", doc)
    return [m for m in found.errors + found.warnings if "[L125]" in m]


def test_L125_a_rack_device_states_its_rack_units():
    assert findings({"chassis": {"width": 440}})
    assert findings({"chassis": {"width": 440, "mount": "rack"}})
    assert not findings({"chassis": {"width": 440, "ru": 1}})


def test_L125_a_rack_face_part_states_its_rack_units():
    assert findings({"chassis": {"mount": "rack-face"}})
    assert not findings({"chassis": {"mount": "rack-face", "ru": 1}})


@pytest.mark.parametrize("mount", NOT_RACKED)
def test_L125_a_box_that_is_not_racked_states_no_rack_units(mount):
    assert not findings({"chassis": {"mount": mount}})
    assert findings({"chassis": {"mount": mount, "ru": 1}})


# --- the library -------------------------------------------------------------

def _devices():
    for path in libwalk.iter_devices([LIB]):
        doc = yaml.safe_load(path.read_text())
        if (doc or {}).get("kind") == "device":
            yield path, doc


def test_the_library_states_a_mount_for_every_box_that_is_not_racked():
    """Each device either has rack units, says how else it is installed, or
    waives L125 with its reason. The count guards against a vacuous pass."""
    seen, open_ = 0, []
    for path, doc in _devices():
        seen += 1
        ch = doc.get("chassis") or {}
        waived = "L125" in ((doc.get("lint") or {}).get("waive") or {})
        if ch.get("mount", "rack") == "rack" and "ru" not in ch and not waived:
            open_.append(str(path.parent.relative_to(LIB)))
    assert seen > 100
    assert not open_, open_


@pytest.mark.parametrize("tree", ["netbox", "nautobot"])
@pytest.mark.parametrize("vendor,model,want", [
    ("ReadyLinks", "GL-8xEP", 0.0),
    ("Halny", "HLX-TGV-EU", 0.0),
])
def test_the_exports_of_boxes_that_are_not_racked_occupy_no_rack(tree, vendor, model, want):
    path = LIB / "exports" / tree / "device-types" / vendor / f"{model}.yaml"
    doc = yaml.safe_load(path.read_text())
    assert doc["u_height"] == want
    assert doc["is_full_depth"] is False


@pytest.mark.parametrize("tree", ["netbox", "nautobot"])
def test_the_r740xd_exports_as_the_2u_server_it_is(tree):
    d = LIB / "exports" / tree / "device-types" / "Dell"
    files = sorted(d.glob("PowerEdge R740xd *.yaml"))
    assert files
    for f in files:
        assert yaml.safe_load(f.read_text())["u_height"] == 2.0, f.name


# --- L43 ---------------------------------------------------------------------

def _l43(doc):
    with lint.collecting() as found:
        lint.lint_device_rack_ears("device.yaml", doc)
    return [m for m in found.errors + found.warnings if "[L43]" in m]


def test_L43_a_rack_face_part_is_its_ears():
    """L43 says ears are never drawn and the body is the metal between them. A
    part that bolts to the rail face IS a pair of ears and whatever hangs off
    them - there is no body between the folds to draw instead - so a 483 mm
    front on one is the part, not a device modelled wearing its flanges."""
    views = {"front": {"size": {"w": 483.0, "h": 44.0}}}
    assert _l43({"chassis": {"width": 483.0, "ru": 1}, "views": views})
    assert not _l43({"chassis": {"width": 483.0, "ru": 1, "mount": "rack-face"}, "views": views})
