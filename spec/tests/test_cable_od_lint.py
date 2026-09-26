"""L122: a `cable-od` is a diameter in mm a real cable can have (docs/pluggables-cables-design.md section 4)."""
import pathlib

from portrayal import lint

P = pathlib.Path("library/components/generic/example/v1/contract.yaml")


def run(doc):
    with lint.collecting() as got:
        lint.lint_component_cable_od(P, doc)
        return [e for e in got.errors if "[L122]" in e]


def field(default):
    return {"kind": "component", "name": "cable-end",
            "fields": {"cable-od": {"type": "number", "default": default}}}


def part(value):
    return {"kind": "component", "name": "wrapper",
            "parts": [{"id": "end", "ref": "generic/cable-end@1", "attrs": {"cable-od": value}}]}


def test_a_default_in_range_passes():
    assert run(field(6.9)) == []


def test_a_string_number_passes():
    assert run(field("6.9")) == []


def test_a_word_is_an_error():
    errs = run(field("thick"))
    assert len(errs) == 1 and "not a number" in errs[0]


def test_too_thin_is_an_error():
    errs = run(field(0.5))
    assert len(errs) == 1 and "outside 2-15" in errs[0]


def test_too_thick_is_an_error():
    errs = run(field(40))
    assert len(errs) == 1 and "outside 2-15" in errs[0]


def test_a_parts_attr_in_range_passes():
    assert run(part(3.0)) == []


def test_a_parts_attr_out_of_range_is_named():
    errs = run(part(40))
    assert len(errs) == 1 and "parts[end].attrs.cable-od" in errs[0]


def test_a_contract_without_cable_od_is_silent():
    assert run({"kind": "component", "name": "x", "fields": {"label": {}}}) == []
