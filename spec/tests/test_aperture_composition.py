"""L26 - an aperture is declared once, and everything else composes it.

Every component here is planted in a tmp library. The obvious way to test this
rule is to point it at the two `casa` I/O cards that redraw eighteen MCX
openings each, but three tests in this repo have already had to be repointed
because they asserted that somebody's real debt was still outstanding, and each
time the person who paid the debt broke the suite. A test that owns its own
defect keeps working whichever way the library goes.
"""
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import lint  # noqa: E402


def plant(root, ref, **contract):
    """Write one contract into a tmp library at `ns/name/vN/contract.yaml`."""
    nsname, major = ref.rsplit("@", 1)
    p = root / "components" / nsname / f"v{major}" / "contract.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"format": 1, "kind": "component", "name": nsname.split("/")[-1],
            "version": f"{major}.0.0", "class": "port",
            "size": {"w": 4.0, "h": 4.0}}
    data.update(contract)
    p.write_text(yaml.safe_dump(data))
    return p


def cutout(name="bore"):
    return {name: {"at": [0.5, 0.5], "size": [3.0, 3.0], "class": "cutout"}}


def warnings_for(path, root):
    """L26 warnings raised by one contract, and nothing else."""
    lint.WARNINGS.clear()
    data = yaml.safe_load(path.read_text())
    lint.lint_component_aperture(path, data, [str(root)])
    return [w for w in lint.WARNINGS if "[L26]" in w]


def test_a_redrawn_opening_is_named(tmp_path):
    """The defect the rule exists for: an opening drawn inline, conforming to
    nothing, composing nothing. `casa/io-6p12` is this shape eighteen times
    over at an ESTIMATED bore."""
    p = plant(tmp_path, "acme/io-card@1", **{
        "class": "line-card", "elements": {**cutout("u0"), **cutout("u1")}})
    ws = warnings_for(p, tmp_path)
    assert len(ws) == 1
    assert "2 element(s) declare class: cutout" in ws[0]
    assert "u0, u1" in ws[0]


def test_the_message_points_at_the_registry_not_at_the_author(tmp_path):
    """Half of what this rule finds is true and unfixable today - there is no
    `std/mcx` and no `mcx` key. The warning has to read as a gap in `std/`, or
    it teaches people to ignore the linter."""
    p = plant(tmp_path, "acme/io-card@1", elements=cutout())
    assert "spec/schemas/standards.yaml" in warnings_for(p, tmp_path)[0]


def test_conforming_yourself_is_enough(tmp_path):
    p = plant(tmp_path, "acme/bore@1", conforms="mcx", elements=cutout())
    assert warnings_for(p, tmp_path) == []


def test_composing_a_conforming_part_is_enough(tmp_path):
    plant(tmp_path, "std/mcx@1", conforms="mcx", elements=cutout())
    p = plant(tmp_path, "acme/mcx-bezel@1", elements=cutout(),
              parts=[{"ref": "std/mcx@1", "id": "bore", "at": [0.5, 0.5]}])
    assert warnings_for(p, tmp_path) == []


def test_a_wrapper_of_a_wrapper_still_resolves(tmp_path):
    """Transitive, or the rule punishes the library for having a middle layer:
    `common/qsfp28-cage` wraps `std/qsfp-ganged`, and a panel assembly that
    wraps the cage is no further from the standard than the cage is."""
    plant(tmp_path, "std/mcx@1", conforms="mcx", elements=cutout())
    plant(tmp_path, "common/mcx-cage@1", elements=cutout(),
          parts=[{"ref": "std/mcx@1", "id": "bore", "at": [0.5, 0.5]}])
    p = plant(tmp_path, "acme/mcx-block@1", elements=cutout(),
              parts=[{"ref": "common/mcx-cage@1", "id": "c", "at": [0, 0]}])
    assert warnings_for(p, tmp_path) == []


def test_a_leaf_that_names_its_plug_has_said_what_it_is(tmp_path):
    """`std/lc-bore@1` carries `interface: lc` and no `conforms:`, and all 82
    `lc-duplex-adapter` placements resolve through it. An aperture that names
    the plug it accepts satisfies the leaf even where the registry has not
    caught up."""
    plant(tmp_path, "std/lc-bore@1", interface="lc", elements=cutout())
    p = plant(tmp_path, "common/lc-adapter@1", elements=cutout(),
              parts=[{"ref": "std/lc-bore@1", "id": "left", "at": [0, 0]}])
    assert warnings_for(p, tmp_path) == []


def test_std_is_exempt_because_it_is_the_bottom_of_the_stack(tmp_path):
    """The same defect, moved into `std/`, is not a defect: those components
    compose nothing because there is nothing under them. Run the rule on them
    and it flags the foundations for not standing on anything."""
    vendor = plant(tmp_path, "acme/bore@1", elements=cutout())
    leaf = plant(tmp_path, "std/bore@1", elements=cutout())
    assert len(warnings_for(vendor, tmp_path)) == 1
    assert warnings_for(leaf, tmp_path) == []


def test_the_population_is_the_cutout_not_the_class(tmp_path):
    """Keyed on geometry, so a `line-card` full of openings is inspected and a
    `port` with no opening is not. Keying on `class: port` would have missed
    252 rendered MCX apertures on the day it shipped."""
    card = plant(tmp_path, "acme/io-card@1", **{
        "class": "line-card", "elements": cutout()})
    jack = plant(tmp_path, "acme/jack@1", elements={
        "jack": {"at": [0.5, 0.5], "size": [3.0, 3.0], "class": "jack"}})
    assert len(warnings_for(card, tmp_path)) == 1
    assert warnings_for(jack, tmp_path) == []
