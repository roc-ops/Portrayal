"""L39's lamp coverage counts the union of the holes, and a multi-window
lamp's own windows (#395).

It used to want ONE hole over half the lamp. A lamp seen through several
windows - the AIS800-32D's lane columns, four 1.4 mm windows in a 1.8 x 11.4
part - could never be covered however honestly its windows were punched, and
the device waived the warning instead.
"""
import pathlib

from portrayal import lint as L

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = [str(ROOT / "library")]
COLUMN = "common/qsfp-lane-leds-column@1"     # 1.8 x 11.4, lanes at y 0.5 + 3k, 1.4 square
DOT = "common/led-dot@1"                       # 2.0 x 2.0, one window


def lamp_warnings(placements, cutouts):
    # the cutout list must not be empty for rule 5 to run at all, so a far-away
    # port-less hole stands in when a case punches nothing near the lamp
    view = {"panel": {"cutouts": cutouts or [
                {"id": "elsewhere", "at": [90.0, 0.0], "size": [2.0, 2.0], "shape": "rect"}]},
            "components": {"placements": placements
                           + ([] if cutouts else [{"ref": DOT, "id": "elsewhere", "at": [90.0, 0.0]}])}}
    with L.collecting() as found:
        L.lint_device_cutouts("t/device.yaml", "front", view, LIB)
    return [w for w in found.warnings if "[L39]" in w and "has no cutout" in w]


def column(at=(10.0, 5.0), rotate=None):
    q = {"ref": COLUMN, "id": "led-port-1", "at": list(at), "for": "port-1"}
    if rotate is not None:
        q["rotate"] = rotate
    return q


def windows(x, y, lanes=(1, 2, 3, 4)):
    return [{"id": f"led-port-1-lane-{k}", "at": [round(x + 0.2, 2), round(y + 0.5 + 3.0 * (k - 1), 2)],
             "size": [1.4, 1.4], "shape": "circle"} for k in lanes]


def test_a_lamp_behind_four_punched_windows_is_covered():
    assert lamp_warnings([column()], windows(10.0, 5.0)) == []


def test_the_rule_still_fires_when_nothing_is_punched():
    """NON-VACUITY: the same lamp with no windows is still reported."""
    got = lamp_warnings([column()], [])
    assert len(got) == 1 and "led-port-1" in got[0], got


def test_one_window_of_four_is_not_enough():
    got = lamp_warnings([column()], windows(10.0, 5.0, lanes=(1,)))
    assert len(got) == 1, got


def test_two_windows_of_four_are_not_more_than_half():
    got = lamp_warnings([column()], windows(10.0, 5.0, lanes=(1, 2)))
    assert len(got) == 1, got


def test_three_windows_of_four_are():
    assert lamp_warnings([column()], windows(10.0, 5.0, lanes=(1, 2, 3))) == []


def test_the_windows_turn_with_the_lamp():
    """A column turned 180 about its centre lands its lanes in the mirrored
    places; a lane spacing that is symmetric about the centre lands them on
    the same holes."""
    assert lamp_warnings([column(rotate=180)], windows(10.0, 5.0)) == []


def test_a_single_window_lamp_counts_the_union_of_two_holes():
    """A 2 x 2 lamp behind two 2 x 0.8 slots: each covers 40%, together 80%.
    The old one-box rule reported it."""
    cuts = [{"id": "slot-a", "at": [20.0, 5.0], "size": [2.0, 0.8], "shape": "rect"},
            {"id": "slot-b", "at": [20.0, 6.2], "size": [2.0, 0.8], "shape": "rect"}]
    assert lamp_warnings([{"ref": DOT, "id": "led-sys", "at": [20.0, 5.0], "for": "chassis"}], cuts) == []


def test_overlapping_holes_are_not_counted_twice():
    """Two identical 2 x 0.8 holes over one lamp cover 40% of it, not 80%."""
    cuts = [{"id": "slot-a", "at": [20.0, 5.0], "size": [2.0, 0.8], "shape": "rect"},
            {"id": "slot-b", "at": [20.0, 5.0], "size": [2.0, 0.8], "shape": "rect"}]
    got = lamp_warnings([{"ref": DOT, "id": "led-sys", "at": [20.0, 5.0], "for": "chassis"}], cuts)
    assert len(got) == 1, got


def test_union_overlap_counts_shared_area_once():
    assert L._union_overlap((0, 0, 10, 10), [(0, 0, 5, 10), (0, 0, 5, 10)]) == 50
    assert L._union_overlap((0, 0, 10, 10), [(0, 0, 6, 10), (4, 0, 10, 10)]) == 100
    assert L._union_overlap((0, 0, 10, 10), [(20, 20, 30, 30)]) == 0
