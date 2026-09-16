"""L31 - a region label that states a distance must agree with what is drawn.

The defect class this exists for is the one where THE WORDS ARE RIGHT AND ONLY
THE NUMBERS ARE WRONG, which no other rule in the suite can see. An ASR 9006
said its air filter was "accessible from the rear" while drawing it at the
front; an ASR 9906 region named its rails at 127.0 and 240.0 mm while the
geometry put them at 78.0 and 191.0. Both files contained their own
contradiction in plain text, and lint was green.

Every fixture here is BUILT, not borrowed. Five tests in one session had to be
repointed because they asserted something missing from a real manifest and the
model got better - a test that fails because the thing it tests improved is the
wrong way round.
"""
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]

from portrayal import lint


def device(view_name, depth, at, size, label):
    """One face, one strip, one region. `at`/`size` are [x, y] and [w, h]."""
    return {"views": {view_name: {
        "size": {"w": size[0] + at[0] + 50, "h": depth} if view_name in ("top", "bottom")
                else {"w": depth, "h": size[1] + at[1] + 50},
        "panel": {"decor": [{"at": at, "size": size, "fill": "#9a9c9e"}]},
        "regions": [{"id": "mounting", "label": label}]}}}


def run(data):
    out = []
    real = lint.warn
    lint.warn = lambda p, c, m: out.append((c, m))
    try:
        lint.lint_device_label_geometry("test.yaml", data)
    finally:
        lint.warn = real
    return [m for c, m in out if c == "L31"]


# ---------------------------------------------------------------- the axis
# y = 0 is the REAR on a top or bottom view, so a plane 145.5 from the front of
# a 734.8 deep chassis is drawn at 589.3, and a strip centred there spans
# 587.35-591.25.

def test_a_label_agreeing_with_the_geometry_is_silent():
    d = device("top", 734.8, [0, 587.35], [444.5, 3.9],
               "Rack mounting surface - 5.73 in (14.55 cm) from the front")
    assert run(d) == []


def test_a_label_naming_the_wrong_edge_fires():
    """The 9906's real defect: right number, wrong edge. 5.73 in from the REAR
    of a 734.8 chassis is 589.3 from the front, nowhere near the strip."""
    d = device("top", 734.8, [0, 587.35], [444.5, 3.9],
               "Rack mounting surface - 5.73 in from the rear")
    out = run(d)
    assert len(out) == 1
    assert "589.3 mm from the front" in out[0], "the label's claim, restated from the front"
    assert "nothing is drawn there" in out[0]


def test_the_message_says_which_way_the_disagreement_runs():
    """Someone will have the label right and the geometry wrong, and someone
    else the other way round. The message has to serve both."""
    d = device("top", 734.8, [0, 100.0], [444.5, 3.9],
               "Rack mounting surface - 5.73 in from the front")
    out = run(d)
    assert len(out) == 1
    assert "145.5 mm from the front" in out[0]        # where the label points
    assert "630.9-634.8 mm from the front" in out[0]  # where the metal actually is


# ------------------------------------------------- left and right are opposite

def test_left_and_right_run_their_depth_axis_opposite_ways():
    """Two views of one axis from opposite sides. A feature 60 mm from the front
    of a 470 deep chassis sits at x = 410 on the LEFT and x = 60 on the RIGHT,
    so one manifest's coordinates cannot be copied to the other."""
    label = "Integral rack flange - 60 mm from the front"
    assert run(device("left", 470.0, [404.0, 0], [6.0, 88.2], label)) == []
    assert run(device("right", 470.0, [54.0, 0], [6.0, 88.2], label)) == []
    # and each fires on the other's coordinate
    assert len(run(device("left", 470.0, [54.0, 0], [6.0, 88.2], label))) == 1
    assert len(run(device("right", 470.0, [404.0, 0], [6.0, 88.2], label))) == 1


# ---------------------------------------------------------- what is NOT a claim

def test_a_bare_direction_word_is_not_a_claim_about_position():
    """"fitted from the rear" is an access direction and "rear-panel bracket" is
    a part name. Neither says where the thing sits within the view, and reading
    them as claims is how a rule earns a reputation for crying wolf. The trigger
    is a NUMBER WITH A UNIT, because a number is what can be wrong."""
    for label in ("Single fan tray - fitted from the rear",
                  "Air filter - right side, accessible from the rear",
                  "Rear-panel cable management bracket",
                  "Front-to-rear cooling path - inlet at the bottom front"):
        assert run(device("top", 734.8, [0, 587.35], [444.5, 3.9], label)) == [], label


def test_a_measurement_that_is_not_a_depth_is_ignored():
    """A label may quote a size or a weight. Anything longer than the face
    cannot be a distance along it."""
    d = device("top", 734.8, [0, 587.35], [444.5, 3.9],
               "Rack mounting surface - 5.73 in from the front, on a 40 in rack from the front")
    assert run(d) == []      # the 40 in exceeds the depth and is dropped


# --------------------------------------------------------------- the parsing

def test_two_measurements_in_one_label_are_both_checked():
    """"5.00 in and 9.45 in from the rear" is two claims sharing one anchor. A
    naive regex stops at the decimal point in the second number and silently
    checks only one of them."""
    view = {"views": {"bottom": {
        "size": {"w": 444.5, "h": 730.8},
        "panel": {"decor": [{"at": [0, 601.85], "size": [444.5, 3.9], "fill": "#9a9c9e"},
                            {"at": [0, 488.85], "size": [444.5, 3.9], "fill": "#9a9c9e"}]},
        "regions": [{"id": "rails", "label":
                     "Vertical rack rail locations - 5.00 in and 9.45 in from the front"}]}}}
    assert run(view) == []
    view["views"]["bottom"]["regions"][0]["label"] = (
        "Vertical rack rail locations - 5.00 in and 9.45 in from the rear")
    assert len(run(view)) == 2, "both claims are checked, not just the first"


def test_a_sentence_boundary_is_not_crossed_but_a_decimal_point_is():
    """The window that collects measurements before a 'from the X' anchor stops
    at a sentence break. A period followed by a space ends a sentence; a period
    followed by a digit is a decimal point."""
    d = device("top", 734.8, [0, 587.35], [444.5, 3.9],
               "Plate thickness is 3.0 mm. Mounting surface 5.73 in from the front")
    assert run(d) == [], "the 3.0 mm belongs to the previous sentence and is not a claim"


def test_one_position_stated_twice_warns_once():
    """"5.73 in (14.55 cm) from the front" is one measurement in two units."""
    d = device("top", 734.8, [0, 100.0], [444.5, 3.9],
               "Rack mounting surface - 5.73 in (14.55 cm) from the front")
    assert len(run(d)) == 1


# ------------------------------------------------------------- staying quiet

def test_a_face_with_nothing_drawn_on_it_has_no_opinion():
    """An undocumented face carrying only regions is not a defect - it is an
    honest empty face, and firing on it would punish saying what is known."""
    d = {"views": {"top": {"size": {"w": 444.5, "h": 734.8},
                           "regions": [{"id": "m", "label": "Surface 5.73 in from the front"}]}}}
    assert run(d) == []


def test_front_and_rear_views_have_no_depth_axis():
    """"12 mm from the front" on a FRONT view is not a position within it."""
    d = {"views": {"front": {"size": {"w": 442.0, "h": 88.2},
                             "panel": {"decor": [{"at": [0, 0], "size": [10.0, 10.0]}]},
                             "regions": [{"id": "m", "label": "Bezel 300 mm from the front"}]}}}
    assert run(d) == []
