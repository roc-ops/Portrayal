"""The benchmark harness: the projection, the matching, and the tiling.

A benchmark is a machine for producing confident numbers, so the parts of it
that can be silently wrong are worth more tests than the parts that cannot. All
three of these can:

  THE PROJECTION turns a placement into a pixel box. An anchor read as a centre,
  a rotation that forgets to swap the box, a y-axis the other way up - each
  produces a tidy JSON file full of plausible numbers and no complaint.

  THE MATCHING decides what counts as found. Greedy-by-confidence with one
  prediction to one box is what stops fifty overlapping guesses on one cage from
  scoring fifty hits.

  THE TILING decides what the model is even shown. A seam that drops the cage
  straddling it would show up as a model that cannot see, not a harness that did
  not look.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))

import benchdata  # noqa: E402
import benchgt  # noqa: E402
import benchscore  # noqa: E402
import benchvlm  # noqa: E402


# ---- the projection ---------------------------------------------------------

def test_a_placement_is_anchored_at_its_top_left():
    """render.py translates to `at` and rotates about the centre, so `at` is the
    corner. Reading it as a centre puts every box half a part up and left."""
    view = {"components": {"placements": [
        {"ref": "x/y@1", "id": "p1", "at": [10.0, 4.0]}]}}
    b = benchgt.boxes_mm(view, _lib(), {})[0]
    assert b["mm"][0] == 10.0 and b["mm"][1] == 4.0


def test_a_quarter_turn_swaps_the_box_and_a_half_turn_does_not():
    """A vertically-mounted RJ45 is 11 x 12.7, not 12.7 x 11 - and a 180 is the
    same footprint, which is why 168 placements on one device carry it."""
    def mm(rot):
        view = {"components": {"placements": [
            {"ref": "x/y@1", "id": "p", "at": [0, 0], "rotate": rot}]}}
        return benchgt.boxes_mm(view, _lib(), {})[0]["mm"][2:]

    assert mm(None) == [12.7, 11.0]
    assert mm(180) == [12.7, 11.0]
    assert mm(90) == [11.0, 12.7]
    assert mm(270) == [11.0, 12.7]


def test_a_part_the_library_does_not_have_is_left_out_not_guessed():
    view = {"components": {"placements": [
        {"ref": "no/such@9", "id": "p", "at": [0, 0]}]}}
    assert benchgt.boxes_mm(view, _lib(), {}) == []


def test_each_box_says_what_the_library_calls_it():
    """The `term` is what keeps four-pixel lamps out of a port score."""
    view = {"components": {"placements": [
        {"ref": "x/y@1", "id": "p", "at": [0, 0], "group": "ports"}]}}
    groups = {"ports": {"term": "Port"}}
    assert benchgt.boxes_mm(view, _lib(), groups)[0]["term"] == "Port"


def test_a_placement_in_no_group_has_no_term_rather_than_a_wrong_one():
    view = {"components": {"placements": [{"ref": "x/y@1", "id": "p", "at": [0, 0]}]}}
    assert benchgt.boxes_mm(view, _lib(), {"ports": {"term": "Port"}})[0]["term"] is None


def test_the_projection_is_origin_plus_millimetres_times_scale():
    assert benchgt.project([10, 4, 12.7, 11.0], [100, 20], 2.0) == \
        [120.0, 28.0, 25.4, 22.0]


def test_the_projection_puts_the_panel_corner_at_the_origin():
    """y grows downward in both systems; a flip here would mirror every device
    about its middle and still look tidy."""
    assert benchgt.project([0, 0, 1, 1], [7, 9], 3.0)[:2] == [7.0, 9.0]


# ---- the matching -----------------------------------------------------------

def test_identical_boxes_are_one_and_disjoint_boxes_are_zero():
    assert benchscore.iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert benchscore.iou([0, 0, 10, 10], [20, 20, 10, 10]) == 0.0


def test_touching_boxes_do_not_overlap():
    """Cages are ganged edge to edge, so this is the common case, not an edge one."""
    assert benchscore.iou([0, 0, 10, 10], [10, 0, 10, 10]) == 0.0


def test_a_port_found_fifty_times_is_found_once():
    """Without one-to-one matching, the way to a perfect recall is to guess a
    lot, and precision is what is supposed to punish that."""
    truth = [[0, 0, 10, 10]]
    preds = [[0, 0, 10, 10, 1.0]] * 50
    hits, _ = benchscore.match(preds, truth, 0.5)
    assert hits == 1
    assert benchscore.prf(hits, 50, 1)[0] == 0.02


def test_the_surest_prediction_picks_first():
    """Two predictions, one box, and the confident one should take it."""
    truth = [[0, 0, 10, 10]]
    weak = [1, 1, 10, 10, 0.1]
    strong = [0, 0, 10, 10, 0.9]
    _, pairs = benchscore.match([weak, strong], truth, 0.5)
    assert pairs[0][0] is strong


def test_a_near_miss_below_the_threshold_is_not_a_hit():
    hits, _ = benchscore.match([[0, 0, 10, 10, 1.0]], [[6, 0, 10, 10]], 0.5)
    assert hits == 0


def test_finding_nothing_scores_zero_rather_than_dividing_by_it():
    assert benchscore.prf(0, 0, 10) == (0.0, 0.0, 0.0)
    assert benchscore.prf(0, 10, 0) == (0.0, 0.0, 0.0)


def test_a_device_that_was_not_run_is_not_a_device_that_failed():
    """The distinction that nearly went into a commit message as the result:
    eight held-out faceplates scored against all thirty-one read as F1 0.357
    where the detector had actually managed 0.892 on what it was given."""
    truth = {
        "a/one": _truth([[0, 0, 10, 10]]),
        "b/two": _truth([[0, 0, 10, 10]]),
    }
    rows, tot, unrun = benchscore.score_all(truth, {"a/one": [[0, 0, 10, 10, 1.0]]})
    assert [r["device"] for r in rows] == ["a/one"]
    assert unrun == ["b/two"]
    assert benchscore.prf(*tot)[2] == 1.0


def test_a_device_run_and_found_nothing_is_scored_as_a_zero():
    """An empty list is an answer. Treating it like an absent device would let a
    detector improve its average by declining to answer."""
    truth = {"a/one": _truth([[0, 0, 10, 10]])}
    rows, _, unrun = benchscore.score_all(truth, {"a/one": []})
    assert unrun == []
    assert rows[0]["f1"] == 0.0


def test_only_the_named_class_is_scored():
    """Half the truth is lamps four pixels across; scoring them would report the
    figure's resolution as the model's eyesight."""
    truth = {"a/one": {"px_per_mm": 3.0, "gate1_error": 0.0, "origin": [0, 0],
                       "box": [100, 50], "figure": "f.png", "boxes": [
                           {"px": [0, 0, 10, 10], "term": "Port"},
                           {"px": [20, 0, 4, 4], "term": "LED"}]}}
    rows, _, _ = benchscore.score_all(truth, {"a/one": [[0, 0, 10, 10, 1.0]]})
    assert rows[0]["truth"] == 1 and rows[0]["f1"] == 1.0


def _truth(boxes):
    return {"px_per_mm": 3.0, "gate1_error": 0.0, "origin": [0, 0],
            "box": [100, 50], "figure": "f.png",
            "boxes": [{"px": b, "term": "Port"} for b in boxes]}


def test_the_error_is_reported_in_millimetres_not_pixels():
    """IoU says two rectangles agree; a modelling pipeline needs to know the
    proposed number would be a quarter of a millimetre out. At 2 px/mm a box
    four pixels adrift is two millimetres, and only one of those is a fact
    about the device."""
    truth = {"a/one": _truth([[0, 0, 10, 10]])}
    truth["a/one"]["px_per_mm"] = 2.0
    err = benchscore.mm_error(truth, {"a/one": [[4, 0, 10, 10, 1.0]]}, thresh=0.3)
    assert err["dx"] == [2.0]
    assert err["dy"] == [0.0]


def test_no_matches_is_not_the_same_as_no_error():
    """An empty quantile must not print as 0.00 mm - that would read as a
    perfect detector where in fact nothing was found at all."""
    assert benchscore.quantile([], 0.5) is None
    assert benchscore.quantile([1.0], 0.5) == 1.0


# ---- the tiling -------------------------------------------------------------

def test_a_panel_is_covered_end_to_end():
    """Every column of a 1455 px panel must fall inside some tile, or the ports
    in the gap are unfindable and the score blames the model."""
    ts = benchvlm.tiles(1455, 145)
    covered = set()
    for x, _, w, _ in ts:
        covered |= set(range(x, x + w))
    assert covered == set(range(1455))


def test_the_tiles_overlap_so_a_cage_on_a_seam_is_whole_somewhere():
    ts = benchvlm.tiles(1455, 145, overlap=0.25)
    assert len(ts) > 1
    assert ts[1][0] < ts[0][0] + ts[0][2], "the second tile must start inside the first"


def test_a_panel_shorter_than_a_tile_is_one_tile():
    assert benchvlm.tiles(200, 145) == [(0, 0, 200, 145)]


def test_the_last_tile_is_pulled_back_rather_than_running_off_the_end():
    for x, _, w, _ in benchvlm.tiles(1455, 145):
        assert x >= 0 and x + w <= 1455


# ---- reading the model's reply ----------------------------------------------

def test_boxes_come_back_in_figure_pixels():
    """The model answers in the enlarged tile's coordinates; a box at (40, 20)
    of a 4x tile whose corner sits at (100, 10) is at (110, 15) in the figure."""
    got = benchvlm.parse_boxes('{"ports": [{"bbox": [40, 20, 80, 60]}]}',
                               4.0, 4.0, 100, 10)
    assert got[0][:4] == [110.0, 15.0, 10.0, 10.0]


def test_a_fenced_reply_with_prose_still_parses():
    """Refusing these would measure the model's manners, not its eyesight."""
    reply = ('Sure! Here are the ports I found:\n```json\n'
             '{"ports": [{"bbox": [0, 0, 8, 8]}]}\n```\nHope that helps.')
    assert len(benchvlm.parse_boxes(reply, 1.0, 1.0, 0, 0)) == 1


def test_an_empty_answer_is_no_boxes_and_not_a_crash():
    assert benchvlm.parse_boxes('{"ports": []}', 1.0, 1.0, 0, 0) == []
    assert benchvlm.parse_boxes('I cannot help with that.', 1.0, 1.0, 0, 0) == []


def test_a_backwards_box_is_straightened_rather_than_dropped():
    got = benchvlm.parse_boxes('{"ports": [{"bbox": [80, 60, 40, 20]}]}',
                               1.0, 1.0, 0, 0)
    assert got[0][:4] == [40.0, 20.0, 40.0, 40.0]


def test_a_zero_area_box_is_not_a_detection():
    assert benchvlm.parse_boxes('{"ports": [{"bbox": [5, 5, 5, 9]}]}',
                                1.0, 1.0, 0, 0) == []


def test_the_same_cage_seen_in_two_tiles_is_merged():
    a = [10, 10, 20, 20, 1.0]
    b = [11, 10, 20, 20, 1.0]
    assert len(benchvlm.merge([a, b])) == 1


def test_two_neighbouring_cages_are_not_merged():
    """Ganged cages sit edge to edge, and merging them would quietly halve the
    count on every device in the set."""
    a = [10, 10, 20, 20, 1.0]
    b = [30, 10, 20, 20, 1.0]
    assert len(benchvlm.merge([a, b])) == 2


# ---- the training tiles -----------------------------------------------------

def test_a_cage_wholly_inside_a_tile_keeps_its_whole_box():
    assert benchdata.clip([100, 10, 20, 20], 90, 0, 200, 145) == (10, 10, 20, 20)


def test_three_quarters_of_a_cage_is_still_a_cage():
    """The threshold has to admit the common case - a cage clipped by a seam is
    the reason the tiles overlap in the first place."""
    assert benchdata.clip([85, 10, 20, 20], 90, 0, 200, 145) == (0, 10, 15, 20)


def test_a_sliver_on_a_seam_is_not_labelled_as_a_cage():
    """Half a cage teaches a detector that half a cage is a cage, and on a face
    of forty-eight identical cages it will apply that everywhere."""
    assert benchdata.clip([80, 10, 20, 20], 90, 0, 200, 145) is None


def test_a_cage_the_tile_does_not_touch_is_not_in_it():
    assert benchdata.clip([500, 10, 20, 20], 0, 0, 200, 145) is None


def test_the_label_is_in_tile_coordinates_not_panel_ones():
    """The tile is what the detector sees, so an unshifted label puts every box
    on the wrong side of every tile after the first."""
    x, y, _, _ = benchdata.clip([210, 30, 20, 20], 200, 10, 200, 145)
    assert (x, y) == (10, 20)


def test_the_dataset_tiles_the_way_the_harness_does():
    """Train and test must see the same shape, or the score is of another task."""
    assert benchdata.tiles(1455, 145) == benchvlm.tiles(1455, 145)


# ---- a library of one part, so the tests state their own inputs -------------

def _lib():
    import tempfile
    d = pathlib.Path(tempfile.mkdtemp())
    c = d / "components" / "x" / "y" / "v1"
    c.mkdir(parents=True)
    (c / "contract.yaml").write_text(
        "name: y\nkind: component\nsize: {w: 12.7, h: 11.0, d: 16.0}\n")
    return str(d)
