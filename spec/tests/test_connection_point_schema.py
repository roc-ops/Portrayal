"""The `cable` connection-point constraint, exercised directly against the schema.

No component declares `cable` yet - the cabling library that needs it is later
in spec B - so nothing in the built library exercises this rule. That is
exactly how it survived broken into a commit: the first draft named `cable`
under `connection-points.properties`, which in JSON Schema makes
`additionalProperties` stop applying to that key entirely, silently dropping
`type: object`, the `direction` enum, `additionalProperties: false` and the
xy shape of `at` - only the extra `required` survived, and every one of
`{"cable": "just-a-string"}`, an unknown-`direction` cable and a cable with a
stray extra field validated as if the constraint had never been added. The
fix moved the extra requirement into an `allOf` branch instead, which ANDs
with the general shape rather than replacing it. Without a test that loads
the schema and validates instances against it, a rule with no component to
trip it is a rule nobody checks - this is that test, run against the schema
alone rather than waiting for a `cable`-bearing part to exist.
"""
import json
import pathlib

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "spec" / "schemas" / "component.schema.json"


def _connection_points_schema():
    """The `connection-points` definition, standalone but still able to
    resolve its own `#/$defs/...` refs (`xy`, `segment`) - those refs resolve
    against the schema object jsonschema is handed, so the top-level `$defs`
    come along for the ride rather than being re-declared here."""
    doc = json.loads(SCHEMA_PATH.read_text())
    schema = dict(doc["properties"]["connection-points"])
    schema["$defs"] = doc["$defs"]
    schema["$schema"] = doc["$schema"]
    return schema


SCHEMA = _connection_points_schema()


def _valid(instance):
    try:
        jsonschema.validate(instance, SCHEMA)
        return True
    except jsonschema.ValidationError:
        return False


def test_a_cable_with_direction_validates():
    assert _valid({"cable": {"at": [1, 2], "direction": "rear"}})


def test_a_cable_without_direction_is_rejected():
    """The whole point of the constraint: a cable point that does not say
    which way the cable leaves says nothing useful to a consumer."""
    assert not _valid({"cable": {"at": [1, 2]}})


def test_a_cable_with_a_bogus_direction_is_rejected():
    assert not _valid({"cable": {"at": [1, 2], "direction": "banana"}})


def test_a_cable_with_an_extra_property_is_rejected():
    """This is the case the broken `properties.cable` form silently accepted:
    naming `cable` under `properties` switched off `additionalProperties:
    false` for it along with everything else."""
    assert not _valid({"cable": {"at": [1, 2], "direction": "rear", "junk": 1}})


def test_a_cable_whose_at_is_not_a_coordinate_is_rejected():
    assert not _valid({"cable": {"at": "nope", "direction": "rear"}})


def test_a_cable_that_is_not_an_object_is_rejected():
    assert not _valid({"cable": "just-a-string"})


def test_a_non_cable_point_needs_no_direction():
    """The requirement is cable-specific. A `mate` point has never needed a
    direction and must not pick one up as a side effect of the `cable` fix -
    that would be the same inversion bug in the opposite direction."""
    assert _valid({"mate": {"at": [1, 2]}})


def test_a_non_cable_point_still_rejects_a_bogus_direction():
    """General validation must still reach every OTHER point, not just
    `cable` - the allOf branch adds a requirement, it does not replace the
    shape every point already had."""
    assert not _valid({"mate": {"at": [1, 2], "direction": "banana"}})
