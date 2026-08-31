"""Device versioning: a device cannot change without saying so.

The rules under test are about DISCIPLINE rather than geometry, so the fixtures
are the smallest devices that can express a change of each kind.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools" / "portrayal"))

import devicelock as dl  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


def dev(version="1.0.0", at=(0, 0), extra_bay=None, gaps=None, note="a"):
    bays = [{"id": "slot-0", "at": list(at), "size": {"w": 10, "h": 10},
             "group": "slots", "accepts": ["x/y@1"]}]
    if extra_bay:
        bays.append({"id": extra_bay, "at": [50, 0], "size": {"w": 10, "h": 10},
                     "group": "slots", "accepts": ["x/y@1"]})
    return {
        "kind": "device", "name": "d", "version": version,
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
    for p in glob.glob(str(ROOT / "library/devices/*/*/device.yaml")):
        import yaml as y
        d = y.safe_load(open(p)) or {}
        for n, c in (d.get("configurations") or {}).items():
            if not (c or {}).get("kind"):
                bad.append(f"{p.split('devices/')[1]}:{n}")
    assert not bad, f"unclassified configurations: {bad[:5]}"


def test_at_most_one_base_per_device():
    import glob, yaml as y
    for p in glob.glob(str(ROOT / "library/devices/*/*/device.yaml")):
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
    for p in glob.glob(str(ROOT / "library/devices/*/*/device.yaml")):
        d = y.safe_load(open(p)) or {}
        for n, c in (d.get("configurations") or {}).items():
            if (c or {}).get("kind") == "example":
                examples.add(n)
    leaked = [n for n in names if any(e in n for e in examples)]
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
    for p in glob.glob(str(ROOT / "library/devices/*/*/device.yaml")):
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
    for p in glob.glob(str(ROOT / "library/devices/*/*/device.yaml")):
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
