"""The schemas resolve, say their units, and report everything they find.

Three faults from roc-ops/Portrayal#169, each small and each aimed at the person
who has just cloned the repository:

  - `device.schema.json` referenced `#/$defs/provenance`, which it did not define.
    Nothing had used a cutout's `provenance:` yet, so the first contributor to
    write one would have got a resolver crash instead of a validation message.
  - `chassis.width/height/depth` were bare numbers with no unit, three lines from
    a `views.size` that says millimetres. The reader is left to infer it.
  - `lint.py` reported the FIRST schema error in a file and stopped, so a manifest
    with four faults took four full lint runs to fix.

The first is tested in its general form rather than as the one instance, because
the instance is now fixed and the class is what recurs.
"""
import json
import pathlib
import re
import sys

import jsonschema
import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "spec/schemas"

from portrayal import lint


def _schema_files():
    return sorted(SCHEMAS.glob("*.schema.json"))


@pytest.mark.parametrize("path", _schema_files(), ids=lambda p: p.name)
def test_every_internal_ref_resolves(path):
    """THE CLASS, not the instance. A `$ref` to a `$defs` key that is not there
    is a crash at use rather than a message, and it hides until somebody writes
    the first manifest that reaches it."""
    text = path.read_text()
    doc = json.loads(text)
    defined = set(doc.get("$defs") or {})
    used = set(re.findall(r'"#/\$defs/([^"]+)"', text))
    assert not (used - defined), (
        f"{path.name} references {sorted(used - defined)} which it does not define; "
        f"it defines {sorted(defined)}")


def test_some_schema_actually_uses_internal_refs():
    """NON-VACUITY for the sweep above: it passes when a schema has no refs at
    all, which is also what it does if the pattern stops matching. Two of the
    three schemas here use them heavily; overlay.schema.json uses none."""
    total = sum(len(set(re.findall(r'"#/\$defs/([^"]+)"', f.read_text())))
                for f in _schema_files())
    assert total >= 10, f"only {total} internal refs across all schemas"


@pytest.mark.parametrize("path", _schema_files(), ids=lambda p: p.name)
def test_the_schemas_are_valid_schemas(path):
    jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text()))


@pytest.mark.parametrize("key", ["width", "height", "depth"])
def test_a_chassis_dimension_says_what_unit_it_is_in(key):
    """Every length in this library is millimetres, and a schema is where
    somebody looks to find that out."""
    doc = json.loads((SCHEMAS / "device.schema.json").read_text())
    field = doc["properties"]["chassis"]["properties"][key]
    assert "mm" in field.get("description", "") or "millimetre" in field.get("description", ""), \
        f"chassis.{key} states no unit: {field}"


def test_a_cutouts_provenance_validates_rather_than_crashing():
    """The dangling ref, from the side a contributor would have met it: write a
    `provenance:` on a cutout and the validator must have something to say."""
    doc = json.loads((SCHEMAS / "device.schema.json").read_text())
    v = jsonschema.Draft202012Validator(doc)
    cutout = {"id": "usb", "at": [1.0, 2.0], "size": [4.5, 12.0],
              "provenance": {"size": "registry - std/usb-a@1"}}
    dev = {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
           "manufacturer": "M", "model": "M", "maturity": "modelled", "profile": "networking",
           "chassis": {"width": 100.0, "height": 44.0, "depth": 200.0},
           "views": {"front": {"size": {"w": 100.0, "h": 44.0},
                               "panel": {"cutouts": [cutout]}}}}
    list(v.iter_errors(dev))          # must not raise a resolver error
    bad = dict(cutout, provenance={"size": 12})
    dev["views"]["front"]["panel"]["cutouts"] = [bad]
    assert any("provenance" in "/".join(str(p) for p in e.path)
               for e in v.iter_errors(dev)), \
        "a non-string provenance value should be rejected, so the $ref is being used"


# --- every error, not the first ----------------------------------------------

def _device_with(n_faults, tmp_path):
    """A manifest carrying `n_faults` independent schema faults."""
    dev = {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
           "manufacturer": "M", "model": "M", "maturity": "modelled", "profile": "networking",
           "chassis": {"width": 100.0, "height": 44.0, "depth": 200.0},
           "views": {"front": {"size": {"w": 100.0, "h": 44.0}}}}
    faults = [("chassis", "width", "wide"), ("chassis", "height", "tall"),
              ("chassis", "depth", "deep")]
    for section, key, value in faults[:n_faults]:
        dev[section][key] = value              # a string where a number belongs
    p = tmp_path / "device.yaml"
    p.write_text(yaml.safe_dump(dev))
    return p


def _all_findings(path):
    """Every error from one lint run over `path`.

    THROUGH `lint.collecting()`. Clearing the globals without restoring them
    leaves this run's findings where the next test reads them, which
    `collecting()`'s own docstring predicts and which
    test_lint_collecting::test_it_restores_what_was_there_before catches - by
    failing, under its own name, over a finding it never made.
    """
    doc = json.loads((SCHEMAS / "device.schema.json").read_text())
    with lint.collecting() as got:
        lint.lint_device(path, jsonschema.Draft202012Validator(doc), [str(ROOT / "library")])
    return got.errors


def _schema_findings(path):
    return [e for e in _all_findings(path) if "[L1]" in e]


def test_three_schema_faults_are_reported_as_three(tmp_path):
    """The whole point. One per run meant a full lint between each fix."""
    found = _schema_findings(_device_with(3, tmp_path))
    assert len(found) == 3, f"reported {len(found)} of 3:\n" + "\n".join(found)


def test_a_clean_manifest_still_reports_nothing(tmp_path):
    """NON-VACUITY in the other direction: a check that reports everything is
    only useful if it reports nothing when there is nothing."""
    assert _schema_findings(_device_with(0, tmp_path)) == []


def test_the_run_still_stops_before_the_structural_checks(tmp_path):
    """Reporting all of them must not turn into CONTINUING past them. The checks
    after this point read a shape the schema has just called wrong, and the
    `return` is what keeps them from tripping over it."""
    every = _all_findings(_device_with(1, tmp_path))
    assert len([e for e in every if "[L1]" in e]) == 1
    assert not [e for e in every if "[L1]" not in e], \
        "a schema-invalid manifest should not reach the structural rules: " + str(every)
