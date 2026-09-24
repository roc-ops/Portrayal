"""Projection math for tilted facets (docs/superpowers/specs/2026-09-24-tilted-facets-design.md)."""
import math

import pytest

from portrayal import facets

UP30 = {"deg": 30, "facing": "up"}


def test_cos_and_axis():
    assert facets.cos_of(UP30) == pytest.approx(math.cos(math.radians(30)))
    assert facets.axis_of(UP30) == "y"
    assert facets.axis_of({"deg": 45, "facing": "left"}) == "x"


def test_derived_profile_up_rises_to_the_lower_edge():
    key, prof = facets.derived_profile(UP30, 20.0, 10.0)
    assert key == "profile-y"
    assert prof[0] == [0.0, 0.0]
    assert prof[1][0] == 10.0 and prof[1][1] == pytest.approx(10 * math.tan(math.radians(30)))


def test_derived_profile_down_and_left_right():
    assert facets.derived_profile({"deg": 45, "facing": "down"}, 20, 10) == \
        ("profile-y", [[0.0, pytest.approx(10.0)], [10.0, 0.0]])
    assert facets.derived_profile({"deg": 45, "facing": "left"}, 20, 10) == \
        ("profile", [[0.0, pytest.approx(20.0)], [20.0, 0.0]])
    assert facets.derived_profile({"deg": 45, "facing": "right"}, 20, 10) == \
        ("profile", [[0.0, 0.0], [20.0, pytest.approx(20.0)]])


def test_projected_box_unrotated_up():
    c = math.cos(math.radians(30))
    assert facets.projected_box([5, 100], 20.0, 10.15, None, UP30) == \
        pytest.approx((5, 100, 25, 100 + 10.15 * c))


def test_projected_box_rotated_90_up():
    # a QSFP28 cage turned to run along a vertical card: true box 20 x 10.15 turned
    # about its centre becomes 10.15 x 20, and THEN the facet's y-scale applies
    c = math.cos(math.radians(45))
    x0, y0, x1, y1 = facets.projected_box([0, 0], 20.0, 10.15, 90, {"deg": 45, "facing": "up"})
    assert x1 - x0 == pytest.approx(10.15)
    assert y1 - y0 == pytest.approx(20.0 * c)
    assert (x0 + x1) / 2 == pytest.approx(10.0)            # centre x unchanged by a y-scale
    assert (y0 + y1) / 2 == pytest.approx(5.075 * c)       # centre y scaled about the part origin


def test_projected_box_without_facet_is_the_plain_box():
    assert facets.projected_box([1, 2], 4, 3, None, None) == (1, 2, 5, 5)


def test_scale_transform():
    assert facets.scale_transform(UP30) == "scale(1,0.866025)"
    assert facets.scale_transform({"deg": 60, "facing": "right"}) == "scale(0.5,1)"


def test_facet_of_finds_only_facet_features():
    c = {"relief": {"features": [{"node": "a", "out": 1},
                                  {"node": "h", "facet": UP30}]}}
    assert facets.facet_of(c, "h") == UP30
    assert facets.facet_of(c, "a") is None
    assert facets.facet_of(c, "zz") is None
