#!/usr/bin/env python3
"""Device fingerprints, so a device cannot change without saying so.

WHY THIS EXISTS. Components are versioned and devices are not - `version:` is
required by the schema and nothing enforces or consumes it, so 32 of 36 devices
sat at 0.1.0 while their geometry, slots and provenance were edited underneath
them. Fixing a device yielded a git commit and an unchanged version string, and
a consumer holding the released SVG could not tell it had gone stale.

Git already records THAT a file changed. What it cannot say is whether the
change was a re-worded provenance note or a moved slot, and those need different
version bumps and different levels of alarm downstream. So the fingerprint is
split into buckets that map onto the bump rules DESIGN.md already states for
components - "art=patch, additive=minor, geometry/IDs=major" - and the check
reports the MINIMUM bump the change requires rather than merely that it happened.

WHAT IS DELIBERATELY NOT HASHED. Rendered output, file byte order, key order and
comments. Two files that differ only in how they are spelled describe the same
device, and a fingerprint that fires on re-indentation would be re-locked
without being read - which is how a check stops being read at all.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

import yaml

LOCK_NAME = "devices.lock.json"
FORMAT = 1


def _stable(value):
    """A value in a form two runs agree on. Sorts mappings, keeps sequence order
    because a sequence's order is part of what a device says."""
    if isinstance(value, dict):
        return {k: _stable(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    if isinstance(value, float) and value.is_integer():
        # 3 and 3.0 are the same millimetre. YAML round-trips them differently
        # depending on how the author typed it, and that is not a change.
        return int(value)
    return value


def _digest(value) -> str:
    blob = json.dumps(_stable(value), sort_keys=True, separators=(",", ":"),
                      default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _placements(doc):
    """Every positioned thing in the device, keyed by view and id."""
    out = {}
    for vname, view in (doc.get("views") or {}).items():
        view = view or {}
        for kind in ("bays", "placements"):
            for item in ((view.get("components") or {}).get(kind) or []):
                key = f"{vname}/{kind}/{item.get('id')}"
                # `group` and `accepts` are DELIBERATELY ABSENT. Both are
                # addressing rather than geometry - see `_placement_groups` and
                # `_bay_accepts`.
                out[key] = {
                    "at": item.get("at"), "size": item.get("size"),
                    "rotate": item.get("rotate"),
                    "ref": item.get("ref"),
                    "default": item.get("default"), "mate-to": item.get("mate-to"),
                }
        for cut in ((view.get("panel") or {}).get("cutouts") or []):
            out[f"{vname}/cutout/{cut.get('id')}"] = {
                "at": cut.get("at"), "size": cut.get("size"),
                "shape": cut.get("shape"),
            }
    return out


def _placement_groups(doc):
    """Which group each placed thing belongs to, keyed the same way.

    This used to live in `shape`, beside the coordinates, and that made LABELLING
    an unlabelled placement read as "a slot moved" - a major bump for adding
    metadata that moves nothing and removes nothing. Backfilling `group` across
    the library is 174 placements on 11 devices; under the old reading every one
    of those devices took a breaking version for it, which is how `major` stops
    meaning anything to a consumer.

    So it sits in `names` instead, where the ids and group names already live,
    and `required_bump` tells the two cases apart: ADDING a group where there was
    none is additive, and REASSIGNING one from A to B is not.
    """
    out = {}
    for vname, view in (doc.get("views") or {}).items():
        view = view or {}
        for kind in ("bays", "placements"):
            for item in ((view.get("components") or {}).get(kind) or []):
                out[f"{vname}/{kind}/{item.get('id')}"] = item.get("group")
    return out


def _bay_accepts(doc):
    """What each bay says it will take, keyed the same way.

    This used to sit in `shape` beside the coordinates, so ADDING a module to a
    bay's `accepts` read as "same ids, different geometry: a slot moved" and
    demanded a major bump. Nothing moves. The Casa chassis hit it first - one new
    rear card put two of them at 1.0.0 - and it would have hit every future
    module: the MX catalogue alone has some sixty cards still to model, each one
    landing in the `accepts` of whatever chassis takes it.

    So it lives in `names`, and `required_bump` tells the two cases apart: a bay
    LEARNING it accepts something more cannot invalidate anything a consumer
    holds, while a bay that stops accepting something can - a configuration
    elsewhere may seat exactly that module.
    """
    out = {}
    for vname, view in (doc.get("views") or {}).items():
        view = view or {}
        for kind in ("bays", "placements"):
            for item in ((view.get("components") or {}).get(kind) or []):
                acc = item.get("accepts")
                if acc:
                    out[f"{vname}/{kind}/{item.get('id')}"] = sorted(acc)
    return out


def buckets(doc):
    """The four things a device change can be, hashed apart.

    `shape` is the breaking surface: chassis dimensions, view sizes, and the
    position, size and wiring of every placed thing. Moving a slot invalidates
    anything that cached a coordinate, which is what major means.

    `names` is the addressing surface: the ids and group names a consumer writes
    down. Renaming `ps0-pm-0` breaks a reference held elsewhere just as surely as
    moving it, which is why DESIGN.md puts geometry and IDs in the same bucket.

    `surface` is everything a reader sees and no consumer computes with -
    silkscreen text, decor, description, provenance, maturity, attrs. Patch.

    `gaps` is hashed on its own because it is the one part of a device that
    makes a CLAIM ABOUT THE WORLD rather than about the drawing, so it needs to
    be re-affirmed when the drawing moves under it. See `stale_gap_scopes`.
    """
    placed = _placements(doc)
    return {
        "shape": _digest({
            "chassis": doc.get("chassis"),
            "views": {v: (w or {}).get("size") for v, w in (doc.get("views") or {}).items()},
            "placed": placed,
        }),
        "names": _digest({
            "ids": sorted(placed),
            "groups": sorted((doc.get("groups") or {}).keys()),
            "configurations": sorted((doc.get("configurations") or {}).keys()),
            "placement-groups": _placement_groups(doc),
            "bay-accepts": _bay_accepts(doc),
        }),
        "surface": _digest({
            "description": doc.get("description"),
            "maturity": doc.get("maturity"),
            "attrs": doc.get("attrs"),
            "provenance": doc.get("provenance"),
            "groups": doc.get("groups"),
            "silkscreen": {v: (w or {}).get("silkscreen")
                           for v, w in (doc.get("views") or {}).items()},
            "decor": {v: ((w or {}).get("panel") or {}).get("decor")
                      for v, w in (doc.get("views") or {}).items()},
            "regions": {v: (w or {}).get("regions")
                        for v, w in (doc.get("views") or {}).items()},
            # A face's `empty` decides whether it counts as finished, so editing
            # it moves a capability LEVEL. Unfingerprinted, that could be
            # rewritten - or quietly deleted - with nothing asking for a version.
            "empty": {v: (w or {}).get("empty")
                      for v, w in (doc.get("views") or {}).items()},
            "configurations": doc.get("configurations"),
        }),
        "gaps": _digest(doc.get("gaps") or []),
    }


def entry(doc):
    # The three NAME SETS are recorded separately, not only hashed, because
    # `required_bump` has to tell an addition from a removal and a hash cannot.
    # Adding a `base` configuration moves the `names` hash while every id stays
    # put, and reading that as "same ids, different geometry" called twenty-three
    # additive changes major.
    e = {"version": str(doc.get("version") or ""),
         "ids": sorted(_placements(doc)),
         "groups": sorted((doc.get("groups") or {}).keys()),
         "configs": sorted((doc.get("configurations") or {}).keys()),
         "placement-groups": _placement_groups(doc),
         "bay-accepts": _bay_accepts(doc)}
    e.update(buckets(doc))
    return e


def required_bump(old, new):
    """The smallest bump this change is allowed to take.

    Additive is minor and anything else about shape or names is major, which is
    the distinction DESIGN.md draws and the one that matters to a consumer: a
    device that GREW has not invalidated what anyone already held, and a device
    whose slot moved or whose id vanished has.
    """
    if old is None:
        return None
    if old.get("shape") == new["shape"] and old.get("names") == new["names"]:
        return "patch" if old.get("surface") != new["surface"] or \
                          old.get("gaps") != new["gaps"] else None
    # ANYTHING REMOVED IS BREAKING, whichever set it left: an id, a group or a
    # configuration name can each be held by something outside this repository.
    for key in ("ids", "groups", "configs"):
        if set(old.get(key) or []) - set(new.get(key) or []):
            return "major"
    # A placement MOVING GROUP is breaking - a consumer addressing it by group
    # loses it. A placement GAINING a group it never had cannot break anyone,
    # because there was nothing there to hold. Absent on both sides of a lock
    # written before this field existed, which is why the guard is `if was`.
    new_pg = new.get("placement-groups") or {}
    for key, was in (old.get("placement-groups") or {}).items():
        if was and key in new_pg and new_pg[key] != was:
            return "major"
    # A BAY THAT STOPS ACCEPTING SOMETHING IS BREAKING; one that accepts more is
    # not. A configuration elsewhere may seat exactly the module just withdrawn.
    old_acc = old.get("bay-accepts") or {}
    new_acc = new.get("bay-accepts") or {}
    for key, was in old_acc.items():
        if set(was or []) - set(new_acc.get(key) or []):
            return "major"
    if old.get("shape") != new["shape"] and \
            set(old.get("ids") or []) == set(new["ids"]):
        return "major"          # same ids, different geometry: a slot moved
    return "minor"              # strictly additive


def _parse(v):
    parts = (v or "0.0.0").split(".")
    while len(parts) < 3:
        parts.append("0")
    try:
        return tuple(int(p) for p in parts[:3])
    except ValueError:
        return (0, 0, 0)


def bump_taken(old_version, new_version):
    """What bump the author actually took, or None if the version is unchanged."""
    o, n = _parse(old_version), _parse(new_version)
    if n == o:
        return None
    if n < o:
        return "backwards"
    if n[0] != o[0]:
        return "major"
    if n[1] != o[1]:
        return "minor"
    return "patch"


RANK = {"patch": 1, "minor": 2, "major": 3}


def sufficient(taken, required):
    if required is None:
        return True
    if taken in (None, "backwards"):
        return False
    return RANK[taken] >= RANK[required]


def stale_gap_scopes(doc):
    """Gap `scope` entries that name nothing in the device.

    A gap is the one part of a device that describes a DOCUMENT rather than the
    drawing - "the HIG has no port-lamp table" - so no rule can check whether it
    is still true. What a rule CAN check is whether it still points at something:
    a gap scoped to a bay that was renamed, or to a group that was never
    declared, has drifted from the model it annotates.

    Measured before it was written: 166 of 169 scope entries across the library
    resolve, so this reports drift rather than accusing the corpus. The three it
    finds are real - a gap scoped to `filters` on a chassis with no such group,
    and two scoped to `ports` and `optics` on a device whose groups are `sfp28`
    and `qsfp28`.

    NOT AN ERROR, because an unresolved scope has an innocent reading: the gap
    may name something the device does not model YET, which is occasionally the
    whole point of the gap.
    """
    names = set((doc.get("groups") or {}).keys())
    names |= set((doc.get("views") or {}).keys())
    names |= set((doc.get("configurations") or {}).keys())

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                names.add(k)
                walk(v)
    walk(doc.get("attrs") or {})
    for vname, view in (doc.get("views") or {}).items():
        view = view or {}
        for kind in ("bays", "placements"):
            for item in ((view.get("components") or {}).get(kind) or []):
                for key in ("id", "group", "ref", "default"):
                    if item.get(key):
                        names.add(item[key])
                for ref in (item.get("accepts") or []):
                    names.add(ref)
        for cut in ((view.get("panel") or {}).get("cutouts") or []):
            if cut.get("id"):
                names.add(cut["id"])
        for mark in (view.get("silkscreen") or []):
            if mark.get("id"):
                names.add(mark["id"])
        for region in (view.get("regions") or []):
            if region.get("id"):
                names.add(region["id"])
    out = []
    for gap in (doc.get("gaps") or []):
        for scope in (gap.get("scope") or []):
            if scope not in names:
                out.append((gap.get("what"), scope))
    return out


def device_files(library: pathlib.Path):
    return sorted(library.glob("devices/*/*/device.yaml"))


def slug(path: pathlib.Path, library: pathlib.Path):
    rel = path.relative_to(library / "devices").parent
    return str(rel)


def load_lock(library: pathlib.Path):
    p = library / LOCK_NAME
    if not p.exists():
        return {"format": FORMAT, "devices": {}}
    return json.loads(p.read_text())


def write_lock(library: pathlib.Path, lock):
    p = library / LOCK_NAME
    p.write_text(json.dumps(lock, indent=1, sort_keys=True) + "\n")
    return p


def check(library: pathlib.Path):
    """Returns a list of (slug, kind, message). Empty means the lock agrees."""
    lock = load_lock(library)
    known = lock.get("devices") or {}
    findings = []
    for path in device_files(library):
        name = slug(path, library)
        doc = yaml.safe_load(path.read_text()) or {}
        now = entry(doc)
        was = known.get(name)
        if was is None:
            findings.append((name, "unlocked",
                             f"{name} is not in {LOCK_NAME}. Run devicelock.py --update "
                             "to record it; from then on a change to it has to say so"))
            continue
        need = required_bump(was, now)
        took = bump_taken(was.get("version"), now["version"])
        if took == "backwards":
            findings.append((name, "backwards",
                             f"{name} version went from {was.get('version')} to "
                             f"{now['version']}. A version is a promise, and it only counts up"))
        elif not sufficient(took, need):
            what = []
            if was.get("shape") != now["shape"]:
                what.append("geometry")
            if was.get("names") != now["names"]:
                what.append("ids or groups")
            if was.get("surface") != now["surface"]:
                what.append("surface (silkscreen, decor, provenance, attrs)")
            if was.get("gaps") != now["gaps"]:
                what.append("gaps")
            gone = sorted(set(was.get("ids") or []) - set(now["ids"]))
            added = sorted(set(now["ids"]) - set(was.get("ids") or []))
            detail = ""
            if gone:
                detail += (f" {len(gone)} id(s) no longer exist, e.g. {', '.join(gone[:3])} "
                           "- anything holding one of those is now wrong, which is what "
                           "major is for.")
            elif added and need == "minor":
                detail += (f" {len(added)} id(s) were added and nothing moved or "
                           "disappeared, so this is additive.")
            findings.append((name, "unbumped",
                             f"{name} changed ({', '.join(what)}) since version "
                             f"{was.get('version')} and the version "
                             + (f"is still {now['version']}"
                                if took is None else f"only took a {took} bump")
                             + f". This change needs at least a {need} bump.{detail}"))
        # THE GAPS RE-AFFIRMATION. Only when the drawing itself moved: a device
        # whose geometry or ids changed may have closed a gap, opened one, or
        # left one pointing at a slot that no longer exists, and only a person
        # who knows the sources can say which. Firing when the surface alone
        # changed would make it noise.
        moved = was.get("shape") != now["shape"] or was.get("names") != now["names"]
        if moved and was.get("gaps") == now["gaps"] and (doc.get("gaps") or []):
            findings.append((name, "gaps-unreviewed",
                             f"{name} changed shape or addressing and its {len(doc['gaps'])} declared "
                             "gap(s) did not change. Re-read them: a gap the change closed "
                             "must go, a gap the change opened must be added, and a gap "
                             "still true is fine - but it has to be the third one on "
                             "purpose rather than by omission"))
    return findings


def update(library: pathlib.Path):
    lock = load_lock(library)
    lock["format"] = FORMAT
    devices = lock.setdefault("devices", {})
    changed = []
    for path in device_files(library):
        name = slug(path, library)
        doc = yaml.safe_load(path.read_text()) or {}
        now = entry(doc)
        if devices.get(name) != now:
            changed.append(name)
        devices[name] = now
    for name in sorted(set(devices) - {slug(p, library) for p in device_files(library)}):
        del devices[name]
        changed.append(f"{name} (removed)")
    write_lock(library, lock)
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--library", default="library", type=pathlib.Path)
    ap.add_argument("--update", action="store_true",
                    help="record the current state; run this AFTER bumping a version")
    args = ap.parse_args(argv)
    if args.update:
        changed = update(args.library)
        print(f"devicelock: {len(changed)} device(s) re-locked"
              + (": " + ", ".join(changed[:6]) if changed else ""))
        return 0
    findings = check(args.library)
    for _, _, msg in findings:
        print(f"devicelock: {msg}")
    print(f"devicelock: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
