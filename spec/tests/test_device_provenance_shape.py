"""Device provenance is `{confidence?, note}`, and the word is never guessed.

roc-ops/Portrayal#167. It used to be `{key: prose}`: 530 distinct keys across 89
devices, a median value of 566 characters and a maximum of 6,704, with the
confidence word a convention at the front of the sentence that 35% of entries
did not follow.

THE RULE THAT NEEDED THE STRUCTURE. `maturity: verified` means no dimension may
be estimated, and L15 implemented that as

    str(value).lstrip().lower().startswith("estimated")

Across the corpus 42 entries opened with the word and 80 more said it somewhere
in the middle of a paragraph - "ESTIMATED shape, from photographs", "the layout
is estimated". The gate on the top maturity level saw a third of what it guarded
against. Nothing is at `verified` yet, so nothing was mis-certified; the first
device to claim it would have been.

WHAT THE MIGRATION DID NOT DO. 944 of 1688 entries opened with one of the eight
words and were migrated carrying it. The other 744 were migrated with the prose
intact and NO CONFIDENCE INVENTED. Reading 744 paragraphs and deciding
measured-or-estimated by eye is how an estimate becomes a measurement, and the
count is the honest report of how much of the library has never said. L93 counts
it; this file holds it from growing.

Components are deliberately NOT migrated: their provenance is `{key: string}`
and #173 settled its key vocabulary. Two shapes is a cost, and it is smaller than
one sweep that touched everything at once.
"""
import json
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint  # noqa: E402

ENUM = set(json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
           ["$defs"]["confidence"]["enum"])


@pytest.fixture(scope="module")
def devices():
    return {f"{p.parts[-3]}/{p.parts[-2]}": yaml.safe_load(p.read_text()) or {}
            for p in sorted(LIB.glob("devices/*/*/device.yaml"))}


def entries(devices):
    for slug, d in devices.items():
        for k, v in (d.get("provenance") or {}).items():
            yield slug, k, v


def test_there_are_entries_to_check(devices):
    """NON-VACUITY. Every sweep below iterates provenance and would pass over an
    empty one."""
    assert sum(1 for _ in entries(devices)) > 1500


def test_every_entry_is_an_object_with_a_note(devices):
    bad = [f"{s}/{k}" for s, k, v in entries(devices)
           if not isinstance(v, dict) or not str(v.get("note") or "").strip()]
    assert not bad, f"{len(bad)} entries are not {{confidence?, note}}: {bad[:5]}"


def test_a_stated_confidence_is_one_of_the_eight(devices):
    bad = {v["confidence"] for _, _, v in entries(devices)
           if isinstance(v, dict) and v.get("confidence") not in (None, *ENUM)}
    assert not bad, f"confidence values outside the enum: {sorted(bad)}"


def test_the_prose_survived_the_migration(devices):
    """Spot-checks against sentences that were in the file before it moved. The
    migration asserted this per file as it ran; this keeps it asserted."""
    p = devices["maiaedge/pbc-2000"]["provenance"]
    assert p["size"]["confidence"] == "datasheet"
    assert 'Chassis (H x W x D) 1.625 x 17.24 x 11.46 in' in p["size"]["note"]
    assert "L43 exists because a device was once modelled wearing its flanges" in p["size"]["note"]
    assert "confidence" not in p["numbering"], "nothing should have been invented here"


def test_the_unstated_confidences_are_counted_and_not_growing(devices):
    """744 at the migration. It may fall; it may not rise, because the only way
    to add one is to write a figure without saying how it is known."""
    bare = [f"{s}/{k}" for s, k, v in entries(devices)
            if isinstance(v, dict) and not v.get("confidence")]
    assert len(bare) <= 744, (
        f"{len(bare)} entries state no confidence, up from 744:\n  "
        + "\n  ".join(sorted(bare)[:8]))


def test_a_good_share_of_them_do_say(devices):
    """The other side, so the test above cannot be satisfied by deleting the
    field everywhere."""
    total = sum(1 for _ in entries(devices))
    said = sum(1 for _, _, v in entries(devices) if isinstance(v, dict) and v.get("confidence"))
    assert said >= 944, f"only {said} of {total} entries carry a confidence"


# --- the rule that needed it -------------------------------------------------

def _verified(tmp_path, provenance):
    """Lint a device claiming `verified` and return its L15 findings."""
    import json
    import jsonschema
    doc = {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
           "maturity": "verified", "profile": "networking",
           "manufacturer": "M", "model": "M",
           "chassis": {"width": 100.0, "height": 44.0, "depth": 200.0},
           "provenance": provenance,
           "views": {"front": {"size": {"w": 100.0, "h": 44.0}}}}
    f = tmp_path / "device.yaml"
    f.write_text(yaml.safe_dump(doc))
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    lint.ERRORS.clear(); lint.WARNINGS.clear()
    lint.lint_device(f, jsonschema.Draft202012Validator(schema), [str(LIB)])
    return [e for e in lint.ERRORS if "[L15]" in e]


SOURCED = {"confidence": "datasheet", "note": "datasheet - the vendor's own Table 3"}


def test_the_verified_gate_catches_a_structured_estimate(tmp_path):
    found = _verified(tmp_path, {"size": SOURCED,
                                 "layout": {"confidence": "estimated",
                                            "note": "a plausible arrangement"}})
    assert any("estimated" in e and "layout" in e for e in found), found


def test_the_verified_gate_now_catches_a_BURIED_estimate(tmp_path):
    """THE DEFECT, end to end. The check was `startswith("estimated")`, so a note
    saying it in the middle of a sentence passed - and 80 of the library's 122
    such notes do exactly that."""
    found = _verified(tmp_path, {"size": SOURCED,
                                 "layout": {"note": "the arrangement is estimated from a photo"}})
    assert any("estimated" in e and "layout" in e for e in found), found


def test_a_verified_device_with_nothing_estimated_passes(tmp_path):
    """NON-VACUITY: a check that fires on everything is not a check. Ordinary
    sourced prose must not trip the word search."""
    found = _verified(tmp_path, {"size": SOURCED,
                                 "layout": {"confidence": "measured",
                                            "note": "measured off figure 7 at 3.1 px/mm"}})
    assert not [e for e in found if "estimated" in e], found


# --- and the component side is untouched --------------------------------------

def test_component_provenance_is_still_a_string():
    """Two shapes, on purpose. Migrating 584 contracts in the same pass would
    have made one reviewable change into an unreviewable one, and #173 had just
    settled the component key vocabulary."""
    c = yaml.safe_load((LIB / "components/std/qsfp28/v1/contract.yaml").read_text())
    prov = c.get("provenance") or {}
    assert prov and all(isinstance(v, str) for v in prov.values()), prov
