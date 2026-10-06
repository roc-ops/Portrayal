"""The nine module envelopes carry the MSAs' OUTSIDE-the-cage envelope
(docs/pluggables-heads-design.md section 2 and 4.1)."""
import pathlib

import pytest

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"]

EXPECT = {
    "sfp-module": {"w-max": 14.00, "above-max": 2.10, "below-max": 1.40, "length-max": 10.00},
    "qsfp-module": {"w-max": 19.0, "above-max": 3.4, "below-max": 1.6, "length-max": 20.0},
    "qsfp-dd-module": {"w-max": 19.0, "above-max": 3.4, "below-max": 1.6,
                       "length-max": {"type-1": 20.0, "type-2": 35.0}},
    "osfp-module": {"w-max": 22.93, "above-max": 0.0, "below-max": 1.6,
                    "length-max": {"type-1": 21.39, "type-2": 37.39}},
    "xfp-module": {"w-max": 22.35, "above-max": 3.0, "below-max": 2.0, "length-max": 9.0},
    "cfp-module": {"w-max": 82.0, "above-max": 0.2, "below-max": 0.2, "length-max": 14.5},
    "cfp2-module": {"w-max": 42.5, "above-max": 3.4, "below-max": 1.6, "length-max": 20.1},
    "cfp4-module": {"w-max": 22.1, "above-max": 3.4, "below-max": 1.6, "length-max": 20.1},
    "cxp-module": {"w-max": 24.05, "above-max": 4.79, "below-max": 1.61, "length-max": 33.55},
}


@pytest.mark.parametrize("key", sorted(EXPECT))
def test_each_module_envelope_states_its_outside_envelope(key):
    head = REG[key].get("head")
    assert head, f"{key} has no head envelope"
    for k, v in EXPECT[key].items():
        assert head[k] == v, (key, k, head[k], v)
    assert head.get("source", "").strip(), f"{key}.head has no source"


def test_only_the_sfp_length_is_a_recommendation():
    assert REG["sfp-module"]["head"].get("length-kind") == "recommended"
    assert "length-kind" not in REG["qsfp-module"]["head"]
    assert "length-kind" not in REG["qsfp-dd-module"]["head"]
    assert "length-kind" not in REG["osfp-module"]["head"]
    assert "length-kind" not in REG["xfp-module"]["head"]
    for key in ("cfp-module", "cfp2-module", "cfp4-module", "cxp-module"):
        assert "length-kind" not in REG[key]["head"], key


def test_the_head_is_wider_than_the_module_it_stands_in_front_of():
    for key in EXPECT:
        assert REG[key]["head"]["w-max"] > REG[key]["w"], key
