#!/usr/bin/env python3
"""Compile comparable-facts.json - one name per measurement, across every device.

`devices.json` publishes what a device IS. This publishes what it MEASURES, in
a vocabulary a side-by-side can line up, with the vendor's own string kept next
to every value so a reader can always see the sentence the number came from.

Nothing here is authored. See comparable.py for the rules and for the comparison
that went wrong and prompted it.
"""
import argparse
import json
from pathlib import Path

import yaml

import comparable as facts_mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", default="library")
    ap.add_argument("--out", default="library/dist")
    args = ap.parse_args()

    lib = Path(args.library)
    devices, census = [], {}
    for man in sorted(lib.glob("devices/*/*/device.yaml")):
        d = yaml.safe_load(man.read_text())
        if (d or {}).get("kind") != "device":
            continue
        resolved = facts_mod.resolve(d)
        tail = facts_mod.unclaimed(d)
        old = facts_mod.superseded(d)
        for k in tail:
            census[k] = census.get(k, 0) + 1
        devices.append({
            "name": d.get("name") or man.parent.name,
            "ns": man.parent.parent.name,
            "manufacturer": d.get("manufacturer", ""),
            "model": d.get("model", ""),
            "facts": resolved,
            # what this device states that no fact claims yet. Per device, so a
            # reader chasing a missing row can see whether the answer is absent
            # or merely unclaimed.
            "unclaimed": tail,
            # prose kept for a fact now read off the groups - not an error,
            # just never the source
            "superseded": old,
        })
    devices.sort(key=lambda x: (x["manufacturer"], x["name"]))

    # THE VOCABULARY IS PUBLISHED ALONGSIDE THE VALUES. A consumer should not
    # have to hardcode the fact list to know what columns exist, nor guess
    # which pairs may be compared - `throughput-gbps` and
    # `switching-capacity-gbps` are both Gbps and must not be merged.
    vocab = {}
    for f in facts_mod.FACTS:
        entry = {"section": f.section, "unit": f.unit, "kind": f.kind,
                 "sources": sorted({k for (k, _, _) in f.sources}),
                 "derived": f.name in facts_mod.DERIVED}
        if f.note:
            entry["note"] = f.note
        vocab[f.name] = entry

    sup = {}
    for e in devices:
        for k in e["superseded"]:
            sup[k] = sup.get(k, 0) + 1

    stated, silent = {}, {}
    for e in devices:
        for k, v in e["facts"].items():
            if v.get("readings"):
                stated[k] = stated.get(k, 0) + 1
            elif v.get("absent"):
                silent[k] = silent.get(k, 0) + 1

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "comparable-facts.json").write_text(json.dumps({
        "vocabulary": vocab,
        "devices": devices,
        # a census, not a complaint - the tail either shrinks as patterns
        # emerge or it stays visibly unshrunk
        "unclaimed": dict(sorted(census.items(), key=lambda kv: (-kv[1], kv[0]))),
        "coverage": dict(sorted(stated.items(), key=lambda kv: (-kv[1], kv[0]))),
        # facts a person has recorded the vendor as not publishing. The
        # difference between this and a blank is the whole point: one is an
        # answer, the other is an open question.
        "declared-silent": dict(sorted(silent.items(), key=lambda kv: (-kv[1], kv[0]))),
        "superseded": dict(sorted(sup.items(), key=lambda kv: (-kv[1], kv[0]))),
    }, indent=1, sort_keys=True))
    print(f"compiled {len(vocab)} comparable facts across {len(devices)} devices "
          f"-> {out}/comparable-facts.json ({len(census)} unclaimed spelling(s))")


if __name__ == "__main__":
    main()
