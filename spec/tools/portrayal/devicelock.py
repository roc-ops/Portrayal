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

from portrayal import manifest
from portrayal import libwalk
# The AGGREGATE's name, written into dist. A device's own lock is
# `device.lock.json` beside its manifest - see `load_lock`.
LOCK_NAME = "devices.lock.json"
DEVICE_LOCK_NAME = "device.lock.json"
FORMAT = 1


def _stable(value):
    """A value in a form two runs agree on. Sorts mappings, keeps sequence order
    because a sequence's order is part of what a device says."""
    if isinstance(value, dict):
        # A KEY THAT IS NOT A STRING must not crash the digest. YAML 1.1 reads a
        # bare `on:` as boolean true, and json.dumps(sort_keys=True) cannot
        # order True against a str: the TypeError killed lint's lock check
        # before it printed L106, the message written for that very mistake.
        # A bool key takes json's own spelling ("true"/"false"), and a dict
        # whose keys are still of mixed kinds has the rest spelled the same
        # way. Both cases crashed before, so no digest that exists moves: an
        # all-string or all-numeric mapping is left exactly as it was.
        def key(k):
            return "true" if k is True else "false" if k is False else k
        keys = {key(k): k for k in value}
        if any(isinstance(k, str) for k in keys) and \
                not all(isinstance(k, str) for k in keys):
            keys = {(k if isinstance(k, str) else json.dumps(k)): v
                    for k, v in keys.items()}
        return {k: _stable(value[keys[k]]) for k in sorted(keys, key=str)}
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
                    # HANDEDNESS SITS BESIDE ROTATION because it is the same
                    # kind of fact - which way round the part is placed - and
                    # `render.py` says so in as many words: "HANDEDNESS IS NOT
                    # ROTATION ... a riser whose cards face the other way needs
                    # the reflection, not the half-turn." Mirroring a part puts
                    # its every feature on the other side while its box stays
                    # put, so anything that cached a sub-feature coordinate is
                    # now wrong, which is what major means. No placement in the
                    # library carries one today; this costs nothing and closes
                    # the hole before the first one does.
                    #
                    # PRESENT ONLY WHEN SET, and that is not tidiness. The
                    # digest is taken over this whole dict, so a new key holding
                    # None still changes every device's hash - writing it
                    # unconditionally asked 88 devices for a MAJOR bump apiece
                    # for a field none of them uses. Adding it conditionally
                    # leaves every current hash exactly where it was and starts
                    # tracking the first placement that does carry one.
                    "rotate": item.get("rotate"),
                    **({"mirror": item["mirror"]} if item.get("mirror") is not None else {}),
                    "ref": item.get("ref"),
                    "default": item.get("default"), "mate-to": item.get("mate-to"),
                }
        for cut in ((view.get("panel") or {}).get("cutouts") or []):
            out[f"{vname}/cutout/{cut.get('id')}"] = {
                "at": cut.get("at"), "size": cut.get("size"),
                "shape": cut.get("shape"),
            }
    return out


def _placement_skins(doc):
    """Which skin each placed thing asks its component for, keyed the same way.

    THIS IS ART AND IT WAS NOT FINGERPRINTED AT ALL. A skin selects which
    drawing of a component is painted - std/usb-a@1's blue USB-3 tongue or its
    white USB-2 one, std/db9@1's black insert or its PC99 teal - and 1062
    placements on 40 devices carry one. Every one of those could have been
    repointed at different artwork, or had its `skin` deleted so the part fell
    back to `default`, and the lock would have reported nothing. The module's
    own first line is "Device fingerprints, so a device cannot change without
    saying so", and this was the gap in it.

    `surface` rather than `shape`, and the reason is already settled in this
    file: a CONFIGURATION's `skins:` map has always been fingerprinted, inside
    the `configurations` blob under `surface`. A placement asking for the same
    thing one part at a time is the same kind of claim and takes the same bucket
    - art a reader sees and no consumer computes with, so a patch.
    """
    out = {}
    for vname, view in (doc.get("views") or {}).items():
        view = view or {}
        for kind in ("bays", "placements"):
            for item in ((view.get("components") or {}).get(kind) or []):
                if item.get("skin") is not None:
                    out[f"{vname}/{kind}/{item.get('id')}"] = item["skin"]
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


def _component_digest(version_dir: pathlib.Path, contract: dict) -> str:
    """A component's own contents, so a device that seats it cannot be redrawn
    in silence.

    THE VERSION STRING WAS NOT ENOUGH. `_composed` resolved a ref to the
    component's declared `version:`, so the guard closed on the author
    remembering to bump - and three components were rewritten in place across
    six bays of two devices, all three left at 1.0.0, and neither device
    re-locked. The component has no lock of its own to catch it and no lint rule
    asks for the bump. roc-ops/Portrayal#405.

    THE CONTRACT IS HASHED AS PARSED YAML, not as bytes, because this module's
    own rule is that "a fingerprint that fires on re-indentation would be
    re-locked without being read" - and a comment is most of what gets edited in
    a contract. THE SKINS ARE HASHED AS BYTES, and that asymmetry is deliberate:
    whitespace inside an SVG path's `d=` is significant, so normalising one
    risks missing a change that moves the drawing. A whitespace-only skin edit
    therefore re-locks, which is the safe direction to be wrong in.
    """
    skins = {}
    for skin in sorted((version_dir / "skins").glob("*.svg")):
        skins[skin.name] = hashlib.sha256(skin.read_bytes()).hexdigest()[:16]
    return _digest({"contract": contract, "skins": skins})


def component_versions(library: pathlib.Path):
    """Every component's declared version, keyed the way a ref names it.

    `common/rj45-port@4` addresses a MAJOR, and the file under v4 says which
    minor is actually there. That indirection is the whole point of the ref -
    and the whole reason a device could change appearance without its lock
    moving.
    """
    out = {}
    root = library / "components"
    if not root.is_dir():
        return out
    for ct in root.glob("*/*/v*/contract.yaml"):
        try:
            doc = manifest.load_yaml(ct) or {}
        except Exception:
            continue
        vendor, name, major = ct.parts[-4], ct.parts[-3], ct.parts[-2]
        # VERSION + CONTENT, in that order, because `composed-refs` is committed
        # beside the device and read by a human: the report prints
        # `acme/widget@1 1.0.0+a1b2c3d4 -> 1.0.0+9f8e7d6c`, which says in one
        # line that the contents moved and the version did not.
        ver = str(doc.get("version") or "")
        out[f"{vendor}/{name}@{major[1:]}"] = (
            ver + "+" + _component_digest(ct.parent, doc))
        out.setdefault(f"{vendor}/{name}", {})[major] = _children(doc)
    return out


def _children(contract):
    """The refs a component draws that it does not itself contain: its `parts`,
    and every ref its own bays seat or take.

    NESTED BAYS WERE NOT FOLLOWED. A component can host bays - an SCB carries a
    routing engine, a SIP carries SPAs - and only `parts:` was walked, so
    `juniper/re-s-1300@1` could be rewritten inside the SCB bays of mx240, mx480
    and mx960 with devicelock asking for nothing; #521 bumped all three by hand.
    A nested bay is read exactly as `_composed` reads a device bay, `default`
    and every ref it `accepts`, because an occupant the bay only accepts is
    still one a configuration can draw there.
    """
    refs = [p.get("ref") for p in (contract.get("parts") or [])]
    for bay in (contract.get("bays") or {}).values():
        bay = bay or {}
        refs += [bay.get("default")] + list(bay.get("accepts") or [])
    return [r for r in refs if r]


def _composed(doc, versions):
    """What this device draws that it does not itself contain, and at which
    version.

    THE LOCK FINGERPRINTS THE DEVICE FILE, so a device could be redrawn by an
    edit somewhere else entirely and report no change at all. That is not
    hypothetical: common/rj45-port went 4.2.0 -> 4.6.0, which altered how nine
    devices draw their management ports, and devicelock re-locked none of them.
    The guard against a device changing without saying so did not extend to a
    device changing because something it composes did.
    Resolved TRANSITIVELY - a card composes a jack which composes a cage, an SCB
    seats a routing engine in a bay of its own - so a change three levels down
    still reaches the device that shows it. See `_children`.
    """
    seen, todo = {}, []
    for view in (doc.get("views") or {}).values():
        for kind in ("bays", "placements"):
            for item in (((view or {}).get("components") or {}).get(kind) or []):
                for ref in ([item.get("ref"), item.get("default")]
                            + list(item.get("accepts") or [])):
                    if ref:
                        todo.append(ref)
    while todo:
        ref = todo.pop()
        if ref in seen:
            continue
        seen[ref] = versions.get(ref, "?")
        base, _, major = ref.partition("@")
        todo.extend((versions.get(base) or {}).get(f"v{major}", []))
    return dict(sorted(seen.items()))


# WHICH CHASSIS KEYS ARE GEOMETRY, AND WHICH ARE NOT.
#
# `shape` means dimensions - "moving a slot invalidates anything that cached a
# coordinate, which is what major means" - and the whole `chassis` mapping used
# to be hashed into it wholesale. Five of its nine keys are not dimensions, so
# correcting a weight typo or recolouring a housing demanded a MAJOR bump while
# nothing moved. #171 took `airflow` out for exactly that reason, on 40 devices;
# this is the rest of it (#271).
#
# `edge` IS A COLOUR, which is the one the issue guessed wrong and `render.py`
# settles in a line: `faceplate.set("stroke", ch.get("edge", "#22262a"))`. Its
# schema entry carried no description, which is why it read as geometry.
#
# THE TWO SETS ARE EXHAUSTIVE OVER THE SCHEMA'S `chassis` PROPERTIES, and
# test_lock_chassis_split.py holds that. `chassis` is `additionalProperties:
# false`, so a tenth key can only arrive by someone adding it to the schema -
# and they have to say which side it falls on rather than have it default into
# `shape` and quietly demand a major from every device that adopts it. Same
# guard, and the same reason, as PORT_ROLES/NON_PORT_ROLES in dcim_export.
CHASSIS_SHAPE = {"width", "height", "depth", "ru"}
CHASSIS_SURFACE = {"color", "edge", "silk", "weight-kg", "airflow"}


def buckets(doc, versions=None):
    """The four things a device change can be, hashed apart.

    `shape` is the breaking surface: chassis DIMENSIONS (see CHASSIS_SHAPE - the
    housing's colours and its weight are not), view sizes, and the
    position, size and wiring of every placed thing. Moving a slot invalidates
    anything that cached a coordinate, which is what major means.

    `names` is the addressing surface: the ids and group names a consumer writes
    down. Renaming `ps0-pm-0` breaks a reference held elsewhere just as surely as
    moving it, which is why DESIGN.md puts geometry and IDs in the same bucket.

    `surface` is everything a reader sees and no consumer computes with -
    silkscreen text, decor, description, provenance, maturity, attrs, portfolio.
    Patch.

    `gaps` is hashed on its own because it is the one part of a device that
    makes a CLAIM ABOUT THE WORLD rather than about the drawing, so it needs to
    be re-affirmed when the drawing moves under it. See `stale_gap_scopes`.
    """
    placed = _placements(doc)
    # PRESENT ONLY WHEN THE DEVICE NAMES ONE, for the same reason `mirror` is
    # conditional above: an empty map is still a new key, and a new key rehashes
    # every device in the library. 48 of the 88 name no skin at all and have
    # nothing new to say; writing it unconditionally billed them for a bump.
    skins = _placement_skins(doc)
    chassis = dict(doc.get("chassis") or {})
    chassis_surface = {k: chassis.pop(k) for k in CHASSIS_SURFACE if k in chassis}
    return {
        "shape": _digest({
            "chassis": chassis or None,
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
            # WHERE THE DEVICE SITS IN ITS VENDOR'S CATALOGUE. Unfingerprinted,
            # `portfolio` could be rewritten - a family relabelled, a series
            # corrected, a whole block deleted - and nothing would ask for a
            # version. That is not hypothetical: 45 UfiSpace devices gained the
            # block, two had wrong values corrected, and devicelock reported
            # zero findings for the lot. It is `surface` and not `names`
            # because it is catalogue metadata a reader sees rather than an
            # identifier anything addresses by, so a patch is the right size.
            "portfolio": doc.get("portfolio"),
            "maturity": doc.get("maturity"),
            # `profile` SITS BESIDE `maturity` AND WAS NOT HASHED. Both say what
            # standard the device is held to - maturity what lint demands of it,
            # profile what `specified` judges its attrs against - and changing
            # either changes a published claim. #170 made profile required, and a
            # required field nothing fingerprints can be retyped from
            # `networking` to `optical` with no version asked for, which is the
            # gap the `portfolio` note above records having found.
            **({"profile": doc.get("profile")} if doc.get("profile") else {}),
            # A WAIVER IS A CLAIM, and an unfingerprinted claim can be retyped
            # with no version asked for - the gap `portfolio` and then `profile`
            # each had. Adding, removing or rewording `lint.waive` changes what
            # the gate says about this device (#180). Conditional, like the two
            # above: a device that waives nothing is not rehashed for the key.
            **({"lint": doc.get("lint")} if doc.get("lint") else {}),
            # A STACK EXCEPTION IS THE SAME KIND OF CLAIM as a waiver - it says a
            # belly-to-belly pair is built otherwise than L108's convention, and
            # why - so it is fingerprinted the same way, and conditionally, so
            # the devices that declare none are not rehashed for the key.
            **({"stack-exceptions": doc.get("stack-exceptions")}
               if doc.get("stack-exceptions") else {}),
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
            **({"placement-skins": skins} if skins else {}),
            # CONDITIONAL, ONE KEY AT A TIME, FOR THE REASON `placement-skins`
            # IS. Written unconditionally, `airflow: None` is still a new key in
            # the hashed map and rehashes all 89 devices - which it did, on the
            # first attempt at #171, asking every one of them for a bump it had
            # not earned. `chassis_surface` carries only the keys this device
            # actually states, so the 24 with no colour are not billed for one.
            **chassis_surface,
        }),
        "gaps": _digest(doc.get("gaps") or []),
        # WHAT THIS DEVICE DRAWS THAT LIVES SOMEWHERE ELSE. Hashed apart from
        # `surface` because it is not this file's content at all - nothing in
        # the device changed, the thing it composes did.
        "composed": _digest(_composed(doc, versions or {})),
    }


def entry(doc, versions=None):
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
         "bay-accepts": _bay_accepts(doc),
         # RECORDED AND NOT ONLY HASHED, so a finding can name the part that
         # moved. A digest can say something changed; it cannot say what.
         "composed-refs": _composed(doc, versions or {})}
    e.update(buckets(doc, versions))
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
        # A COMPOSED CHANGE IS A PATCH. The device's own geometry and ids are
        # untouched; a part it draws was redrawn, so anything holding a
        # coordinate is still right and anything holding a picture is not.
        # `"composed" in old` guards the migration: a lock written before this
        # field existed must not report every device in the library at once.
        composed_moved = ("composed" in old
                          and old["composed"] != new["composed"])
        return "patch" if old.get("surface") != new["surface"] or \
                          old.get("gaps") != new["gaps"] or composed_moved \
            else None
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
    return list(libwalk.iter_devices([library]))


def slug(path: pathlib.Path, library: pathlib.Path):
    rel = path.relative_to(library / "devices").parent
    return str(rel)


def lock_path(library: pathlib.Path, name: str):
    """The lock file that sits beside one device's manifest."""
    return library / "devices" / name / DEVICE_LOCK_NAME


def load_lock(library: pathlib.Path):
    """Every device's lock, assembled - the shape `check` and `update` expect.

    ONE FILE PER DEVICE, BESIDE ITS MANIFEST. The lock used to be a single
    906 KB alphabetically sorted JSON, and every device PR inserted a 74-996
    line entry into it. Cross-vendor inserts merged cleanly; two same-vendor
    devices that sort adjacently conflicted in JSON the contributor never wrote,
    and a component version bump rewrote the entry of every device that seats it
    - which is why the RJ45 family change needed ten stacked PRs, #131-#140
    (#182).

    A device's lock now travels in that device's directory, so two devices can
    never conflict and a reviewer sees the fingerprint beside the thing it
    fingerprints. The aggregate is a BUILD OUTPUT: `library/dist/devices.lock.json`,
    written by the same pass that writes the indexes, for anything outside the
    checkout that wants one file.
    """
    devices = {}
    for path in device_files(library):
        f = lock_path(library, slug(path, library))
        if f.exists():
            devices[slug(path, library)] = json.loads(f.read_text())
    return {"format": FORMAT, "devices": devices}


def write_entries(library: pathlib.Path, entries):
    """Write these devices' locks and no others.

    `--update` used to rewrite the whole file whatever changed, so a one-word
    provenance fix on one device produced a diff against a 906 KB artefact and
    a reviewer had to take on trust that the other 88 entries were untouched.
    Only the devices in `entries` are written now, and `git status` says which.
    """
    written = []
    for name, ent in sorted(entries.items()):
        f = lock_path(library, name)
        f.parent.mkdir(parents=True, exist_ok=True)
        body = {"format": FORMAT, **ent}
        f.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n")
        written.append(f)
    return written


def aggregate(library: pathlib.Path, out: pathlib.Path):
    """Every device's lock in one file, for a consumer outside the checkout.

    A BUILD OUTPUT AND NOT A SOURCE. It is derived from the per-device files, so
    it cannot drift from them and nothing has to keep it in step; it is in
    `dist/` for the same reason `devices.json` is - so a reader without a clone
    has the whole picture in one fetch.
    """
    out.write_text(json.dumps(load_lock(library), indent=1, sort_keys=True) + "\n")
    return out


def check(library: pathlib.Path):
    """Returns a list of (slug, kind, message). Empty means the lock agrees."""
    lock = load_lock(library)
    known = lock.get("devices") or {}
    findings = []
    versions = component_versions(library)
    for path in device_files(library):
        name = slug(path, library)
        doc = manifest.load_yaml(path) or {}
        now = entry(doc, versions)
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
                what.append("surface (silkscreen, decor, provenance, attrs, "
                            "portfolio, skins)")
            if was.get("gaps") != now["gaps"]:
                what.append("gaps")
            # NAME THE COMPOSED CHANGE. The one bucket whose cause is not in
            # this file is the one that most needs saying out loud - without
            # this the report is "changed ()" and the reader has nowhere to go.
            if "composed" in was and was["composed"] != now["composed"]:
                before = was.get("composed-refs") or {}
                after = now.get("composed-refs") or {}
                moved = [f"{r} {before[r]} -> {after[r]}" for r in sorted(after)
                         if r in before and before[r] != after[r]]
                moved += [f"{r} added" for r in sorted(set(after) - set(before))]
                moved += [f"{r} gone" for r in sorted(set(before) - set(after))]
                what.append("a composed component"
                            + (f" ({'; '.join(moved[:3])})" if moved else ""))
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
    """Re-lock the devices whose fingerprint moved, and only those."""
    versions = component_versions(library)
    known = load_lock(library)["devices"]
    live = {slug(p, library): p for p in device_files(library)}
    changed, writing = [], {}
    for name, path in live.items():
        now = entry(manifest.load_yaml(path) or {}, versions)
        # COMPARE WITHOUT THE FORMAT MARKER, which `write_entries` adds and
        # `entry` does not produce. Comparing with it made every device differ
        # on the first run after the split and re-locked all 89.
        if {k: v for k, v in (known.get(name) or {}).items() if k != "format"} != now:
            changed.append(name)
            writing[name] = now
    write_entries(library, writing)
    # A DEVICE THAT IS GONE TAKES ITS LOCK WITH IT. With one file this was a key
    # to delete; now it is a file, and leaving it behind would fingerprint a
    # device that no longer exists.
    for name in sorted(set(known) - set(live)):
        lock_path(library, name).unlink(missing_ok=True)
        changed.append(f"{name} (removed)")
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
