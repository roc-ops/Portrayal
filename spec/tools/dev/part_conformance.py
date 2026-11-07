"""Part conformance, the prototype (docs/part-conformance-design.md).

Runs the two checks over a sample of devices in a built library:

  cabling   every place a cable can end, in each configuration, laid to a
            matching far end: offered to an agent, accepted, not a loose end,
            routed, standing on its mating point along its axis;
  settings  every state the drawings declare is a state the agent's tools take,
            and gives the document and the drawing the page does.

and, in its scan mode, the four codes that ask whether every port is usable
(C19 to C22) over every configuration, with no cable laid.

The kit does the work (part_conformance.mjs, under node); this is the front
door: the sample, the timing, the summary and the report file.

    python3 spec/tools/dev/part_conformance.py --dist library/dist \\
        --sample spec/tools/dev/part_conformance_sample.json --out report.json
    python3 spec/tools/dev/part_conformance.py --dist library/dist --scan --all --out scan.json
    python3 spec/tools/dev/part_conformance.py --by-family scan.json --out families.json

The report is written to --out, never to a redirect. Exit status 1 when a
BLOCKING finding exists and --strict is given; a finding marked gap, standin,
warn or note only reports.
"""
import argparse
import json
import os
import pathlib
import re
import resource
import shutil
import subprocess
import sys
import time

import yaml

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNNER = HERE / "part_conformance_run.mjs"
SAMPLE = HERE / "part_conformance_sample.json"
FAMILIES = HERE / "port_families.yaml"

# What each code says, and whether it blocks a merge (design section 5).
CODES = {
    "S0": ("settings", "block", "the check could not run on this configuration"),
    "S1": ("settings", "block", "a state the drawings declare is unknown to the agent's catalogue"),
    "S2": ("settings", "report", "the catalogue lists a state no drawing declares"),
    "S3": ("settings", "block", "the drawing and the catalogue disagree on a vocabulary"),
    "S4": ("settings", "block", "state.set refuses a state the drawings declare"),
    "S5": ("settings", "block", "state.set gives another document than the page writes"),
    "S6": ("settings", "block", "an accepted state is dropped before the drawing"),
    "S7": ("settings", "block", "a declared state has no rule that paints it"),
    "S8": ("settings", "gap", "a display's whole readings cannot be set by any command"),
    "S9": ("settings", "block", "field refuses a field the drawn part declares"),
    "C0": ("cabling", "block", "the check could not run on this configuration"),
    "C1": ("cabling", "block", "a cable to an offered end is refused at add time"),
    "C2": ("cabling", "block", "an accepted cable is a loose end"),
    "C3": ("cabling", "block", "an accepted cable does not route"),
    "C4": ("cabling", "block", "the route does not start on the end's point"),
    "C5": ("cabling", "block", "the first leg leaves the end off its axis"),
    "C6": ("cabling", "block", "the end falls outside the device in a face pane"),
    "C7": ("cabling", "block", "a side pane would draw the end off its panel (setback)"),
    "C8": ("cabling", "block", "a drawn port is not offered to an agent"),
    "C9": ("cabling", "block", "an offered port has no drawing"),
    "C10": ("cabling", "standin", "a port on an angled facet declares no axis"),
    "C11": ("cabling", "block", "a coupler has cable ends on one side only"),
    "C12": ("cabling", "gap", "no matching far end or optic to test this end with"),
    "C13": ("cabling", "block", "the plug's first leg runs inside its own device"),
    "C14": ("cabling", "standin", "an end declares no mating point"),
    "C15": ("cabling", "block", "a made-up end is accepted at add time"),
    "C18": ("cabling", "block", "the back of a seated part has ends the host draws no point for"),
    "C19": ("cabling", "block", "a powered part presents no power end an agent is offered"),
    "C20": ("cabling", "block", "a drawn inlet, terminal or stud is not a place a cord or lug can land"),
    "C21": ("cabling", "block", "a connector or cage slot has no mate in its accepts and no sentence says none can exist"),
    "C22": ("cabling", "block", "a drawn port presents no registered interface, itself or through what it composes"),
    "C16": ("cabling", "gap", "the catalogue alone does not answer for an end of a listed part"),
    "C17": ("cabling", "block", "a part a cage lists cannot be fitted to it"),
    "O1": ("cabling", "block", "a bay lists a part the library does not hold"),
}
CHECKS = ("settings", "cabling", "usable")


def node():
    found = shutil.which("node") or os.path.expanduser("~/tools/node-v20.20.2-linux-x64/bin/node")
    if not pathlib.Path(found).exists():
        raise SystemExit("node is not installed")
    return found


def load_sample(path):
    data = json.loads(pathlib.Path(path).read_text())
    return data["parts"] if isinstance(data, dict) else data


# ── the sentences that say no mate can exist ─────────────────────────────────────────────────────────
_UNMATED = re.compile(r"^unmated:", re.M)


def contract_ref(path):
    """`ns/name@major` of library/components/<ns>/<name>/v<major>/contract.yaml."""
    return f"{path.parents[2].name}/{path.parents[1].name}@{path.parent.name[1:]}"


def load_unmated(library):
    """{ref: sentence} for every contract that carries `unmated`. Only a file with the key is parsed."""
    out = {}
    for path in sorted(pathlib.Path(library).glob("components/*/*/v*/contract.yaml")):
        text = path.read_text()
        if _UNMATED.search(text):
            doc = yaml.safe_load(text) or {}
            if "unmated" in doc:                      # kept even when empty, so the records test can fail it
                out[contract_ref(path)] = doc["unmated"]
    return out


def read_registries(schemas):
    """The two registries as the scan reads them: connectors {interface: {cover, unmated?}} and
    families {name: {interface, rates, unmated?}}. `unmated` is kept as written, so a test can judge it."""
    schemas = pathlib.Path(schemas)
    interfaces = (yaml.safe_load((schemas / "connectors.yaml").read_text()) or {}).get("interfaces") or {}
    families = (yaml.safe_load((schemas / "pluggables.yaml").read_text()) or {}).get("families") or {}
    connectors = {k: {"cover": bool((v or {}).get("cover")), **({"unmated": v["unmated"]} if "unmated" in (v or {}) else {})}
                  for k, v in interfaces.items()}
    fams = {k: {"interface": v.get("interface"), "rates": v.get("rates") or [], **({"unmated": v["unmated"]} if "unmated" in v else {})}
            for k, v in families.items()}
    return {"connectors": connectors, "families": fams}


def usable_options(library, schemas):
    return {"parts": load_unmated(library), **read_registries(schemas)}


# ── running ──────────────────────────────────────────────────────────────────────────────────────────
def run(dist, refs, max_configs=3, max_ends=12, max_states=400, skip=(), site=None, scan=False, usable=None):
    """Run the node half over `refs`; returns (report dict, seconds)."""
    opts = json.dumps({"refs": list(refs), "maxConfigs": max_configs, "maxEnds": max_ends,
                       "maxStates": max_states, "skip": list(skip), "site": site, "scan": scan, "usable": usable or {}})
    t = time.monotonic()
    p = subprocess.run([node(), str(RUNNER), str(dist), opts], capture_output=True, text=True, cwd=str(HERE))
    took = time.monotonic() - t
    if p.returncode != 0:
        raise SystemExit(f"node failed:\n{p.stderr[-2000:]}")
    return json.loads(p.stdout.strip().splitlines()[-1]), took


def findings(report):
    """[(ref, cfg, check, finding)] for every finding of a report."""
    out = []
    for part in report["parts"]:
        if part.get("error"):
            out.append((part["ref"], None, "both", {"code": "X0", "text": part["error"], "n": 1}))
        for f in (part.get("occupants") or {}).get("found", []):
            out.append((part["ref"], "(every listed part)", "occupants", f))
        for row in part["configs"]:
            for check in CHECKS:
                for f in (row.get(check) or {}).get("found", []):
                    out.append((part["ref"], row["cfg"], check, f))
    return out


def level_of(f):
    return f.get("level") or CODES.get(f["code"], ("", "block", ""))[1]


def summarise(report):
    by_code = {}
    for ref, cfg, check, f in findings(report):
        row = by_code.setdefault(f["code"], {"parts": set(), "configs": 0, "n": 0, "level": level_of(f), "causes": 0, "keys": set()})
        row["parts"].add(ref)
        row["configs"] += 1
        row["n"] += f.get("n", 1)
        for c in f.get("causes") or []:
            row["causes"] += 1
            row["keys"].add(c["part"] or c["device"])
    return {c: {"level": r["level"], "parts": sorted(r["parts"]), "configs": r["configs"], "n": r["n"],
                **({"causes": r["causes"], "cause-parts": len(r["keys"])} if r["causes"] else {}),
                "says": CODES.get(c, ("", "", ""))[2]} for c, r in sorted(by_code.items())}


def seconds(report):
    out = {"settings": 0.0, "cabling": 0.0, "usable": 0.0, "occupants": 0.0, "configs": 0}
    for part in report["parts"]:
        out["occupants"] += (part.get("occupants") or {}).get("seconds", 0.0)
        for row in part["configs"]:
            out["configs"] += 1
            for check in CHECKS:
                out[check] += (row.get(check) or {}).get("seconds", 0.0)
    return {k: round(v, 2) if isinstance(v, float) else v for k, v in out.items()}


def below_own_rate(report):
    """The cage slots that accept modules and none at the cage's own rate: distinct (device, path)."""
    return sorted({(part["ref"], b["path"]) for part in report["parts"] for row in part["configs"]
                   for b in ((row.get("usable") or {}).get("counts") or {}).get("belowOwnRate", [])})


def text(report, took, verbose=False):
    lines = [f"part conformance over {len(report['parts'])} parts in {took:.1f} s ({seconds(report)})"]
    shown = set()
    for ref, cfg, check, f in findings(report):
        if not verbose and f["code"] in shown:
            continue
        shown.add(f["code"])
        lines.append(f"  {level_of(f):7} {f['code']:4} {ref}{'/' + cfg if cfg else ''}: {f['text']}")
    lines.append("")
    for code, row in summarise(report).items():
        extra = f" {row['causes']:5} causes over {row['cause-parts']} parts or devices" if "causes" in row else ""
        lines.append(f"  {code:4} {row['level']:7} {len(row['parts']):3} parts {row['configs']:4} configs{extra}: {row['says']}")
    if report.get("scan"):
        s = report["scan"]
        lines.append(f"  cage slots that accept modules and none at their own rate: {s['cages-below-own-rate']}")
        lines.append(f"  scan: {s['wall-seconds']} s wall, {s['node-cpu-seconds']} s node CPU, load {s['load-start']} to {s['load-end']}")
    return "\n".join(lines)


# ── the family of a part ─────────────────────────────────────────────────────────────────────────────
def contract_of(library, ref):
    ns, tail = ref.split("/")
    name, major = tail.split("@")
    path = pathlib.Path(library) / "components" / ns / name / f"v{major}" / "contract.yaml"
    return (yaml.safe_load(path.read_text()) or {}) if path.exists() else {}


def family_of(spec, contract, name):
    """The family of a part by the five rules of port_families.yaml, in order. `name` is the part's name (or, for a
    cause with no part, the drawn path)."""
    entry = (spec.get("interfaces") or {}).get(contract.get("interface"))
    if entry:                                                                   # 1. its own registered interface
        if isinstance(entry, str):
            return entry
        return (entry.get("by-class") or {}).get(contract.get("class"), entry["family"])
    attrs = contract.get("attrs") or {}
    if contract.get("class") == "psu":                                          # 2. a supply, by its attrs
        psu = spec["psu"]
        dc = any(str(attrs.get(k)) in vals for k, vals in (psu.get("dc-when") or {}).items())
        dc = dc or any(word in (psu.get("dc-named") or []) for word in name.lower().split("-"))
        return psu["dc"] if dc else psu["ac"]
    if contract.get("class") in (spec.get("classes") or {}):                    # 3. a ground part
        return spec["classes"][contract["class"]]
    low = name.lower()
    for pattern in spec.get("name-patterns") or []:                             # 4. a name
        if any(s in low for s in pattern["contains"]):
            return pattern["family"]
    return spec["other"]                                                        # 5. otherwise


def first_words(value, n=12):
    words = str(value).split()
    return " ".join(words[:n]) + (" ..." if len(words) > n else "")


def by_family(report, library, spec, dist=None):
    """Every cause of a scan report sorted into a family: {families: {name: {parts, devices, vendors, causes}}, totals}."""
    makers = {}
    rack = pathlib.Path(dist or report.get("dist") or "") / "rack.json"
    if rack.is_file():
        makers = {k: v.get("manufacturer") for k, v in (json.loads(rack.read_text()).get("devices") or {}).items()}
    fams = {name: {"parts": {}, "devices": set(), "vendors": set(), "causes": 0} for name in spec["families"]}
    for _ref, _cfg, _check, f in findings(report):
        for c in f.get("causes") or []:
            if c["part"]:
                contract = contract_of(library, c["part"])
                fam = fams[family_of(spec, contract, c["part"].split("/")[1].split("@")[0])]
                if c["part"] not in fam["parts"]:
                    fam["parts"][c["part"]] = {"ref": c["part"], "class": contract.get("class"),
                                               "provenance": {k: first_words(v) for k, v in (contract.get("provenance") or {}).items()}}
                vendor = makers.get(c["device"]) or c["part"].split("/")[0]
            else:
                fam = fams[family_of(spec, {}, c["path"])]
                vendor = makers.get(c["device"]) or ""
            fam["devices"].add(c["device"])
            if vendor:
                fam["vendors"].add(vendor)
            fam["causes"] += 1
    out = {name: {"parts": sorted(f["parts"].values(), key=lambda p: p["ref"]), "devices": sorted(f["devices"]),
                  "vendors": sorted(f["vendors"]), "causes": f["causes"]} for name, f in fams.items()}
    return {"families": out, "totals": {name: {"parts": len(f["parts"]), "devices": len(f["devices"])} for name, f in out.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dist", default="library/dist")
    ap.add_argument("--sample", default=str(SAMPLE), help="a JSON file: {parts: [{ref, why}]} or a list of refs")
    ap.add_argument("--refs", nargs="*", help="devices to run, instead of the sample")
    ap.add_argument("--all", action="store_true", help="every device of the build (the scheduled run)")
    ap.add_argument("--max-configs", type=int, default=3)
    ap.add_argument("--max-ends", type=int, default=12, help="cable ends judged per configuration and variant (a stratified sample)")
    ap.add_argument("--max-states", type=int, default=400)
    ap.add_argument("--skip", nargs="*", default=[], choices=["cabling", "settings", "occupants"])
    ap.add_argument("--out", required=True, help="where the JSON report is written")
    ap.add_argument("--site", help="a checkout of the site: its side-pane geometry is asked where the faceplate stands (C7)")
    ap.add_argument("--strict", action="store_true", help="exit 1 on a blocking finding")
    ap.add_argument("--verbose", action="store_true", help="print every finding, not the first of each code")
    ap.add_argument("--scan", action="store_true", help="C19 to C22 only, every configuration, no cable laid")
    ap.add_argument("--library", default=str(ROOT / "library"), help="the library whose contracts carry `unmated`")
    ap.add_argument("--schemas", default=str(ROOT / "spec" / "schemas"), help="the folder of connectors.yaml and pluggables.yaml")
    ap.add_argument("--by-family", metavar="REPORT", help="sort the causes of a scan report into families (port_families.yaml) and write them to --out")
    ap.add_argument("--families", default=str(FAMILIES), help="the family rules, for --by-family")
    a = ap.parse_args(argv)
    if a.by_family:
        report = json.loads(pathlib.Path(a.by_family).read_text())
        spec = yaml.safe_load(pathlib.Path(a.families).read_text())
        result = by_family(report, a.library, spec, a.dist if pathlib.Path(a.dist, "rack.json").is_file() else None)
        pathlib.Path(a.out).write_text(json.dumps(result, indent=1) + "\n")
        for name, t in result["totals"].items():
            print(f"  {name:40} {t['parts']:4} parts {t['devices']:4} devices")
        return 0
    dist = pathlib.Path(a.dist).resolve()
    if a.all:
        refs = sorted(p.name[: -len(".configs.json")] for p in dist.glob("*.configs.json"))
        why = {}
    elif a.refs:
        refs, why = a.refs, {}
    else:
        parts = load_sample(a.sample)
        refs = [p["ref"] if isinstance(p, dict) else p for p in parts]
        why = {p["ref"]: p.get("why", "") for p in parts if isinstance(p, dict)}
    usable = usable_options(a.library, a.schemas)
    load_start, cpu_start = os.getloadavg(), resource.getrusage(resource.RUSAGE_CHILDREN)
    report, took = run(dist, refs, a.max_configs, a.max_ends, a.max_states, a.skip, a.site, scan=a.scan, usable=usable)
    cpu_end, load_end = resource.getrusage(resource.RUSAGE_CHILDREN), os.getloadavg()
    for part in report["parts"]:
        part["why"] = why.get(part["ref"], "")
    report["dist"] = a.dist            # as given: the report names no path of this machine
    report["seconds"] = round(took, 2)
    report["timing"] = seconds(report)
    if a.scan:
        report["scan"] = {"wall-seconds": round(took, 1),
                          "node-cpu-seconds": round((cpu_end.ru_utime + cpu_end.ru_stime) - (cpu_start.ru_utime + cpu_start.ru_stime), 1),
                          "load-start": [round(x, 2) for x in load_start], "load-end": [round(x, 2) for x in load_end],
                          "cages-below-own-rate": len(below_own_rate(report)), "devices": len(report["parts"])}
    report["summary"] = summarise(report)
    pathlib.Path(a.out).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(text(report, took, a.verbose))
    blocking = [f for _, _, _, f in findings(report) if level_of(f) == "block"]
    return 1 if (a.strict and blocking) else 0


if __name__ == "__main__":
    sys.exit(main())
