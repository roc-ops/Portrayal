"""Seven parts that nothing plugs into say why, and none of them offers a connector.

A printed earth symbol, four fasteners and two ESD wrist-strap points are drawn on hundreds of
devices. None of them is a place a cable of the rack lands, so each carries an `unmated` sentence
(spec/schemas/component.schema.json) and none presents an interface, a slot or a mate. The sentence
and the absence of a connector are pinned here; the records file holds no row for any of them, because
a part with a sentence needs none (spec/tests/test_port_usable_records.py).
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "library" / "components"
RECORDS = ROOT / "library" / "conformance-exceptions.yaml"

# ref -> the words its sentence has to carry, so the sentence says what the part is
PARTS = {
    "common/ground-symbol@1": ("earth symbol", "no hardware"),
    "common/screw-head@1": ("fastener",),
    "amphenol-ns/cover-thumbscrew@1": ("fastener",),
    "dell/thumbscrew-blue-14g@1": ("fastener",),
    "edgecore/agr-panel-screw@1": ("fastener",),
    "common/esd-jack@1": ("wrist strap", "no cable of the rack"),
    "casa/ground-strap@2": ("wrist strap", "no cable of the rack"),
}
OFFERS = ("interface", "presents", "cages", "mates")        # the keys of a part that takes a cable or a plug


def contract(ref):
    namespace, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((COMPONENTS / namespace / name / f"v{major}" / "contract.yaml").read_text())


@pytest.mark.parametrize("ref", PARTS)
def test_the_part_says_why_nothing_plugs_into_it(ref):
    sentence = contract(ref).get("unmated")
    assert isinstance(sentence, str) and len(sentence) >= 40, f"{ref}: no `unmated` sentence of at least 40 characters"
    missing = [word for word in PARTS[ref] if word not in sentence]
    assert not missing, f"{ref}: its sentence does not say {missing}: {sentence!r}"


@pytest.mark.parametrize("ref", PARTS)
def test_the_part_offers_no_interface_slot_or_mate(ref):
    offered = [key for key in OFFERS if key in contract(ref)]
    assert not offered, f"{ref} states {offered}, so it is a connector and cannot say that nothing plugs into it"


def test_the_records_file_holds_no_row_for_these_parts():
    rows = yaml.safe_load(RECORDS.read_text())["rows"]
    assert not [r["part"] for r in rows if r["part"] in PARTS], "a part with a sentence needs no row"
