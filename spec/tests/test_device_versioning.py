"""Device versioning: a device cannot change without saying so.

The rules under test are about DISCIPLINE rather than geometry, so the fixtures
are the smallest devices that can express a change of each kind.
"""
import pathlib
import sys


from portrayal import devicelock as dl
from portrayal import libwalk

ROOT = pathlib.Path(__file__).resolve().parents[2]


def dev(version="1.0.0", at=(0, 0), extra_bay=None, gaps=None, note="a",
        portfolio=None):
    bays = [{"id": "slot-0", "at": list(at), "size": {"w": 10, "h": 10},
             "group": "slots", "accepts": ["x/y@1"]}]
    if extra_bay:
        bays.append({"id": extra_bay, "at": [50, 0], "size": {"w": 10, "h": 10},
                     "group": "slots", "accepts": ["x/y@1"]})
    return {
        "kind": "device", "name": "d", "version": version,
        **({"portfolio": portfolio} if portfolio else {}),
        "chassis": {"width": 100, "height": 40, "depth": 30},
        "groups": {"slots": {"term": "Slot", "index-origin": 0}},
        "provenance": {"size": note},
        "gaps": gaps if gaps is not None else [],
        "views": {"front": {"size": {"w": 100, "h": 40},
                            "components": {"bays": bays}}},
    }


# ---- what kind of change is this? -------------------------------------------

def test_an_unchanged_device_needs_no_bump():
    a = dl.entry(dev())
    assert dl.required_bump(a, dl.entry(dev())) is None


def test_a_reworded_provenance_is_a_patch():
    a = dl.entry(dev(note="a"))
    assert dl.required_bump(a, dl.entry(dev(note="b"))) == "patch"


def test_a_moved_slot_is_major_even_though_nothing_was_removed():
    """The ids are identical; a coordinate someone cached is not."""
    a = dl.entry(dev(at=(0, 0)))
    assert dl.required_bump(a, dl.entry(dev(at=(1, 0)))) == "major"


def test_an_added_bay_is_minor():
    a = dl.entry(dev())
    assert dl.required_bump(a, dl.entry(dev(extra_bay="slot-1"))) == "minor"


def test_a_removed_bay_is_major():
    a = dl.entry(dev(extra_bay="slot-1"))
    assert dl.required_bump(a, dl.entry(dev())) == "major"


def test_key_order_and_integral_floats_are_not_changes():
    """Two files that differ only in how they are spelled are one device.
    A fingerprint that fires on re-indentation gets re-locked without being
    read, which is how a check stops being read at all."""
    a = dev()
    b = dev()
    b["views"]["front"]["components"]["bays"][0]["at"] = [0.0, 0.0]
    b["chassis"] = {"depth": 30, "width": 100, "height": 40}
    assert dl.entry(a)["shape"] == dl.entry(b)["shape"]


# ---- a placement's group is addressing, not geometry -------------------------

def _grouped(g, **kw):
    """A device whose one placement carries group `g` (None = unlabelled)."""
    d = dev(**kw)
    p = {"id": "esd-jack", "at": [1, 1], "ref": "common/esd-jack@1"}
    if g is not None:
        p["group"] = g
    d["groups"]["grounding"] = {"term": "Point", "index-origin": 1}
    d["views"]["front"]["components"]["placements"] = [p]
    return d


def test_labelling_an_unlabelled_placement_is_minor_not_major():
    """THE BACKFILL. `group` used to sit in the shape bucket beside the
    coordinates, so adding one read as "same ids, different geometry: a slot
    moved". Backfilling the library is 174 placements across 11 devices, and
    every one of them took a 1.0.0 for metadata that moves nothing."""
    a = dl.entry(_grouped(None))
    b = dl.entry(_grouped("grounding"))
    assert dl.required_bump(a, b) == "minor"


def test_moving_a_placement_between_groups_is_still_major():
    """The other half. A consumer that addressed this thing by its group loses
    it, which is exactly what major is for."""
    a = dl.entry(_grouped("grounding"))
    b = dl.entry(_grouped("slots"))
    assert dl.required_bump(a, b) == "major"


def test_a_group_label_does_not_move_the_shape_hash():
    """Stated directly, so a future edit that puts `group` back into `_placements`
    fails here rather than quietly re-inflating every bump."""
    assert dl.entry(_grouped(None))["shape"] == dl.entry(_grouped("grounding"))["shape"]


def test_rel_pos_alone_is_not_a_change_at_all():
    """Six of the eight devices in this backfill needed only `rel-pos`, and
    nothing should have asked them for a version."""
    a = dev()
    b = dev()
    b["views"]["front"]["components"]["bays"][0]["rel-pos"] = 3
    assert dl.required_bump(dl.entry(a), dl.entry(b)) is None


def test_a_lock_written_before_the_field_existed_does_not_fire():
    """Old entries carry no `placement-groups`. That must read as 'unknown', not
    as 'every placement was reassigned'."""
    a = dl.entry(_grouped("grounding"))
    del a["placement-groups"]
    assert dl.required_bump(a, dl.entry(_grouped("grounding"))) is None


# ---- was the bump the author took big enough? -------------------------------

def test_a_patch_does_not_cover_a_moved_slot():
    assert not dl.sufficient(dl.bump_taken("1.0.0", "1.0.1"), "major")


def test_a_major_covers_anything():
    for need in ("patch", "minor", "major"):
        assert dl.sufficient(dl.bump_taken("1.0.0", "2.0.0"), need)


def test_no_bump_at_all_covers_nothing():
    assert not dl.sufficient(None, "patch")


def test_a_version_only_counts_up():
    assert dl.bump_taken("2.0.0", "1.9.9") == "backwards"
    assert not dl.sufficient("backwards", "patch")


# ---- the gaps re-affirmation ------------------------------------------------

GAP = [{"what": "port-led-semantics", "reason": "vendor-silent",
        "wanted": "a table", "scope": ["slots"]}]


def test_a_shape_change_asks_for_the_gaps_to_be_re_read(tmp_path):
    lib = _library(tmp_path, dev(gaps=GAP))
    dl.update(lib)
    _write(lib, dev(version="2.0.0", at=(1, 0), gaps=GAP))
    kinds = {k for _, k, _ in dl.check(lib)}
    assert "gaps-unreviewed" in kinds, "a moved slot left 1 gap unexamined and nothing said so"


def test_a_surface_change_does_not(tmp_path):
    """Firing on every provenance edit would make it noise."""
    lib = _library(tmp_path, dev(gaps=GAP))
    dl.update(lib)
    _write(lib, dev(version="1.0.1", note="b", gaps=GAP))
    assert not [f for f in dl.check(lib) if f[1] == "gaps-unreviewed"]


def test_a_device_with_no_gaps_is_not_nagged(tmp_path):
    lib = _library(tmp_path, dev(gaps=[]))
    dl.update(lib)
    _write(lib, dev(version="2.0.0", at=(1, 0), gaps=[]))
    assert not [f for f in dl.check(lib) if f[1] == "gaps-unreviewed"]


def test_re_locking_clears_the_prompt(tmp_path):
    """Re-locking is the 'I have read them' step, so it has to actually clear."""
    lib = _library(tmp_path, dev(gaps=GAP))
    dl.update(lib)
    _write(lib, dev(version="2.0.0", at=(1, 0), gaps=GAP))
    assert dl.check(lib)
    dl.update(lib)
    assert dl.check(lib) == []


# ---- gap scopes -------------------------------------------------------------

def test_a_gap_scoped_to_a_real_group_is_silent():
    assert dl.stale_gap_scopes(dev(gaps=GAP)) == []


def test_a_gap_scoped_to_nothing_is_reported():
    bad = [{"what": "w", "reason": "vendor-silent", "wanted": "x",
            "scope": ["no-such-thing"]}]
    assert dl.stale_gap_scopes(dev(gaps=bad)) == [("w", "no-such-thing")]


def test_a_gap_may_scope_an_id_a_view_or_a_nested_attr():
    d = dev(gaps=[{"what": "w", "reason": "vendor-silent", "wanted": "x",
                   "scope": ["slot-0", "front", "power-max-w"]}])
    d["attrs"] = {"power": {"power-max-w": "527 W"}}
    assert dl.stale_gap_scopes(d) == [], "a nested attribute key is a legitimate scope"


# ---- helpers ----------------------------------------------------------------

def _library(tmp_path, doc):
    lib = tmp_path / "library"
    (lib / "devices" / "v" / "d").mkdir(parents=True)
    _write(lib, doc)
    return lib


def _write(lib, doc):
    import yaml
    (lib / "devices" / "v" / "d" / "device.yaml").write_text(yaml.safe_dump(doc))


# ---- configurations say what kind of thing they are (#51) --------------------

def test_no_configuration_is_left_unclassified():
    """A consumer must be able to tell a SKU you can buy from a drawing."""
    import glob
    bad = []
    for p in libwalk.iter_devices([ROOT / "library"]):
        import yaml as y
        d = y.safe_load(open(p)) or {}
        for n, c in (d.get("configurations") or {}).items():
            if not (c or {}).get("kind"):
                bad.append(f"{p.split('devices/')[1]}:{n}")
    assert not bad, f"unclassified configurations: {bad[:5]}"


def test_at_most_one_base_per_device():
    import glob, yaml as y
    for p in libwalk.iter_devices([ROOT / "library"]):
        d = y.safe_load(open(p)) or {}
        bases = [n for n, c in (d.get("configurations") or {}).items()
                 if (c or {}).get("kind") == "base"]
        assert len(bases) <= 1, f"{p}: {bases}"


def test_examples_never_become_device_types():
    """The C40G exported 'C40G bdm-3plus1' - a device type named after a
    redundancy drawing, chosen because it was listed second."""
    import glob
    names = [pathlib.Path(f).stem
             for f in glob.glob(str(ROOT / "library/exports/*/device-types/*/*.yaml"))]
    # THE COMMITTED EXPORTS, which is what this can see. `build.sh` stopped
    # producing them when the export moved to `publish.sh`, so a run here checks
    # what is in the tree rather than what the exporter would make right now.
    # That is the right thing to check - they are committed data and a consumer
    # reads them as they are - but it means an exporter change is only caught
    # once somebody runs ./publish.sh. Asserted non-empty so the check cannot
    # pass by finding nothing.
    assert names, "no exported device types found; run ./publish.sh"
    import yaml as y
    examples = set()
    for p in libwalk.iter_devices([ROOT / "library"]):
        d = y.safe_load(open(p)) or {}
        for n, c in (d.get("configurations") or {}).items():
            if (c or {}).get("kind") == "example":
                examples.add(n)
    # A CONFIGURATION IS A TRAILING TOKEN, NOT A SUBSTRING. `e in n` reported
    # "PowerEdge R740xd lff-12-rear-2-lff" as an illustration because the
    # r740xd's `rear-2-lff` example is a substring of it - and that
    # configuration is ORDERABLE, a row of ISM table 28. The exporter separates
    # the model from the configuration with a SPACE ("C40G bdm-3plus1" above),
    # so an example leaks only when it is the whole stem or the whole tail after
    # a space. Matching mid-word condemns by accident.
    # NOT an exact "<model> <config>": sixteen stems in the tree are part-number
    # style (`5912-54X-O-48V-B`) with no model prefix, and building the
    # expected name from the model would stop checking those at all.
    leaked = sorted({n for n in names
                     for e in examples
                     if n == e or n.endswith(" " + e)})
    assert not leaked, f"illustrations exported as device types: {leaked}"


def test_adding_a_configuration_is_minor_not_major():
    """A `base` added to every modular chassis moved the names hash while every
    id stayed put, and the first version of this rule called all 23 major."""
    a = dev()
    b = dev()
    b["configurations"] = {"base": {"kind": "base"}}
    assert dl.required_bump(dl.entry(a), dl.entry(b)) == "minor"


def test_removing_a_configuration_is_major():
    """A configuration name can be held by something outside this repository."""
    a = dev(); a["configurations"] = {"base": {"kind": "base"}, "dc": {"kind": "orderable"}}
    b = dev(); b["configurations"] = {"base": {"kind": "base"}}
    assert dl.required_bump(dl.entry(a), dl.entry(b)) == "major"


def test_removing_a_group_is_major():
    a = dev()
    b = dev(); b["groups"] = {}
    assert dl.required_bump(dl.entry(a), dl.entry(b)) == "major"


def test_every_base_leaves_its_traffic_bays_empty():
    """The point of a base: a chassis you can log into, with nothing decided
    about traffic cards yet.

    A BLANK IS NOT A POPULATED SLOT. A chassis ships with blanking panels in its
    empty bays, for airflow, so a base that left holes would be drawing something
    nobody has ever seen on a rack.

    The blank set is built ONCE. It used to be rebuilt inside the device loop and
    every contract was parsed twice per rebuild - about thirty-five thousand YAML
    loads to recompute the same constant - which made this single test 125 of the
    suite's 293 seconds. It is the same set every time round.
    """
    import glob, yaml as y
    blanks = set()
    for q in glob.glob(str(ROOT / "library/components/*/*/v*/contract.yaml")):
        c = y.safe_load(open(q)) or {}
        if c.get("class") == "blank":
            blanks.add(f"{q.split('components/')[1].split('/')[0]}/{c['name']}")
    for p in libwalk.iter_devices([ROOT / "library"]):
        d = y.safe_load(open(p)) or {}
        base = next((c for c in (d.get("configurations") or {}).values()
                     if (c or {}).get("kind") == "base"), None)
        if not base:
            continue
        roles = {g: (gd or {}).get("role") for g, gd in (d.get("groups") or {}).items()}
        traffic = [b["id"] for v in (d.get("views") or {}).values()
                   for b in (((v or {}).get("components") or {}).get("bays") or [])
                   if roles.get(b.get("group")) == "traffic"]
        seated = [t for t in traffic
                  if (base.get("bays") or {}).get(t, "x") not in ("",)
                  and (base.get("bays") or {}).get(t, "x").split("@")[0] not in blanks]
        assert not seated, f"{p}: base leaves {seated[:3]} functionally populated"


def test_a_base_is_always_the_default():
    import glob, yaml as y
    for p in libwalk.iter_devices([ROOT / "library"]):
        d = y.safe_load(open(p)) or {}
        cfgs = d.get("configurations") or {}
        bases = [n for n, c in cfgs.items() if (c or {}).get("kind") == "base"]
        if not bases:
            continue
        dflt = [n for n, c in cfgs.items() if (c or {}).get("default")]
        assert dflt == bases, f"{p}: base={bases} default={dflt}"


def test_editing_a_faces_empty_declaration_is_at_least_a_patch():
    """`empty` decides whether a face counts as finished, so rewriting it moves a
    capability level. Unfingerprinted it could be edited - or deleted - with
    nothing asking for a version."""
    a = dev()
    b = dev()
    b["views"]["front"]["empty"] = "searched the whole corpus and found nothing at all about this face"
    assert dl.required_bump(dl.entry(a), dl.entry(b)) == "patch"


# ---- a bay's `accepts` is addressing, not geometry ---------------------------

def _accepting(*refs):
    """A device whose one bay accepts `refs`."""
    d = dev()
    d["views"]["front"]["components"]["bays"][0]["accepts"] = list(refs)
    return d


def test_a_bay_learning_it_accepts_more_is_minor():
    """THE MODULE CATALOGUE. `accepts` used to sit in the shape bucket beside the
    coordinates, so adding one card to a bay read as "same ids, different
    geometry: a slot moved". One new Casa rear card put two chassis at 1.0.0, and
    the MX catalogue alone has some sixty cards still to model."""
    a = dl.entry(_accepting("x/y@1"))
    b = dl.entry(_accepting("x/y@1", "x/z@1"))
    assert dl.required_bump(a, b) == "minor"


def test_a_bay_that_stops_accepting_something_is_major():
    """The other half. A configuration elsewhere may seat exactly that module."""
    a = dl.entry(_accepting("x/y@1", "x/z@1"))
    b = dl.entry(_accepting("x/y@1"))
    assert dl.required_bump(a, b) == "major"


def test_accepts_does_not_move_the_shape_hash():
    """Stated directly, so putting it back into `_placements` fails here rather
    than quietly re-inflating every bump."""
    assert dl.entry(_accepting("x/y@1"))["shape"] == \
           dl.entry(_accepting("x/y@1", "x/z@1"))["shape"]


def test_reordering_accepts_is_not_a_change():
    """The list is a set of claims, not a sequence; re-sorting it is not news."""
    a = dl.entry(_accepting("x/y@1", "x/z@1"))
    b = dl.entry(_accepting("x/z@1", "x/y@1"))
    assert dl.required_bump(a, b) is None


def test_a_lock_predating_the_field_cannot_manufacture_a_major():
    """An entry written before `bay-accepts` existed carries no map, so the
    removal check has nothing to compare and must not guess. It still reports a
    bump - the names hash moved when the field joined it - but a MINOR one, which
    is the safe direction: it asks to be looked at rather than either crying
    breakage or saying nothing.

    The first version of this test asserted None and was simply wrong: deleting
    the recorded map does not un-hash the contribution it already made."""
    a = dl.entry(_accepting("x/y@1", "x/z@1"))
    del a["bay-accepts"]
    assert dl.required_bump(a, dl.entry(_accepting("x/y@1"))) == "minor"


# ---- portfolio is fingerprinted ---------------------------------------------
#
# It was not, and that is the whole reason these exist. 45 UfiSpace devices
# gained a `portfolio` block, two of them had wrong values corrected, and
# devicelock reported ZERO findings for the lot - catalogue metadata could be
# rewritten, or deleted outright, and no version would be asked for. It sits in
# `surface` rather than `names` because it is metadata a reader sees rather than
# an identifier anything addresses by, so a patch is the right size.

def test_relabelling_a_family_is_a_patch():
    """The case that went unnoticed: `series: S9620` corrected to `S9600
    Series`, which is the difference between matching the vendor's site and
    not."""
    a = dl.entry(dev(portfolio={"line": "Telecoms", "family": "Open Aggregation Router",
                                "series": "S9620"}))
    b = dl.entry(dev(portfolio={"line": "Telecoms", "family": "Open Aggregation Router",
                                "series": "S9600 Series"}))
    assert dl.required_bump(a, b) == "patch"


def test_gaining_a_portfolio_block_is_a_patch():
    a = dl.entry(dev())
    b = dl.entry(dev(portfolio={"line": "Telecoms", "family": "Open Aggregation Router"}))
    assert dl.required_bump(a, b) == "patch"


def test_DELETING_a_portfolio_block_is_also_asked_for():
    """The direction that matters most. A field that only fires when it gains a
    value can be emptied for free, and silence reads as 'no answer' rather than
    'the answer was removed'."""
    a = dl.entry(dev(portfolio={"line": "Telecoms", "family": "Open Aggregation Router"}))
    assert dl.required_bump(a, dl.entry(dev())) == "patch"


def test_adding_a_second_category_is_a_patch():
    """`also-listed-in` decides whether a box appears in a second filtered list,
    so editing it changes what a consumer sees."""
    a = dl.entry(dev(portfolio={"line": "Telecoms", "family": "F"}))
    b = dl.entry(dev(portfolio={"line": "Telecoms", "family": "F",
                                "also-listed-in": ["AI Networking"]}))
    assert dl.required_bump(a, b) == "patch"


def test_portfolio_moves_surface_and_not_geometry_or_ids():
    """Severity, not just detection. A relabelled family must never read as a
    moved slot - that would call a metadata edit major and teach people to
    ignore the tool."""
    a = dl.entry(dev(portfolio={"line": "Telecoms", "family": "A"}))
    b = dl.entry(dev(portfolio={"line": "Telecoms", "family": "B"}))
    assert a["shape"] == b["shape"] and a["names"] == b["names"]
    assert a["surface"] != b["surface"]


# ---- art the lock could not see ---------------------------------------------
#
# A placement's `skin` chooses WHICH DRAWING of a component is painted -
# std/usb-a@1's blue USB-3 tongue or its white USB-2 one, std/db9@1's black
# insert or its PC99 teal. 1062 placements on 40 devices carry one and none of
# them was fingerprinted, so any of them could be repointed at different artwork,
# or have its `skin` deleted so the part fell back to `default`, with the lock
# reporting nothing. `mirror` was the same hole for handedness.

def _skinned(skin=None, mirror=None, **kw):
    d = dev(**kw)
    pl = {"id": "port", "ref": "std/usb-a@1", "at": [1, 1], "group": "slots"}
    if skin is not None:
        pl["skin"] = skin
    if mirror is not None:
        pl["mirror"] = mirror
    d["views"]["front"]["components"]["placements"] = [pl]
    return d


def test_repainting_a_placement_is_a_patch():
    a = dl.entry(_skinned(skin="default"))
    assert dl.required_bump(a, dl.entry(_skinned(skin="usb2"))) == "patch"


def test_asking_for_a_skin_where_there_was_none_is_a_patch():
    a = dl.entry(_skinned())
    assert dl.required_bump(a, dl.entry(_skinned(skin="usb2"))) == "patch"


def test_dropping_a_skin_back_to_the_default_is_a_change():
    """The dangerous direction: DELETING the key silently repaints the part."""
    a = dl.entry(_skinned(skin="usb2"))
    assert dl.required_bump(a, dl.entry(_skinned())) == "patch"


def test_a_skin_is_surface_and_not_shape():
    """Art, not geometry - nothing moved, so nothing downstream cached a number
    that is now wrong. The same bucket a CONFIGURATION's `skins:` map has always
    taken."""
    a, b = dl.buckets(_skinned(skin="default")), dl.buckets(_skinned(skin="usb2"))
    assert a["shape"] == b["shape"]
    assert a["names"] == b["names"]
    assert a["surface"] != b["surface"]


def test_a_device_naming_no_skin_hashes_as_it_always_did():
    """THE COST OF LEARNING A FIELD, and why it is paid conditionally.

    The digest covers the whole bucket, so a new key holding an empty map still
    rehashes every device in the library - 48 of the 88 name no skin at all and
    have nothing new to say. Writing it unconditionally billed them all for a
    bump nobody could explain.
    """
    plain = dev()
    assert "placement-skins" not in dl._placement_skins(plain)
    assert dl.buckets(plain)["surface"] == dl._digest({
        "description": None, "portfolio": None, "maturity": None, "attrs": None,
        "provenance": {"size": "a"}, "groups": {"slots": {"term": "Slot", "index-origin": 0}},
        "silkscreen": {"front": None}, "decor": {"front": None},
        "regions": {"front": None}, "empty": {"front": None},
        "configurations": None,
    }), "a device with no skins must hash exactly as it did before the field existed"


def test_mirroring_a_placement_is_major():
    """Handedness puts every feature on the other side while the box stays put,
    so anything holding a sub-feature coordinate is now wrong."""
    a = dl.entry(_skinned())
    assert dl.required_bump(a, dl.entry(_skinned(mirror=True))) == "major"


def test_an_unmirrored_placement_hashes_as_it_always_did():
    """Same conditional-key reasoning as the skins map: no placement in the
    library carries `mirror`, and none of them may be billed for it."""
    a = dl._placements(_skinned())
    assert "mirror" not in a["front/placements/port"]
    assert "mirror" in dl._placements(_skinned(mirror=True))["front/placements/port"]
