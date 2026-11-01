"""The part-conformance prototype finds the faults it is for, and only those.

`spec/tools/dev/part_conformance.py` (docs/part-conformance-design.md) runs two
checks over a built part. These tests give it a library built here, a few lines
of JSON in the shape the build writes, so the expected findings do not depend
on what a live device lacks the day this runs:

- a good part is clean; each planted fault is found, under its code, and
  planting it is the only change;
- the same runner, pointed at the real build, walks something: it is not a
  check that passes because it looked at nothing.
"""
import copy
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "spec/tools/dev/part_conformance.py"
DIST = ROOT / "library" / "dist"


def _need_node():
    if shutil.which("node") is None:
        pytest.skip("node not installed")


def comp(ref, **rest):
    ns, tail = ref.split("/")
    name, major = tail.split("@")
    return {"ns": ns, "name": name, "major": f"v{major}", "class": "port", "kind": "component", "parts": [], "cages": [],
            "bays": {}, "attrs": {}, "fields": {}, "faces": None, **rest}


JACK = comp("std/rj45@2", attrs={"media": "rj45", "connector": "rj45"})
PLUG = comp("generic/rj45-plug@1", attrs={"media": "rj45", "connector": "rj45"}, mates="rj45")
LAMP = comp("common/led-dot@1", **{"class": "led"})


def slot(pid, accepts=("generic/rj45-plug@1",)):
    return {"id": pid, "kind": "connector", "interface": "rj45", "media": None, "bores": [], "accepts": list(accepts),
            "default": None, "at": [0, 0], "mate": [1, 1], "rotate": None}


def panel(back):
    """A two-jack coupler; `back` gives it a rear that carries two ends."""
    face = comp("acme/pnl@1", **{"class": "adapter-panel", "kind": "module"},
                parts=[{"id": "p1", "ref": "std/rj45@2"}, {"id": "p2", "ref": "std/rj45@2"}],
                cages=[slot("p1"), slot("p2")], faces={"rear": "acme/pnl-rear@1"} if back else None)
    rear = comp("acme/pnl-rear@1", **{"class": "adapter-panel"}, parts=[{"id": "b1", "ref": "std/rj45@2"}, {"id": "b2", "ref": "std/rj45@2"}],
                cages=[slot("b1"), slot("b2")])
    return [face, rear] if back else [face]


def element(pid, cls="port", x=10, y=5, **extra):
    return {"id": pid.replace("/", "--"), "path": pid, "class": cls, "parent": None, "box": {"x": x, "y": y, "w": 12, "h": 10}, **extra}


def build(tmp_path, *, lamp_states_in_catalogue=True, back=True, tilt=False, mate=True):
    """A library of one 1U device `dev` with two jacks, a lamp and a bay for the coupler."""
    mating = {"connection-points": {"mate": {"at": [6, 5], "dir": "front", "face": [16, 10]}}} if mate else {}
    front = [{"id": "chassis-faceplate", "path": "chassis", "class": "chassis", "parent": None, "box": {"x": 0, "y": 0, "w": 436, "h": 43.7}},
             element("port-1", x=30, **mating), element("port-2", x=60, **mating),
             element("led-sys", "led", x=100, y=3, states=["off", "ok", "fault"])]
    dist = tmp_path / "dist"
    dist.mkdir()
    def put(name, value):
        (dist / name).write_text(json.dumps(value))
    put("components.json", {"components": [JACK, PLUG, LAMP, *panel(back)]})
    put("rack.json", {"format": 1, "devices": {"dev": {"ru": 1, "w": 436, "h": 43.7, "d": 300, "mount": "rack", "kind": "switch",
                                                        "manufacturer": "Acme", "model": "DEV", "default": "base", "configs": ["base"]}}})
    put("dev.configs.json", {
        "default": "base", "pdu-class": None, "bays": {"front": [{"id": "bay-1", "accepts": ["acme/pnl@1"], "default": None, "group": "b"}], "rear": []},
        "cages": {"front": [slot("port-1"), slot("port-2")], "rear": []},
        "configs": [{"name": "base", "files": {"front": "dev.base.front.svg", "rear": "dev.base.rear.svg"}, "bays": {}, "occupants": {},
                     "states": {"led-sys": ["off", "ok", "fault"]} if lamp_states_in_catalogue else {}, "names": {}, "slots": [], "mount-points": []}]})
    rear = [{"id": "chassis-faceplate", "path": "chassis", "class": "chassis", "parent": None, "box": {"x": 0, "y": 0, "w": 436, "h": 43.7}}]
    for view, els in (("front", front), ("rear", rear)):
        put(f"dev.base.{view}.elements.json", {"device": "dev", "config": "base", "view": view, "viewBox": [0, 0, 436, 43.7], "elements": els})
        tilted = '<g data-path="port-1" data-tilt="30" data-tilt-on="x"></g>' if tilt and view == "front" else ""
        (dist / f"dev.base.{view}.svg").write_text(f'<svg><style>.state-ok{{fill:#2c2}}.state-off{{fill:#555}}.state-fault{{fill:#c22}}</style>{tilted}</svg>')
    return dist


def run(dist, tmp_path, *, skip=()):
    out = tmp_path / "report.json"
    p = subprocess.run([sys.executable, str(TOOL), "--dist", str(dist), "--refs", "dev", "--out", str(out), "--max-ends", "20",
                        *(["--skip", *skip] if skip else [])], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-1500:] + p.stdout[-1500:]
    report = json.loads(out.read_text())
    codes = {}
    part = report["parts"][0]
    for f in (part.get("occupants") or {}).get("found", []):
        codes.setdefault(f["code"], []).append(f)
    for row in part["configs"]:
        for check in ("settings", "cabling"):
            for f in row[check]["found"]:
                codes.setdefault(f["code"], []).append(f)
    return report, codes


@pytest.fixture(scope="module", autouse=True)
def node():
    _need_node()


def blocking(codes):
    return sorted(c for c in codes if c not in ("C15", "C14"))   # C15 is the kit's, not the part's: asserted apart


def test_a_good_part_is_clean(tmp_path):
    report, codes = run(build(tmp_path), tmp_path)
    assert blocking(codes) == [], codes
    row = report["parts"][0]["configs"][0]
    # it walked something: two jacks offered, drawn, judged on both rails; one lamp, set
    assert row["cabling"]["counts"]["offered"] == 2 and row["cabling"]["counts"]["judged"] >= 4, row["cabling"]["counts"]
    assert row["settings"]["counts"]["set"] == 3 and row["settings"]["counts"]["drawn"] == 1, row["settings"]["counts"]
    assert report["parts"][0]["occupants"]["counts"]["occupants"] == 1


def test_a_lamp_the_catalogue_does_not_know_is_found_both_ways(tmp_path):
    """The Explorer reads the drawing; the agent reads the catalogue. A lamp only the first knows is settable one way."""
    report, codes = run(build(tmp_path, lamp_states_in_catalogue=False), tmp_path)
    assert {"S1", "S4"} <= set(codes), codes
    assert codes["S4"][0]["n"] == 3 and "declares no state" in codes["S4"][0]["examples"][0]
    # and nothing else changed
    assert blocking(codes) == ["S1", "S4"], codes


def test_a_coupler_with_one_side_is_found(tmp_path):
    report, codes = run(build(tmp_path, back=False), tmp_path)
    assert blocking(codes) == ["C11"], codes
    assert "acme/pnl" in codes["C11"][0]["examples"][0] or "PNL" in codes["C11"][0]["text"]


def test_an_angled_port_with_no_axis_is_reported_not_blocked(tmp_path):
    report, codes = run(build(tmp_path, tilt=True), tmp_path)
    assert "C10" in codes and report["summary"]["C10"]["level"] == "standin", codes
    assert blocking(codes) == ["C10"], "the stand-in is reported; nothing else is wrong with the part"
    assert "30" in codes["C10"][0]["text"], "it names the angle the drawing declares"


def test_an_end_with_no_mating_point_is_a_stand_in(tmp_path):
    report, codes = run(build(tmp_path, mate=False), tmp_path)
    assert "C14" in codes and report["summary"]["C14"]["level"] == "standin"
    assert blocking(codes) == [], codes


def test_a_made_up_end_is_not_silently_accepted(tmp_path):
    report, codes = run(build(tmp_path), tmp_path)
    assert "C15" in codes, "a cable to a port that does not exist was accepted and nothing said so"
    assert report["summary"]["C15"]["level"] == "block", "D-0035: a made-up end is a blocking code"


def test_the_report_is_written_to_out_and_names_its_timing(tmp_path):
    report, _ = run(build(tmp_path), tmp_path)
    assert report["seconds"] > 0 and set(report["timing"]) >= {"settings", "cabling", "occupants", "configs"}
    assert "summary" in report


# ── the port-usable codes: C19 to C22, judged in the scan mode ──────────────────────────────────────
#
# Every test builds the one library below, changes one thing, and reads what the scan finds. A baseline
# with the fault absent is clean; the same world with the fault planted is found, under its code.

SENTENCE = "a printed marking on the panel; it takes no cable, cord or lug"       # at least 40 characters
CFP2 = {"interface": "cfp2", "rates": ["cfp2"], "source": "a test family"}
SFP = {"interface": "sfp", "rates": ["sfp", "sfp-plus", "sfp28"], "source": "a test family"}
DEV_REF = "std/rj45@2:1.0.0"


def registries(tmp_path, *, connectors=None, families=None):
    """A schemas folder holding the two registries the runner reads."""
    folder = tmp_path / "schemas"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "connectors.yaml").write_text(yaml.safe_dump({"format": 1, "interfaces": connectors or {"rj45": {"standard": "rj45"}}}))
    (folder / "pluggables.yaml").write_text(yaml.safe_dump({"format": 1, "families": families or {"cfp2": CFP2, "sfp": SFP}}))
    return folder


def contract(tmp_path, ref, **fields):
    """A contract in a library folder: only what the runner reads of it (`unmated`, the rest for the family file)."""
    ns, tail = ref.split("/")
    name, major = tail.split("@")
    folder = tmp_path / "library" / "components" / ns / name / f"v{major}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "contract.yaml").write_text(yaml.safe_dump({"format": 1, "kind": "component", "name": name, "version": f"{major}.0.0", **fields}))
    return tmp_path / "library"


def world(tmp_path, *, comps, front=(), rear=(), cages=(), rear_cages=(), cfgs=None, bays=None):
    """A dist of one device `dev`; `cfgs` maps a configuration name to its {view: [elements]}."""
    cfgs = cfgs or {"base": {"front": list(front), "rear": list(rear)}}
    dist = tmp_path / "dist"
    dist.mkdir(parents=True)
    def put(name, value):
        (dist / name).write_text(json.dumps(value))
    put("components.json", {"components": [JACK, PLUG, *comps]})
    put("rack.json", {"format": 1, "devices": {"dev": {"ru": 1, "w": 436, "h": 43.7, "d": 300, "mount": "rack", "kind": "switch",
                                                        "manufacturer": "Acme", "model": "DEV", "default": next(iter(cfgs)), "configs": list(cfgs)}}})
    rows = []
    chassis = {"id": "chassis-faceplate", "path": "chassis", "class": "chassis", "parent": None, "box": {"x": 0, "y": 0, "w": 436, "h": 43.7}}
    for name, views in cfgs.items():
        files = {}
        for view in ("front", "rear"):
            files[view] = f"dev.{name}.{view}.svg"
            put(f"dev.{name}.{view}.elements.json", {"device": "dev", "config": name, "view": view, "viewBox": [0, 0, 436, 43.7],
                                                     "elements": [chassis, *views.get(view, [])]})
            (dist / files[view]).write_text("<svg></svg>")
        rows.append({"name": name, "files": files, "bays": dict(bays or {}), "occupants": {}, "states": {}, "names": {}, "slots": [], "mount-points": []})
    put("dev.configs.json", {"default": next(iter(cfgs)), "pdu-class": None, "bays": {"front": [], "rear": []},
                             "cages": {"front": list(cages), "rear": list(rear_cages)}, "configs": rows})
    return dist


def scan(dist, tmp_path, *, schemas=None, library=None, refs=("dev",), extra=()):
    out = tmp_path / "scan.json"
    p = subprocess.run([sys.executable, str(TOOL), "--dist", str(dist), "--scan", "--refs", *refs, "--out", str(out),
                        "--library", str(library or tmp_path / "library"), "--schemas", str(schemas or registries(tmp_path)), *extra],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-1500:] + p.stdout[-1500:]
    return json.loads(out.read_text())


def usable(report):
    """{code: [finding]} over every configuration of every part of a scan report."""
    codes = {}
    for part in report["parts"]:
        for row in part["configs"]:
            assert "cabling" not in row and "settings" not in row, "the scan lays no cable and sets no state"
            for f in row["usable"]["found"]:
                codes.setdefault(f["code"], []).append({**f, "cfg": row["cfg"]})
    return codes


def causes(report, code):
    return [c for f in usable(report).get(code, []) for c in f["causes"]]


def test_c21_finds_a_connector_slot_whose_accepts_hold_no_plug(tmp_path):
    cap = comp("generic/rj45-cap@1", **{"class": "cap"}, mates="rj45")
    jack = comp("std/rj45@2", interface="rj45")
    drawn = [element("port-1", "port", ref=DEV_REF)]
    good = scan(world(tmp_path / "a", comps=[cap, jack], front=drawn, cages=[slot("port-1", ["generic/rj45-plug@1", "generic/rj45-cap@1"])]), tmp_path / "a")
    assert usable(good) == {}, usable(good)
    bad = scan(world(tmp_path / "b", comps=[cap, jack], front=drawn, cages=[slot("port-1", ["generic/rj45-cap@1"])]), tmp_path / "b")
    assert sorted(usable(bad)) == ["C21"], usable(bad)
    assert [(c["part"], c["path"]) for c in causes(bad, "C21")] == [("std/rj45@2", "port-1")]


def test_c21_lets_off_a_plug_a_cover_mount_and_an_interface_with_a_sentence(tmp_path):
    jack = comp("std/rj45@2", interface="rj45")
    for name, iface, accepts, sentence in (("plug", "rj45", ["generic/rj45-plug@1"], None), ("cover", "guard", [], None),
                                           ("sentence", "rj45x", [], SENTENCE), ("none", "rj45", [], None)):
        folder = tmp_path / name
        folder.mkdir()
        schemas = registries(folder, connectors={"rj45": {"standard": "rj45"}, "guard": {"cover": True},
                                                 "rj45x": ({"unmated": sentence} if sentence else {})})
        dist = world(folder, comps=[jack], front=[element("port-1", "port", ref=DEV_REF)], cages=[{**slot("port-1", accepts), "interface": iface}])
        found = usable(scan(dist, folder, schemas=schemas))
        assert (sorted(found) == ["C21"]) == (name == "none"), (name, found)
    # the sentence is the only difference between `sentence` and a slot that is found
    folder = tmp_path / "bare"
    folder.mkdir()
    dist = world(folder, comps=[jack], front=[element("port-1", "port", ref=DEV_REF)], cages=[{**slot("port-1", []), "interface": "rj45x"}])
    assert sorted(usable(scan(dist, folder, schemas=registries(folder, connectors={"rj45": {"standard": "rj45"}, "rj45x": {"standard": "rj45"}})))) == ["C21"]


def test_c21_on_a_cage_finds_no_module_unless_the_family_has_a_sentence_for_the_rate(tmp_path):
    cage_part = comp("std/cfp2@1", interface="cfp2")
    module = comp("generic/cfp2-lc@1", **{"class": "transceiver"}, mates="cfp2")
    cable = comp("generic/cfp2-cable@1", mates="cfp2")                                  # a cable end is class port
    cage = lambda accepts: {"id": "port-1", "kind": "cage", "interface": "cfp2", "media": "cfp2", "bores": [], "accepts": accepts,
                            "default": None, "at": [0, 0], "mate": [1, 1], "rotate": None}
    drawn = [element("port-1", "port", ref="std/cfp2@1:1.0.0")]
    results = {}
    for name, accepts, families in (("empty", [], {"cfp2": CFP2}),
                                    ("sentence", [], {"cfp2": {**CFP2, "unmated": {"cfp2": SENTENCE}}}),
                                    ("other-rate", [], {"cfp2": {**CFP2, "rates": ["cfp", "cfp2"], "unmated": {"cfp": SENTENCE}}}),
                                    ("module", ["generic/cfp2-lc@1"], {"cfp2": CFP2}),
                                    ("cable", ["generic/cfp2-cable@1"], {"cfp2": CFP2})):
        folder = tmp_path / name
        folder.mkdir()
        dist = world(folder, comps=[cage_part, module, cable], front=drawn, cages=[cage(accepts)])
        results[name] = sorted(usable(scan(dist, folder, schemas=registries(folder, families=families))))
    assert results == {"empty": ["C21"], "sentence": [], "other-rate": ["C21"], "module": [], "cable": []}, results


def test_the_scan_counts_the_cages_that_accept_no_module_at_their_own_rate(tmp_path):
    cage_part = comp("std/sfp@1", interface="sfp")
    cage = {"id": "port-1", "kind": "cage", "interface": "sfp", "media": "sfp28", "bores": [], "default": None, "at": [0, 0], "mate": [1, 1], "rotate": None}
    counts = {}
    for name, module in (("lower", comp("acme/sfp-plus-sr@1", **{"class": "transceiver"}, mates="sfp", attrs={"rate": "sfp-plus"})),
                         ("lower-port", comp("acme/sfp-plus-dac@1", mates="sfp", attrs={"rate": "sfp-plus"})),
                         ("off-ladder", comp("acme/qsfp-sr@1", **{"class": "transceiver"}, mates="sfp", attrs={"rate": "qsfp"})),
                         ("higher", comp("acme/sfp56-sr@1", **{"class": "transceiver"}, mates="sfp", attrs={"rate": "sfp56"})),
                         ("own", comp("acme/sfp28-sr@1", **{"class": "transceiver"}, mates="sfp", attrs={"rate": "sfp28"})),
                         ("generic", comp("generic/sfp-lc@1", **{"class": "transceiver"}, mates="sfp"))):
        folder = tmp_path / name
        folder.mkdir()
        ref = f"{module['ns']}/{module['name']}@1"
        dist = world(folder, comps=[cage_part, module], front=[element("port-1", "port", ref="std/sfp@1:1.0.0")], cages=[{**cage, "accepts": [ref]}])
        report = scan(dist, folder)
        assert usable(report) == {}, (name, usable(report))
        counts[name] = report["scan"]["cages-below-own-rate"]
    assert counts == {"lower": 1, "lower-port": 1, "off-ladder": 0, "higher": 0, "own": 0, "generic": 0}, counts


def test_c22_finds_a_port_part_that_presents_no_interface_unless_it_composes_one(tmp_path):
    bare = comp("acme/bare-port@1")
    composing = comp("acme/bare-port@1", parts=[{"id": "j", "ref": "std/rj45@2"}])
    jack = comp("std/rj45@2", interface="rj45")
    drawn = [element("port-1", "port", ref="acme/bare-port@1:1.0.0")]
    good = scan(world(tmp_path / "a", comps=[composing, jack], front=drawn), tmp_path / "a")
    assert usable(good) == {}, usable(good)
    bad = scan(world(tmp_path / "b", comps=[bare, jack], front=drawn), tmp_path / "b")
    assert sorted(usable(bad)) == ["C22"], usable(bad)
    assert [c["part"] for c in causes(bad, "C22")] == ["acme/bare-port@1"]


def test_c22_lets_off_a_plug_and_a_part_carrying_a_sentence(tmp_path):
    drawn = [element("port-1", "port", ref="acme/p@1:1.0.0")]
    for name, part, fields in (("mates", comp("acme/p@1", mates="rj45"), {}),
                               ("occupies", comp("acme/p@1", behaviour="occupies"), {}),
                               ("sentence", comp("acme/p@1"), {"unmated": SENTENCE}),
                               ("neither", comp("acme/p@1"), {})):
        folder = tmp_path / name
        folder.mkdir()
        library = contract(folder, "acme/p@1", **fields)
        found = usable(scan(world(folder, comps=[part], front=drawn), folder, library=library))
        assert (sorted(found) == ["C22"]) == (name == "neither"), (name, found)


def test_c20_reports_the_part_it_used_to_skip_as_a_marking_unless_it_carries_a_sentence(tmp_path):
    marking = comp("acme/rps-port@1", **{"class": "inlet"})
    drawn = [element("rps", "inlet", ref="acme/rps-port@1:1.0.0")]
    bad = scan(world(tmp_path / "a", comps=[marking], front=drawn), tmp_path / "a")
    assert sorted(usable(bad)) == ["C20"], usable(bad)
    assert [c["part"] for c in causes(bad, "C20")] == ["acme/rps-port@1"]
    library = contract(tmp_path / "b", "acme/rps-port@1", unmated=SENTENCE)
    assert usable(scan(world(tmp_path / "b", comps=[marking], front=drawn), tmp_path / "b", library=library)) == {}


def test_c19_lets_off_a_supply_whose_part_carries_a_sentence(tmp_path):
    supply = comp("acme/psu@1", **{"class": "psu"})
    drawn = [element("psu-1", "psu", ref="acme/psu@1:1.0.0")]
    bad = scan(world(tmp_path / "a", comps=[supply], front=drawn), tmp_path / "a")
    assert sorted(usable(bad)) == ["C19"], usable(bad)
    assert [c["part"] for c in causes(bad, "C19")] == ["acme/psu@1"]
    library = contract(tmp_path / "b", "acme/psu@1", unmated=SENTENCE)
    assert usable(scan(world(tmp_path / "b", comps=[supply], front=drawn), tmp_path / "b", library=library)) == {}


def test_every_finding_lists_every_cause_uncapped_with_the_part_that_draws_it(tmp_path):
    bare = comp("acme/lug@1", **{"class": "inlet"})
    five = [element(f"in-{i}", "inlet", x=20 + 30 * i, ref="acme/lug@1:1.0.0") for i in range(5)]
    own = element("own", "inlet", x=400)                                    # the device's own drawing: no ref
    report = scan(world(tmp_path, comps=[bare], front=[*five, own]), tmp_path)
    found = usable(report)
    assert sorted(found) == ["C20"] and len(found["C20"]) == 1, found
    got = found["C20"][0]["causes"]
    assert len(got) == 6, got                                               # five bare inlets and the device's own: no cap of three
    assert all(set(c) == {"part", "device", "cfg", "view", "path"} for c in got), got
    assert sorted((c["part"], c["path"]) for c in got) == sorted([("acme/lug@1", f"in-{i}") for i in range(5)] + [("", "own")])
    assert {(c["device"], c["cfg"], c["view"]) for c in got} == {("dev", "base", "front")}


def test_the_part_of_a_skin_art_element_is_the_component_whose_skin_draws_it(tmp_path):
    inlet = comp("acme/art-inlet@1", **{"class": "inlet"})
    port = comp("acme/art-port@1")
    art = [element("panel/art-1", "inlet", ref="acme/art-inlet@1:1.0.0"), element("panel/art-2", "port", ref="acme/art-port@1:1.0.0")]
    report = scan(world(tmp_path, comps=[inlet, port], front=art), tmp_path)
    assert [(c["part"], c["path"]) for c in causes(report, "C20")] == [("acme/art-inlet@1", "panel/art-1")]
    assert [(c["part"], c["path"]) for c in causes(report, "C22")] == [("acme/art-port@1", "panel/art-2")]


def test_a_published_slot_the_configuration_does_not_draw_is_not_judged(tmp_path):
    jack = comp("std/rj45@2", interface="rj45")
    drawn = [element("port-1", "port", ref=DEV_REF)]
    slots = [slot("port-1", []), slot("port-2", [])]                         # cages[] lists a slot of any configuration
    bad = scan(world(tmp_path / "a", comps=[jack], front=drawn, cages=slots), tmp_path / "a")
    assert [c["path"] for c in causes(bad, "C21")] == ["port-1"], "only the drawn slot is on this device as built"
    both = [element("port-1", "port", ref=DEV_REF), element("port-2", "port", ref=DEV_REF)]
    assert [c["path"] for c in causes(scan(world(tmp_path / "b", comps=[jack], front=both, cages=slots), tmp_path / "b"), "C21")] == ["port-1", "port-2"]


def test_c22_finds_a_drawn_port_whose_part_the_build_does_not_hold(tmp_path):
    drawn = [element("port-1", "port", ref="acme/missing@1:1.0.0")]
    report = scan(world(tmp_path, comps=[], front=drawn), tmp_path)
    assert [c["part"] for c in causes(report, "C22")] == ["acme/missing@1"]


def test_the_scan_judges_every_configuration_and_lays_no_cable(tmp_path):
    bare = comp("acme/lug@1", **{"class": "inlet"})
    clean = {"front": [], "rear": []}
    cfgs = {f"c{i}": clean for i in range(3)}
    cfgs["c3"] = {"front": [element("in-1", "inlet", ref="acme/lug@1:1.0.0")], "rear": []}     # beyond the default three
    # each configuration draws other files, so none is folded into another
    cfgs = {name: {"front": list(v["front"]) + [element(f"marker-{name}", "led", x=300)], "rear": []} for name, v in cfgs.items()}
    dist = world(tmp_path, comps=[bare], cfgs=cfgs)
    report = scan(dist, tmp_path)
    assert [row["cfg"] for row in report["parts"][0]["configs"]] == ["c0", "c1", "c2", "c3"]
    assert [c["cfg"] for c in causes(report, "C20")] == ["c3"], usable(report)
    # the cabling run, at its default three configurations, never reaches the fourth
    normal = tmp_path / "normal.json"
    subprocess.run([sys.executable, str(TOOL), "--dist", str(dist), "--refs", "dev", "--out", str(normal), "--skip", "settings", "occupants"],
                   capture_output=True, text=True, check=True)
    assert [r["cfg"] for r in json.loads(normal.read_text())["parts"][0]["configs"]] == ["c0", "c1", "c2"]


def families_report(refs_and_devices):
    """A scan report holding one C20 cause per (part, device)."""
    parts = {}
    for ref, device in refs_and_devices:
        row = parts.setdefault(device, {"ref": device, "configs": [{"cfg": "base", "usable": {"found": [{"code": "C20", "text": "t", "n": 0, "causes": []}]}}]})
        row["configs"][0]["usable"]["found"][0]["causes"].append({"part": ref, "device": device, "cfg": "base", "view": "rear", "path": "x"})
        row["configs"][0]["usable"]["found"][0]["n"] += 1
    return {"dist": "dist", "parts": list(parts.values())}


def test_by_family_assigns_by_the_five_rules_in_order(tmp_path):
    spec = {
        "acme/mini@1": {"class": "port", "interface": "mini-usb-b"},                                  # 1: an interface
        "acme/ac-psu@1": {"class": "psu", "attrs": {"input": "ac"}},                                  # 2: a supply, by its attrs
        "acme/dc-psu@1": {"class": "psu", "attrs": {"input": "dc"}},
        "acme/stud@1": {"class": "ground"},                                                           # 3: a ground part
        "acme/vcp-port@1": {"class": "port"},                                                         # 4: a name
        "acme/console-jack@1": {"class": "port"},                                                     # 4: a name whose family has commas in it
        "acme/odd@1": {"class": "port"},                                                           # 5: none of them
        "acme/dc-both@1": {"class": "psu", "interface": "iec-c14", "attrs": {"input": "dc"}},        # rules 1 and 2 match: 1 wins
        "acme/dc-ground@1": {"class": "ground"},                                                      # rules 3 and 4 match: 3 wins
        "acme/pole@1": {"class": "screw", "interface": "terminal-stud"},                              # the interface's own exception for a class
    }
    library = tmp_path / "library"
    for ref, fields in spec.items():
        contract(tmp_path, ref, provenance={"existence": "datasheet - the guide lists it on the rear panel of the box", "size": "estimated"}, **fields)
    report = tmp_path / "scan.json"
    report.write_text(json.dumps(families_report([(ref, f"dev-{i}") for i, ref in enumerate(spec)])))
    out = tmp_path / "families.json"
    p = subprocess.run([sys.executable, str(TOOL), "--by-family", str(report), "--library", str(library), "--out", str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-1500:]
    got = json.loads(out.read_text())["families"]
    where = {part["ref"]: name for name, fam in got.items() for part in fam["parts"]}
    assert where == {"acme/mini@1": "console (RJ45, USB, Mini-B, DB9)", "acme/ac-psu@1": "power inlets (AC)", "acme/dc-psu@1": "DC terminals and barrels",
                     "acme/stud@1": "ground and earth studs", "acme/vcp-port@1": "stack and virtual chassis", "acme/odd@1": "other",
                     "acme/dc-both@1": "power inlets (AC)", "acme/dc-ground@1": "ground and earth studs",
                     "acme/pole@1": "DC terminals and barrels", "acme/console-jack@1": "console (RJ45, USB, Mini-B, DB9)"}, where
    first = next(p for p in got["other"]["parts"] if p["ref"] == "acme/odd@1")
    assert first["provenance"]["existence"].startswith("datasheet - the guide lists") and first["class"] == "port"
    assert got["other"]["vendors"] == ["acme"] and got["other"]["devices"] == ["dev-6"]


def by_family_where(tmp_path, spec):
    """`--by-family` over one C20 cause per part of `spec` ({ref: contract fields}), with the real family file:
    {ref: family name}."""
    for ref, fields in spec.items():
        contract(tmp_path, ref, **fields)
    report = tmp_path / "scan.json"
    report.write_text(json.dumps(families_report([(ref, f"dev-{i}") for i, ref in enumerate(spec)])))
    out = tmp_path / "families.json"
    p = subprocess.run([sys.executable, str(TOOL), "--by-family", str(report), "--library", str(tmp_path / "library"), "--out", str(out)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-1500:]
    got = json.loads(out.read_text())["families"]
    return {part["ref"]: name for name, fam in got.items() for part in fam["parts"]}


KEY_FAMILIES = {
    "flexstack": "stack and virtual chassis", "stackwise-480": "stack and virtual chassis",
    "stackpower": "stack and virtual chassis", "ex4200-vcp": "stack and virtual chassis",
    "cisco-rps2300": "RPS", "ex3300-rps": "RPS",
    "rj45": "console (RJ45, USB, Mini-B, DB9)",
    "screw-terminal-2": "DC terminals and barrels", "screw-terminal-4": "DC terminals and barrels",
    "terminal-381-5": "DC terminals and barrels", "orv3-busbar": "DC terminals and barrels",
    "wire-wrap-3": "other", "screw-terminal-5": "other", "terminal-350-6": "other",
}


def test_by_family_places_each_stack_rps_console_terminal_and_alarm_key_in_its_family(tmp_path):
    spec, want = {}, {}
    for i, (key, family) in enumerate(KEY_FAMILIES.items()):
        # a key mapped to "other" gets a name the DC pattern would take, so only the key can keep it out of DC
        ref = f"acme/terminal-x{i}@1" if family == "other" else f"acme/p-{i}@1"
        spec[ref] = {"class": "port", "interface": key}
        want[ref] = family
    assert by_family_where(tmp_path, spec) == want


def test_by_family_keeps_a_busbar_out_of_usb_and_a_usb_port_in_it(tmp_path):
    # "busbar" contains "usb"
    where = by_family_where(tmp_path, {"acme/input-feed-busbar@1": {"class": "port"},
                                       "acme/some-bus-bar@1": {"class": "port"},
                                       "acme/usb-a-port@1": {"class": "port"}})
    assert where == {"acme/input-feed-busbar@1": "DC terminals and barrels",
                     "acme/some-bus-bar@1": "DC terminals and barrels",
                     "acme/usb-a-port@1": "USB"}


def test_by_family_sends_a_supply_to_dc_by_its_role_or_a_dc_word_of_its_name(tmp_path):
    where = by_family_where(tmp_path, {
        "acme/pwr-do@1": {"class": "psu", "attrs": {"role": "dc-power-supply"}},          # DC by its role, no dc in the name
        "acme/a9k-pwr-2kw-dc@1": {"class": "psu", "attrs": {"role": "power-module"}},     # DC by a word of its name
        "acme/x-hvacdc@1": {"class": "psu", "attrs": {"role": "hvac-dc-power-supply"}},  # dc is not a word of it
        "acme/dcs201-psu-ac@1": {"class": "psu", "attrs": {"role": "power-supply"}},      # nor of this
        "acme/plain-psu@1": {"class": "psu", "attrs": {"input": "ac"}},
    })
    assert where == {"acme/pwr-do@1": "DC terminals and barrels", "acme/a9k-pwr-2kw-dc@1": "DC terminals and barrels",
                     "acme/x-hvacdc@1": "power inlets (AC)", "acme/dcs201-psu-ac@1": "power inlets (AC)",
                     "acme/plain-psu@1": "power inlets (AC)"}


DC_NAMED_SUPPLIES = ("cisco/a9k-pwr-2kw-dc@1", "juniper/jpsu-550-c-dc-afi@1", "juniper/jpsu-550-c-dc-afo@1",
                     "juniper/ex4100-h-24f-dc-psu@1", "juniper/ex4100-h-24mp-dc-psu@1", "juniper/mx2000-psm-dc-v@1",
                     "juniper/qfx10002-jpsu-1600w-dc-afo@1", "juniper/qfx524x-2ru-pwr-do@1")


def test_every_dc_supply_of_the_real_library_is_in_the_dc_family_and_the_hvdc_one_is_not():
    loader = importlib.util.spec_from_file_location("part_conformance", TOOL)
    module = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(module)
    families = yaml.safe_load(module.FAMILIES.read_text())
    got, says_dc = {}, []
    for path in sorted((ROOT / "library/components").glob("*/*/v*/contract.yaml")):
        text = path.read_text()
        if "class: psu" not in text:
            continue
        c = yaml.safe_load(text)
        if c.get("class") != "psu":
            continue
        name = path.parts[-3]
        ref = f"{path.parts[-4]}/{name}@{path.parts[-2][1:]}"
        got[ref] = module.family_of(families, c, name)
        if c.get("interface") in families["interfaces"]:
            continue            # placed by rule 1, not by the supply rule
        if (c.get("attrs") or {}).get("role") == "dc-power-supply" or "dc" in name.split("-"):
            says_dc.append(ref)
    dc = families["psu"]["dc"]
    stray = [ref for ref in says_dc if got[ref] != dc]
    print("supplies that say DC and are not in the DC family:", stray)
    assert not stray, f"supplies that say DC and are not in the DC family: {stray}"
    for ref in DC_NAMED_SUPPLIES:
        assert got[ref] == dc, f"{ref} is in {got[ref]}"
    assert got["juniper/mx304-psu-hvacdc@1"] == families["psu"]["ac"]


def test_every_family_the_family_file_names_is_one_of_its_families():
    families = yaml.safe_load((ROOT / "spec/tools/dev/port_families.yaml").read_text())
    known, named = set(families["families"]), set()
    for entry in families["interfaces"].values():
        named.add(entry if isinstance(entry, str) else entry["family"])
        if isinstance(entry, dict):
            named.update((entry.get("by-class") or {}).values())
    named.update(families["classes"].values())
    named.update(p["family"] for p in families["name-patterns"])
    named.update([families["psu"]["ac"], families["psu"]["dc"], families["other"]])
    assert named <= known, f"not in `families`: {sorted(named - known)}"


@pytest.mark.skipif(not (DIST / "devices.json").exists(), reason="library/dist not built - run ./build.sh")
def test_on_the_real_build_it_walks_ends_and_states(tmp_path):
    out = tmp_path / "real.json"
    p = subprocess.run([sys.executable, str(TOOL), "--dist", str(DIST), "--refs", "fhd-1ube", "s9700-53dx", "--max-configs", "1",
                        "--out", str(out)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-1500:]
    r = json.loads(out.read_text())
    switch = next(x for x in r["parts"] if x["ref"] == "s9700-53dx")["configs"][0]
    assert switch["cabling"]["counts"]["offered"] > 40 and switch["cabling"]["counts"]["judged"] >= 6
    assert switch["settings"]["counts"]["drawn"] > 40
    assert not [f for f in switch["cabling"]["found"] if f["code"] == "C0"], "the check threw"
