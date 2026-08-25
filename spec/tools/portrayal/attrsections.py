#!/usr/bin/env python3
"""The sections of `attrs`, and the one flattening every consumer must share.

`attrs` was a flat bag of 74 distinct spellings across 13 devices, and the drift
was visible without looking hard: `power-max`, `power-ac-max-w`, `power-max-ac-w`
and `power-max-dc-w` were four names for one fact, and `profiles.yaml` had grown
an alias list per fact to cope. An alias list is a record of a problem, not a
fix - it makes `specified` mean "has a key spelled one of four ways" rather than
"states its power draw", which is a far worse predicate and one nobody can argue
with on its merits.

Sections end that. A requirement can now name a SECTION - "has thermal data" -
and the spellings inside it were normalised in the same pass, so where a key
still has to be named there is exactly one of it.

WHY THE SECTION IS NOT PART OF THE KEY
--------------------------------------
`attrs.power.power-max-w` looks redundant and the temptation is to write
`attrs.power.max-w`. It is deliberate, for two reasons.

First, these keys leave the manifest. Every one of them is flattened onto the
SVG root as `data-<key>`, and a drawing is a file somebody opens somewhere else -
`data-max-w` on its own says nothing, and `data-power-max-w` says exactly what it
holds. A key has to survive being read without its container.

Second, the section is a CLASSIFICATION of a fact, not a namespace for it. The
same fact keeps the same name whether or not we later decide `airflow` is
thermal or environmental, so re-filing a key is a one-line move that changes no
drawing, no export and no consumer. That is what makes the taxonomy cheap enough
to correct - and a taxonomy nobody can correct is one nobody will.

So: keys are globally unique, and lint L25 is an ERROR if two sections ever claim
the same one, because the flattening below cannot represent it.
"""

# The order is the order they are printed in - the box, then what it does, then
# what it costs to run, then what it is made of, then the paperwork.
SECTIONS = (
    "physical",
    "performance",
    "power",
    "thermal",
    "environmental",
    "platform",
    "features",
    "management",
    "compliance",
    "lifecycle",
    "other",
)

# `other` is a section, not an escape hatch, and the difference is that somebody
# counts it. 17 of the 22 keys that fit no section appeared on exactly one
# device, so the tail is real and a 23rd section per one-off device would be a
# taxonomy of one thing each. What must not happen is the tail going quiet: lint
# L24 counts `other` per device and the gaps register carries it as
# `attrs-unclassified`, so it either shrinks as patterns emerge or stays visibly
# unshrunk. An `other` that nobody counts is how a taxonomy dies.
TAIL = "other"

# `lifecycle.eol` is a three-state field and the third state is the point. A
# device with no lifecycle section has NOT been checked; `none-announced` means
# somebody searched and the vendor has announced nothing, which is a real finding
# and must not be indistinguishable from nobody looking. `announced` owes an
# `eol-announcement` URL - EOL notices are nearly always public, and a date with
# no link is a claim about a product that no reader can check.
EOL_STATES = ("none-announced", "announced")


def flatten(attrs):
    """{section: {key: value}} -> {key: value}, in section order.

    Every consumer that wants "the facts about this device" calls this rather
    than iterating sections itself, so `data-*` on a drawing, the search blob and
    an export cannot disagree about what the bag holds.

    Tolerates a flat bag so that a manifest the schema has already rejected
    still renders far enough to be looked at. It is not a second supported
    shape: `attrs` is `additionalProperties: false` over the sections, so an
    unsectioned key is a schema error (L1) before it reaches here.
    """
    out = {}
    for section in SECTIONS:
        for k, v in (attrs or {}).get(section, {}).items():
            out[k] = v
    for k, v in (attrs or {}).items():          # a pre-section flat bag
        if k not in SECTIONS and not isinstance(v, dict):
            out[k] = v
    return out


def unsectioned(attrs):
    """Keys sitting at the top of `attrs` instead of inside a section."""
    return [k for k, v in (attrs or {}).items()
            if k not in SECTIONS and not isinstance(v, dict)]


def collisions(attrs):
    """{key: [section, section]} for any key claimed by more than one section."""
    seen, dupes = {}, {}
    for section in SECTIONS:
        for k in (attrs or {}).get(section, {}):
            if k in seen:
                dupes.setdefault(k, [seen[k]]).append(section)
            else:
                seen[k] = section
    return dupes
