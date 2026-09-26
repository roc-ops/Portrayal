"""L121: a module-shaped pluggable declares its head, the head fits the MSA's
outside envelope or says why not, and nothing it builds stands past it
(docs/pluggables-heads-design.md section 4.3)."""
import pathlib

import pytest

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
lint.STANDARDS.update(lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])

P = pathlib.Path("library/components/generic/x/v1/contract.yaml")


def run(doc, path=P):
    with lint.collecting() as got:
        lint.lint_component_head(path, doc)
        return ([e for e in got.errors if "[L121]" in e],
                [w for w in got.warnings if "[L121]" in w])


def sfp(**head):
    doc = {"kind": "component", "name": "x", "class": "transceiver",
           "behaviour": "occupies", "mates": "sfp", "conforms": "sfp-module",
           "size": {"w": 13.55, "h": 8.55, "d": 47.5},
           "relief": {"features": [{"node": "body", "out": 10.0}]}}
    if head is not None:
        doc["head"] = {"at": [0.0, 0.0], "size": {"w": 13.55, "h": 8.55, "d": 10.0}, **head}
    return doc


def test_a_head_inside_the_envelope_passes():
    assert run(sfp()) == ([], [])


def test_a_module_occupant_without_a_head_is_an_error():
    doc = sfp(); del doc["head"]
    errs, _ = run(doc)
    assert len(errs) == 1 and "declares no `head:`" in errs[0]


def test_a_part_that_conforms_to_no_module_envelope_is_not_asked():
    doc = sfp(); del doc["head"]; doc["conforms"] = "rj45-ganged"
    assert run(doc) == ([], [])


def test_a_superseded_part_is_not_asked():
    doc = sfp(); del doc["head"]; doc["superseded-by"] = "generic/x@2"
    assert run(doc) == ([], [])


def test_too_tall_above_is_an_error_naming_the_dimension():
    errs, _ = run(sfp(at=[0.0, -2.70], size={"w": 13.55, "h": 11.25, "d": 10.0}))
    assert len(errs) == 1 and "above" in errs[0] and "2.1" in errs[0]


def test_an_exceeds_entry_with_a_source_waives_it():
    errs, warns = run(sfp(at=[0.0, -2.70], size={"w": 13.55, "h": 11.25, "d": 10.0},
                          exceeds=[{"dimension": "above", "source": "Finisar FCLF852x Fig 2"}]))
    assert errs == [] and warns == []


def test_a_stale_waiver_is_an_error():
    errs, _ = run(sfp(exceeds=[{"dimension": "above", "source": "x"}]))
    assert len(errs) == 1 and "stale" in errs[0]


def test_a_long_sfp_head_is_only_a_note_because_the_length_is_recommended():
    doc = sfp(size={"w": 13.55, "h": 8.55, "d": 22.7})
    doc["relief"]["features"][0]["out"] = 22.7
    errs, warns = run(doc)
    assert errs == [] and len(warns) == 1 and "recommended" in warns[0]


def test_a_long_qsfp_head_is_an_error_because_the_length_is_a_maximum():
    doc = sfp(size={"w": 18.35, "h": 8.5, "d": 25.0})
    doc.update(conforms="qsfp-module", size={"w": 18.35, "h": 8.5, "d": 52.4})
    doc["relief"]["features"][0]["out"] = 25.0
    errs, _ = run(doc)
    assert len(errs) == 1 and "length" in errs[0]


def test_a_qsfp_dd_type_2_takes_the_longer_limit():
    doc = sfp(size={"w": 18.35, "h": 8.5, "d": 30.0}, type=2)
    doc.update(conforms="qsfp-dd-module", size={"w": 18.35, "h": 8.5, "d": 58.26})
    doc["relief"]["features"][0]["out"] = 30.0
    assert run(doc) == ([], [])
    doc["head"]["type"] = 1
    errs, _ = run(doc)
    assert len(errs) == 1 and "length" in errs[0]


def test_a_relief_feature_past_the_head_is_an_error():
    doc = sfp(); doc["relief"]["features"].append({"node": "brick", "out": 34.8})
    errs, _ = run(doc)
    assert len(errs) == 1 and "brick" in errs[0]


def test_the_head_node_must_draw_the_head(tmp_path):
    comp = tmp_path / "generic/x/v1"; (comp / "skins").mkdir(parents=True)
    (comp / "skins/default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">'
        '<rect id="head" x="0.1" y="0.1" width="13.35" height="8.35"/></svg>')
    doc = sfp(node="head"); doc["skins"] = ["default"]
    assert run(doc, comp / "contract.yaml") == ([], [])       # within half a stroke
    doc["head"]["size"]["h"] = 13.2; doc["head"]["exceeds"] = [
        {"dimension": "below", "source": "x"}]
    errs, _ = run(doc, comp / "contract.yaml")
    assert any("does not draw" in e for e in errs)


def _long_head():
    """A head 19.8 deep, its body standing to the head's rear face."""
    doc = sfp(size={"w": 13.55, "h": 8.55, "d": 19.8})
    doc["relief"]["features"][0]["out"] = 19.8
    return doc


def test_cable_furniture_behind_the_head_is_not_held_to_it():
    """A feature that STARTS at or past the head's rear - a strap or ring
    lying along the cable behind the head - is the cable's, not the head's.
    Clause 4 limits what the head builds; this starts where the head ends."""
    doc = _long_head()
    doc["relief"]["features"].append({"node": "strap", "lift": 19.8, "out": 63.5})
    errs, _ = run(doc)
    assert not any("strap" in e for e in errs), errs


def test_a_feature_starting_inside_the_head_is_still_held_to_it():
    doc = _long_head()
    doc["relief"]["features"].append({"node": "strap", "lift": 10, "out": 63.5})
    errs, _ = run(doc)
    assert len(errs) == 1 and "strap" in errs[0] and "63.5" in errs[0], errs
