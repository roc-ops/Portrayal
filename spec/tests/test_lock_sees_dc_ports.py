"""The device lock reads a DC port as an export fact.

A published DC port (`dc-ports` in configs.json) is held by whatever lands a
feed on it, so the lock judges it as it judges `fed-by` and `through`:

  - a device that GAINS a port, in any configuration, is a minor;
  - a port that goes, or whose path, direction, poles or a pole's role change,
    is a major, and so is a figure (voltage, rating, awg, side) that changes or
    is dropped; a figure stated where there was none is a minor;
  - a device that presents no port is not rehashed: it records nothing new.

The tests write a temporary library of synthetic parts and read the entry the
lock records for a device before and after one edit to a part.
"""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from portrayal import devicelock as dl
from portrayal import manifest

from test_dc_ports_published import DEVICES, PARTS, _port, write_library

ROOT = Path(__file__).resolve().parents[2]


def locked(tmp_path, parts=None, device="supply-box", devices=None):
    """The entry the lock records for `device` over a library of `parts`."""
    lib = write_library(tmp_path / "lib", parts or PARTS, devices or DEVICES)
    doc = manifest.load_yaml(lib / "devices/fixture" / device / "device.yaml")
    return dl.entry(doc, dl.component_versions(lib))


def edited(edit, name="dc-supply"):
    parts = copy.deepcopy(PARTS)
    edit(parts[name])
    return parts


def no_dc(name="dc-supply"):
    return edited(lambda p: p.pop("dc"), name)


def bump(tmp_path, before, after, **kw):
    a = locked(tmp_path / "before", before, **kw)
    b = locked(tmp_path / "after", after, **kw)
    return dl.required_bump(a, b)


def first_port(part):
    return part["dc"]["ports"][0]


# --- a port gained ------------------------------------------------------------------------

def test_a_device_that_gains_a_port_is_asked_for_a_minor(tmp_path):
    assert bump(tmp_path, no_dc(), PARTS) == "minor"


def test_a_device_that_gains_a_port_in_a_bay_configuration_is_asked_for_a_minor(tmp_path):
    assert bump(tmp_path, no_dc(), PARTS, device="bayed-box") == "minor"


def test_a_second_port_moves_the_first_ones_path_and_is_a_major(tmp_path):
    """A port's path is the part's own while it is the only one and the part's
    and its id once there are several (section 5.2), so a feed addressed to the
    first is addressed to nothing after."""
    def add(part):
        part["dc"]["ports"].append(_port("extra", [("rtn", "terminal-rtn"), ("batt", "terminal-48v")]))
    assert bump(tmp_path, PARTS, edited(add)) == "major"


def test_a_port_added_beside_others_that_keep_their_paths_is_a_minor(tmp_path):
    def add(part):
        part["dc"]["ports"].append(_port("c", [("rtn", "a-rtn"), ("batt", "a-batt")]))
    assert bump(tmp_path, PARTS, edited(add, "dc-twin"), device="twin-box") == "minor"


def test_a_figure_stated_where_there_was_none_is_a_minor(tmp_path):
    for stated in ({"rating-a": 20}, {"awg": [10]}):
        assert bump(tmp_path, PARTS, edited(lambda p: first_port(p).update(stated), "dc-twin"),
                    device="twin-box") == "minor"


# --- a port lost or changed ------------------------------------------------------------------

def test_a_port_that_goes_is_a_major(tmp_path):
    assert bump(tmp_path, PARTS, no_dc()) == "major"


def test_a_port_removed_from_a_part_that_keeps_another_is_a_major(tmp_path):
    assert bump(tmp_path, PARTS, edited(lambda p: p["dc"]["ports"].pop(), "dc-twin"), device="twin-box") == "major"


def test_a_port_whose_id_and_so_path_changes_is_a_major(tmp_path):
    assert bump(tmp_path, PARTS, edited(lambda p: first_port(p).update(id="in"), "dc-twin"), device="twin-box") == "major"


def test_a_port_whose_direction_changes_is_a_major(tmp_path):
    assert bump(tmp_path, PARTS, edited(lambda p: first_port(p).update(direction="output"))) == "major"


def test_a_pole_removed_is_a_major(tmp_path):
    assert bump(tmp_path, PARTS, edited(lambda p: first_port(p)["poles"].pop())) == "major"


def test_a_pole_moved_to_another_slot_is_a_major(tmp_path):
    assert bump(tmp_path, PARTS, edited(lambda p: first_port(p)["poles"][0].update(slot="terminal-48v"))) == "major"


def test_a_poles_role_changed_is_a_major(tmp_path):
    assert bump(tmp_path, PARTS, edited(lambda p: first_port(p)["poles"][0].update(role="pos"))) == "major"


@pytest.mark.parametrize("key,value", [("voltage", {"nominal": -60}), ("rating-a", 30), ("awg", [10]), ("side", "b")])
def test_a_figure_changed_is_a_major(tmp_path, key, value):
    assert bump(tmp_path, PARTS, edited(lambda p: first_port(p).update({key: value}))) == "major"


@pytest.mark.parametrize("key", ["voltage", "rating-a", "awg", "side"])
def test_a_figure_dropped_is_a_major(tmp_path, key):
    assert bump(tmp_path, PARTS, edited(lambda p: first_port(p).pop(key))) == "major"


def test_a_source_reworded_is_nothing_the_port_publishes(tmp_path):
    a = locked(tmp_path / "a", PARTS)
    b = locked(tmp_path / "b", edited(lambda p: first_port(p).update(source={"poles": "terminals", "awg": "terminals"})))
    assert a["dc-ports"] == b["dc-ports"]


# --- the guard ----------------------------------------------------------------------------------

def test_a_device_that_presents_no_port_records_nothing_new(tmp_path):
    """The fingerprint of a device with no DC port is what it was: no key, and
    the same entry whether or not another part of the library states a port."""
    with_dc = locked(tmp_path / "a", PARTS, device="plain-box")
    without = locked(tmp_path / "b", {k: v for k, v in PARTS.items() if k != "dc-supply"} | {
        "dc-supply": no_dc()["dc-supply"]}, device="plain-box")
    assert "dc-ports" not in with_dc
    assert with_dc == without
    assert set(with_dc) == {"version", "ids", "groups", "configs", "placement-groups", "bay-accepts",
                            "placement-addressing", "composed-refs", "shape", "names", "surface",
                            "placement-attrs", "placement-geometry", "placement-surface", "gaps", "composed"}


def test_a_device_whose_part_states_no_port_is_a_patch_when_the_part_is_redrawn(tmp_path):
    parts = edited(lambda p: p.update(description="redrawn"), "dc-plain")
    assert bump(tmp_path, PARTS, parts, device="plain-box") == "patch"


def test_a_lock_written_before_the_field_does_not_report_a_device_with_no_port(tmp_path):
    old = locked(tmp_path / "a", PARTS, device="plain-box")
    assert dl.required_bump(old, locked(tmp_path / "b", PARTS, device="plain-box")) is None


def test_a_lock_written_before_the_field_asks_only_for_what_a_port_gained_costs(tmp_path):
    """An old lock has no `dc-ports` and so is read as presenting none: the
    first port a device gains is a minor, never a major."""
    old = locked(tmp_path / "a", no_dc())
    assert "dc-ports" not in old
    new = locked(tmp_path / "b", PARTS)
    assert dl.required_bump(old, new) == "minor"


def test_an_unchanged_port_asks_for_nothing(tmp_path):
    assert bump(tmp_path, PARTS, copy.deepcopy(PARTS)) is None


# --- the real library ---------------------------------------------------------------------------------

def test_devicelock_names_no_device_of_the_real_library():
    """Passes before this change as well as after."""
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/devicelock.py"),
                        "--library", str(ROOT / "library")], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(ROOT / "spec/tools")})
    assert (r.returncode, r.stdout.strip()) == (0, "devicelock: 0 finding(s)"), r.stdout + r.stderr


def test_no_lock_of_the_real_library_records_a_port():
    locks = sorted((ROOT / "library/devices").glob("*/*/device.lock.json"))
    assert locks
    assert [str(f) for f in locks if "dc-ports" in json.loads(f.read_text())] == []
