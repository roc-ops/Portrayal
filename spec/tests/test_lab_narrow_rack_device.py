"""A lab places two rack devices of half the opening or less side by side in one rack unit.

A `rack` device whose stated width is at most half the 450 mm opening is narrow, as a
finger bracket is. It may say which `side` it is on, and one can stand on each rail at one
rack unit. The width is the one the device already states: no key is added to a device.
The devices here are written into a scratch library, so the test pins no device of the library.
"""
import copy

import pytest
import yaml

from portrayal import labs


def _device(root, name, width, mount=None, ru=1):
    chassis = {"ru": ru, "width": width}
    if mount:
        chassis["mount"] = mount
    path = root / "devices" / "acme" / name / "device.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump({"kind": "device", "name": name, "chassis": chassis}))


@pytest.fixture()
def lib(tmp_path):
    _device(tmp_path, "half-200", 200.0)
    _device(tmp_path, "half-200-b", 200.0)
    _device(tmp_path, "half-225", 225.0)
    _device(tmp_path, "over-226", 226.0)
    _device(tmp_path, "full-440", 440.0)
    _device(tmp_path, "bracket-60", 60.0, mount="rack-face")
    return tmp_path


def lab(*devices):
    return {"format": 1, "kind": "lab", "name": "narrow-rack-device", "rack": {"height-ru": 42},
            "devices": copy.deepcopy(list(devices)), "links": []}


def check(lib, *devices):
    found, placed = labs.check(lab(*devices), [lib])
    return [(code, msg) for code, sev, msg in found if sev == "error"], {p["id"]: p for p in placed}


def test_two_200_mm_devices_stand_on_the_two_rails_of_one_unit(lib):
    errors, placed = check(lib, {"id": "a", "ref": "half-200", "ru": 10, "side": "left"},
                           {"id": "b", "ref": "half-200-b", "ru": 10, "side": "right"})
    assert errors == []
    assert (placed["a"]["ru"], placed["a"]["side"]) == (10, "left")
    assert (placed["b"]["ru"], placed["b"]["side"]) == (10, "right")


def test_half_the_opening_is_narrow_and_a_millimetre_more_is_not(lib):
    errors, _ = check(lib, {"id": "a", "ref": "half-225", "ru": 10, "side": "left"})
    assert errors == []
    errors, _ = check(lib, {"id": "a", "ref": "over-226", "ru": 10, "side": "left"})
    assert [c for c, _m in errors] == ["L153"]
    errors, _ = check(lib, {"id": "a", "ref": "full-440", "ru": 10, "side": "left"})
    assert [c for c, _m in errors] == ["L153"]


def test_one_rail_holds_one_device_and_a_sideless_device_takes_both(lib):
    same = check(lib, {"id": "a", "ref": "half-200", "ru": 10, "side": "left"},
                 {"id": "b", "ref": "half-200-b", "ru": 10, "side": "left"})[0]
    assert [c for c, _m in same] == ["L142"]
    assert "left" in same[0][1]
    both = check(lib, {"id": "a", "ref": "half-200", "ru": 10, "side": "left"},
                 {"id": "b", "ref": "half-200-b", "ru": 10})[0]
    assert [c for c, _m in both] == ["L142"]
    full = check(lib, {"id": "a", "ref": "half-200", "ru": 10, "side": "left"},
                 {"id": "b", "ref": "full-440", "ru": 10})[0]
    assert [c for c, _m in full] == ["L142"]


def test_two_devices_with_no_side_still_cannot_share_a_unit(lib):
    errors, _ = check(lib, {"id": "a", "ref": "half-200", "ru": 10}, {"id": "b", "ref": "half-200-b", "ru": 10})
    assert [c for c, _m in errors] == ["L142"]
    assert "Two rack devices cannot share a rack unit" in errors[0][1]


def test_the_rack_face_rule_is_as_it_was(lib):
    errors, _ = check(lib, {"id": "h", "ref": "full-440", "ru": 10},
                      {"id": "a", "ref": "bracket-60", "ru": 10, "side": "left"},
                      {"id": "b", "ref": "bracket-60", "ru": 10, "side": "right"})
    assert errors == []
