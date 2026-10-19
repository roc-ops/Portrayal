"""The MX2000 chassis state a weight, and the MX2008 front prints what its chassis prints (#996).

`mx480` carries `weight-base-kg` and `weight-max-kg` from its guide's physical
specification table; the three MX2000 chassis do the same, each from its own
guide's table (never a sibling's), or record a gap that says which table was
read and that it gives no figure.

The MX2008 chassis labels its control boards `CB-RE`; the hardware guide calls
the board an RCB, and the bay names and descriptions keep that.
"""
from pathlib import Path

import pytest
import yaml

LIB = Path(__file__).resolve().parents[2] / "library/devices/juniper"


def load(name):
    return yaml.safe_load((LIB / name / "device.yaml").read_text())


@pytest.mark.parametrize("name", ["mx2008", "mx2010", "mx2020"])
def test_mx2000_chassis_state_both_weights_or_a_gap(name):
    d = load(name)
    phys = (d.get("attrs") or {}).get("physical") or {}
    if "weight-base-kg" in phys or "weight-max-kg" in phys:
        base, top = phys.get("weight-base-kg"), phys.get("weight-max-kg")
        assert isinstance(base, (int, float)) and isinstance(top, (int, float)), \
            f"{name}: state both weights or neither"
        assert 0 < base < top
        assert phys.get("weight-note"), f"{name}: say which table the weights came from"
    else:
        gaps = [g for g in d.get("gaps") or [] if g.get("what") == "weight"]
        assert gaps, f"{name} states no weight and records no gap for it"
        assert "table" in (gaps[0].get("note") or gaps[0].get("wanted") or "").lower()


def test_mx480_and_mx960_still_carry_theirs():
    assert load("mx480")["attrs"]["physical"]["weight-base-kg"] == 29.7
    assert load("mx480")["attrs"]["physical"]["weight-max-kg"] == 100.26
    assert load("mx960")["attrs"]["physical"]["weight-max-kg"] == 169.64


def test_mx2008_front_prints_cb_re_not_rcb():
    d = load("mx2008")
    front = d["views"]["front"]
    texts = {s["for"]: s["text"] for s in front["silkscreen"]}
    assert texts["rcb0"] == "CB-RE 0"
    assert texts["rcb1"] == "CB-RE 1"
    assert not [s for s in front["silkscreen"] if "RCB" in str(s["text"])]


def test_mx2008_keeps_rcb_in_its_bays_and_descriptions():
    d = load("mx2008")
    bays = {b["id"]: b for b in d["views"]["front"]["components"]["bays"]}
    assert "rcb0" in bays and "rcb1" in bays
    assert "RCB" in d["description"]
    assert "RCB" in d["groups"]["res"]["description"]
