"""Every port on a device is usable, and the records of the ones that are not.

Every connector in the library has a mate, or says why none can exist
(docs/part-conformance-design.md, section 10). The part-conformance runner's scan
mode judges the whole build under four codes (C19 to C22); this test holds what
`library/conformance-exceptions.yaml` and the `unmated` sentences say about its
findings. The switches are the file's, never this test's:

- with no `cap:` in the file, a finding no record covers, a stale row, too many
  rows, a row for a closed code and a crashed runner are printed, and the test
  passes;
- with `cap:` present they fail the pull request;
- the shape of the file, a sentence beside a mate, a part with both a row and a
  sentence for one code, and a registry sentence under 40 characters fail
  whatever the file says.

No handler here turns a failure into a warning.
"""
import copy
import datetime
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import time

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "spec/tools/dev/part_conformance.py"
RECORDS = ROOT / "library/conformance-exceptions.yaml"
DIST = ROOT / "library" / "dist"

SENTENCE = "a printed marking on the panel; it takes no cable, cord or lug"       # at least 40 characters

CODES = ("C19", "C20", "C21", "C22")
PART_SENTENCE_CODES = ("C19", "C20", "C22")          # the codes a part's own `unmated` is read by
MATE_CLASSES = ("port", "transceiver")
TOP_KEYS = ("format", "rows", "cap", "closed")
ROW_KEYS = ("part", "code", "why", "order", "since")
MIN_SENTENCE = 40
RUN_TIMEOUT = 900            # seconds; a runner that hangs fails the pull request once `cap:` is present
SCHEMAS = ROOT / "spec" / "schemas"
LIBRARY = ROOT / "library"


def _tool():
    spec = importlib.util.spec_from_file_location("part_conformance", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Verdict:
    """What a judgement found. `always` fails whatever the file says; `capped` fails once the file has a `cap:`."""

    def __init__(self):
        self.always, self.capped = [], []

    def printed(self):
        return [*self.always, *self.capped]


def failures(v, doc):
    """The lines that fail a pull request: the switches are the file's (`cap:` present), never this test's."""
    return [*v.always, *(v.capped if isinstance(doc, dict) and "cap" in doc else [])]


def ref_of(c):
    return f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}"


def mates_of(c):
    m = c.get("mates")
    return [] if not m else [m] if isinstance(m, str) else list(m)


def long_enough(s):
    return isinstance(s, str) and len(s) >= MIN_SENTENCE


def shape(doc, out):
    """Rule 1: the file is well formed."""
    if not isinstance(doc, dict):
        out.append("conformance-exceptions.yaml is not a mapping")
        return []
    out.extend(f"unknown top-level key {k!r}" for k in doc if k not in TOP_KEYS)
    if doc.get("format") != 1:
        out.append("format must be 1")
    rows = doc.get("rows")
    if not isinstance(rows, list):
        out.append("rows must be a list")
        rows = []
    if "cap" in doc and not (type(doc["cap"]) is int and doc["cap"] >= 0):
        out.append(f"cap must be a non-negative integer, not {doc['cap']!r}")
    closed = doc.get("closed", [])
    if not isinstance(closed, list) or any(c not in CODES for c in closed):
        out.append(f"closed must list codes from {', '.join(CODES)}, not {closed!r}")
    for i, r in enumerate(rows):
        if not isinstance(r, dict):
            out.append(f"row {i} is not a mapping")
            continue
        if r.get("code") not in CODES and "code" in r:
            continue                                       # a row for a code this test does not read
        out.extend(f"row {i} ({r.get('part')}) has no {k}" for k in ROW_KEYS if k not in r)
        out.extend(f"row {i} has an unknown key {k!r}" for k in r if k not in ROW_KEYS)
        if "order" in r and not str(r["order"] or "").strip():
            out.append(f"row {i} ({r.get('part')}) names no order: no order, no row")
    return [r for r in rows if isinstance(r, dict) and r.get("code") in CODES and all(k in r for k in ROW_KEYS)]


def sentences(w, out):
    """Rules 2 and 4: a sentence beside a mate (L89's two-way honesty), and a registry sentence too short."""
    comps = {ref_of(c): c for c in w["components"]}
    is_mate = lambda ref: comps.get(ref, {}).get("class") in MATE_CLASSES
    for ref, sentence in w["part-unmated"].items():
        if not long_enough(sentence):
            out.append(f"{ref}: `unmated` is under {MIN_SENTENCE} characters")
        c = comps.get(ref)
        slots = [*((c or {}).get("cages") or []), *([c["presents"]] if (c or {}).get("presents") else [])]
        for slot in slots:
            if any(is_mate(a) for a in slot.get("accepts") or []):
                out.append(f"{ref} carries `unmated` and presents a slot ({slot.get('id', 'its own')}) whose accepts hold a mate: remove the sentence")
                break
    for iface, entry in w["connectors"].items():
        if "unmated" not in (entry or {}):
            continue
        if not long_enough(entry["unmated"]):
            out.append(f"connectors.yaml {iface}: `unmated` is under {MIN_SENTENCE} characters")
        mates = sorted(ref_of(c) for c in w["components"] if iface in mates_of(c) and c.get("class") in MATE_CLASSES)
        if mates:
            out.append(f"connectors.yaml {iface} carries `unmated` and {mates[0]} mates it: remove the sentence")
    for name, fam in w["families"].items():
        if "unmated" in fam and not isinstance(fam["unmated"], dict):
            out.append(f"pluggables.yaml {name}: `unmated` must map a rate to its sentence")
            continue
        for rate, sentence in (fam.get("unmated") or {}).items():
            if not long_enough(sentence):
                out.append(f"pluggables.yaml {name} {rate}: `unmated` is under {MIN_SENTENCE} characters")
            if rate not in (fam.get("rates") or []):
                out.append(f"pluggables.yaml {name} {rate}: not a rate of the family")
            fills = sorted(ref_of(c) for c in w["components"] if c.get("class") in MATE_CLASSES and fam.get("interface") in mates_of(c)
                           and (c.get("attrs") or {}).get("rate") in (None, rate))
            if fills:
                out.append(f"pluggables.yaml {name} {rate} carries `unmated` and {fills[0]} fills it: remove the sentence")


def causes_of(report):
    """[(code, part, device)] of every cause of a scan report, and the lines for a check that threw."""
    found, threw = [], []
    for part in report["parts"]:
        if part.get("error"):
            threw.append(f"{part['ref']}: {part['error']}")
        for r in part["configs"]:
            for check in ("usable", "cabling"):
                for f in (r.get(check) or {}).get("found", []):
                    if f["code"] in ("C0", "X0"):
                        threw.append(f"{part['ref']}/{r['cfg']}: {f['text']}")
                    for c in f.get("causes") or []:
                        if f["code"] in CODES:
                            found.append((f["code"], c["part"], c["device"]))
    return found, threw


def judge(report, doc, w, crash=None, full=True):
    """The records against a scan. `full` is true when the scan was the whole library, the only scan a row can be stale against."""
    v = Verdict()
    rows = shape(doc, v.always)
    sentences(w, v.always)
    v.always.extend(f"{r['part']} has a row for {r['code']} and a sentence: keep one" for r in rows
                    if r["code"] in PART_SENTENCE_CODES and r["part"] in w["part-unmated"])
    if crash:
        v.capped.append(f"the runner failed: {crash}")
        return v
    found, threw = causes_of(report)
    v.capped.extend(f"the check threw: {t}" for t in threw)
    covered = {(r["code"], r["part"]) for r in rows}
    keys = {(code, part or device) for code, part, device in found}
    v.capped.extend(f"{code} {key}: no row and no sentence covers it" for code, key in sorted(keys - covered))
    if full:
        v.capped.extend(f"{code} {key}: a row for a finding that no longer occurs" for code, key in sorted(covered - keys))
    cap = doc.get("cap") if isinstance(doc, dict) else None
    if type(cap) is int and len(rows) > cap:
        v.capped.append(f"{len(rows)} rows are over the cap of {cap}")
    closed = doc.get("closed", []) if isinstance(doc, dict) and isinstance(doc.get("closed", []), list) else []
    v.capped.extend(f"{r['code']} {r['part']}: a row for {r['code']}, which is closed" for r in rows if r["code"] in closed)
    return v


def run_scan(dist, tmp_path, refs=None):
    """The runner in scan mode: (report, None), or (None, why) when it did not finish."""
    out = tmp_path / "scan.json"
    where = ["--all"] if refs is None else ["--refs", *refs]
    try:
        p = subprocess.run([sys.executable, str(TOOL), "--dist", str(dist), "--scan", *where, "--out", str(out)],
                           capture_output=True, text=True, cwd=ROOT, timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"it did not finish in {RUN_TIMEOUT} s"
    if p.returncode != 0 or not out.exists():
        return None, f"it exited {p.returncode}: {(p.stderr or p.stdout)[-400:]}"
    return json.loads(out.read_text()), None


def row(part, code="C20", **rest):
    return {"part": part, "code": code, "why": "the guide draws it and says nothing more", "order": "#1234",
            "since": datetime.date(2026, 10, 30), **rest}


def cause(part, code="C20", device="dev", cfg="base", view="rear", path="x"):
    return {"code": code, "part": part, "device": device, "cfg": cfg, "view": view, "path": path}


def report_of(*causes):
    """A scan report holding exactly these causes, one finding per code."""
    by_code = {}
    for c in causes:
        by_code.setdefault(c["code"], []).append({k: v for k, v in c.items() if k != "code"})
    found = [{"code": code, "text": "t", "n": len(cs), "causes": cs} for code, cs in sorted(by_code.items())]
    return {"parts": [{"ref": "dev", "configs": [{"cfg": "base", "usable": {"found": found, "counts": {}}}]}]}


def component(ref, **rest):
    ns, tail = ref.split("/")
    name, major = tail.split("@")
    return {"ns": ns, "name": name, "major": f"v{major}", "class": "port", "attrs": {}, "parts": [], **rest}


def world(**rest):
    return {"components": [], "connectors": {}, "families": {}, "part-unmated": {}, **rest}


def verdict(report, doc, w=None, crash=None, full=True):
    return judge(report, doc, w or world(), crash=crash, full=full)


def test_the_records_file_shape_is_held_from_the_first_merge():
    """Rule 1 of what fails whatever the file says."""
    good = {"format": 1, "rows": [row("acme/p@1")]}
    assert verdict(report_of(), good).always == []
    plants = {
        "an unknown top-level key": {**good, "note": "x"},
        "a row with no order": {**good, "rows": [{k: v for k, v in row("acme/p@1").items() if k != "order"}]},
        "a row with an empty order": {**good, "rows": [row("acme/p@1", order="")]},
        "a row with no why": {**good, "rows": [{k: v for k, v in row("acme/p@1").items() if k != "why"}]},
        "a cap that is not an integer": {**good, "cap": "3"},
        "a negative cap": {**good, "cap": -1},
        "a closed list naming another code": {**good, "closed": ["C9"]},
    }
    for name, doc in plants.items():
        found = verdict(report_of(), doc).always
        assert found, f"{name} was not found"
    # and each of those is the only change: the good file with a cap and a closed list of the four codes is clean
    assert verdict(report_of(), {**good, "cap": 1, "closed": ["C21"]}).always == []
    # a row for a code this test does not read is left alone
    assert verdict(report_of(), {"format": 1, "rows": [row("acme/p@1", code="C11")]}).always == []


def test_a_sentence_beside_a_mate_fails_in_each_of_its_three_places():
    plug = component("generic/rj45-plug@1", mates="rj45")
    cap = component("generic/rj45-cap@1", **{"class": "cap"}, mates="rj45")
    module = component("generic/sfp-lc@1", **{"class": "transceiver"}, mates="sfp")
    doc = {"format": 1, "rows": []}
    # a part with a sentence whose slot accepts a plug
    host = component("acme/host@1", cages=[{"id": "p", "kind": "connector", "interface": "rj45", "accepts": ["generic/rj45-plug@1"]}])
    w = world(components=[plug, host], **{"part-unmated": {"acme/host@1": SENTENCE}})
    assert len(verdict(report_of(), doc, w).always) == 1
    # the same part when the slot accepts only a dust cap
    w = world(components=[plug, cap, component("acme/host@1", cages=[{"id": "p", "kind": "connector", "interface": "rj45", "accepts": ["generic/rj45-cap@1"]}])],
              **{"part-unmated": {"acme/host@1": SENTENCE}})
    assert verdict(report_of(), doc, w).always == []
    # a connectors.yaml entry with a sentence that a part mates
    w = world(components=[plug], connectors={"rj45": {"unmated": SENTENCE}})
    assert len(verdict(report_of(), doc, w).always) == 1
    assert verdict(report_of(), doc, world(components=[plug], connectors={"usb-a": {"unmated": SENTENCE}})).always == []
    # a pluggables rate sentence that a module fills; a rate no module fills is the sentence's honest use
    families = {"sfp": {"interface": "sfp", "rates": ["sfp", "sfp28"], "unmated": {"sfp28": SENTENCE}}}
    assert len(verdict(report_of(), doc, world(components=[module], families=families)).always) == 1
    rated = component("acme/sfp-plus@1", **{"class": "transceiver"}, mates="sfp", attrs={"rate": "sfp"})
    assert verdict(report_of(), doc, world(components=[rated], families=families)).always == []


def test_a_registry_sentence_under_forty_characters_fails():
    doc = {"format": 1, "rows": []}
    assert len(verdict(report_of(), doc, world(connectors={"rj45": {"unmated": "no plug exists"}})).always) == 1
    families = {"cfp2": {"interface": "cfp2", "rates": ["cfp2"], "unmated": {"cfp2": "no module"}}}
    assert len(verdict(report_of(), doc, world(families=families)).always) == 1
    families["cfp2"]["unmated"]["cfp2"] = SENTENCE
    assert verdict(report_of(), doc, world(families=families)).always == []


def test_an_empty_registry_sentence_is_read_and_fails(tmp_path):
    """The reader keeps a sentence that is present and empty, so the shape rule can fail it."""
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    (schemas / "connectors.yaml").write_text(yaml.safe_dump({"format": 1, "interfaces": {"rj45": {"unmated": ""}}}))
    (schemas / "pluggables.yaml").write_text(yaml.safe_dump({"format": 1, "families": {"cfp2": {"interface": "cfp2", "rates": ["cfp2"], "unmated": {"cfp2": ""}}}}))
    read = _tool().read_registries(schemas)
    assert len(verdict(report_of(), {"format": 1, "rows": []}, world(**read)).always) == 2
    library = tmp_path / "library" / "components" / "acme" / "p" / "v1"
    library.mkdir(parents=True)
    (library / "contract.yaml").write_text("format: 1\nname: p\nunmated: ''\n")
    assert _tool().load_unmated(tmp_path / "library") == {"acme/p@1": ""}


def test_a_part_with_both_a_row_and_a_sentence_for_one_code_fails():
    doc = {"format": 1, "rows": [row("acme/p@1", code="C20")]}
    w = world(components=[component("acme/p@1")], **{"part-unmated": {"acme/p@1": SENTENCE}})
    assert len(verdict(report_of(), doc, w).always) == 1
    # a row for a code the part's sentence is not read by is not the same code
    doc = {"format": 1, "rows": [row("acme/p@1", code="C21")]}
    assert verdict(report_of(cause("acme/p@1", "C21")), doc, w).always == []
    # and the sentence alone, or the row alone, is fine
    assert verdict(report_of(), {"format": 1, "rows": []}, w).always == []
    assert verdict(report_of(cause("acme/p@1")), {"format": 1, "rows": [row("acme/p@1")]}, world()).always == []


def test_with_no_cap_an_unrecorded_finding_a_stale_row_and_a_crash_are_printed_and_pass():
    no_cap = {"format": 1, "rows": [row("acme/stale@1")]}
    cases = {
        "an unrecorded finding": verdict(report_of(cause("acme/new@1")), {"format": 1, "rows": []}),
        "a stale row": verdict(report_of(), no_cap),
        "a crash": verdict(None, no_cap, crash="the runner exited 1"),
    }
    for name, v in cases.items():
        assert v.capped, f"{name} was not found"
        assert failures(v, no_cap) == [], f"{name} failed a file with no cap"
        assert v.printed(), name


def test_with_a_cap_each_of_the_five_fails():
    base = {"format": 1, "cap": 5, "rows": [row("acme/old@1")]}
    covered = report_of(cause("acme/old@1"))
    assert failures(verdict(covered, base), base) == []                      # the baseline of every plant below
    plants = {
        "an unrecorded finding": (report_of(cause("acme/old@1"), cause("acme/new@1")), base, None),
        "a stale row": (report_of(), base, None),
        "rows over cap": (covered, {**base, "cap": 0}, None),
        "a row for a closed code": (covered, {**base, "closed": ["C20"]}, None),
        "a runner that exits non-zero": (None, base, "the runner exited 1"),
    }
    for name, (report, doc, crash) in plants.items():
        v = verdict(report, doc, crash=crash)
        assert failures(v, doc), f"{name} did not fail with a cap"


def test_a_stale_row_is_judged_only_over_the_whole_library():
    doc = {"format": 1, "cap": 5, "rows": [row("acme/old@1")]}
    assert failures(verdict(report_of(), doc, full=True), doc)
    assert failures(verdict(report_of(), doc, full=False), doc) == []


def test_a_row_covers_its_part_on_every_device_and_a_device_row_only_its_own_causes():
    doc = {"format": 1, "cap": 5, "rows": [row("acme/p@1")]}
    two = report_of(cause("acme/p@1", device="dev-1"), cause("acme/p@1", device="dev-2"), cause("acme/p@1", device="dev-3", view="front"))
    assert failures(verdict(two, doc), doc) == []                           # a new device placing a listed part adds no row
    other_code = report_of(cause("acme/p@1", code="C22"))
    assert failures(verdict(other_code, doc), doc), "a row covers its own code only"
    own = {"format": 1, "cap": 5, "rows": [row("dev-1")]}
    mine = report_of(cause("", device="dev-1"))
    assert failures(verdict(mine, own), own) == []
    elsewhere = report_of(cause("", device="dev-2"))
    assert failures(verdict(elsewhere, own), own), "a device row covers that device's own causes only"
    placed = report_of(cause("acme/p@1", device="dev-1"))
    assert failures(verdict(placed, own), own), "a device row does not cover a part placed on the device"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_runner_that_exits_non_zero_is_a_crash_the_cap_fails(tmp_path):
    report, why = run_scan(tmp_path / "no-such-dist", tmp_path, refs=["dev"])
    assert report is None and why, "a scan of a dist that is not there must not return a report"
    capped = {"format": 1, "cap": 0, "rows": []}
    assert failures(verdict(report, capped, crash=why), capped)
    assert failures(verdict(report, {"format": 1, "rows": []}, crash=why), {"format": 1, "rows": []}) == []


def read_world(dist):
    tool = _tool()
    return {"components": json.loads((dist / "components.json").read_text())["components"], **tool.read_registries(SCHEMAS),
            "part-unmated": tool.load_unmated(LIBRARY)}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.skipif(not (DIST / "devices.json").exists(), reason="library/dist not built - run ./build.sh")
def test_the_port_records_hold_over_the_whole_library(tmp_path):
    """The scan over every device of the build, against `library/conformance-exceptions.yaml` and the `unmated` sentences."""
    started = time.monotonic()
    doc = yaml.safe_load(RECORDS.read_text())
    report, crash = run_scan(DIST, tmp_path)
    v = judge(report, doc, read_world(DIST), crash=crash, full=True)
    found, _threw = causes_of(report) if report else ([], [])
    took = time.monotonic() - started
    print(f"\nport-usable records: {len(found)} causes over {len(report['parts']) if report else 0} devices in {took:.1f} s; "
          f"{len(doc.get('rows') or [])} rows, cap {doc.get('cap', 'none (reporting only)')}; {len(v.printed())} lines to print")
    for line in v.printed()[:60]:
        print(f"  {line}")
    if report:
        assert report["parts"] and all(row["usable"] for p in report["parts"] for row in p["configs"]), "the scan walked nothing"
    assert failures(v, doc) == [], failures(v, doc)[:20]
