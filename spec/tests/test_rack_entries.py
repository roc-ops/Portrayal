"""A rack product states where a cable may leave it: `enclosure.entries`.

An entry is `{id, where, kind, box, source}`. The schema holds the shape of each
key. The lint holds what crosses keys (L193). `rack.json` `frames` carries the
entries of a product that states them. The two APC open frames state the `top`
entry, and so do two more (MORE_FRAMES). A product that states no entries reads exactly as it did.
"""
import copy
import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

from portrayal import lint, rack_index, racks_index
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/rack-product.schema.json").read_text())

KINDS = ["brush", "knockout", "cutout", "open"]
PLACES = ["roof", "floor", "left", "right"]
FRAMES = ["apc/ar201", "apc/ar203a"]
# two products this change leaves alone, one frame and one cabinet
UNTOUCHED = ["apc/ar3100b2", "chatsworth/13853-x03"]
# the open frames that state the `top` entry as well (see test_rack_open_frames.py)
MORE_FRAMES = ["fs/fs-or4p-45u", "startech/4postrack42"]
# the keys of a frames row before entries existed
ROW_KEYS = ["ref", "vendor", "name", "version", "major", "manufacturer", "model", "maturity",
            "part-numbers", "description", "aliases", "form", "ru", "numbering", "width",
            "hole-centres", "opening", "holes", "rails", "max-device-depth", "outer",
            "weight-kg", "load"]

def rack(key):
    return load_yaml(LIB / "racks" / key / "rack.yaml")


def errors(doc):
    return [e.message for e in Draft202012Validator(SCHEMA).iter_errors(doc)]


def framed(entries, **kw):
    """The AR201 frame with these entries in its enclosure."""
    doc = copy.deepcopy(rack("apc/ar201"))
    doc.pop("enclosure", None)
    doc["enclosure"] = {"entries": entries}
    doc.update(kw)
    return doc


def l193(doc, key="apc/ar201"):
    got = []
    real = lint.err
    lint.err = lambda path, rule, msg: got.append((rule, msg))
    try:
        lint.lint_rack(LIB / "racks" / key / "rack.yaml", doc, [str(LIB)])
    finally:
        lint.err = real
    return [m for r, m in got if r == "L193"]


def entry(**kw):
    out = {"id": "top", "where": "roof", "kind": "open"}
    out.update(kw)
    return out


# ---- the schema ---------------------------------------------------------------------

@pytest.mark.parametrize("kind", KINDS)
def test_the_schema_accepts_each_kind(kind):
    assert errors(framed([entry(kind=kind)])) == []


@pytest.mark.parametrize("where", PLACES)
def test_the_schema_accepts_each_place(where):
    assert errors(framed([entry(where=where)])) == []


def test_the_schema_accepts_a_box_and_a_source():
    plan = entry(id="roof-brush", kind="brush", box={"x": 100, "z": 20, "w": 200, "d": 80}, source="a note")
    side = entry(id="left-cut", where="left", kind="cutout", box={"y": 100, "z": 20, "h": 200, "d": 80})
    assert errors(framed([plan, side])) == []


def test_an_undeclared_kind_is_refused():
    assert errors(framed([entry(kind="grommet")]))
    assert errors(framed([entry(kind="Open")]))


@pytest.mark.parametrize("where", ["front", "rear", "top", "back"])
def test_an_undeclared_place_is_refused(where):
    assert errors(framed([entry(where=where)]))


@pytest.mark.parametrize("bad", ["any", "Top", "top brush", "top_brush", "-top", "top-", ""])
def test_a_bad_id_is_refused(bad):
    assert errors(framed([entry(id=bad)])), bad


@pytest.mark.parametrize("key", ["id", "where", "kind"])
def test_an_entry_states_its_id_place_and_kind(key):
    one = entry()
    del one[key]
    assert errors(framed([one])), key


def test_an_unknown_key_on_an_entry_is_refused():
    assert errors(framed([entry(colour="black")]))


def test_a_box_with_an_unknown_key_is_refused():
    assert errors(framed([entry(box={"x": 0, "z": 0, "w": 10, "d": 10, "h": 5, "u": 1})]))


def test_the_entries_are_not_empty():
    assert errors(framed([]))


# ---- the lint -----------------------------------------------------------------------

def test_a_frame_with_entries_alone_passes():
    assert l193(framed([entry()])) == []


def test_a_duplicate_id_is_refused():
    got = l193(framed([entry(), entry(where="left")]))
    assert any("'top'" in m and "twice" in m for m in got), got


def test_any_is_no_id():
    got = l193(framed([entry(id="any")]))
    assert any("any" in m and "reserved" in m for m in got), got


def test_a_box_outside_outer_is_refused():
    big = entry(kind="brush", box={"x": 400, "z": 0, "w": 200, "d": 10})   # outer.w is 513
    assert any("outside" in m for m in l193(framed([big])))
    deep = entry(kind="brush", box={"x": 0, "z": 300, "w": 10, "d": 100})  # outer.d is 376
    assert any("outside" in m for m in l193(framed([deep])))
    tall = entry(where="left", kind="cutout", box={"y": 2100, "z": 0, "h": 100, "d": 10})  # outer.h is 2136
    assert any("outside" in m for m in l193(framed([tall])))


def test_a_box_inside_outer_passes():
    inside = entry(kind="brush", box={"x": 100, "z": 20, "w": 200, "d": 80})
    side = entry(id="left-cut", where="left", kind="cutout", box={"y": 100, "z": 20, "h": 200, "d": 80})
    assert l193(framed([inside, side])) == []


def test_a_roof_box_with_side_keys_is_refused():
    got = l193(framed([entry(kind="brush", box={"y": 10, "z": 10, "h": 10, "d": 10})]))
    assert any("roof" in m and "x" in m and "w" in m for m in got), got


def test_a_floor_box_with_a_missing_plan_key_is_refused():
    got = l193(framed([entry(where="floor", kind="brush", box={"x": 10, "z": 10, "w": 10})]))
    assert any("floor" in m for m in got), got


def test_a_side_box_with_plan_keys_is_refused():
    got = l193(framed([entry(where="right", kind="cutout", box={"x": 10, "z": 10, "w": 10, "d": 10})]))
    assert any("right" in m and "y" in m and "h" in m for m in got), got


def test_an_open_entry_with_no_box_needs_an_outer():
    doc = framed([entry()])
    del doc["outer"]
    doc["provenance"].pop("outer")
    got = l193(doc)
    assert any("outer" in m and "open" in m for m in got), got


def test_an_open_entry_with_a_box_needs_no_outer():
    doc = framed([entry(box={"x": 0, "z": 0, "w": 10, "d": 10})])
    del doc["outer"]
    doc["provenance"].pop("outer")
    assert l193(doc) == []


def test_a_brush_with_no_box_needs_no_outer():
    doc = framed([entry(kind="brush")])
    del doc["outer"]
    doc["provenance"].pop("outer")
    assert l193(doc) == []


@pytest.mark.parametrize("part,value", [
    ("doors", [{"face": "front", "leaves": 1, "kind": "solid"}]),
    ("panels", {"per-side": 1}),
    ("roof", {"removable": True}),
])
def test_a_frame_is_still_refused_a_cabinet_part(part, value):
    doc = framed([entry()])
    doc["enclosure"][part] = value
    got = l193(doc)
    assert any(f"`{part}`" in m and "cabinet" in m and "enclosure" in m for m in got), got


def test_a_frame_with_doors_and_no_entries_is_refused():
    doc = framed([entry()])
    del doc["enclosure"]["entries"]
    doc["enclosure"]["doors"] = [{"face": "front", "leaves": 1, "kind": "solid"}]
    assert any("`doors`" in m for m in l193(doc))


def test_a_cabinet_with_entries_and_doors_passes():
    doc = copy.deepcopy(rack("apc/ar3100b2"))
    assert doc["enclosure"].get("doors")
    doc["enclosure"]["entries"] = [
        entry(id="top-brush", kind="brush"),
        entry(id="floor", where="floor", kind="knockout"),
    ]
    assert errors(doc) == []
    assert l193(doc, "apc/ar3100b2") == []


# ---- the two APC frames -------------------------------------------------------------

@pytest.mark.parametrize("key", FRAMES)
def test_the_apc_frame_states_the_top_entry(key):
    doc = rack(key)
    assert errors(doc) == []
    assert l193(doc, key) == []
    assert list(doc["enclosure"]) == ["entries"]
    [top] = doc["enclosure"]["entries"]
    assert (top["id"], top["where"], top["kind"]) == ("top", "roof", "open")
    assert "box" not in top
    assert doc["version"] == "1.1.0"


def test_each_source_quotes_the_products_own_form_note():
    ar201 = rack("apc/ar201")
    ar203a = rack("apc/ar203a")
    quote201 = "two upright rails joined by a top angle and a bottom angle at each end"
    quote203 = "Open frame, no doors or panels."
    assert quote201 in ar201["provenance"]["form"]["note"].replace("\n", " ")
    assert quote203 in ar203a["provenance"]["form"]["note"].replace("\n", " ")
    assert quote201 in ar201["enclosure"]["entries"][0]["source"]
    assert quote203 in ar203a["enclosure"]["entries"][0]["source"]


# ---- rack.json frames ---------------------------------------------------------------

@pytest.fixture(scope="module")
def frames(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist")
    racks_index.build([LIB], out, ROOT / "spec/schemas")
    return rack_index.frames(out)


@pytest.mark.parametrize("key", FRAMES)
def test_frames_carry_the_entries_of_a_product_that_states_them(frames, key):
    row = next(r for ref, r in frames.items() if ref.startswith(key + "@"))
    assert row["enclosure"] == {"entries": rack(key)["enclosure"]["entries"]}


@pytest.mark.parametrize("key", UNTOUCHED)
def test_a_product_with_no_entries_indexes_exactly_as_before(frames, key):
    doc = rack(key)
    assert "entries" not in (doc.get("enclosure") or {})
    row = next(r for ref, r in frames.items() if ref.startswith(key + "@"))
    assert "enclosure" not in row
    want = {k: v for k, v in row.items() if k in ROW_KEYS}
    assert list(row) == [k for k in row if k in ROW_KEYS]
    assert json.dumps(row) == json.dumps(want)


def test_only_the_open_frames_gain_an_enclosure(frames):
    have = sorted(ref.split("@")[0] for ref, r in frames.items() if "enclosure" in r)
    assert have == sorted(FRAMES + MORE_FRAMES)
