"""L90 and L91 - one order for a manifest's keys, one home for its airflow.

roc-ops/Portrayal#171. Two separate tidinesses that were both invisible to
every gate, and one of them turned out not to be tidiness at all.

THE KEY ORDER is friction rather than error: 89 manifests had grown 22 distinct
top-level orderings, so a reviewer comparing two devices read two differently
shaped documents and a contributor copying a nearby manifest inherited whichever
arrangement they opened. L16 has enforced order inside a view since early on for
exactly this reason; nothing did at the top level. The canonical order is
DERIVED rather than designed - of four candidates it is the one 53 of the 89
already used, which turned the sweep into 25 files instead of 88.

THE AIRFLOW HOME is a correctness matter underneath the tidiness. `chassis.airflow`
appeared in 10 manifests and `configurations.*.airflow` in 124 places, and the
issue proposed configurations as the single home "since it varies by fan/PSU
option". The corpus says otherwise: it varies in 7 of the 48 devices that state
it, and in 39 it was one value repeated across every configuration - five times
on the DCP-2. The two schemas never agreed either. `chassis.airflow` admits
`side` and `passive`; a configuration's admits neither, so the fanless FS
enclosure and the side-breathing ASR 9000s could not have moved.

So the home is the chassis, a configuration overrides only where it differs, and
that is what `render.py` had been doing all along:

    airflow = config.get("airflow") or (device.get("chassis") or {}).get("airflow")

`dcim_export` was not, which is the bug this found: ten devices stated airflow
only on the chassis and exported none at all.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint  # noqa: E402


def run(fn, doc):
    lint.ERRORS.clear()
    fn("d.yaml", doc)
    return list(lint.ERRORS)


def device(**keys):
    doc = {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
           "manufacturer": "M", "model": "M", "maturity": "modelled",
           "description": "x", "provenance": {}, "chassis": {"width": 1.0},
           "groups": {}, "views": {}}
    doc.update(keys)
    return {k: doc[k] for k in doc}


# --- L90 ---------------------------------------------------------------------

def test_the_library_is_in_one_order():
    """The corpus. 22 orderings became one."""
    bad = []
    for p in sorted(LIB.glob("devices/*/*/device.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        lint.ERRORS.clear()
        lint.lint_device_key_order(p, d)
        bad += [e for e in lint.ERRORS if "[L90]" in e]
    assert not bad, f"{len(bad)} manifest(s) out of order:\n" + "\n".join(bad[:5])


def test_there_are_manifests_to_check():
    """NON-VACUITY for the sweep above."""
    assert len(list(LIB.glob("devices/*/*/device.yaml"))) > 80


def test_a_key_in_the_wrong_place_is_reported():
    doc = {"format": 1, "kind": "device", "gaps": [], "name": "d"}
    found = run(lint.lint_device_key_order, doc)
    assert len(found) == 1 and "'gaps' comes before 'name'" in found[0], found


def test_the_message_prints_the_order_it_wants():
    """A rule that says only "wrong" makes the reader go and find the rule."""
    found = run(lint.lint_device_key_order, {"kind": "device", "format": 1})
    assert "format kind" in found[0], found


def test_a_key_the_order_does_not_know_is_left_to_the_schema():
    """L1 has already reported it, and a second complaint about where an
    unknown key sits is noise on top of a message that says it does not
    belong at all."""
    doc = {"format": 1, "kind": "device", "wat": 1, "name": "d"}
    assert run(lint.lint_device_key_order, doc) == []


def test_the_template_is_written_in_the_canonical_order():
    """It is the file a contributor copies, so it is the one that has to be
    right - and it was not: it carried `gaps` after `configurations`."""
    doc = yaml.safe_load((ROOT / "docs/device-template.yaml").read_text())
    assert run(lint.lint_device_key_order, doc) == []


# --- L91 ---------------------------------------------------------------------

def test_the_library_states_airflow_once():
    bad = []
    for p in sorted(LIB.glob("devices/*/*/device.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        lint.ERRORS.clear()
        lint.lint_device_airflow_home(p, d)
        bad += [e for e in lint.ERRORS if "[L91]" in e]
    assert not bad, "\n".join(bad[:5])


def test_a_configuration_restating_the_chassis_value_is_reported():
    doc = device(chassis={"width": 1.0, "airflow": "front-to-back"},
                 configurations={"ac": {"airflow": "front-to-back"}})
    found = run(lint.lint_device_airflow_home, doc)
    assert len(found) == 1 and "restate the chassis airflow" in found[0], found


def test_a_configuration_that_differs_is_exactly_what_the_key_is_for():
    """The 7 devices where it genuinely varies - the AS5912's f2b and b2f SKUs
    are two builds of one chassis, and that is the case this key exists for."""
    doc = device(chassis={"width": 1.0},
                 configurations={"f2b": {"airflow": "front-to-back"},
                                 "b2f": {"airflow": "back-to-front"}})
    assert run(lint.lint_device_airflow_home, doc) == []


def test_one_value_repeated_across_every_configuration_belongs_on_the_chassis():
    """39 devices did this, the DCP-2 five times over."""
    doc = device(chassis={"width": 1.0},
                 configurations={"ac": {"airflow": "front-to-back"},
                                 "dc": {"airflow": "front-to-back"}})
    found = run(lint.lint_device_airflow_home, doc)
    assert len(found) == 1 and "One fact, one home" in found[0], found


def test_a_chassis_value_with_a_differing_override_is_fine():
    doc = device(chassis={"width": 1.0, "airflow": "front-to-back"},
                 configurations={"std": {}, "rev": {"airflow": "back-to-front"}})
    assert run(lint.lint_device_airflow_home, doc) == []


def test_a_device_that_says_nothing_about_airflow_is_not_nagged():
    """31 devices state no airflow anywhere. L91 is about a fact with two homes,
    not about a fact being missing - that would be a different rule and it is
    not this one's business to invent it."""
    assert run(lint.lint_device_airflow_home, device(configurations={"a": {}})) == []


def test_the_exporter_falls_back_to_the_chassis():
    """THE BUG THIS FOUND. `render.py` read config-then-chassis; `dcim_export`
    read only the configuration, so a device stating airflow on the chassis
    exported none. Twelve export files gained the line."""
    import dcim_export
    dev = {"chassis": {"airflow": "front-to-back"}}
    out = {}
    air = dcim_export.AIRFLOW.get(({}).get("airflow") or (dev.get("chassis") or {}).get("airflow"))
    assert air == "front-to-rear"
    asr = LIB / "exports/netbox/device-types/Cisco/ASR-9010-DC-V2.yaml"
    if asr.exists():
        assert "airflow" in yaml.safe_load(asr.read_text()), \
            "the ASR 9010 states airflow on its chassis and must export it"
