"""L197: a device's decor `kind` does not name a connector.

Every port on a device must be usable: anything that takes a cable, cord, plug,
lug or pluggable is modelled as a connector part, and the library holds
something that plugs into it. A connector drawn as panel decor is a drawing a
plug has nothing to mate. No build output carries that, so the rule reads the
manifest, and the names it looks for are a list in
spec/schemas/connector-decor-names.yaml: a floor of names, not a proof.

The rule is a warning and the library's present findings are in
library/lint-baseline.json. These tests pin the rule on devices written to a
temporary folder, the names file's shape, the baseline's count, and the words in
the contributor documents that say the rule.
"""
import json
import pathlib
import re

import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
NAMES = ROOT / "spec/schemas/connector-decor-names.yaml"
BASELINE = ROOT / "library/lint-baseline.json"

# THE L197 FINDINGS IN library/lint-baseline.json WHEN THIS RULE LANDED. A lower
# count is progress (a decor connector became a part, or was renamed for what it
# is); a higher one is a new decor connector, and the fix is a part that
# presents the interface, not a larger number here.
BASELINE_L197 = 150


def _device(tmp_path, decor, placements=()):
    """A device manifest written to tmp_path and read back, as the linter reads one."""
    doc = {"kind": "device", "views": {"front": {
        "panel": {"decor": list(decor)},
        "components": {"placements": list(placements), "bays": []}}}}
    path = tmp_path / "device.yaml"
    path.write_text(yaml.safe_dump(doc))
    return str(path), lint.load_yaml(path)


def _run(tmp_path, decor, placements=()):
    path, data = _device(tmp_path, decor, placements)
    with lint.collecting() as got:
        lint.lint_device_connector_decor(path, data)
    return got


def _l197(found):
    return [m for m in found if "[L197]" in m]


# --- the rule ----------------------------------------------------------------

def test_a_listed_decor_kind_gets_l197_as_a_warning(tmp_path):
    got = _run(tmp_path, [{"id": "console-opening", "kind": "console-opening",
                           "at": [10, 10], "size": [8, 4]}])
    assert len(_l197(got.warnings)) == 1, got.warnings
    assert "console-opening" in _l197(got.warnings)[0]
    assert _l197(got.errors) == [], "L197 is a warning"
    assert lint.RULES["L197"][-1] == lint.WARNING


def test_a_decor_that_is_not_listed_gets_nothing(tmp_path):
    got = _run(tmp_path, [{"id": "case-screw", "kind": "case-screw", "at": [1, 1], "size": [3, 3]}])
    assert _l197(got.warnings) == [] and _l197(got.errors) == []


def test_a_decor_that_frames_a_placed_port_gets_nothing(tmp_path):
    got = _run(tmp_path,
               [{"id": "rj45-shell-1", "kind": "port-shell", "at": [10, 10], "size": [16, 14]}],
               [{"id": "port-1", "ref": "std/rj45@2", "at": [11, 11]}])
    assert _l197(got.warnings) == [] and _l197(got.errors) == []


# --- the names file ----------------------------------------------------------

def test_the_names_file_has_the_stated_shape():
    text = NAMES.read_text()
    doc = yaml.safe_load(text)
    names = doc["names"]
    assert doc["format"] == 1 and names, "a names file with no names would pass every device"
    for name, reason in names.items():
        assert re.fullmatch(r"[a-z][a-z0-9-]*", name), f"{name!r} is not a decor kind"
        assert isinstance(reason, str) and reason.strip(), f"{name} has no reason"
    keys = re.findall(r"^  ([a-z][a-z0-9-]*):", text, flags=re.M)
    assert len(keys) == len(set(keys)), "a name is listed twice"
    assert len(keys) == len(names)


def test_a_name_with_no_reason_is_what_the_shape_test_refuses(tmp_path):
    bad = yaml.safe_load("format: 1\nnames:\n  console-opening:\n")
    assert [n for n, r in bad["names"].items() if not (isinstance(r, str) and r.strip())] \
        == ["console-opening"]


# --- the baseline ------------------------------------------------------------

def test_the_l197_count_in_the_baseline_has_not_grown():
    base = json.loads(BASELINE.read_text())
    count = sum(rules.get("L197", 0) for rules in base.values())
    assert count <= BASELINE_L197, \
        f"{count} L197 findings are baselined, over the {BASELINE_L197} recorded: a new decor " \
        "connector; model it as a part that presents its interface"
    assert count > 0, "the baseline records no L197 finding, so it was not re-recorded"


# --- what the prose says ------------------------------------------------------

def test_gate_4b_sits_between_gate_4_and_gate_5_and_the_skill_has_its_row():
    guide = (ROOT / "docs/modelling-a-device.md").read_text()
    g4, g4b, g5 = (guide.find(s) for s in ("**Gate 4.**", "## Gate 4b", "## Gate 5"))
    assert 0 <= g4 < g4b < g5, "Gate 4b belongs after Gate 4 and before Gate 5"
    gate = guide[g4b:g5]
    for word in ("part_conformance.py", "--scan", "test_port_usable_records.py",
                 "C19", "C22", "conformance-exceptions.yaml"):
        assert word in gate, f"Gate 4b does not mention {word}"
    skill = (ROOT / ".claude/skills/portrayal-model-device/SKILL.md").read_text()
    rows = [r.split("|")[1].strip() for r in skill.splitlines() if r.startswith("| ")]
    assert rows.index("4") + 1 == rows.index("4b") == rows.index("5") - 1


def test_the_pull_request_template_asks_what_mates_each_connector():
    template = (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
    assert "what mates each connector" in " ".join(template.split())
