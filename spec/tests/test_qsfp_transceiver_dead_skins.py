"""Pluggables D, task 2: `common/qsfp-transceiver`'s five `body-*.svg` skins
are dead, and the docs must stop implying they are read.

`common/qsfp-transceiver@1` is `superseded-by: generic/qsfp-lc@1`
(test_superseded_by.py) and nothing in the library places it
(test_cage_accepts.py's `all_refs` check). Its `skins:` list names only `lc`;
`body-top.svg`, `body-bottom.svg`, `body-left.svg`, `body-right.svg` and
`body-rear.svg` sit in its `skins/` directory unreferenced by that list, by any
`relief.features[].node`, and - per docs/pluggables-3d-design.md - by
`relief.js`/`viewer3d.js` either. D1 (Jason, 2026-09-21) is to delete them, not
wire them in.

A LIBRARY-WIDE VERSION OF THE FIRST TEST WOULD BE WRONG. `body-*.svg` is a
documented convention (library/components/README.md) for "parts that have a 3D
body", and fifteen OTHER components - `common/psu-ac-650`, `common/fan-module`,
`edgecore/agr-fan` among them - carry the same five names, equally unread by
`relief.js` today, and are not being retired here. Scoping to
`common/qsfp-transceiver` is deliberate, not a shortcut: this is the one part
the plan (docs/superpowers/plans/2026-09-21-pluggables-d-standing-proud.md,
task 2) actually retires, and a sweep of every `body-*.svg` in the library
would fail on components nobody asked to touch.

The second test targets the ONE claim this task's brief calls out by name: that
"the viewer uses them to texture the box." That exact sentence sat in
`library/components/README.md` until #400 (spec A) replaced it with "NOTHING
READS THEM TODAY" - and the plan doc for that spec (excluded below) still
carries the old wording as its own historical record of what was wrong. The
regex is deliberately narrow (`uses ... to texture ... box`) rather than a
looser "texture" + "box" scan, because a looser one also matches
docs/pluggables-3d-design.md's "The README says the viewer textures a box from
them; nothing in `relief.js` ... reads them" - which is that document
QUOTING the old claim in order to refute it, not making it. That document and
docs/pluggables-design.md are D's own decision record (docs/superpowers/plans/
2026-09-21-pluggables-d-standing-proud.md's task-2 brief names both and says
leave their descriptive sentences) and are excluded from the scan by name for
the same reason docs/superpowers/plans/ is excluded wholesale: a plan or design
doc's job is to narrate a defect, including by quoting it.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DOCS = ROOT / "docs"

# The plan/decision documents allowed to describe or quote the old claim
# without being read as re-asserting it. See the module docstring.
EXEMPT_DOCS = {
    DOCS / "pluggables-3d-design.md",
    DOCS / "pluggables-design.md",
}

# The exact false claim #400 removed from library/components/README.md, and
# the one docs/superpowers/plans/2026-09-18-pluggables-a-generic-transceivers.md
# still carries verbatim as the record of what was wrong.
STALE_CLAIM = re.compile(r"viewer\s+uses\s+(?:them|it)\s+to\s+texture\s+(?:the|a)\s+box",
                          re.IGNORECASE)


def test_common_qsfp_transceiver_ships_no_orphan_body_skins():
    """Every `body-*.svg` under `common/qsfp-transceiver`'s version directories
    is gone - the part D1 decided to delete rather than wire in.

    Walks every `v*/` directory rather than assuming `v1`, so a future major
    bump of this same component cannot quietly reintroduce the five files this
    test exists to keep out.
    """
    base = LIB / "components/common/qsfp-transceiver"
    assert base.is_dir(), f"expected {base} to exist"
    checked = 0
    for major_dir in sorted(base.glob("v*")):
        checked += 1
        skins_dir = major_dir / "skins"
        orphans = sorted(p.name for p in skins_dir.glob("body-*.svg")) if skins_dir.is_dir() else []
        assert orphans == [], (
            f"{major_dir} ships {orphans}, which D1 (2026-09-21) decided to "
            "delete - nothing in the contract's `skins:` list, no "
            "`relief.features[].node`, and no reader in relief.js/viewer3d.js "
            "names them (docs/pluggables-3d-design.md)")
    assert checked > 0, f"no v*/ directory found under {base} - the walk found nothing to check"


def test_no_doc_outside_plans_claims_the_viewer_textures_from_body_skins():
    """No `.md` under `library/` or `docs/` - excluding
    `docs/superpowers/plans/` and the two decision docs that narrate this exact
    defect - claims "the viewer uses [body skins] to texture the box".

    That claim was true of nothing even before D1: docs/pluggables-3d-design.md
    already established `relief.js` never read these files. #400 already fixed
    `library/components/README.md`'s copy of the claim, so this is a regression
    guard rather than today's fix - it is the plan's own test-first item for
    task 2, kept here so nobody's edit reintroduces the sentence.
    """
    plans_dir = DOCS / "superpowers" / "plans"
    hits = []
    for md in sorted(LIB.rglob("*.md")) + sorted(DOCS.rglob("*.md")):
        if plans_dir in md.parents or md in EXEMPT_DOCS:
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        if STALE_CLAIM.search(text):
            hits.append(str(md.relative_to(ROOT)))
    assert hits == [], f"stale 'viewer textures a box from body skins' claim in: {hits}"
