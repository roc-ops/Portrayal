"""A fan or supply in a drawing states which way the build it is drawn in breathes (#1329).

A configuration's airflow reaches the drawing as `data-airflow` on the SVG root. The fan and the supply
inside it said something else, or nothing: a part states its own airflow by convention (`attrs.airflow`),
a shared part keeps saying `front-to-back` in a back-to-front build that only recolours it, and 179
fans and supplies state nothing. A tool filtering by airflow could not check that the fans and supplies
drawn in a build are the ones for that direction.

Three things are pinned here:

* the Edgecore back-to-front builds that recolour a shared part also say `airflow: back-to-front` in
  that part's `component-attrs`, as the Cisco and UfiSpace builds already do (data);
* every `class: fan` and `class: psu` group in a compiled face carries `data-config-airflow`, the
  configuration's airflow as `manifest.config_airflow` resolves it, and nothing else carries it - the
  part's own `data-airflow` is left as the part and the build state it (build output);
* the components README names the values and every word a fan or supply uses (documentation).

Each check is a function that returns its problems, so a test can run it on a deliberately wrong copy
and see it fail: the planted violation is part of the test.
"""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from portrayal.manifest import config_airflow

SPEC = Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
LIB = ROOT / "library"
DIST = LIB / "dist"
RENDER = SPEC / "tools/portrayal/render.py"
README = LIB / "components/README.md"

B2F, F2B = "back-to-front", "front-to-back"
DIRECTIONS = {F2B, B2F}

# the five builds the rendered checks read: device -> configurations drawn
RENDERED = {
    "edgecore/as7726-32x": ["ac-f2b", "ac-b2f", "dc-f2b", "dc-b2f"],
    "ufispace/s9301-32db": ["ac", "ac-b2f"],
    "arista/7050cx4-24d8": ["base", "r"],
    "cisco/n9k-c93108tc-fx3": ["ac-500w-port-side-exhaust", "hvac-hvdc-1200w-port-side-exhaust"],
    "juniper/mx150": ["default"],
}
# fan and supply groups drawn per face, pinned so a unit dropped from the stamp fails
GROUPS = {
    "edgecore/as7726-32x": {"rear": 8, "front": 0},
    "ufispace/s9301-32db": {"rear": 8},
    "arista/7050cx4-24d8": {"rear": 5},
    "cisco/n9k-c93108tc-fx3": {"rear": 6},
}

G_TAG = re.compile(r"<g\b[^>]*>")
CLASS = re.compile(r'\sdata-class="([^"]*)"')
OWN = re.compile(r'\sdata-airflow="([^"]*)"')
STAMP = re.compile(r'\sdata-config-airflow="([^"]*)"')
ANY_TAG = re.compile(r"<[A-Za-z][^>]*>")


# ---------------------------------------------------------------- the data

def recolours(key):
    return key.endswith("-finish") or key.endswith("-edge") or key == "airflow-legend"


def check_recoloured_entries(doc):
    """(problems, entries checked): in a device document, every `component-attrs` entry of a
    configuration whose resolved airflow is back-to-front that sets a recolouring key also sets
    `airflow: back-to-front`."""
    problems, n = [], 0
    for cname, cfg in (doc.get("configurations") or {}).items():
        if config_airflow(doc, cfg) != B2F:
            continue
        for part, entry in ((cfg or {}).get("component-attrs") or {}).items():
            if not isinstance(entry, dict) or not any(recolours(k) for k in entry):
                continue
            n += 1
            if entry.get("airflow") != B2F:
                problems.append(f"{doc['name']}.{cname}.{part}: airflow is {entry.get('airflow')!r}")
    return problems, n


def edgecore_documents():
    return {p.parent.name: yaml.safe_load(p.read_text())
            for p in sorted((LIB / "devices/edgecore").glob("*/device.yaml"))}


def test_every_edgecore_back_to_front_part_it_recolours_states_the_direction():
    docs = edgecore_documents()
    # the checker, on a copy that is right and then wrong in two places
    good = copy.deepcopy(docs["as7726-32x"])
    for cfg in good["configurations"].values():
        if config_airflow(good, cfg) == B2F:
            for entry in (cfg.get("component-attrs") or {}).values():
                if any(recolours(k) for k in entry):
                    entry["airflow"] = B2F
    assert check_recoloured_entries(good) == ([], 4)
    bad = copy.deepcopy(good)
    del bad["configurations"]["ac-b2f"]["component-attrs"]["fan-module"]["airflow"]
    bad["configurations"]["dc-b2f"]["component-attrs"]["psu-dc-650"]["airflow"] = F2B
    problems, _ = check_recoloured_entries(bad)
    assert len(problems) == 2
    assert "ac-b2f.fan-module" in problems[0] and "dc-b2f.psu-dc-650" in problems[1]

    problems, n = [], 0
    for doc in docs.values():
        p, k = check_recoloured_entries(doc)
        problems += p
        n += k
    assert n == 48, f"checked {n} entries, expected 48"
    assert not problems, "\n".join(problems)


def check_stated_directions(doc):
    """(problems, entries checked): every `airflow` that is front-to-back or back-to-front in a
    `component-attrs` or `bay-attrs` entry equals the configuration's resolved airflow. Vendor words
    (`exhaust`, `intake`) are another vocabulary and are skipped."""
    problems, n = [], 0
    for cname, cfg in (doc.get("configurations") or {}).items():
        want = config_airflow(doc, cfg)
        for field in ("component-attrs", "bay-attrs"):
            for key, entry in ((cfg or {}).get(field) or {}).items():
                if not isinstance(entry, dict) or entry.get("airflow") not in DIRECTIONS:
                    continue
                n += 1
                if entry["airflow"] != want:
                    problems.append(f"{doc['name']}.{cname}.{field}.{key}: says {entry['airflow']}, "
                                    f"the build is {want}")
    return problems, n


def test_a_part_never_states_a_direction_its_build_does_not_have():
    # a front-to-back configuration with a back-to-front entry is named
    plant = {"name": "plant", "chassis": {"airflow": F2B}, "configurations": {
        "ok": {"component-attrs": {"fan": {"airflow": F2B}}},
        "wrong": {"component-attrs": {"fan": {"airflow": B2F}}},
        "other-words": {"component-attrs": {"fan": {"airflow": "intake"}}}}}
    problems, n = check_stated_directions(plant)
    assert n == 2 and len(problems) == 1 and "wrong.component-attrs.fan" in problems[0]

    problems, n = [], 0
    for p in sorted((LIB / "devices").glob("*/*/device.yaml")):
        doc = yaml.safe_load(p.read_text())
        a, k = check_stated_directions(doc)
        problems += a
        n += k
    assert n >= 100, f"checked only {n} entries"
    assert not problems, "\n".join(problems)


# ---------------------------------------------------------------- the drawing

def fan_psu_groups(svg_text):
    """[(class, data-airflow, data-config-airflow)] for each fan or supply group."""
    out = []
    for tag in G_TAG.findall(svg_text):
        cls = CLASS.search(tag)
        if cls and cls.group(1) in ("fan", "psu"):
            own, stamp = OWN.search(tag), STAMP.search(tag)
            out.append((cls.group(1), own.group(1) if own else None, stamp.group(1) if stamp else None))
    return out


def stamp_problems(svg_text, want, label):
    """Fan and supply groups whose `data-config-airflow` is not `want` (None: absent)."""
    return [f"{label}: {cls} says {stamp!r}, the configuration is {want!r}"
            for cls, _, stamp in fan_psu_groups(svg_text) if stamp != want]


def render_device(device, out):
    r = subprocess.run([sys.executable, str(RENDER), str(LIB / "devices" / device / "device.yaml"),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads((out / f"{device.split('/')[1]}.configs.json").read_text())


@pytest.fixture(scope="module")
def drawn(tmp_path_factory):
    """{device: (output dir, configs.json)} for the five devices; rendered once for tests 3 to 5."""
    out = {}
    for device in RENDERED:
        d = tmp_path_factory.mktemp(device.split("/")[1])
        out[device] = (d, render_device(device, d))
    return out


def faces(drawn_dev, config):
    """{face: svg text} of one configuration, through configs.json."""
    d, idx = drawn_dev
    c = next(c for c in idx["configs"] if c["name"] == config)
    return c, {face: (d / name).read_text() for face, name in c["files"].items() if name.endswith(".svg")}


def test_every_fan_and_supply_drawn_states_its_configurations_airflow(drawn):
    sample = '<g id="a" data-class="fan" data-airflow="front-to-back" data-config-airflow="back-to-front">'
    assert stamp_problems(sample, B2F, "plant") == []
    assert len(stamp_problems(sample.replace(' data-config-airflow="back-to-front"', ""), B2F, "plant")) == 1
    assert len(stamp_problems(sample.replace("back-to-front", F2B).replace("data-airflow=\"front-to-back\"",
                                                                         "data-airflow=\"x\""), B2F, "plant")) == 1

    problems = []
    for device, configs in RENDERED.items():
        if device not in GROUPS:
            continue
        for cfg in configs:
            c, svgs = faces(drawn[device], cfg)
            assert c["airflow"] in DIRECTIONS, (device, cfg)
            for face, text in svgs.items():
                problems += stamp_problems(text, c["airflow"], f"{device} {cfg} {face}")
            for face, n in GROUPS[device].items():
                assert len(fan_psu_groups(svgs[face])) == n, (device, cfg, face)
    assert not problems, "\n".join(problems)


def test_only_fans_and_supplies_carry_it_and_the_parts_own_statement_is_untouched(drawn):
    def strays(text):
        return [t for t in ANY_TAG.findall(text) if STAMP.search(t)
                and (CLASS.search(t) or [None, None])[1] not in ("fan", "psu")]

    # the attribute added to a port is found, and a fan's own statement rewritten is not what it was
    port = '<g id="p" data-class="port" data-config-airflow="back-to-front">'
    assert len(strays(port)) == 1
    assert strays('<g id="f" data-class="fan" data-config-airflow="back-to-front">') == []

    def own_words(text, cls):
        return {a for c, a, _ in fan_psu_groups(text) if c == cls}

    def own(device, config, cls):
        _, svgs = faces(drawn[device], config)
        return own_words(svgs["rear"], cls)

    for device, (d, _) in drawn.items():
        for svg in d.glob("*.svg"):
            assert not strays(svg.read_text()), svg.name
    as7726 = "edgecore/as7726-32x"
    for cfg in ("ac-b2f", "dc-b2f"):
        assert own(as7726, cfg, "fan") == {B2F} and own(as7726, cfg, "psu") == {B2F}, cfg
    assert own(as7726, "ac-f2b", "fan") == {F2B} and own(as7726, "ac-f2b", "psu") == {None}
    fan_words = own("ufispace/s9301-32db", "ac-b2f", "fan")
    assert fan_words == {"intake"}
    _, svgs = faces(drawn["ufispace/s9301-32db"], "ac-b2f")
    assert {s for _, _, s in fan_psu_groups(svgs["rear"])} == {B2F}
    assert own("cisco/n9k-c93108tc-fx3", "hvac-hvdc-1200w-port-side-exhaust", "psu") == {"dual-direction"}
    # a fan whose own word was overwritten with the build's is no longer what the part said
    rewritten = '<g data-class="fan" data-airflow="back-to-front" data-config-airflow="back-to-front">'
    assert own_words(rewritten, "fan") != fan_words


def test_a_configuration_that_states_no_airflow_gets_no_stamp(drawn):
    c, svgs = faces(drawn["juniper/mx150"], "default")
    assert c["airflow"] is None
    planted = '<g data-class="fan" data-airflow="front-to-back" data-config-airflow="front-to-back">'
    assert len(stamp_problems(planted, None, "plant")) == 1
    groups = [g for text in svgs.values() for g in fan_psu_groups(text)]
    assert len(groups) == 2
    assert all(stamp is None for _, _, stamp in groups)
    assert {a for _, a, _ in groups} == {F2B}
    assert not stamp_problems("".join(svgs.values()), None, "mx150")


@pytest.mark.skipif(not DIST.is_dir() or not any(DIST.glob("*.configs.json")),
                    reason="dist/ not built; run ./publish.sh --no-images")
def test_every_published_fan_and_supply_agrees_with_its_configuration(tmp_path):
    # one dist SVG with its stamp flipped, copied under tmp_path with its index
    idx_file = DIST / "as7726-32x.configs.json"
    cfg = next(c for c in json.loads(idx_file.read_text())["configs"] if c["name"] == "ac-b2f")
    (tmp_path / idx_file.name).write_text(idx_file.read_text())
    for name in cfg["files"].values():
        if name.endswith(".svg"):
            text = (DIST / name).read_text()
            if name == cfg["files"]["rear"]:
                text = text.replace('data-config-airflow="back-to-front"',
                                    'data-config-airflow="front-to-back"', 1)
            (tmp_path / name).write_text(text)
    planted, _ = walk_dist(tmp_path, only=["ac-b2f"])
    assert len(planted) == 1, planted

    problems, n = walk_dist(DIST)
    assert n >= 1000, f"compared only {n} fan and supply groups"
    assert not problems, "\n".join(problems[:20])
    print(f"fan and supply groups compared: {n}")


def walk_dist(dist, only=None):
    """(problems, groups compared) over every index in `dist`, every configuration, every face."""
    problems, n = [], 0
    for f in sorted(dist.glob("*.configs.json")):
        for c in json.loads(f.read_text())["configs"]:
            if only and c["name"] not in only:
                continue
            for name in c["files"].values():
                if name.endswith(".svg"):
                    text = (dist / name).read_text()
                    n += len(fan_psu_groups(text))
                    problems += stamp_problems(text, c["airflow"], f"{f.name} {c['name']} {name}")
    return problems, n


# ---------------------------------------------------------------- the README

def airflow_section(text):
    m = re.search(r"^## Airflow\n(.*?)(?=^## )", text, re.S | re.M)
    return m.group(1) if m else None


def words_in_use(contracts):
    """The distinct short `attrs.airflow` words on fan and supply contracts, and whether any contract
    states a sentence instead (a value with a bracket)."""
    words, sentence = set(), False
    for c in contracts:
        if c.get("class") not in ("fan", "psu"):
            continue
        v = (c.get("attrs") or {}).get("airflow")
        if not isinstance(v, str):
            continue
        if "(" in v:
            sentence = True
        else:
            words.add(v)
    return words, sentence


def readme_problems(section, contracts):
    if section is None:
        return ["the components README has no `## Airflow` section"]
    words, sentence = words_in_use(contracts)
    problems = []
    for token in sorted(words | {F2B, B2F, "data-config-airflow"}):
        if f"`{token}`" not in section:
            problems.append(f"`{token}` is not named in the section")
    if sentence and "sentence" not in section:
        problems.append("contracts state a sentence and the section does not say what it does with them")
    return problems


def test_the_components_readme_states_the_airflow_values_and_every_word_in_use():
    section = airflow_section(README.read_text())
    contracts = [yaml.safe_load(p.read_text()) for p in sorted(LIB.glob("components/*/*/v*/contract.yaml"))]
    assert not readme_problems(section, contracts), readme_problems(section, contracts)
    # the section with one word taken out, and a contract with a word no section names
    cut = section.replace("`port-side intake`", "")
    assert readme_problems(cut, contracts) == ["`port-side intake` is not named in the section"]
    new = contracts + [{"class": "fan", "attrs": {"airflow": "reverse-flow"}}]
    assert readme_problems(section, new) == ["`reverse-flow` is not named in the section"]
    assert readme_problems(None, contracts)
