"""#935: adding rack products changes nothing that was there.

`kind: rack` is additive. A device is still a thing placed in a rack, the
Rack Builder's generic frames are still the only frames it offers, and the
rack file (`rack.schema.json`, version 3) is byte for byte what it was: a rack
product reaches the Rack Builder through `frames` in `rack.json`, the one key
`rack.json` gained, and `frame.ref` (docs/rack-products-design.md sections 9 and 11).

The golden values below are the state before racks existed. A change to one of
them is not a failure of this file but a decision, and belongs to the pull
request that makes it.
"""
import hashlib
import json
import pathlib

import pytest

from portrayal import libwalk

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"

# sha256 of spec/schemas/rack.schema.json, the Rack Builder's file, version 3.
# It moved when the cable media description gained `stack`, `usb` and `console`
# (a description only; the site takes the new schema when it re-vendors the kit).
RACK_FILE_SCHEMA_SHA256 = "91212329da56d966431af2b534e2d032fb6505855aeaca94cfe7116c12d2784c"


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def test_the_rack_file_schema_is_the_one_the_rack_builder_reads():
    assert sha(ROOT / "spec/schemas/rack.schema.json") == RACK_FILE_SCHEMA_SHA256


def test_a_rack_product_schema_is_a_file_of_its_own():
    assert (ROOT / "spec/schemas/rack-product.schema.json").exists()
    assert (ROOT / "spec/schemas/rack.schema.json").exists()
    assert sha(ROOT / "spec/schemas/rack-product.schema.json") != \
        sha(ROOT / "spec/schemas/rack.schema.json")


def test_no_rack_product_sits_among_the_devices():
    stray = [p for p in (LIB / "devices").rglob("rack.yaml")]
    assert not stray, stray
    assert not list((LIB / "devices").glob("*/*/rack.lock.json"))


def test_the_device_walk_finds_no_rack_and_the_rack_walk_no_device():
    racks = {p.parent for p in libwalk.iter_racks([LIB])}
    devices = {p.parent for p in libwalk.iter_devices([LIB])}
    assert racks and devices and not (racks & devices)
    assert all(LIB / "racks" in p.parents for p in racks)
    assert all(LIB / "devices" in p.parents for p in devices)


@pytest.fixture(scope="module")
def dist():
    if not (DIST / "devices.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    return DIST


def test_devices_json_lists_the_devices_and_no_rack(dist):
    listed = {d["name"] for d in json.loads((dist / "devices.json").read_text())["devices"]}
    walked = {p.parent.name for p in libwalk.iter_devices([LIB])}
    assert listed == walked
    racks = {p.parent.name for p in libwalk.iter_racks([LIB])}
    assert not (racks & listed)


def test_the_rack_builders_catalogue_gains_frames_and_nothing_else(dist):
    """`frames` (step 2 of the build order) is the one key rack.json gained for
    rack products: the format stays 1 and the keys it had are the keys it has."""
    cat = json.loads((dist / "rack.json").read_text())
    assert cat["format"] == 1
    assert set(cat) == {"format", "generated-from", "devices", "frames"}
    assert "racks" not in cat
    assert sorted(cat["frames"]) == sorted(
        f"{libwalk.rack_key(p)}@1" for p in libwalk.iter_racks([LIB]))


def test_components_json_lists_no_rack(dist):
    text = (dist / "components.json").read_text()
    assert "ar203a" not in text and "ar201" not in text
