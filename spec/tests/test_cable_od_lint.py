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


# --- #644: a device that places a cable end directly -----------------------
#
# A configuration's occupants carry refs only, but a device may PLACE a cable
# end with `mate-to` and attrs, and the build's data-r-from binding draws that
# placement's `cable-od`. L122 reads it there too.

D = pathlib.Path("library/devices/example/dev/device.yaml")


def run_device(doc):
    with lint.collecting() as got:
        lint.lint_device_cable_od(D, doc)
        return [e for e in got.errors if "[L122]" in e]


def device(attrs, sectioned=False):
    a = {"physical": attrs} if sectioned else attrs
    return {"name": "dev", "views": {"front": {"components": {"placements": [
        {"id": "port-1", "ref": "common/bnc-jack@1", "at": [0, 0]},
        {"id": "port-1-cable", "ref": "generic/bnc-plug@1", "mate-to": "port-1",
         "attrs": a}]}}}}


def test_a_device_placement_in_range_passes():
    assert run_device(device({"cable-od": 6.1})) == []


def test_a_device_placement_out_of_range_is_an_error():
    errs = run_device(device({"cable-od": 40}))
    assert len(errs) == 1 and "outside 2-15" in errs[0] and "port-1-cable" in errs[0]


def test_a_device_placement_that_is_not_a_number_is_an_error():
    errs = run_device(device({"cable-od": "1e1"}))
    assert len(errs) == 1 and "not a number" in errs[0]


def test_a_sectioned_device_attr_is_read_too():
    errs = run_device(device({"cable-od": 0.5}, sectioned=True))
    assert len(errs) == 1 and "outside 2-15" in errs[0]


def test_a_placement_without_cable_od_is_not_asked():
    assert run_device(device({"media": "coax-bnc"})) == []


def test_the_real_library_has_no_device_cable_od_errors():
    import yaml
    root = pathlib.Path(__file__).resolve().parents[2]
    checked = 0
    with lint.collecting() as got:
        for p in sorted(root.glob("library/devices/*/*/device.yaml")):
            lint.lint_device_cable_od(p, yaml.safe_load(p.read_text()))
            checked += 1
    assert checked > 100
    assert [e for e in got.errors if "[L122]" in e] == []
