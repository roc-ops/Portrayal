#!/usr/bin/env python3
"""Compile a devices.json index from the device manifests.

The demo's device picker reads this. It used to be hand-maintained, which meant
it silently went stale (and vanished entirely on a clean rebuild) - generate it
from the manifests instead, the same way components.json is generated.
"""
import argparse
import json
from pathlib import Path

import yaml

from portrayal import attrsections as attrs_mod
from portrayal import capability
from portrayal.manifest import view_parts, load_yaml, alias_names, device_options
from portrayal import libwalk

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"

# WHAT A CONSUMER OUTSIDE THIS REPOSITORY CAN RELY ON. `kit/` reads
# `devices.json` and there was no version in it, no git tag and no CHANGELOG -
# so a consumer had no way to tell a breaking change to the dist from a Tuesday
# (#185). This number goes up when a field a reader depends on is removed,
# renamed or changes meaning; adding one does not move it. CHANGELOG.md records
# what each change was.
CONTRACT = 1

# Placement and group attrs worth indexing. An allowlist, not everything: `states`
# and `leds` hold transcribed vendor prose ("Blue = all lanes linked, Off = not
# all lanes linked"), and folding that into the haystack makes half the portfolio
# match "off" and "link".
SEARCH_ATTRS = ("media", "speed", "role", "function", "type", "slot")


def search_blob(d, ddir=None):
    """Everything a reader might type that is not already in the index entry.

    The filter searched manufacturer, model, series, family and description, and
    so found devices by how their summary happened to be PHRASED. "Qumran" and
    "ROADM" found nothing while a device with a Qumran ASIC and two ROADM line
    units sat in the list. What a device IS lives in attrs, and attrs live in
    <device>.configs.json - which the browser would have to fetch once per device
    to index, thirteen times today and three hundred at the size the filter
    exists for. So it is flattened here, once, at build.

    Group attrs matter as much as device attrs and are easy to miss: on the
    AGR400 the only place that says 400G is `groups.qsfpdd-400g.attrs.speed`.
    Component refs are in too, so "qsfp-dd" and "lc-duplex" find the devices that
    carry them without anyone having written those words in a sentence.
    """
    words = []

    def take(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                words.append(str(k))
                take(v)
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                take(v)
        elif obj is not None:
            words.append(str(obj))

    # FLATTENED, not walked. `take` appends keys as well as values, so walking
    # the sections would put "physical", "power" and "other" into every device's
    # haystack and make those words match the whole portfolio - a filter term
    # that matches everything is worse than one that matches nothing.
    take(attrs_mod.flatten(d.get("attrs")))
    take(d.get("part-numbers") or {})
    # every other name the box is sold or listed under (#514), so an HCL's AS
    # number or a DriveNets name typed into the filter finds the drawing
    take(alias_names(d))
    for g, gdef in (d.get("groups") or {}).items():
        words.append(g)
        gdef = gdef or {}
        words.append(str(gdef.get("term") or ""))
        for k in SEARCH_ATTRS:
            if (gdef.get("attrs") or {}).get(k):
                words.append(str(gdef["attrs"][k]))
    for cfg in (d.get("configurations") or {}).values():
        take((cfg or {}).get("part-numbers") or {})
    refs = set()
    for view in (d.get("views") or {}).values():
        vp = view_parts(view or {})
        for q in vp["placements"]:
            refs.add(q["ref"])
            for k in SEARCH_ATTRS:
                if (q.get("attrs") or {}).get(k):
                    words.append(str(q["attrs"][k]))
        for b in vp["bays"]:
            refs.update(b.get("accepts") or [])
    # The NOS an overlay exists for. "arcos" used to be findable on the
    # AS7326-56X because somebody had written it into an attr; the attr moved to
    # overlays/arcos.yaml, which is its right home, and the word would have gone
    # with it. What a device can be joined to is a fact worth searching for, so
    # it is indexed from the overlay itself rather than from a sentence.
    for f in sorted((ddir / "overlays").glob("*.yaml")) if ddir else []:
        o = load_yaml(f) or {}
        words.append(str(o.get("nos") or ""))
    # sorted, because `refs` is a set and set iteration order varies between
    # processes. Everything else feeding `words` is already ordered; this was the
    # one leak, and it made devices.json differ between two builds of an
    # unchanged tree - same tokens, same count, different order. Harmless to the
    # filter, which matches tokens, but it defeats verifying a build by checksum,
    # which is how this project checks that a change moved nothing.
    for ref in sorted(refs):              # 'std/qsfp-dd@1' -> 'qsfp-dd'
        words.append(ref.split("/")[-1].rsplit("@", 1)[0])
    seen, out = set(), []
    for w in " ".join(words).lower().split():
        if w not in seen:
            seen.add(w)
            out.append(w)
    return " ".join(out)


def decor_confidence(d):
    """{token: n} over every decor entry that projects or recesses in 3D.

    Only the entries that carry a Z - `out`, `lift`, `sink`, `vent`. A flat
    coloured rectangle is artwork and has no magnitude to source, so counting it
    would bury the ones that do under the ones that cannot.

    A device's 3D was the ONE PLACE in the library that could never say where its
    numbers came from: components gained `confidence` on every relief feature and
    a chassis kept extruding decor with nothing attached. `unstated` here is the
    same signal it is for a component - a projection nobody sourced looks exactly
    like a measured one.
    """
    counts = {}
    for view in (d.get("views") or {}).values():
        for e in ((view.get("panel") or {}).get("decor") or []):
            if not any(e.get(k) for k in ("out", "lift", "sink", "vent")):
                continue
            k = e.get("confidence") or "unstated"
            counts[k] = counts.get(k, 0) + 1
    return counts


def check_unique_names(devices):
    """Raise if two devices share a name. A FUNCTION so a test can call it.

    Written inline first, which meant the only way to test it was to rebuild
    the check in the test - a mirror of the guard rather than the guard, and
    this repository has spent a whole session finding out what those are worth.
    """
    seen = {}
    for d in devices:
        if d["name"] in seen:
            raise SystemExit(
                f"devices_index: two devices are called {d['name']!r} - "
                f"{seen[d['name']]} and {d.get('ns')}. A device's name is its "
                "filename in dist/, which carries no vendor, so these would "
                "render over each other. Rename one, or give dist a namespace")
        seen[d["name"]] = d.get("ns")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", action="append", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    devices = []
    for root in args.library:
        for man in libwalk.iter_devices([root]):
            d = load_yaml(man)
            if d.get("kind") != "device":
                continue
            cap = capability.report(man, d, args.library, SCHEMAS)
            devices.append({
                "name": d["name"],
                # the picker greys out what a model cannot do rather than
                # offering it and drawing something wrong, so it needs this
                # before it has loaded the device
                "capability": cap["capability"],
                "gaps": cap["gaps"],
                "model": d.get("model", d["name"]),
                # the box's other names, `model` excluded (#514)
                "aliases": alias_names(d),
                "manufacturer": d.get("manufacturer", ""),
                # THE NAMESPACE, because a consumer cannot recover it. `name` is
                # bare - `c100g`, not `casa/c100g` - and components.json keys its
                # own entries by `ns`, so without this there is nothing to join
                # them on. The DCIM export needs exactly that join: it maps a
                # component's namespace to the manufacturer that ships it, and
                # built the map by walking devices/<ns>/<model>/ off the source
                # tree because the index did not carry it.
                "ns": man.parent.parent.name,
                # THE CITATION, which is a fact about the world rather than about
                # the drawing, and the only field of the manifest that reached no
                # artifact at all. 49 of 84 devices carry one. The export puts it
                # in a DCIM record's comments so the person reading that record
                # can get back to the document the numbers came from.
                "datasheet": d.get("datasheet") or {},
                "version": d.get("version", ""),
                "description": d.get("description", ""),
                # where it sits in the vendor's catalogue. The picker groups on
                # this; absent is fine and sorts under the manufacturer alone.
                "portfolio": d.get("portfolio") or {},
                # WHAT IT CAN BE BOUGHT WITH, before anything is loaded: the
                # feeds (`ac`, `dc`, `hvdc`) and airflows its orderable builds
                # resolve to, so a picker can filter "DC, back-to-front" across
                # the library without opening every configs.json (#513).
                "options": device_options(d),
                # what the type-ahead filter matches on beyond the fields above
                "search": search_blob(d, man.parent),
                # where this chassis's own 3D projections came from, counted
                "decor-confidence": decor_confidence(d),
            })
    devices.sort(key=lambda x: (x["manufacturer"], x["name"]))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    totals = {}
    for e in devices:
        for k, n in e["decor-confidence"].items():
            totals[k] = totals.get(k, 0) + n
    # A DEVICE'S NAME IS ITS FILENAME IN dist/, AND NOTHING CHECKED IT WAS
    # UNIQUE. `library/dist/<name>.<config>.<view>.svg` carries no vendor, so
    # two vendors shipping a model of the same name would render over each
    # other and the index would list one of them twice - silently, because
    # neither the build nor the picker has any way to notice (#185).
    #
    # FAILING IS THE ANSWER AND RENAMING IS NOT. Putting the vendor in every
    # dist filename would break `kit/`, every doc that cites one and every URL
    # anyone has kept, to solve a problem the library does not have yet - 89
    # devices, 89 distinct names. A collision is a modelling decision someone
    # has to make (rename one, or namespace the dist), and this is the line
    # that makes them make it.
    check_unique_names(devices)

    (out / "devices.json").write_text(
        json.dumps({"contract": CONTRACT, "devices": devices,
                    "decor-confidence": totals},
                   indent=1, sort_keys=True))
    print(f"compiled {len(devices)} devices -> {out}/devices.json")


if __name__ == "__main__":
    main()
