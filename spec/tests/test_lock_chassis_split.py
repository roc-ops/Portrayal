"""`shape` means dimensions, and five of the nine chassis keys are not one.

DESIGN.md defines a major as "a moved slot invalidates a cached coordinate
exactly as a renamed id invalidates a held reference", and `devicelock.buckets`
says the same: `shape` is "chassis dimensions, view sizes, and the position, size
and wiring of every placed thing".

The whole `chassis` mapping was hashed into it wholesale, so correcting a weight
typo or recolouring a housing demanded a MAJOR bump while nothing moved. #171
took `airflow` out for exactly that reason - it asked 40 devices for a major
because a fact had moved between two keys - and left the rest to keep that change
reviewable. This is the rest (#271).

`edge` is the one worth writing down. Its schema entry was `{"type": "string"}`
with no description, so it read as geometry and #271's own table guessed "probably
yes - a dimension". It is a COLOUR, and `render.py` settles it in a line:

    faceplate.set("stroke", ch.get("edge", "#22262a"))

A grep answered what a table of guesses could not, which is why the schema entry
now says so.
"""
import copy
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import devicelock as dl    # noqa: E402

BASE = {
    "chassis": {"width": 440.0, "height": 44.45, "depth": 500.0, "ru": 1,
                "color": "#111", "weight-kg": 9.0, "silk": "#eee",
                "edge": "#000", "airflow": "front-to-back"},
    "views": {}, "groups": {}, "configurations": {},
}


def _moved(key, value):
    """Which buckets change when this one chassis key changes."""
    before = dl.buckets(BASE)
    after = dl.buckets({**copy.deepcopy(BASE),
                        "chassis": {**BASE["chassis"], key: value}})
    return {k for k in ("shape", "names", "surface", "gaps")
            if before.get(k) != after.get(k)}


# --- the split is exhaustive over the schema, not over today's library -------

def test_every_chassis_key_the_schema_allows_is_classified():
    """THE GUARD. `chassis` is `additionalProperties: false`, so a tenth key can
    only arrive by someone adding it to the schema - and they have to say which
    side it falls on rather than have it default into `shape` and quietly demand
    a major from every device that adopts it.

    Same guard, and the same reason, as PORT_ROLES/NON_PORT_ROLES one tool over.
    """
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    keys = set(schema["properties"]["chassis"]["properties"])
    assert dl.CHASSIS_SHAPE | dl.CHASSIS_SURFACE == keys, (
        f"schema-only: {sorted(keys - (dl.CHASSIS_SHAPE | dl.CHASSIS_SURFACE))}, "
        f"classified-but-absent: {sorted((dl.CHASSIS_SHAPE | dl.CHASSIS_SURFACE) - keys)}")
    assert not (dl.CHASSIS_SHAPE & dl.CHASSIS_SURFACE), "a key cannot be both"


def test_the_schema_still_closes_the_chassis_mapping():
    """If it ever stopped, an unclassified key would fall into `shape` silently
    and the test above would have nothing to catch it with."""
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    assert schema["properties"]["chassis"]["additionalProperties"] is False


# --- what each key now costs -------------------------------------------------

@pytest.mark.parametrize("key,value", [
    ("width", 441.0), ("height", 88.9), ("depth", 501.0), ("ru", 2),
])
def test_a_dimension_is_still_a_major(key, value):
    """These are the keys something caches a coordinate from."""
    assert _moved(key, value) == {"shape"}


@pytest.mark.parametrize("key,value", [
    ("color", "#222"),          # housing fill
    ("edge", "#123"),           # faceplate stroke - a colour, not a shape
    ("silk", "#ddd"),           # silkscreen text colour
    ("weight-kg", 9.5),         # a fact about the box; no coordinate reads it
    ("airflow", "back-to-front"),   # taken out in #171
])
def test_recolouring_or_reweighing_a_chassis_is_a_patch(key, value):
    """Nothing moves, so nothing that cached a coordinate is invalidated."""
    assert _moved(key, value) == {"surface"}


def test_edge_is_the_colour_render_py_strokes_with():
    """The claim the split rests on, asserted against the renderer rather than
    against a reading of the name."""
    src = (ROOT / "spec/tools/portrayal/render.py").read_text()
    assert 'ch.get("edge"' in src
    line = next(l for l in src.splitlines() if 'ch.get("edge"' in l)
    assert "stroke" in line, line


# --- the trap #171 fell into, and this could have fallen into again ----------

def test_a_device_without_a_key_is_not_rehashed_for_it():
    """`airflow: None` written unconditionally is still a NEW KEY in the hashed
    map, and it rehashed all 89 devices on the first attempt at #171 - asking
    every one of them for a bump it had not earned. The same trap is waiting for
    each of the four keys this change moves, so the surface keys are carried one
    at a time and only when the device states them.
    """
    bare = {"chassis": {"width": 440.0, "height": 44.45, "depth": 500.0},
            "views": {}, "groups": {}, "configurations": {}}
    with_colour = {**bare, "chassis": {**bare["chassis"], "color": "#111"}}
    # a device that states no colour hashes as though the key did not exist
    assert dl.buckets(bare)["surface"] != dl.buckets(with_colour)["surface"]
    # ...and its shape is the dimensions alone, whatever surface keys exist
    assert dl.buckets(bare)["shape"] == dl.buckets(with_colour)["shape"]


def test_the_dimensions_alone_decide_shape():
    """Every surface key at once must not move `shape` by so much as a bit."""
    bare = {"chassis": {"width": 440.0, "height": 44.45, "depth": 500.0},
            "views": {}, "groups": {}, "configurations": {}}
    dressed = {**bare, "chassis": {**bare["chassis"], "color": "#111",
                                   "edge": "#000", "silk": "#eee",
                                   "weight-kg": 9.0, "airflow": "front-to-back"}}
    assert dl.buckets(bare)["shape"] == dl.buckets(dressed)["shape"]
