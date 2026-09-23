"""One closed speed vocabulary (L110, #512).

`speed` flattens to data-speed on every port the renderer draws, so it is what a
filter selects on - and "every 1G port" is one selector only if 1G is spelled
one way. It was spelled four ways, USB generations and a PON flavour rode in the
same attr, and the DCIM exporter's table knew two of the four 1G spellings, so
eight copper ports on the CSR180 and CSR200 exported nothing.

The set lives in spec/schemas/speeds.yaml. Lint reads it, and so does this file,
so the rule and its tests cannot disagree about what the set is.
"""
import pathlib
import re

import pytest

from portrayal import libwalk, lint
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

DECIDED = ["10m", "100m", "1g", "2.5g", "5g", "10g", "20g", "25g", "40g", "50g",
           "100g", "200g", "400g", "800g", "1.6t"]


def _bps(s):
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([mgt])", s)
    assert m, f"{s!r} is not a rate"
    return float(m.group(1)) * {"m": 1e6, "g": 1e9, "t": 1e12}[m.group(2)]


@pytest.fixture
def errors(monkeypatch):
    got = []
    monkeypatch.setattr(lint, "ERRORS", got)
    return got


def _l110(errs):
    return [e for e in errs if "[L110]" in e]


# --- the registry ------------------------------------------------------------

def test_the_registry_is_the_decided_set_in_ascending_order():
    assert list(lint.PORT_SPEEDS) == DECIDED
    rates = [_bps(s) for s in lint.PORT_SPEEDS]
    assert rates == sorted(rates) and len(set(rates)) == len(rates)


# --- the rule, on a device ---------------------------------------------------

def _device(group_speed=None, port_speed=None):
    return {
        "groups": {"ports": {"term": "Port", "role": "traffic",
                             "attrs": {"media": "rj45", **({"speed": group_speed} if group_speed else {})}}},
        "views": {"front": {"components": {"placements": [
            {"ref": "common/rj45-eth@1", "id": "port-1", "at": [0, 0], "group": "ports",
             "attrs": {**({"speed": port_speed} if port_speed else {})}},
        ]}}},
    }


@pytest.mark.parametrize("group,port", [("1g", None), (None, "10g"), (None, None), ("1.6t", "1.6t")])
def test_a_speed_from_the_set_passes(errors, group, port):
    lint.lint_device_speed_vocabulary("d.yaml", _device(group, port))
    assert _l110(errors) == []


@pytest.mark.parametrize("bad", ["100m-1g", "1000base-t", "100/1000base-t", "10/100/1000",
                                 "400g-capable", "10g-pon", "usb3", "1G", "10G"])
def test_a_group_speed_outside_the_set_is_an_error(errors, bad):
    lint.lint_device_speed_vocabulary("d.yaml", _device(group_speed=bad))
    (msg,) = _l110(errors)
    assert "groups/ports" in msg and repr(bad) in msg


def test_a_placement_speed_outside_the_set_is_an_error(errors):
    lint.lint_device_speed_vocabulary("d.yaml", _device(port_speed="usb-2.0"))
    (msg,) = _l110(errors)
    assert "front/port-1" in msg and "`usb`" in msg


# --- the rule, on a component ------------------------------------------------

def test_a_component_part_speed_is_read(errors):
    lint.lint_component_speed_vocabulary("c.yaml", {"parts": [
        {"ref": "std/qsfp-dd@1", "id": "port-0", "at": [0, 0], "attrs": {"speed": "400g-capable"}},
        {"ref": "std/qsfp-dd@1", "id": "port-1", "at": [0, 20], "attrs": {"speed": "100g"}},
    ]})
    (msg,) = _l110(errors)
    assert "parts/port-0" in msg


def test_a_component_own_speed_is_read(errors):
    lint.lint_component_speed_vocabulary("c.yaml", {"attrs": {"media": "sfp", "speed": "100m-1g"}})
    assert len(_l110(errors)) == 1


def test_a_speed_the_component_prints_as_a_field_is_not_a_port_rate(errors):
    """common/dimm-plan: `speed` is the DIMM sticker's MT/s, declared as a field."""
    lint.lint_component_speed_vocabulary("c.yaml", {
        "fields": {"speed": {"label": "Speed", "type": "text", "default": "2933"}},
        "attrs": {"speed": "2933"}})
    assert _l110(errors) == []


# --- the library -------------------------------------------------------------

def test_the_library_is_at_zero_and_the_sweep_measured_something(errors):
    """Every device and component, through the rule itself. The count is the
    guard against a walk that finds nothing and passes."""
    seen = 0
    for f in libwalk.iter_devices([LIB]):
        d = load_yaml(f) or {}
        seen += sum(1 for g in (d.get("groups") or {}).values()
                    if ((g or {}).get("attrs") or {}).get("speed"))
        lint.lint_device_speed_vocabulary(f, d)
    for f in libwalk.iter_components([LIB]):
        d = load_yaml(f) or {}
        seen += sum(1 for p in (d.get("parts") or []) if (p.get("attrs") or {}).get("speed"))
        lint.lint_component_speed_vocabulary(f, d)
    assert seen > 100, seen
    assert _l110(errors) == [], "\n".join(_l110(errors))
