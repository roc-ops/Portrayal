"""A network port says what rate it runs at (L113, #511).

`speed` is what `[data-speed]` selects on and what the DCIM exporter types an
interface from. A device port that carries Ethernet and states no speed is
invisible to the first and GUESSED by the second - `iface_type` falls back to
25G for any SFP, so the ASR 9001's two 10G cluster ports and three Smartoptics
OSC cages exported as SFP28.

#511's audit found 124 device-level network ports with a group and no speed.
Most were not missing a rate at all: they were timing jacks and consoles whose
`media` said `rj45`, which claims Ethernet. So L113 asks only ports whose
effective media carries an interface, and the fix for a ToD or console jack is
the media that says what it carries - `rj45-tod`, `rj48`, `rj45-serial` - not a
speed it does not have.

What is left is counted below, with a ceiling that only goes down.
"""
import pathlib

import pytest

from portrayal import dcim_export as dx
from portrayal import libwalk, lint
from portrayal.manifest import load_yaml, view_parts

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
LIB_ROOTS = [LIB]


@pytest.fixture
def found():
    with lint.collecting() as got:
        yield got.errors, got.warnings


def _l113(msgs):
    return [m for m in msgs if "[L113]" in m]


def _device(port=None, group=None, ref="common/rj45-eth@1", maturity="modelled",
            group_name="ports", role="traffic"):
    groups = {group_name: {"term": "Port", **({"role": role} if role else {}),
                           **({"attrs": group} if group else {})}}
    pl = {"ref": ref, "id": "port-1", "at": [0, 0], "group": group_name,
          **({"attrs": port} if port else {})}
    return {"maturity": maturity, "groups": groups,
            "views": {"front": {"components": {"placements": [pl]}}}}


# --- the catalogue -----------------------------------------------------------

def test_l113_is_a_device_rule_after_l112():
    assert lint.RULES["L113"][0] == "device"
    assert "L112" in lint.RULES and "L112" not in lint.RESERVED


# --- which media are asked ---------------------------------------------------

def test_the_interface_media_are_the_trees_own_two_lists():
    """No list restated: the pluggable cages L40 and L102 ask about, and the
    media the exporter's PART_MEDIA types as an interface rather than `other`."""
    assert lint.PLUGGABLE_CAGES <= lint.INTERFACE_MEDIA
    assert "rj45" in lint.INTERFACE_MEDIA
    assert dx.PART_MEDIA[("rj45-telemetry", None)] == "other"
    assert "rj45-telemetry" not in lint.INTERFACE_MEDIA


@pytest.mark.parametrize("media", ["rj45-serial", "rj45-tod", "rj48", "rj45-sync",
                                   "rj45-alarm", "rj45-telemetry", "usb-a", "coax-smb", "fiber"])
def test_a_jack_that_is_not_ethernet_is_not_asked(found, media):
    lint.lint_device_port_rate("d.yaml", _device(port={"media": media},
                                                 ref="std/rj45@2"), LIB_ROOTS)
    assert _l113(found[0] + found[1]) == []


@pytest.mark.parametrize("media", ["rj45", "sfp", "sfp-plus", "sfp28", "qsfp28", "qsfp-dd", "osfp", "xfp"])
def test_an_ethernet_port_without_a_speed_is_found(found, media):
    lint.lint_device_port_rate("d.yaml", _device(port={"media": media}), LIB_ROOTS)
    (msg,) = _l113(found[1])
    assert "front/port-1" in msg and "no `speed`" in msg


def test_the_part_answers_when_the_device_names_no_media(found):
    """A bare std/rj45@2 with nothing on the placement or the group is an
    `rj45` by its contract - which is exactly how 65 timing jacks read as
    Ethernet. It is asked."""
    lint.lint_device_port_rate("d.yaml", _device(ref="std/rj45@2"), LIB_ROOTS)
    assert len(_l113(found[1])) == 1


# --- what answers it ---------------------------------------------------------

def test_the_group_speed_answers_for_its_members(found):
    lint.lint_device_port_rate("d.yaml", _device(group={"media": "rj45", "speed": "1g"}), LIB_ROOTS)
    assert _l113(found[0] + found[1]) == []


def test_the_port_speed_answers(found):
    lint.lint_device_port_rate("d.yaml", _device(port={"media": "sfp", "speed": "1g"}), LIB_ROOTS)
    assert _l113(found[0] + found[1]) == []


def test_a_cage_carrying_a_proprietary_link_has_no_speed_to_give(found):
    """It says what runs in it, and the exporter types it `other` from that."""
    lint.lint_device_port_rate("d.yaml", _device(
        port={"media": "sfp", "proprietary-link": "Digital return"}, ref="std/sfp@1"),
        LIB_ROOTS)
    assert _l113(found[1]) == []
    # Not a label, so not a declaration: still asked.
    lint.lint_device_port_rate("d.yaml", _device(
        port={"media": "sfp", "proprietary-link": ""}, ref="std/sfp@1"), LIB_ROOTS)
    assert len(_l113(found[1])) == 1


def test_a_group_without_a_role_is_found(found):
    lint.lint_device_port_rate("d.yaml", _device(port={"media": "rj45", "speed": "1g"}, role=None),
                               LIB_ROOTS)
    (msg,) = _l113(found[1])
    assert "has no `role`" in msg


def test_a_port_in_no_group_is_found(found):
    d = _device(port={"media": "rj45", "speed": "1g"})
    del d["views"]["front"]["components"]["placements"][0]["group"]
    lint.lint_device_port_rate("d.yaml", d, LIB_ROOTS)
    (msg,) = _l113(found[1])
    assert "no group" in msg


def test_a_lamp_is_not_a_port(found):
    lint.lint_device_port_rate("d.yaml", _device(ref="common/led-dot@1"), LIB_ROOTS)
    assert _l113(found[0] + found[1]) == []


# --- the gate ----------------------------------------------------------------

def test_a_warning_at_modelled_and_an_error_at_verified(found):
    lint.lint_device_port_rate("d.yaml", _device(maturity="verified"), LIB_ROOTS)
    assert len(_l113(found[0])) == 1 and _l113(found[1]) == []


# --- the library -------------------------------------------------------------

# What is left, and why each one is left. Every entry here is recorded in the
# device's `gaps:` (or, for the server, is out of scope) - none is a rate that
# was findable and not looked for.
LEFT = {
    "cisco/asr-9901": {"cmp"},                     # vendor-silent
    "juniper/mx204": {"gm-ptp"},                   # vendor-silent
    "juniper/mx80": {"ethernet"},                  # the guide says 1 Gbps and 10/100
    "maiaedge/port-extender": {"mgmt"},            # vendor-silent
    "smartoptics/dcp-sc-28p": {"port-probe"},      # vendor-silent
    "edgecore/csr180": {"stack-a-upper"},          # which jack it is is itself a gap
    "dell/r740xd": {"idrac9"},                     # a server; out of scope for now
}
# THE CEILING ONLY GOES DOWN. It was 123 when L113 was written, and #511's
# device sweep took it to the entries above.
CEILING = 7


def _findings():
    ports = 0
    with lint.collecting() as got:
        for f in libwalk.iter_devices([LIB]):
            d = load_yaml(f) or {}
            for v in (d.get("views") or {}).values():
                ports += sum(1 for p in view_parts(v)["placements"]
                             if lint.contract_class(p.get("ref"), LIB_ROOTS) == "port")
            lint.lint_device_port_rate(f, d, LIB_ROOTS)
    return _l113(got.errors), _l113(got.warnings), ports


def test_the_library_is_under_its_ceiling_and_the_sweep_measured_something():
    errs, warns, ports = _findings()
    assert ports > 3000, ports                    # a walk that found nothing passes nothing
    assert errs == [], "\n".join(errs)
    assert len(warns) <= CEILING, "\n".join(warns)


def test_every_port_left_is_one_the_table_above_explains():
    _errs, warns, _ports = _findings()
    got = {}
    for w in warns:
        path, rest = w.split(": [L113] ", 1)
        dev = "/".join(pathlib.Path(path).parts[-3:-1])
        got.setdefault(dev, set()).add(rest.split(":", 1)[0].split("/", 1)[1])
    assert got == LEFT


# --- the export --------------------------------------------------------------

def test_a_fast_ethernet_jack_exports_as_100base_tx():
    """The ASR 9001/9901 service LAN ports are 10/100 by the install guide.
    Stating it must retype them, not drop them."""
    assert dx.iface_type({"ref": "common/rj45-ganged-eth@1", "id": "x"},
                         {"speed": "100m"}, "management") == "100base-tx"


def test_a_timing_or_serial_jack_with_its_media_named_is_not_an_interface():
    for media in ("rj45-tod", "rj48", "rj45-serial", "rj45-sync"):
        assert dx.iface_type({"ref": "std/rj45@2", "id": "x"}, {"media": media}, "management") is None
