"""A generated block must agree with the library it is generated for.

`expand.py` turns a compact block description into the placements, cutouts and
numerals a device.yaml carries longhand. The risk it introduces is not that it
fails loudly - it is that a subtly wrong model produces geometry that lints,
renders, and is wrong in a way that looks deliberate. So these tests hold the
model against blocks the library already contains, and against the registry the
pitch is supposed to come from.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import expand as E

LIB = ROOT / "library"
STD = E.load_standards(ROOT / "spec/schemas")


def placements(dev, group):
    d = yaml.safe_load((LIB / "devices" / dev / "device.yaml").read_text())
    out = [p for v in (d.get("views") or {}).values()
           for p in ((v.get("components") or {}).get("placements") or [])
           if p.get("group") == group]
    def n(p):
        tail = "".join(c for c in str(p["id"]).rsplit("-", 1)[-1] if c.isdigit())
        return int(tail) if tail else -1

    out.sort(key=n)
    return out


# (device, group, first index, count, block spec) - origins read off the files,
# so a failure means the MODEL disagrees, not that a number was mistyped here.
CASES = [
    ("ufispace/s9705-48d", "fabric", 0, 24,
     {"ref": "std/qsfp-dd@1", "at": [85.7, 9.65], "rows": 2, "row-pitch": 13.16,
      "pitch": {"registry": "qsfp-ganged"}, "gang": 2, "gutter": 13.16}),
    ("ufispace/s9705-48d", "fabric", 24, 24,
     {"ref": "std/qsfp-dd@1", "at": [85.7, 53.48], "rows": 2, "row-pitch": 13.16,
      "pitch": {"registry": "qsfp-ganged"}, "gang": 2, "gutter": 13.16}),
    ("ufispace/s9620-54dc", "sfp28", 0, 40,
     {"ref": "std/sfp-ganged@1", "at": [24.0, 9.8], "rows": 2, "row-pitch": 15.0,
      "pitch": "registry", "gang": 12, "gutter": 2.3}),
]


@pytest.mark.parametrize("dev,group,start,count,spec", CASES)
def test_a_generated_block_lands_where_the_library_puts_it(dev, group, start, count, spec):
    real = placements(dev, group)[start:start + count]
    block = dict(spec, id=group, count=count)
    block["number-from"] = int(str(real[0]["id"]).rsplit("-", 1)[-1])
    # the turn each row carries, read off the file - since the stacked-cage
    # convention (docs/pluggables-3d-design.md, S3) that is the BOTTOM row
    for key, row in (("top", real[::2]), ("bottom", real[1::2])):
        rots = {p.get("rotate", 0) for p in row}
        if rots != {0}:
            block.setdefault("rotate", {})[key] = sorted(rots)[-1]
    gen = [p for p in E.block_items(block, LIB, STD)[0] if p.get("group") == group]
    assert [p["id"] for p in gen] == [p["id"] for p in real]
    assert [p.get("rotate", 0) for p in gen] == [p.get("rotate", 0) for p in real]
    for r, g in zip(real, gen):
        assert abs(r["at"][0] - g["at"][0]) <= 0.011, (r["id"], r["at"], g["at"])
        assert abs(r["at"][1] - g["at"][1]) <= 0.011, (r["id"], r["at"], g["at"])


def test_a_lamp_brackets_its_ganged_shell_rather_than_following_its_port():
    """The offset a lamp takes is not always from its own port.

    On s9705-48d the lamps bracket each two-column shell: the left column's lamp
    sits 3.97mm outside it to the LEFT, the right column's 20.97mm to the RIGHT.
    Read as a single per-port offset, half the lamps land 21mm from where the
    device puts them - and they would still lint, still render, and still look
    deliberate. The numerals print with their lamps and take the same list.

    Checked against every one of the 48, so the alternation cannot silently
    apply to the first shell and stop.
    """
    real = {p["id"]: p for p in placements("ufispace/s9705-48d", "port-leds")
            if p["id"].startswith("led-p")}
    nums = {}
    d = yaml.safe_load((LIB / "devices/ufispace/s9705-48d/device.yaml").read_text())
    for s in (d["views"]["front"].get("silkscreen") or []):
        if str(s.get("for", "")).startswith("port-"):
            nums[s["for"]] = s

    led = {"ref": "common/led-dot@1", "id-format": "led-port-{n}",
           "dx-by-col": [-3.97, 20.97], "dy-top": 3.7, "dy-bottom": 4.68,
           "group": "port-leds"}
    num = {"dx-by-col": [-2.97, 21.97], "dy-top": 2.4, "dy-bottom": 9.43,
           "font-size": 1.9, "anchor": "middle", "fill": "#f2f2f2"}
    block = {"id": "fabric", "ref": "std/qsfp-dd@1", "at": [85.7, 9.65],
             "count": 24, "rows": 2, "row-pitch": 13.16, "gang": 2,
             "gutter": 13.16, "pitch": {"registry": "qsfp-ganged"},
             "led": led, "numerals": num, "number-from": 0}
    gen, _, silks = E.block_items(block, LIB, STD)
    lamps = [p for p in gen if p.get("group") == "port-leds"]
    assert len(lamps) == 24
    for g in lamps:
        r = real[g["id"]]
        assert abs(r["at"][0] - g["at"][0]) <= 0.011, (g["id"], r["at"], g["at"])
        assert abs(r["at"][1] - g["at"][1]) <= 0.011, (g["id"], r["at"], g["at"])
    for s in silks:
        r = nums[s["for"]]
        assert abs(r["at"][0] - s["at"][0]) <= 0.011, (s["for"], r["at"], s["at"])


def test_a_block_lands_where_its_marker_is_and_not_at_the_end():
    """Paint order is meaning, and the device fingerprint is order-sensitive, so
    a tool that appends its output reports a geometry change on a file nothing
    moved in. The author puts `{block: <id>}` where the items belong."""
    layout = {"views": {"front": {"components": {
        "placements": [{"id": "first"}, {"block": "p"}, {"id": "last"}],
        "blocks": [{"id": "p", "ref": "std/sfp-ganged@1", "at": [0, 0],
                    "count": 2, "rows": 1, "pitch": "registry"}]}}}}
    out = E.expand(layout, LIB, STD)
    ids = [p["id"] for p in out["views"]["front"]["components"]["placements"]]
    assert ids == ["first", "port-0", "port-1", "last"]


def test_a_named_mark_is_centred_on_its_anchor():
    """The reason to have named marks at all, beyond not writing 468 triangles.

    The hand-drawn arrow pairs in this library sit 0.3mm BELOW their `at`, so
    aligning one with anything means knowing that and compensating - which is
    how a legend row came to be centred on nothing at all. A named mark's ink
    is centred on its anchor, so `at` means what a person assumes it means.
    """
    p, filled = E.mark_path("arrow-pair", 1.2, 1.4)
    assert filled, "a solid symbol must be filled, not stroked"
    ys = [float(t) for t in p.replace("M", " ").replace("L", " ")
          .replace("Z", " ").split()][1::2]
    assert abs((min(ys) + max(ys)) / 2) < 1e-9, "ink must straddle y=0"
    xs = [float(t) for t in p.replace("M", " ").replace("L", " ")
          .replace("Z", " ").split()][0::2]
    assert abs((min(xs) + max(xs)) / 2) < 1e-9, "ink must straddle x=0"
    up, _ = E.mark_path("arrow-up", 2.0)
    assert up.count("L") == 2 and up.endswith("Z")


def test_an_unknown_mark_is_refused_rather_than_drawn_as_nothing():
    """A typo must not silently produce an empty legend - which is exactly what
    a missing font glyph does, and the reason these are paths and not text."""
    with pytest.raises(SystemExit) as e:
        E.mark_path("arrow-sideways")
    assert "unknown silkscreen mark" in str(e.value)


def test_marks_expand_on_views_that_have_no_blocks():
    """Marks are not a property of a port block - a rear face with two legends
    and no repeating anything still wants them."""
    layout = {"views": {"rear": {"silkscreen": [
        {"at": [10.0, 5.0], "mark": "arrow-up", "size": 1.6, "for": "fan-0"}]}}}
    out = E.expand(layout, LIB, STD)
    m = out["views"]["rear"]["silkscreen"][0]
    assert "mark" not in m and m["path"].startswith("M ")
    assert m["for"] == "fan-0"


def test_the_registry_states_pitch_two_ways_and_both_are_read():
    """`qsfp-ganged` carries an explicit pitch beside a narrower opening because
    its cages share a wall. `sfp-ganged` carries none, because for that family
    `w` IS the pitch and adjacent instances abut. Reading only one key finds one
    family and silently narrows the other."""
    p, how = E.registry_pitch(LIB, STD, "std/qsfp-dd@1", "qsfp-ganged")
    assert (p, how) == (19.0, "pitch")
    assert STD["qsfp-ganged"]["w"] < p, "the opening is narrower than the pitch"
    p, how = E.registry_pitch(LIB, STD, "std/sfp-ganged@1")
    assert p == 14.25 and how.startswith("w")


def test_a_pitch_that_cannot_be_looked_up_is_refused_not_guessed():
    """A single-cage standard states no pitch. The tool must say so rather than
    fall back to the opening width, which would be wrong by the wall thickness
    on every port in the block."""
    with pytest.raises(SystemExit) as e:
        E.block_items({"id": "x", "ref": "std/osfp@1", "at": [0, 0], "count": 4,
                       "rows": 2, "row-pitch": 10.0, "pitch": {"registry": "osfp"}},
                      LIB, STD)
    assert "no standard that states one" in str(e.value)


def test_a_generated_cutout_is_the_aperture_and_not_a_second_measurement():
    """The same rule #5 holds for hand-authored holes: a cutout restates the
    opening its component already declares. Generating it is the cheapest way to
    make that true by construction."""
    block = {"id": "fabric", "ref": "std/qsfp-dd@1", "at": [85.7, 9.65],
             "count": 4, "rows": 2, "row-pitch": 13.16,
             "pitch": {"registry": "qsfp-ganged"}, "cutouts": True}
    pl, cuts, _ = E.block_items(block, LIB, STD)
    assert len(cuts) == 4
    ap = E.aperture_of(LIB, STD, "std/qsfp-dd@1")
    for c, p in zip(cuts, pl):
        assert c["id"] == p["id"]
        assert c["size"] == [ap[0][0], ap[0][1]]
        assert c["at"] == p["at"], "unrotated, the hole sits at the placement"


def test_a_generated_lamp_gets_a_hole_too():
    """FOUND BY THE FIRST FACE THIS TOOL EVER GENERATED. It punched 32 ports and
    left 32 lamps unpunched, and lint said so 32 times: on a panel that declares
    cutouts, a lamp needs one as much as the port beside it.

    It is the same failure the tool exists to prevent, committed by the tool -
    a rule applied to the thing being counted and not to what gets emitted
    alongside it. A loop does not get tired, but it does only do what it was
    told, and it had been told about ports.
    """
    led = {"ref": "common/led-dot@1", "id-format": "led-p{n}", "dx": -3.0,
           "dy": 2.0, "group": "port-leds"}
    block = {"id": "p", "ref": "std/qsfp-dd@1", "at": [10.0, 10.0], "count": 4,
             "rows": 2, "row-pitch": 13.0, "pitch": {"registry": "qsfp-ganged"},
             "cutouts": True, "led": led}
    pl, cuts, _ = E.block_items(block, LIB, STD)
    ports = [p for p in pl if p["id"].startswith("port-")]
    lamps = [p for p in pl if p["id"].startswith("led-p")]
    assert len(ports) == 4 and len(lamps) == 4
    holes = {c["id"] for c in cuts}
    assert holes == {p["id"] for p in ports} | {p["id"] for p in lamps}, \
        "every generated part on a punched panel needs its own opening"

    lamp_cut = next(c for c in cuts if c["id"] == "led-p0")
    lamp = next(p for p in lamps if p["id"] == "led-p0")
    assert lamp_cut["at"] == lamp["at"], "the hole sits where the lamp sits"
    assert lamp_cut["size"] == [2.0, 2.0], "the hole is the lamp's own aperture"
    assert lamp_cut["shape"] == "circle"


def test_a_lamp_with_several_windows_is_left_for_a_person_to_punch():
    """THE FIX FOR THE ABOVE WAS WRITTEN, RUN, AND WAS WRONG, so this holds the
    line it taught.

    A lamp column holding four windows in one body has no single aperture to
    derive. The size lookup falls back to the BODY, so the generator emitted one
    1.7 x 10.7 hole and called it a circle - a 1:6 round hole, and a claim that
    the metal carries one long slot rather than four windows, which the vendor's
    images at 10 px/mm cannot settle either way. It silenced 32 lint warnings by
    drawing something false, which is strictly worse than the warnings.

    Where a component declares more than one opening the tool now punches
    nothing and the warning stands. A rule that cannot be satisfied honestly
    should stay unsatisfied.
    """
    multi = LIB / "components/edgecore/qsfpdd-lane-leds/v1/contract.yaml"
    if not multi.exists():
        pytest.skip("multi-window lamp part not in this library")
    assert not E._single_opening(LIB, STD, "edgecore/qsfpdd-lane-leds@1")
    led = {"ref": "edgecore/qsfpdd-lane-leds@1", "id-format": "led-p{n}",
           "dx": -3.0, "dy": 0.0, "group": "port-leds"}
    block = {"id": "p", "ref": "std/qsfp-dd@1", "at": [10.0, 10.0], "count": 4,
             "rows": 2, "row-pitch": 13.0, "pitch": {"registry": "qsfp-ganged"},
             "cutouts": True, "led": led}
    _, cuts, _ = E.block_items(block, LIB, STD)
    assert {c["id"] for c in cuts} == {f"port-{i}" for i in range(4)}, \
        "ports are punched; a four-window lamp column is not guessed at"


def test_a_block_with_no_cutouts_generates_no_lamp_holes():
    """The rule is conditional on the panel declaring cutouts at all. Punching
    holes into a face that has none would invent a construction the device does
    not have."""
    led = {"ref": "common/led-dot@1", "id-format": "led-p{n}", "dx": -3.0}
    block = {"id": "p", "ref": "std/qsfp-dd@1", "at": [0, 0], "count": 2,
             "rows": 1, "pitch": {"registry": "qsfp-ganged"}, "led": led}
    _, cuts, _ = E.block_items(block, LIB, STD)
    assert cuts == []


def test_numbering_covers_the_whole_block_or_none_of_it():
    """The defect this tool exists to make impossible: a numbering rule applied
    to fifty ports and stopped four short. A loop does not get tired."""
    block = {"id": "p", "ref": "std/sfp-ganged@1", "at": [0, 0], "count": 54,
             "rows": 2, "row-pitch": 15.0, "pitch": "registry",
             "numerals": {"dx": 1.0, "dy": -2.0}}
    _, _, silks = E.block_items(block, LIB, STD)
    assert [s["text"] for s in silks] == [str(i) for i in range(54)]
    assert {s["for"] for s in silks} == {f"port-{i}" for i in range(54)}


def test_numeral_offsets_can_key_off_the_ROW_as_well_as_the_column():
    """The gap two separate modelling runs each hand-wrote 48 lines around.

    A face that prints `1 (up)(down) 2` on ONE baseline between its two rows puts
    the odd port's numeral left of centre and the even port's right of it: same
    y, different x, keyed to the ROW. `dx-by-col` cannot say that, so both runs
    wrote the marks out longhand on a face where everything else generated.

    Checked against the committed device rather than an invented case - these are
    the real offsets, and all 32 numerals land on the millimetre.
    """
    # FROZEN from the device that first exercised this - real numbers, and no
    # longer read from a library entry that is free to be remodelled.
    real = {f"port-{n}": {"at": [round(38.3 + (n - 1) // 2 * 19.0
                                  + ((n - 1) // 2) // 2 * 6.0
                                  + (5.9 if n % 2 else 13.1), 2),
                          24.92 if n % 2 else 24.92]}
            for n in range(1, 33)}
    block = {"id": "qsfpdd-400g", "ref": "std/qsfp-dd@1", "at": [38.3, 12.0],
             "count": 32, "rows": 2, "row-pitch": 14.5, "gang": 2, "gutter": 6.0,
             "pitch": {"registry": "qsfp-ganged"}, "number-from": 1,
             "numerals": {"dx-by-row": [5.9, 13.1], "dy-top": 12.92,
                          "dy-bottom": -1.58, "font-size": 1.9,
                          "anchor": "middle", "fill": "#e8eaec"}}
    _, _, silks = E.block_items(block, LIB, STD)
    assert len(silks) == 32
    for s in silks:
        r = real[s["for"]]
        assert abs(r["at"][0] - s["at"][0]) <= 0.011, (s["for"], r["at"], s["at"])
        assert abs(r["at"][1] - s["at"][1]) <= 0.011, (s["for"], r["at"], s["at"])


def test_row_and_column_offsets_add_when_both_are_given():
    """A numeral on such a face is displaced by which shell it sits in AND which
    row it names, so the two lists compose rather than one overriding."""
    block = {"id": "p", "ref": "std/sfp-ganged@1", "at": [0.0, 0.0], "count": 4,
             "rows": 2, "row-pitch": 10.0, "pitch": "registry",
             "numerals": {"dx-by-col": [1.0, 2.0], "dx-by-row": [10.0, 20.0]}}
    _, _, silks = E.block_items(block, LIB, STD)
    # port 0: col 0 row 0 -> 1.0 + 10.0 ; port 1: col 0 row 1 -> 1.0 + 20.0
    assert silks[0]["at"][0] == 11.0, silks[0]
    assert silks[1]["at"][0] == 21.0, silks[1]


def test_a_block_hands_its_attrs_to_every_port_but_not_to_its_lamps():
    """TWO MEDIA, ONE NUMBERING. The MaiaEdge Port Extender numbers 48 SFP28
    tenant ports and 8 QSFP28 uplinks 1-56 in one space, so both blocks share
    one group and the group cannot say which media a port is. Each port has to
    carry its own - which, placed by hand, it always could, and generated by a
    block it could not. The lamps a block generates are not ports and take none."""
    block = {"id": "ports", "ref": "std/sfp-ganged@1", "at": [0, 0], "count": 4,
             "rows": 2, "row-pitch": 13.73, "pitch": 14.25, "number-from": 1,
             "attrs": {"media": "sfp28", "speed": "25g"},
             "led": {"ref": "common/led-dot@1", "dx": 6.0, "dy-top": -3.0, "dy-bottom": 11.0}}
    pl, _, _ = E.block_items(block, LIB, STD)
    ports = [p for p in pl if p["id"].startswith("port-")]
    lamps = [p for p in pl if not p["id"].startswith("port-")]
    assert len(ports) == 4 and len(lamps) == 4
    assert all(p.get("attrs") == {"media": "sfp28", "speed": "25g"} for p in ports)
    assert all("attrs" not in p for p in lamps)
    # each port's attrs is its own - editing one must not reach the others
    ports[0]["attrs"]["speed"] = "10g"
    assert ports[1]["attrs"]["speed"] == "25g"
