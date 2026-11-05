"""The terminals and studs of the Amphenol Network Solutions 300CB08 panels are places a lug lands.

The panel's output terminal draws a BATT screw above an RTN screw and its input terminal draws two studs one above the other,
and each used to be art only, so nothing could be landed on them. The installation guide says what lands on each: a single-hole
lug on each output screw, and a dual-hole lug on the two studs of an input terminal, which it prints on 1 inch centres in the
specification table, the lug reference guide and the callout of every rear view.

  - amphenol-ns/output-terminal composes common/terminal-screw-34@1 once for each drawn screw, so each screw presents the
    registered `terminal-stud` key that generic/ring-lug@1 mates;
  - amphenol-ns/input-stud-pair presents `stud-pair-1` over two such screws exactly one inch apart, the pair that
    generic/two-hole-lug-1@1 mates, and each screw is still a seat a ring lug lands on;
  - the composed screws stand inside the boxes the skins already draw, and no skin is redrawn;
  - the records file keeps no row for a part that now presents a key.

These read the contracts, the registry and the records file. They read no library/dist and render nothing.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMAS = ROOT / "spec/schemas"

SCREW = "common/terminal-screw-34@1"
RING_LUG = "generic/ring-lug@1"
TWO_HOLE_LUG = "generic/two-hole-lug-1@1"
OUTPUT_TERMINAL = "amphenol-ns/output-terminal@1"
STUD_PAIR = "amphenol-ns/input-stud-pair@1"
FEED = "amphenol-ns/input-feed-studs@1"
INCH = 25.4
EPS = 0.01


def contract(ref):
    name, major = ref.split("@")
    return yaml.safe_load((LIB / "components" / name / f"v{major}" / "contract.yaml").read_text())


def registry():
    return yaml.safe_load((SCHEMAS / "connectors.yaml").read_text())["interfaces"]


def mates(ref):
    found = contract(ref).get("mates")
    return [found] if isinstance(found, str) else found or []


def centre(part):
    half = contract(part["ref"])["size"]
    return (part["at"][0] + half["w"] / 2, part["at"][1] + half["h"] / 2)


def inside(point, element):
    (x, y), (ex, ey), (w, h) = point, element["at"], element["size"]
    return ex - EPS <= x <= ex + w + EPS and ey - EPS <= y <= ey + h + EPS


def screws(ref):
    return [p for p in contract(ref).get("parts") or [] if p["ref"] == SCREW]


def test_the_screw_presents_the_stud_key_and_a_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert "terminal-stud" in registry()
    assert "terminal-stud" in mates(RING_LUG)
    assert contract(RING_LUG)["class"] == "port"


def test_the_output_terminal_composes_one_screw_in_each_drawn_screw_box():
    data = contract(OUTPUT_TERMINAL)
    placed = screws(OUTPUT_TERMINAL)
    drawn = [data["elements"]["batt"], data["elements"]["rtn"]]
    assert len(placed) == len(drawn) == 2
    for part, element in zip(placed, drawn):
        assert inside(centre(part), element), (part["id"], centre(part), element)
        assert part.get("lift"), f"{part['id']}: the screw stands on its drawn head, so it is lifted"
    assert placed[0]["at"][1] < placed[1]["at"][1], "BATT is the upper screw, RTN the lower"
    assert len({p["id"] for p in placed}) == 2


def test_the_output_terminal_screws_stand_above_the_heads_the_skin_relief_draws():
    data = contract(OUTPUT_TERMINAL)
    heads = {f["node"]: f["cyl"] for f in data["relief"]["features"] if f["node"] in ("batt", "rtn")}
    placed = screws(OUTPUT_TERMINAL)
    assert len(placed) == 2
    for part, node in zip(placed, ("batt", "rtn")):
        assert part["lift"] == pytest.approx(heads[node]), (node, part["lift"], heads[node])


def test_the_stud_pair_presents_the_one_inch_pair_over_two_screws():
    data = contract(STUD_PAIR)
    spec = registry()[data["interface"]]
    assert data["interface"] == "stud-pair-1"
    assert spec["spans"] == {"interface": "terminal-stud", "count": 2}
    placed = screws(STUD_PAIR)
    assert len(placed) == 2
    (ax, ay), (bx, by) = centre(placed[0]), centre(placed[1])
    assert ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 == pytest.approx(INCH, abs=EPS)
    assert data["connection-points"]["mate"]["at"] == pytest.approx([(ax + bx) / 2, (ay + by) / 2], abs=EPS)
    assert placed[0]["lift"] == placed[1]["lift"]


def test_the_stud_pair_screws_stand_inside_the_drawn_studs():
    data = contract(STUD_PAIR)
    placed = screws(STUD_PAIR)
    assert len(placed) == 2
    for part, element in zip(placed, (data["elements"]["stud-top"], data["elements"]["stud-bottom"])):
        assert inside(centre(part), element), (part["id"], centre(part), element)


def test_the_stud_pair_seats_at_the_height_its_screws_present():
    data = contract(STUD_PAIR)
    head = contract(SCREW)["relief"]["features"][0]["cyl"]
    lifts = {p["lift"] for p in screws(STUD_PAIR)}
    assert len(lifts) == 1
    assert data["connection-points"]["mate"]["seat-out"] == pytest.approx(lifts.pop() + head)


def test_a_two_hole_lug_one_inch_across_mates_the_pair():
    iface = contract(STUD_PAIR)["interface"]
    assert contract(TWO_HOLE_LUG)["class"] == "port"
    assert iface in mates(TWO_HOLE_LUG)


def test_a_part_that_presents_a_key_keeps_no_exception_row():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    held = {(r["part"], r["code"]) for r in rows}
    for ref in (OUTPUT_TERMINAL, FEED):
        assert (ref, "C20") not in held, f"{ref} presents a key and a lug lands on it: its C20 row is stale"
