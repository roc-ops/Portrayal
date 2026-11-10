"""The AIS800-64D and AIS800-64O grounding pair is on the pitch of the lug their guides name.

Both quick start guides fix the grounding wire to the rear panel with two M6 screws through one lug, Panduit LCDXN2-14AF-E
or an equivalent. That lug's part drawing prints two holes of .27 in. diameter .63 in. apart (tolerance .02 in.), so the
5/8 in. (15.875 mm) pair the devices place sits inside the lug's own tolerance and the pitch is no longer a gap:

  - the pair is still common/ground-stud-pair-5-8-m6@1, the host of generic/two-hole-lug-5-8@1;
  - the pair's pitch lies within the drawing's tolerance of its .63 in.;
  - the pitch's provenance names the lug and its drawing and is no longer marked as an inference;
  - the devices carry no `ground-pair-pitch` gap.

These read the device and part documents and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

DEVICES = ("edgecore/ais800-64d", "edgecore/ais800-64o")
PAIR = "common/ground-stud-pair-5-8-m6@1"
LUG = "generic/two-hole-lug-5-8@1"
HOLE_SPACING_IN, HOLE_SPACING_TOL_IN = 0.63, 0.02


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device(model):
    return yaml.safe_load((LIB / "devices" / model / "device.yaml").read_text())


@pytest.mark.parametrize("model", DEVICES)
def test_the_pair_is_the_five_eighths_host_the_lug_mates(model):
    placed = [p for p in device(model)["views"]["rear"]["components"]["placements"] if p["id"] == "ground-screws"]
    assert [p["ref"] for p in placed] == [PAIR]
    assert placed[0]["attrs"]["stud-size"] == "M6"
    assert contract(PAIR)["interface"] == contract(LUG)["mates"] == "stud-pair-5-8"


def test_the_pair_pitch_is_inside_the_lug_drawings_tolerance():
    xs = sorted(p["at"][0] for p in contract(PAIR)["parts"])
    pitch = xs[1] - xs[0]
    assert pitch == pytest.approx(15.875)
    assert abs(pitch - HOLE_SPACING_IN * 25.4) <= HOLE_SPACING_TOL_IN * 25.4


@pytest.mark.parametrize("model", DEVICES)
def test_the_pitch_names_the_lug_drawing_and_is_not_an_inference(model):
    note = device(model)["provenance"]["ground-pair"]
    assert note["confidence"] == "datasheet"
    assert "LCDXN2-14AF-E" in note["note"] and ".63" in note["note"]
    assert "INFERRED" not in note["note"]


@pytest.mark.parametrize("model", DEVICES)
def test_the_device_carries_no_pitch_gap(model):
    assert "ground-pair-pitch" not in {g["what"] for g in device(model)["gaps"]}
