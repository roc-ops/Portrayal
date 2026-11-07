"""A breakout mode is `<count>x<speed>`, and the export says it on both targets.

`interfaces[].breakout.modes` of a listing or a device is the structured
breakout field. L195 holds its spelling to a count from 1 up, the letter `x`,
and a speed from the closed set in speeds.yaml, so a filter for ports that
break out can read the count in front of the `x`. The S9600 boxes whose SFP28
cages share QSFP28 port 0's lanes name that fact `sfp28-sharing`, as the three
other S9600-family boxes do; it is not a breakout.
"""
import pathlib
import subprocess
import sys

import pytest
import yaml

from portrayal import libwalk, lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
TOOL = ROOT / "spec/tools/portrayal/dcim_export.py"


def findings(doc):
    with lint.collecting() as found:
        lint.lint_breakout_modes(pathlib.Path("x/listing.yaml"), doc)
    return [e for e in found.errors if "[L195]" in e]


def rule(*modes):
    return {"interfaces": [{"physical": "port-{n}", "name": "Ethernet{n}", "range": "1-4",
                            "breakout": {"modes": list(modes)}}]}


# ---- the rule ------------------------------------------------------------------

def test_a_good_mode_passes():
    assert findings(rule("4x25g", "1x400g", "8x50g", "2x100g")) == []


@pytest.mark.parametrize("mode", ["4 x 25GE", "4x25", "0x25g", "04x25g", "4x25G", "4x7g", "x25g", "4x", ""])
def test_a_misspelt_mode_fails(mode):
    got = findings(rule("1x100g", mode))
    assert len(got) == 1 and repr(mode) in got[0], got


def test_the_set_is_read_from_speeds_yaml():
    assert "25g" in lint.PORT_SPEEDS and "400g" in lint.PORT_SPEEDS
    assert findings(rule(f"2x{lint.PORT_SPEEDS[0]}")) == []


def test_a_rule_with_no_modes_is_skipped():
    assert findings({"interfaces": [{"physical": "mgmt-eth", "name": "ma1"}]}) == []
    assert findings({"interfaces": [{"physical": "p", "name": "n", "breakout": {}}]}) == []
    assert findings({}) == []


def test_a_listing_and_a_device_are_both_read():
    assert lint.RULES["L195"][0] == "listing, device"
    assert lint.RULES["L195"][4] == lint.ERROR


# ---- every mode on main ----------------------------------------------------------

def _files():
    return libwalk.iter_listings(LIB) + libwalk.iter_devices(LIB)


@pytest.mark.heavy
def test_every_mode_in_the_library_passes():
    seen = 0
    for p in _files():
        doc = yaml.safe_load(p.read_text())
        for r in doc.get("interfaces") or []:
            seen += len(((r or {}).get("breakout") or {}).get("modes") or [])
        assert findings(doc) == [], p
    assert seen >= 100, f"read only {seen} modes - the walk found no breakout rules"


# ---- the S9600 lane sharing --------------------------------------------------------

@pytest.mark.parametrize("box", ["s9600-28dx", "s9600-32x", "s9600-64x"])
def test_the_s9600_lane_sharing_is_named_for_what_it_is(box):
    doc = yaml.safe_load((LIB / "devices/ufispace" / box / "device.yaml").read_text())
    attrs = doc["attrs"]
    assert "sfp28-sharing" in attrs["features"], box
    assert "breakout" not in attrs["features"], box
    assert "breakout" not in attrs, box


# ---- the export ---------------------------------------------------------------------

@pytest.mark.skipif(not (DIST / "listings.json").exists(), reason="library/dist not built")
def test_breakout_is_in_the_exported_description_of_both_targets(tmp_path):
    """sonic/s9300-32d carries a breakout rule; its type is filed under SONiC."""
    r = subprocess.run([sys.executable, str(TOOL), "--dist", str(DIST), "--out", str(tmp_path),
                        "--no-raster", "--device", "s9300-32d"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    for target in ("netbox", "nautobot"):
        made = sorted((tmp_path / target / "device-types" / "SONiC").glob("*.yaml"))
        assert made, f"no SONiC type in the {target} export"
        for p in made:
            ifaces = yaml.safe_load(p.read_text())["interfaces"]
            said = [i for i in ifaces if str(i.get("description", "")).startswith("Breakout:")]
            assert said, f"{target}: no interface of {p.name} says Breakout:"
            assert "4x100g" in said[0]["description"], (target, said[0])
