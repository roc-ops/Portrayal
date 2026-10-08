"""A size nobody measured reads exactly like one somebody did.

`MPC7E-10G` is one part. The library draws it at 420.9 x 29.5 in the MX240 and
at 30.1 x 405.0 in the MX960 - not the same rectangle at two angles, but two
different guesses at a card with one real size (#261).

The provenance was honest about it all along:

    registry + layout - the face is the slot geometry of its chassis family
    ... NOT measured from a faceplate drawing

**And that sentence is why no search could find them.** Any grep of that prose
for a confidence word finds `measured`, in the clause that exists to deny it.
104 contracts hid behind their own honesty, and #261 found them by PARSING
provenance rather than grepping it.

So the gate cannot read prose. `size-confidence` is a structured field the schema
has described all along and the index has tallied all along - and 502 of the 526
parts with a size never filled it, so the tally counted almost nothing. L97 asks
for it.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

import libdata            # noqa: E402
from portrayal import lint  # noqa: E402

VOCAB = {"measured", "photo-measured", "drawing", "datasheet", "registry",
         "borrowed", "estimated", "known-wrong"}


def _sized():
    return [(ref, path, doc) for ref, path, doc in libdata.components() if doc.get("size")]


def test_l97_is_registered_as_a_component_rule():
    assert lint.RULES["L97"][0] == "component"


def test_the_rule_fires_on_a_stated_size_with_no_confidence():
    with lint.collecting() as got:
        lint.lint_component_size_confidence(
            pathlib.Path("t.yaml"), {"size": {"w": 10.0, "h": 5.0}})
    assert len(got.warnings) == 1 and "[L97]" in got.warnings[0]


def test_the_rule_is_quiet_when_every_stated_dimension_is_answered():
    with lint.collecting() as got:
        lint.lint_component_size_confidence(
            pathlib.Path("t.yaml"),
            {"size": {"w": 10.0, "h": 5.0},
             "size-confidence": {"w": "measured", "h": "measured"}})
    assert got.warnings == []


def test_a_dimension_that_is_not_stated_is_not_asked_about():
    """Most parts state w and h and no depth. Asking for a confidence about a
    number that does not exist would make the census noise."""
    with lint.collecting() as got:
        lint.lint_component_size_confidence(
            pathlib.Path("t.yaml"),
            {"size": {"w": 10.0, "h": 5.0},
             "size-confidence": {"w": "estimated", "h": "estimated"}})
    assert got.warnings == []


# --- the 104, and why they are estimated -------------------------------------

def _chassis_sized():
    out = []
    for ref, path, doc in _sized():
        if "registry + layout" in str((doc.get("provenance") or {}).get("size", "")):
            out.append((ref, doc))
    return out


def test_every_chassis_sized_part_now_says_it_is_an_estimate():
    """#261's own instruction: *do not launder these into measurements*. If no
    drawing turns up, the right outcome is the estimate stays visible."""
    unmarked = [ref for ref, doc in _chassis_sized()
                if (doc.get("size-confidence") or {}).get("w") != "estimated"]
    assert not unmarked, unmarked
    # 102 until #261, which took 36 out of the group: the 18 MX960 vertical twins
    # were removed, and the 18 horizontal MX cards they twinned now state the Visio
    # stencil's lever envelope as a drawn width rather than a chassis opening.
    assert len(_chassis_sized()) >= 66, "the group has shrunk without explanation"


def test_each_one_says_which_chassis_opening_it_is():
    """The number is the slot, and a reader needs to know *which* slot - that is
    the whole of why one model number came out two sizes."""
    thin = [ref for ref, doc in _chassis_sized()
            if "slot opening" not in str(doc.get("size-notes", ""))
            and "window" not in str(doc.get("size-notes", ""))]
    assert not thin, thin


def test_prose_would_call_most_of_them_measured_which_is_the_point():
    """NOT A JOKE. This asserts the trap is real, and measures how real.

    **97 of the 104** carry the word `measured` in the sentence that exists to
    DENY it - "NOT measured from a faceplate drawing" - so a prose-reading rule
    would mark those 97 as measured. That is worse than silence, because it
    would be believed. The other seven are blank panels whose note says the
    guide "does not dimension it separately" and never uses the word at all, so
    prose would have called them nothing; wrong two different ways.
    """
    grp = _chassis_sized()
    misread = [ref for ref, doc in grp
               if "measured" in str((doc.get("provenance") or {}).get("size", ""))]
    # 90 until #261 took 36 MX card contracts out of the group (see above)
    assert len(misread) >= 59, (
        f"only {len(misread)} of {len(grp)} would be misread as measured; if the "
        "prose was rewritten, this test has served its purpose and can go")
    assert len(misread) < len(grp), (
        "every one now says `measured`, which would make the point differently")


def test_the_vocabulary_is_the_one_the_schema_owns():
    import json
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    assert set(schema["$defs"]["confidence"]["enum"]) == VOCAB


def test_the_backlog_is_counted_and_shrinking():
    """A census warning of the L92/L93 kind: it fires on what is unstated and is
    meant to shrink. An upper bound, so answering one is never a failure."""
    unstated = [ref for ref, _p, doc in _sized()
                if any(doc["size"].get(d) is not None
                       and not (doc.get("size-confidence") or {}).get(d)
                       for d in ("w", "h", "d"))]
    assert len(unstated) <= 465, f"{len(unstated)} parts do not say, up from 465"
    assert len(_sized()) >= 500, "the census did not find the catalogue"
