"""The ASR 9902 and ASR 9903 are one body width, one RP pitch and one supply.

Cisco's Fixed-Port Routers Hardware Installation Guide dimensions the ASR 9902
at 17.3 in (Figure 18) and the ASR 9903 at 17.32 in (Figure 19, 439.9 mm). The
Visio stencil draws both bodies the same width and so does this library; the ASR
9903 data sheet's 443.86 mm is an overall figure (#374). So:

- the 9903's body is 439.9 mm on every face that carries a width,
- the A99-RP-F sits on the same pitch in both chassis (the two models' RP bays
  were 211.44 and 209.58 mm apart for the identical 747.7-art-unit spacing),
- and the PWR-1.6KW supply has one width in the two chassis' bays and in the part
  they seat, 74.94 mm (read from the 9902's own drawing; estimated).
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

BODY = 439.9
SUPPLY_W = 74.94


def _device(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "device.yaml").read_text())


def _contract(ref):
    name, major = ref.split("@")
    path = LIB / "components" / name / f"v{major}" / "contract.yaml"
    return yaml.safe_load(path.read_text())


def _bays(doc, face):
    return {b["id"]: b for b in doc["views"][face]["components"]["bays"]}


def test_the_9903_body_is_the_guides_439_9():
    doc = _device("asr-9903")
    assert doc["chassis"]["width"] == pytest.approx(BODY, abs=0.005)
    for face in ("front", "rear", "top", "bottom"):
        assert doc["views"][face]["size"]["w"] == pytest.approx(BODY, abs=0.005), face


def test_the_two_chassis_seat_the_rp_on_one_pitch():
    pitches = {}
    for name in ("asr-9902", "asr-9903"):
        bays = _bays(_device(name), "front")
        pitches[name] = bays["rp-1"]["at"][0] - bays["rp-0"]["at"][0]
    assert pitches["asr-9903"] == pytest.approx(209.55, abs=0.02), pitches
    assert pitches["asr-9902"] == pytest.approx(209.58, abs=0.02), pitches
    assert abs(pitches["asr-9903"] - pitches["asr-9902"]) < 0.05, pitches


@pytest.mark.parametrize("name", ["asr-9902", "asr-9903"])
def test_the_supply_has_one_width_in_the_bay_and_the_part(name):
    doc = _device(name)
    bays = [b for b in _bays(doc, "rear").values() if b["group"] == "power-modules"]
    assert bays
    for bay in bays:
        assert bay["size"]["w"] == pytest.approx(SUPPLY_W, abs=0.005), bay["id"]
        for ref in bay["accepts"]:
            assert _contract(ref)["size"]["w"] == pytest.approx(SUPPLY_W, abs=0.005), ref


def test_every_9903_supply_and_fan_sits_inside_the_rear_face():
    doc = _device("asr-9903")
    face_w = doc["views"]["rear"]["size"]["w"]
    for bay in _bays(doc, "rear").values():
        x, w = bay["at"][0], bay["size"]["w"]
        assert 0 <= x and x + w <= face_w + 1e-6, bay["id"]
