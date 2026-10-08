"""L89: a component major nothing reaches says why nothing reaches it.

The library is the only consumer of its own parts - every reference lives in
this repository - so "does anything use this" has an exact answer and nothing
was asking for it. 55 majors of 587 turned out to be reachable from no device,
and from the outside they looked exactly like the 532 that were.

They were not one thing. 38 are ASR 9000 cards drawn off stencils and datasheets
whose chassis `accepts` lists name a different card generation (#262). Four are
older majors superseded by a version every device now uses. One is a reference
drawing that nothing should ever seat. Deleting them all would throw away
sourced work; keeping them all quietly is how the count reached 55.

So the field is a SENTENCE, not a deletion and not a waiver flag - the same
shape as `optical.unused` (L80) and a view's `empty:` (L45).

THE TRAP THIS RULE HAD TO AVOID. `ufispace/psu-120-ac@1` is named inside the
S9502's own note, in a paragraph explaining why that device does NOT place it:
the AC build is a different front panel, not the DC panel with another
connector. A substring search would have read that explanation as a use, and the
one part whose absence is best documented would have been the one part that
looked seated. Refs are matched as whole strings for exactly that reason.
"""
import pathlib
import re
import sys

import json
import jsonschema
import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
from portrayal import lint
from portrayal import components_catalogue as cat


def run(root):
    with lint.collecting() as _found:
        lint.lint_unplaced_majors(root)
    return [e for e in _found.errors if "[L89]" in e]


# --- the live library ---------------------------------------------------------

def test_the_library_has_no_unexplained_majors():
    """The corpus, which is the only run that matters. Every major is reachable
    from a device, or carries the sentence saying what would seat it."""
    found = run(LIB)
    assert found == [], f"{len(found)} unexplained:\n" + "\n".join(found[:10])


def test_most_of_the_library_is_actually_reachable():
    """NON-VACUITY for the test above, which passes by finding nothing - which
    is also what it does if the glob breaks or `devices/` moves. The rule has
    its own guard for this; this asserts the guard's premise independently."""
    majors = {f"{c.parts[-4]}/{c.parts[-3]}@{c.parts[-2][1:]}"
              for c in LIB.glob("components/*/*/v*/contract.yaml")}
    declared = {f"{c.parts[-4]}/{c.parts[-3]}@{c.parts[-2][1:]}"
                for c in LIB.glob("components/*/*/v*/contract.yaml")
                if (yaml.safe_load(c.read_text()) or {}).get("unplaced")}
    assert len(majors) > 400, f"only {len(majors)} contracts found - the walk is broken"
    assert len(declared) < len(majors) // 4, (
        f"{len(declared)} of {len(majors)} majors are declared unplaced; the field is "
        "becoming the answer rather than the exception")


# --- the rule, on libraries built to exercise one thing each ------------------

def write(root, ref, **keys):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    p = root / "components" / ns / name / f"v{major}" / "contract.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = {"format": 1, "kind": "module", "name": name, "version": "1.0.0",
           "class": "psu", "size": {"w": 10.0, "h": 10.0}}
    doc.update(keys)
    p.write_text(yaml.safe_dump(doc))
    return p


def device(root, name, *refs, note=None):
    p = root / "devices" / "acme" / name / "device.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = {"format": 1, "kind": "device", "name": name, "version": "1.0.0",
           "manufacturer": "Acme", "model": name, "maturity": "modelled",
           "chassis": {"width": 440.0, "height": 44.0, "depth": 300.0},
           "views": {"front": {"size": {"w": 440.0, "h": 44.0},
                               "panel": {"placements": [
                                   {"ref": r, "id": f"p{i}", "at": [float(i), 1.0]}
                                   for i, r in enumerate(refs)]}}}}
    if note:
        doc["views"]["front"]["note"] = note
    p.write_text(yaml.safe_dump(doc))
    return p


def bulk(root, n):
    """Enough seated parts that the rule's own broken-walk guard stays quiet."""
    refs = [f"std/filler-{i}@1" for i in range(n)]
    for r in refs:
        write(root, r)
    device(root, "filler", *refs)


def test_a_part_nothing_reaches_is_reported(tmp_path):
    bulk(tmp_path, 8)
    write(tmp_path, "common/orphan@1")
    found = run(tmp_path)
    assert len(found) == 1 and "common/orphan@1" in found[0], found


def test_a_part_a_device_places_is_not_reported(tmp_path):
    bulk(tmp_path, 8)
    write(tmp_path, "common/seated@1")
    device(tmp_path, "box", "common/seated@1")
    assert run(tmp_path) == []


def test_the_sentence_is_what_clears_it(tmp_path):
    bulk(tmp_path, 8)
    write(tmp_path, "common/orphan@1",
          unplaced="no chassis in this library has a bay it fits; see issue 262 for the matrix")
    assert run(tmp_path) == []


def test_a_bay_on_a_seated_part_counts_as_a_use(tmp_path):
    """How the MIC twins are referenced. `mpc1e-3d-v2k` names ten of them in
    a bay's `accepts`, and no device names any of them directly - so a walk that
    stopped at a contract's `parts:` would have called all ten dead. Both
    existing dependency walkers in this repository stop there."""
    bulk(tmp_path, 8)
    write(tmp_path, "common/mic@1")
    write(tmp_path, "common/carrier@1",
          bays={"mic0": {"at": [0.0, 0.0], "size": [10.0, 10.0],
                         "accepts": ["common/mic@1"], "default": "common/mic@1"}})
    device(tmp_path, "box", "common/carrier@1")
    assert run(tmp_path) == []


def test_a_part_composed_only_by_an_unplaced_part_needs_no_sentence_of_its_own(tmp_path):
    """The QSFP pull tab: composed by the QSFP transceiver, which is itself
    unplaced. One sentence about the transceiver covers both, and requiring a
    second would put the reason on the sub-part - the one place nobody looks."""
    bulk(tmp_path, 8)
    write(tmp_path, "common/tab@1")
    write(tmp_path, "common/optic@1", parts=[{"ref": "common/tab@1", "at": [0.0, 0.0]}],
          unplaced="devices model the cage, not the optic in it; nothing seats a transceiver yet")
    assert run(tmp_path) == []


def test_a_sentence_that_outlived_its_gap_is_reported(tmp_path):
    """The half that keeps the other half honest. Without it `unplaced:` is a
    line you add once and nobody ever removes, and the library slowly fills with
    parts described as unused that are not."""
    bulk(tmp_path, 8)
    write(tmp_path, "common/seated@1",
          unplaced="nothing seats this part yet, and here is a sentence long enough to pass")
    device(tmp_path, "box", "common/seated@1")
    found = run(tmp_path)
    assert len(found) == 1 and "has been closed" in found[0], found


def test_a_ref_named_inside_a_sentence_is_not_a_use(tmp_path):
    """THE S9502 CASE, which is why refs match whole strings. That device's note
    names `ufispace/psu-120-ac@1` while explaining that it deliberately does not
    place it."""
    bulk(tmp_path, 8)
    write(tmp_path, "common/orphan@1")
    device(tmp_path, "box", note="common/orphan@1 is built and sourced, and this "
                                 "device does not place it because the AC face differs")
    found = run(tmp_path)
    assert len(found) == 1 and "common/orphan@1" in found[0], found


def test_a_broken_walk_says_so_rather_than_passing(tmp_path):
    """A library where nothing is reachable is this rule failing, not the
    library being empty - and reporting 500 parts as unexplained would bury
    that. The guard fires instead."""
    for i in range(10):
        write(tmp_path, f"common/part-{i}@1")
    found = run(tmp_path)
    assert len(found) == 1 and "walk is broken" in found[0], found


# --- a dead major goes, which is what pays for the v<major> level (#172) -------

def test_a_superseded_major_nothing_names_must_be_deleted_not_described(tmp_path):
    """#172 kept the directory level on these terms. Without this, `unplaced:`
    becomes the place old majors go to be described instead of removed, which is
    the accumulation that made dropping the level look right in the first
    place."""
    bulk(tmp_path, 8)
    write(tmp_path, "common/psu@1", unplaced="superseded by @2, which every device places; kept for now")
    write(tmp_path, "common/psu@2")
    device(tmp_path, "box", "common/psu@2")
    found = run(tmp_path)
    assert len(found) == 1 and "delete the directory" in found[0], found


def test_a_superseded_major_something_still_names_may_stay(tmp_path):
    """THE PBC CASE, and the reason this asks for a mention rather than a
    seating. `common/psu-550w@1` is retired and seated by nothing, and the
    PBC-2000's `psu-module-width` gap argues from its 84.0 mm against the 73.5
    of the `@2` the device actually places. A retired major can be one side of
    an open question, and deleting it takes the figure with it."""
    bulk(tmp_path, 8)
    write(tmp_path, "common/psu@1", unplaced="retired, but the rear photograph reads closer to this one")
    write(tmp_path, "common/psu@2")
    device(tmp_path, "box", "common/psu@2",
           note="the photograph reads 85.5, closer to the retired common/psu@1 than to what is placed")
    assert run(tmp_path) == []


def test_an_older_major_is_only_superseded_by_a_LIVE_one(tmp_path):
    """Two dead majors of one name are both just unreferenced. Calling the lower
    one 'superseded' by a sibling nothing uses would demand a deletion that
    fixes nothing and lose the sentence explaining both."""
    bulk(tmp_path, 8)
    for v in (1, 2):
        write(tmp_path, f"common/psu@{v}",
              unplaced="the chassis that takes this supply is not modelled yet, see issue 262")
    assert run(tmp_path) == []


def test_the_live_library_keeps_no_retired_major(tmp_path):
    """The corpus side of the two tests above: #172's deletions happened, and
    nothing survives them. A name keeps two majors on disk only while the old
    one is still reachable or still argued from; three names do today, each
    for the reason given in `kept` below, and no other name may."""
    import collections
    majors = collections.defaultdict(list)
    for c in LIB.glob("components/*/*/v*/contract.yaml"):
        majors[f"{c.parts[-4]}/{c.parts[-3]}"].append(int(c.parts[-2][1:]))
    multi = {n: sorted(v) for n, v in majors.items() if len(v) > 1}
    # KEPT ON PURPOSE, each while something still argues from it (the rule
    # in the docstring above). The QSFP generics' @1 are the seating fixtures of the
    # mechanism tests (a superseded part still resolves, so a fixture need not
    # move with the accept lists); common/qsfp-pull-tab@1 is what the retired
    # common/qsfp-transceiver@1 composes. Each @1 carries `superseded-by`.
    kept = {"generic/qsfp-lc": [1, 2], "generic/qsfp-dd-lc": [1, 2],
            "common/qsfp-pull-tab": [1, 2]}
    assert multi == kept, multi
    # psu-550w USED TO BE HERE, the one retired major kept on purpose: the
    # PBC-2000's `psu-module-width` gap argued from @1's 84.0 mm against the
    # 73.5 of the @2 that device placed. A square-on photograph of the PBC-2000's
    # rear measured its supplies at 73.9 and 73.6, the gap closed, and @1 was
    # deleted the same day - the rule working as written: kept while something
    # argues from it, gone when nothing does. usb-a was here before that, until
    # #264 split its @3 out as `common/usb-a-bezel@1`.


# --- the field itself ---------------------------------------------------------

def test_the_schema_wants_a_sentence_not_a_word():
    """A one-word `unplaced: yes` would make the field a flag, which is the
    failure mode of every waiver list."""
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    v = jsonschema.Draft202012Validator(schema)
    part = {"format": 1, "kind": "module", "name": "t", "version": "1.0.0",
            "class": "psu", "size": {"w": 1.0, "h": 1.0}}
    assert list(v.iter_errors(dict(part, unplaced="yes"))), "a bare flag should be rejected"
    assert not list(v.iter_errors(dict(
        part, unplaced="no chassis in this library has a bay that fits it; see issue 262")))


def test_the_catalogue_does_not_read_the_sentence_as_a_use(tmp_path):
    """A superseded major's `unplaced:` sentence names what replaced it. The
    catalogue counts refs in a contract's raw text on purpose - a part cited in
    provenance as the origin of a borrowed figure is worth showing - but this
    one field is about the ABSENCE of a user, so counting it would have the
    superseded part reporting itself as composing its replacement.

    Built in a scratch library: the live case, `common/psu-550w@1`, was deleted
    once nothing argued from it, and a test of the catalogue should not depend
    on the corpus happening to keep a retired part."""
    old = tmp_path / "components/common/widget/v1"
    new = tmp_path / "components/common/widget/v2"
    for d in (old, new):
        d.mkdir(parents=True)
    text = (
        "format: 1\nkind: component\nname: widget\nversion: 1.0.0\n"
        "unplaced: >-\n"
        "  superseded by common/widget@2, which every device now places; kept only\n"
        "  while a gap somewhere still argues from this major's own width.\n"
        "size: {w: 10, h: 10}\n"
    )
    (old / "contract.yaml").write_text(text)
    (new / "contract.yaml").write_text(
        "format: 1\nkind: component\nname: widget\nversion: 2.0.0\nsize: {w: 10, h: 10}\n")
    assert "common/widget@2" in text, "the sentence should name what replaced it"
    assert "common/widget@2" not in cat.without_non_use_refs(text)
    assert "widget" in cat.without_non_use_refs(text), \
        "only the unplaced block should be removed"
    composed = cat.composed_by(tmp_path)
    assert "common/widget@1" not in composed.get("common/widget@2", set())
