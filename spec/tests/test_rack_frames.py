"""#935 step 2: `rack.json` carries `frames`, the rack products the Rack Builder
can apply to a frame (docs/rack-products-design.md section 9).

One row per product in library/racks/, keyed by its ref, holding the product's
numbers as the product states them and nothing it does not. The rows are built
here from the product manifests through racks_index, as the build does, so no
full library build is needed.
"""
import json
import pathlib

import pytest

from portrayal import libwalk, rack_index, racks_index
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

REFS = ["apc/ar201@1", "apc/ar203a@1", "fs/fs-or4p-45u@1", "fs/fs-or4p-xxu@1",
        "fs/fs-dr-8u@1",
        "chatsworth/13853-x03@1", "chatsworth/55053-x03@1",
        "startech/4postrack12a@1", "startech/4postrack42@1", "startech/rk1219walloh@1",
        "generic/2-post-frame@1", "generic/4-post-frame@1", "generic/4-post-cabinet@1"]

# what a row says of a product besides its numbers
IDENTITY = {"ref", "vendor", "name", "version", "major", "manufacturer", "model", "maturity",
            "part-numbers", "aliases", "description"}
NUMBERS = ["form", "ru", "numbering", "width", "hole-centres", "opening", "holes", "rails",
           "max-device-depth", "outer", "weight-kg", "load"]
# the product's own keys that never reach a row: sources, not numbers
SOURCES = {"format", "kind", "datasheet", "references", "provenance", "gaps", "aliases"}


@pytest.fixture(scope="module")
def dist(tmp_path_factory):
    out = tmp_path_factory.mktemp("dist")
    racks_index.build([LIB], out, ROOT / "spec/schemas")
    return out


@pytest.fixture(scope="module")
def frames(dist):
    return rack_index.frames(dist)


def product(ref):
    key = ref.rsplit("@", 1)[0]
    f = next(p for p in libwalk.iter_racks([LIB]) if libwalk.rack_key(p) == key)
    return load_yaml(f)


def test_a_row_for_each_rack_product_keyed_by_its_ref(frames):
    assert sorted(frames) == sorted(REFS)
    on_disk = {libwalk.rack_key(p) for p in libwalk.iter_racks([LIB])}
    assert on_disk == {r.rsplit("@", 1)[0] for r in REFS}, "a product was added: give it a row above"
    assert all(frames[r]["ref"] == r for r in frames)


@pytest.mark.parametrize("ref", REFS)
def test_a_row_holds_exactly_the_numbers_its_product_holds(frames, ref):
    row, doc = frames[ref], product(ref)
    for k in NUMBERS:
        if k in doc:
            assert row[k] == doc[k], (ref, k)
        else:
            assert k not in row, f"{ref}: {k} is not in the product, so not in its row"
    assert set(row) <= IDENTITY | set(NUMBERS), set(row) - IDENTITY - set(NUMBERS)
    assert not (set(row) & (SOURCES - {"aliases"}))


def test_no_row_holds_a_key_its_product_does_not(frames):
    """The generic shapes state no depth, weight, outer size or load; AR201 has no rear rail."""
    for ref in ("generic/2-post-frame@1", "generic/4-post-frame@1", "generic/4-post-cabinet@1"):
        for k in ("max-device-depth", "weight-kg", "outer", "load"):
            assert k not in frames[ref], (ref, k)
        assert all("depth" not in r for r in frames[ref]["rails"]), ref
    assert [r["id"] for r in frames["apc/ar201@1"]["rails"]] == ["front"]
    # nothing is ever written as a zero or a null in place of a missing key
    for row in frames.values():
        assert None not in row.values(), row["ref"]


def test_ar203a_row_is_golden(frames):
    assert frames["apc/ar203a@1"] == {
        "ref": "apc/ar203a@1", "vendor": "apc", "name": "ar203a", "version": "1.0.0", "major": 1,
        "manufacturer": "APC", "model": "AR203A", "maturity": "modelled",
        "part-numbers": {"AR203A": "APC NetShelter Open Frame Rack, 4 Post, 44U, Square Holes"},
        "description": product("apc/ar203a@1")["description"],
        "form": "4-post-frame", "ru": 44, "numbering": {"direction": "bottom-up", "start": 1}, "width": 19,
        "hole-centres": 465.1, "opening": 450.85,
        "holes": {"style": "square", "size": 9.5, "fixing": "M6"},
        "rails": [{"id": "front"}, {"id": "rear", "depth": {"fixed": 740}}],
        "max-device-depth": 740,
        "outer": {"w": 600, "h": 2130, "d": 747},
        "weight-kg": 40.32, "load": {"static-kg": 907.2}}


def test_generic_four_post_frame_row_is_golden(frames):
    assert frames["generic/4-post-frame@1"] == {
        "ref": "generic/4-post-frame@1", "vendor": "generic", "name": "4-post-frame", "version": "1.0.0", "major": 1,
        "manufacturer": "Generic", "model": "4-post-frame", "maturity": "modelled",
        "description": product("generic/4-post-frame@1")["description"],
        "form": "4-post-frame", "ru": 42, "numbering": {"direction": "bottom-up", "start": 1}, "width": 19,
        "hole-centres": 465, "opening": 450, "holes": {"style": "square"},
        "rails": [{"id": "front"}, {"id": "rear"}]}


def test_the_rack_json_a_build_writes_carries_them_and_nothing_else_changes(dist, tmp_path):
    """build() puts `frames` beside `devices`, and the format stays 1."""
    (tmp_path / "devices.json").write_text(json.dumps({"devices": []}))
    for name in ("racks", "rack-products.json"):
        src = dist / name
        if src.is_dir():
            (tmp_path / name).mkdir()
            for f in src.iterdir():
                (tmp_path / name / f.name).write_bytes(f.read_bytes())
        else:
            (tmp_path / name).write_bytes(src.read_bytes())
    out = rack_index.build(tmp_path)
    assert out["format"] == 1
    assert sorted(out) == ["devices", "format", "frames", "generated-from"]
    assert sorted(out["frames"]) == sorted(REFS)
    assert out["devices"] == {}


def test_the_devices_of_rack_json_are_what_they_were_with_or_without_products(dist, tmp_path):
    (tmp_path / "devices.json").write_text(json.dumps({"devices": [
        {"name": "sw", "manufacturer": "X", "model": "S1", "profile": "networking"}]}))
    (tmp_path / "sw.configs.json").write_text(json.dumps({
        "chassis": {"w": 440, "h": 44.45, "d": 300, "ru": 1}, "default": "base", "configs": [{"name": "base"}]}))
    without = rack_index.build(tmp_path)
    (tmp_path / "racks").mkdir()
    for f in (dist / "racks").iterdir():
        (tmp_path / "racks" / f.name).write_bytes(f.read_bytes())
    (tmp_path / "rack-products.json").write_bytes((dist / "rack-products.json").read_bytes())
    with_products = rack_index.build(tmp_path)
    assert without["devices"] and with_products["devices"] == without["devices"]
    assert without["frames"] == {} and len(with_products["frames"]) == len(REFS)


def test_a_dist_with_no_rack_products_has_an_empty_frames(tmp_path):
    (tmp_path / "devices.json").write_text(json.dumps({"devices": []}))
    assert rack_index.build(tmp_path)["frames"] == {}
