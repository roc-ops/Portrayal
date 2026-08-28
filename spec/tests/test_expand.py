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
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import expand as E  # noqa: E402

LIB = ROOT / "library"
STD = E.load_standards(ROOT / "spec/schemas")


def placements(dev, group):
    d = yaml.safe_load((LIB / "devices" / dev / "device.yaml").read_text())
    out = [p for v in (d.get("views") or {}).values()
           for p in ((v.get("components") or {}).get("placements") or [])
           if p.get("group") == group]
    out.sort(key=lambda p: int(str(p["id"]).rsplit("-", 1)[-1]))
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
    rots = {p.get("rotate", 0) for p in real[::2]}
    if rots != {0}:
        block["rotate"] = {"top": sorted(rots)[-1]}
    gen = [p for p in E.block_items(block, LIB, STD)[0] if p.get("group") == group]
    assert [p["id"] for p in gen] == [p["id"] for p in real]
    assert [p.get("rotate", 0) for p in gen] == [p.get("rotate", 0) for p in real]
    for r, g in zip(real, gen):
        assert abs(r["at"][0] - g["at"][0]) <= 0.011, (r["id"], r["at"], g["at"])
        assert abs(r["at"][1] - g["at"][1]) <= 0.011, (r["id"], r["at"], g["at"])


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


def test_numbering_covers_the_whole_block_or_none_of_it():
    """The defect this tool exists to make impossible: a numbering rule applied
    to fifty ports and stopped four short. A loop does not get tired."""
    block = {"id": "p", "ref": "std/sfp-ganged@1", "at": [0, 0], "count": 54,
             "rows": 2, "row-pitch": 15.0, "pitch": "registry",
             "numerals": {"dx": 1.0, "dy": -2.0}}
    _, _, silks = E.block_items(block, LIB, STD)
    assert [s["text"] for s in silks] == [str(i) for i in range(54)]
    assert {s["for"] for s in silks} == {f"port-{i}" for i in range(54)}
