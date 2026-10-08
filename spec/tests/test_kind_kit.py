"""`kind: kit`, the third kind of contract (roc-ops/Portrayal#905).

A rail, bracket or slide kit is a set of ordinary components that a device
names from `chassis.kits` and never places (docs/rack-mounting-design.md,
section 4). It has no `class` and no `size`, admits only the kit keys, is left
out of components.json and the component catalogue, and is published in
kits.json. Lint L155-L159 hold what the schema cannot say.

No real kit is in the library yet, so every test here builds its own on
tmp_path, and each rule is tested both ways.
"""
import copy
import json
import pathlib
import subprocess
import sys

import jsonschema
import pytest
import yaml

from portrayal import components_catalogue as cat
from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)

PART = {"format": 1, "kind": "component", "name": "inner", "version": "1.0.0",
        "class": "bracket", "size": {"w": 20, "h": 40},
        "description": "An inner rail. Test part."}

KIT = {
    "format": 1, "kind": "kit", "name": "slide", "version": "1.0.0",
    "description": "A three-member slide. Test kit.",
    "motion": "sliding", "travel": "full", "install": "drop-in",
    "parts": [{"ref": "acme/inner@1", "id": "inner", "count": 2},
              {"ref": "acme/outer@1", "id": "outer", "count": 2}],
    "configurations": [
        {"id": "four-post", "racks": ["4-post"], "parts": ["inner", "outer"],
         "depth": {"square": [631, 868], "round": [617, 861]}, "rail-depth": 714},
        {"id": "short", "racks": ["4-post", "2-post"], "parts": ["inner"],
         "depth": [500, 600], "preset": 550, "tolerance": 2}],
    "accessories": [{"kind": "cma", "ref": "acme/cma@1", "rail-depth": 845,
                     "sides": ["left", "right"]},
                    {"kind": "srb", "ref": "acme/srb@1"}],
    "provenance": {"depth": "a test figure"},
    "unplaced": "A test kit: nothing in this temporary library names it from chassis.kits.",
}


def _write(lib, ref, doc):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    d = lib / "components" / ns / name / f"v{major}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "contract.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    return d / "contract.yaml"


@pytest.fixture
def lib(tmp_path):
    """A library holding the kit's parts and accessories, and the kit."""
    lib = tmp_path / "library"
    for ref in ("acme/inner@1", "acme/outer@1", "acme/cma@1", "acme/srb@1"):
        name = ref.split("/")[1].split("@")[0]
        _write(lib, ref, {**PART, "name": name})
    (lib / "devices").mkdir(parents=True)
    return lib


def _schema_errors(doc):
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in VALIDATOR.iter_errors(doc)]


def _kit_findings(lib, doc):
    path = _write(lib, "acme/slide@1", doc)
    with lint.collecting() as found:
        lint.lint_kit(path, doc, [str(lib)])
    return found.errors + found.warnings


def _codes(findings):
    return sorted({f.split("[")[1].split("]")[0] for f in findings})


# --- the schema -----------------------------------------------------------------

def test_a_kit_validates_without_class_or_size():
    assert _schema_errors(KIT) == []


def test_a_kit_with_one_depth_range_validates():
    doc = copy.deepcopy(KIT)
    doc["configurations"][0]["depth"] = [600, 900]
    assert _schema_errors(doc) == []


@pytest.mark.parametrize("key,value", [
    ("class", "bracket"), ("size", {"w": 1, "h": 1}), ("skins", ["default"]),
    ("elements", {}), ("title", "a title")])
def test_a_kit_admits_only_the_kit_keys(key, value):
    assert _schema_errors({**KIT, key: value})


@pytest.mark.parametrize("key", ["motion", "parts", "configurations"])
def test_a_kit_requires_motion_parts_and_configurations(key):
    assert _schema_errors({k: v for k, v in KIT.items() if k != key})


def test_a_kit_part_is_ref_id_and_count_and_nothing_else():
    doc = copy.deepcopy(KIT)
    doc["parts"][0] = {"ref": "acme/inner@1", "id": "inner", "at": [0, 0]}
    errs = _schema_errors(doc)
    assert any("'count' is a required property" in e for e in errs)
    assert any("'at' is not one of" in e for e in errs)


@pytest.mark.parametrize("where,value", [
    ("motion", "rolling"), ("install", "bolted"), ("travel", -5), ("travel", "most"),
    ("configurations/0/racks", ["3-post"]), ("configurations/0/depth", {"oval": [1, 2]}),
    ("configurations/0/depth", [600]), ("accessories/0/kind", "shelf"),
    ("accessories/0/sides", ["top"])])
def test_a_kit_key_outside_its_vocabulary_is_refused(where, value):
    doc = copy.deepcopy(KIT)
    *path, last = where.split("/")
    node = doc
    for p in path:
        node = node[int(p)] if p.isdigit() else node[p]
    node[last] = value
    assert _schema_errors(doc)


def test_a_component_still_requires_class_and_size():
    comp = {k: v for k, v in PART.items() if k != "size"}
    assert any("'size' is a required property" in e for e in _schema_errors(comp))
    comp = {k: v for k, v in PART.items() if k != "class"}
    assert any("'class' is a required property" in e for e in _schema_errors(comp))
    assert _schema_errors(PART) == []


@pytest.mark.parametrize("key,value", [
    ("motion", "fixed"), ("travel", 300), ("install", "both"),
    ("configurations", KIT["configurations"]), ("accessories", KIT["accessories"])])
def test_a_component_takes_none_of_the_kit_keys(key, value):
    assert _schema_errors({**PART, key: value})


def test_a_composed_part_still_needs_at_and_takes_no_count():
    comp = {**PART, "parts": [{"ref": "acme/outer@1", "id": "o", "at": [0, 0]}]}
    assert _schema_errors(comp) == []
    comp["parts"] = [{"ref": "acme/outer@1", "id": "o"}]
    assert any("'at' is a required property" in e for e in _schema_errors(comp))
    comp["parts"] = [{"ref": "acme/outer@1", "id": "o", "at": [0, 0], "count": 2}]
    assert _schema_errors(comp)


# --- lint: each rule both ways --------------------------------------------------

def test_a_whole_kit_is_clean(lib):
    assert _kit_findings(lib, KIT) == []


def test_L155_a_part_ref_that_resolves_nowhere(lib):
    doc = copy.deepcopy(KIT)
    doc["parts"][1]["ref"] = "acme/missing@1"
    assert _codes(_kit_findings(lib, doc)) == ["L155"]


def test_L155_a_part_that_is_itself_a_kit(lib):
    _write(lib, "acme/other-kit@1", {**KIT, "name": "other-kit"})
    doc = copy.deepcopy(KIT)
    doc["parts"][1]["ref"] = "acme/other-kit@1"
    found = _kit_findings(lib, doc)
    assert _codes(found) == ["L155"] and "is a kit" in found[0]


def test_L155_two_parts_under_one_id(lib):
    doc = copy.deepcopy(KIT)
    doc["parts"][1]["id"] = "inner"
    doc["configurations"][0]["parts"] = ["inner"]
    found = _kit_findings(lib, doc)
    assert _codes(found) == ["L155"] and "'inner' is used by another part" in found[0]


def test_L156_a_configuration_naming_a_part_the_kit_lacks(lib):
    doc = copy.deepcopy(KIT)
    doc["configurations"][1]["parts"] = ["inner", "bracket"]
    found = _kit_findings(lib, doc)
    assert _codes(found) == ["L156"] and "'bracket'" in found[0]


def test_L156_two_configurations_under_one_id(lib):
    doc = copy.deepcopy(KIT)
    doc["configurations"][1]["id"] = "four-post"
    assert _codes(_kit_findings(lib, doc)) == ["L156"]


@pytest.mark.parametrize("depth", [[868, 631], [700, 700], {"square": [631, 868], "round": [861, 617]}])
def test_L157_a_range_whose_min_is_not_below_its_max(lib, depth):
    doc = copy.deepcopy(KIT)
    doc["configurations"][0]["depth"] = depth
    assert _codes(_kit_findings(lib, doc)) == ["L157"]


@pytest.mark.parametrize("motion", ["fixed", "telescoping", "shelf"])
def test_L158_travel_on_a_kit_that_does_not_slide(lib, motion):
    doc = {**KIT, "motion": motion}
    assert _codes(_kit_findings(lib, doc)) == ["L158"]
    doc.pop("travel")
    assert _kit_findings(lib, doc) == []


def test_L159_an_accessory_ref_that_resolves_nowhere(lib):
    doc = copy.deepcopy(KIT)
    doc["accessories"][0]["ref"] = "acme/no-arm@1"
    assert _codes(_kit_findings(lib, doc)) == ["L159"]


def test_L159_an_accessory_that_is_a_kit(lib):
    _write(lib, "acme/other-kit@1", {**KIT, "name": "other-kit"})
    doc = copy.deepcopy(KIT)
    doc["accessories"][1]["ref"] = "acme/other-kit@1"
    assert _codes(_kit_findings(lib, doc)) == ["L159"]


def test_a_component_is_not_asked_the_kit_questions(lib):
    path = _write(lib, "acme/plain@1", {**PART, "name": "plain", "travel": 5})
    with lint.collecting() as found:
        lint.lint_kit(path, {**PART, "travel": 5}, [str(lib)])
    assert not found.errors and not found.warnings


def test_the_kit_rules_are_catalogued_as_kit_rules():
    for code in ("L155", "L156", "L157", "L158", "L159"):
        assert lint.RULES[code][0] == "kit"


def test_a_kit_goes_through_the_whole_lint_run_without_the_component_rules(lib):
    """The command line, on a library of four parts and a kit: the component
    rules that read `size`, skins and elements are not run on the kit, so the
    run reports the kit's own fault and no traceback."""
    doc = copy.deepcopy(KIT)
    doc["configurations"][0]["depth"] = [900, 600]
    _write(lib, "acme/slide@1", doc)
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/lint.py"),
                        "--schemas", str(ROOT / "spec/schemas"), "--library", str(lib)],
                       capture_output=True, text=True)
    assert "Traceback" not in r.stderr, r.stderr
    assert "slide/v1/contract.yaml: [L157]" in r.stdout, r.stdout
    kit_lines = [ln for ln in r.stdout.splitlines() if "slide/v1/contract.yaml" in ln]
    assert all("[L157]" in ln for ln in kit_lines), kit_lines


# --- the indexes ----------------------------------------------------------------

def test_kits_json_carries_the_kit_and_components_json_does_not(lib, tmp_path):
    _write(lib, "acme/slide@1", KIT)
    # a part the index can compile: a contract with no skins draws nothing
    out = tmp_path / "dist"
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/components_index.py"),
                        "--library", str(lib), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    comps = json.loads((out / "components.json").read_text())["components"]
    assert "acme/slide@1" not in {f"{c['ns']}/{c['name']}@{c['major'][1:]}" for c in comps}
    assert all(c["kind"] != "kit" for c in comps)
    assert "acme/slide@1" not in json.loads((out / "components-detail.json").read_text())["components"]
    kits = json.loads((out / "kits.json").read_text())["kits"]
    assert [k["ref"] for k in kits] == ["acme/slide@1"]
    k = kits[0]
    assert (k["ns"], k["name"], k["major"], k["version"], k["kind"]) == \
        ("acme", "slide", "v1", "1.0.0", "kit")
    assert (k["motion"], k["travel"], k["install"]) == ("sliding", "full", "drop-in")
    assert k["parts"] == KIT["parts"]
    assert k["configurations"] == KIT["configurations"]
    assert k["accessories"] == KIT["accessories"]
    assert k["provenance"] == KIT["provenance"] and k["superseded-by"] is None


def test_kits_json_is_written_empty_when_the_library_has_no_kit(lib, tmp_path):
    out = tmp_path / "dist"
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/components_index.py"),
                        "--library", str(lib), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert json.loads((out / "kits.json").read_text()) == {"kits": []}


def test_the_catalogue_lists_a_kit_apart_and_does_not_count_it(lib):
    _write(lib, "acme/slide@1", KIT)
    page = cat.build(lib)
    assert "\n4 component majors in " in page
    assert "## Rail kits (1)" in page
    assert "| `acme/slide@1` | sliding | drop-in | four-post, short | acme/inner@1, acme/outer@1 |" in page
    namespaces = page.split("## Rail kits")[0]
    assert "acme/slide@1" not in namespaces


def test_the_catalogue_has_no_kit_table_without_a_kit(lib):
    assert "Rail kits" not in cat.build(lib)
