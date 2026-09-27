"""`maturity` and `profile` are required, and a declared profile is a defined one.

roc-ops/Portrayal#170. Both fields had a default that quietly meant something,
and in both cases the default was saying something untrue about finished work.

`maturity` was absent on twelve devices and absent means `draft` - so the
Edgecore AS7726-32X, all five Smartoptics DCPs, the FS enclosure and the
Celestica ES1010 were reading as drafts. They are not: every one of them passes
L15's provenance bar at `modelled`, which is how we know the field was missing
rather than the work. A default that mislabels the work is worse than a field
somebody has to fill in.

`profile` was absent on 67 of 89, and absent does not mean lenient - it means
the `specified` capability flag CANNOT BE EVALUATED at all. The flag read as a
fact about the 22 devices that had one. `capability._specified` is careful about
this and returns a third answer rather than `no`; what it could not do is make
the field appear.

TWO THINGS THIS FILE GUARDS THAT ARE NOT THE FIELDS THEMSELVES.

A profile only means anything if `spec/schemas/profiles.yaml` defines it -
`dell/r740xd` declared `server` when no such profile existed, which capability
reports as `profile-undefined` and is no better than declaring none. And
`profile` was not fingerprinted by devicelock though `maturity` beside it was,
so a required field could be retyped from `networking` to `optical` - changing
what the device is judged against - with no version asked for.
"""
import json
import pathlib
import sys

import jsonschema
import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
from portrayal import devicelock
from portrayal import libwalk


@pytest.fixture(scope="module")
def devices():
    return {f"{p.parts[-3]}/{p.parts[-2]}": yaml.safe_load(p.read_text()) or {}
            for p in libwalk.iter_devices([LIB])}


@pytest.fixture(scope="module")
def profiles():
    return yaml.safe_load((ROOT / "spec/schemas/profiles.yaml").read_text())["profiles"]


def test_there_are_devices_to_check(devices):
    """NON-VACUITY for every sweep below."""
    assert len(devices) > 80


@pytest.mark.parametrize("field", ["maturity", "profile"])
def test_the_schema_requires_it(field):
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    assert field in schema["required"]


@pytest.mark.parametrize("field", ["maturity", "profile"])
def test_every_device_states_it(devices, field):
    missing = sorted(s for s, d in devices.items() if not d.get(field))
    assert not missing, f"{len(missing)} device(s) state no {field}: {missing[:6]}"


def test_a_manifest_missing_one_is_actually_rejected():
    """The schema half, from the side a contributor meets it. Requiring a key in
    a file nothing validates against would be a comment."""
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    v = jsonschema.Draft202012Validator(schema)
    dev = {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
           "maturity": "modelled", "profile": "networking",
           "manufacturer": "M", "model": "M",
           "chassis": {"width": 100.0, "height": 44.0, "depth": 200.0},
           "views": {"front": {"size": {"w": 100.0, "h": 44.0}}}}
    assert not list(v.iter_errors(dev)), "the complete manifest should validate"
    for field in ("maturity", "profile"):
        short = {k: x for k, x in dev.items() if k != field}
        assert any(field in str(e.message) for e in v.iter_errors(short)), field


def test_every_declared_profile_is_a_defined_one(devices, profiles):
    """`dell/r740xd` said `server` when profiles.yaml had only `networking` and
    `optical`, which capability reports as `profile-undefined`. Declaring a
    profile nothing defines is the same silence as declaring none, wearing a
    different label."""
    bad = sorted({d["profile"] for d in devices.values()
                  if d.get("profile") and d["profile"] not in profiles})
    assert not bad, f"profile(s) no entry defines: {bad}"


def test_a_defined_profile_is_one_something_uses(devices, profiles):
    """The other direction, the way #173 asked it of `class`: a profile nothing
    declares is a class nobody can be measured against, and it reads as a
    supported choice."""
    used = {d.get("profile") for d in devices.values()}
    assert not (set(profiles) - used), f"defined and unused: {sorted(set(profiles) - used)}"


def test_every_profile_says_what_it_requires(profiles):
    for name, spec in profiles.items():
        assert spec.get("description"), f"{name} has no description"
        assert spec.get("requires"), f"{name} demands nothing, so the flag is free"


def test_changing_the_profile_asks_for_a_version(devices):
    """It sat beside `maturity`, which IS hashed, and was not. A required field
    nothing fingerprints can be changed with no version consequence - and this
    one decides what `specified` judges the device against."""
    base = dict(devices["ufispace/s9300-32d"])
    before = devicelock.buckets(base)
    after = devicelock.buckets({**base, "profile": "optical"})
    assert before["surface"] != after["surface"], \
        "retyping the profile changed no fingerprint, so no bump would be asked for"


def test_maturity_still_asks_for_one_too(devices):
    """The sibling, so a later refactor cannot drop one while keeping the
    other - which is exactly the asymmetry this found."""
    base = dict(devices["ufispace/s9300-32d"])
    before = devicelock.buckets(base)
    after = devicelock.buckets({**base, "maturity": "draft"})
    assert before["surface"] != after["surface"]


def test_the_version_field_says_where_its_rules_live():
    """The issue's fourth bullet: `version` ranged 0.2.7 to 3.0.5 with the bump
    policy written in DESIGN.md and CONTRIBUTING and nowhere the field itself
    could point at."""
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    desc = schema["properties"]["version"].get("description", "")
    assert "device.lock.json" in desc and "DESIGN.md" in desc, desc[:120]
