"""The site file, version 0 (spec/schemas/site.schema.json, docs/site-file-design.md).

A site file sits above the rack file: rooms, the racks placed in them,
surfaces, devices that are not in a rack, pathways, and the cables whose two
ends are not in one rack. Two of its rules cannot be written in JSON Schema,
so `portrayal.sitefile` checks them: every id is unique across the whole
document, and a cable is stored at the lowest level that holds both its ends.

Each test names the fault it plants. The fixture is made up (`zorb`), and
places the rack of `fixtures/racks/acceptance.rack.json` by reference.
"""
import copy
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from portrayal import sitefile

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "spec/schemas/site.schema.json"
FIXTURE = ROOT / "spec/tests/fixtures/zorb.site.json"
RACK_FILE = ROOT / "spec/tests/fixtures/racks/acceptance.rack.json"


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def schema_errors(doc):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return [f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
            for e in jsonschema.Draft202012Validator(schema).iter_errors(doc)]


def room(doc):
    return doc["site"]["buildings"][0]["floors"][0]["spaces"][0]


def findings(doc):
    """What the checker says of `doc`, read as if it stood where the fixture does."""
    return sitefile.check(doc, base=FIXTURE.parent)


def test_the_fixture_validates_against_site_schema_json():
    """The positive case: the shape the note describes is the shape the schema
    accepts, and the checker finds nothing in it either."""
    doc = fixture()
    assert schema_errors(doc) == []
    assert findings(doc) == []


def test_the_fixture_holds_what_the_note_asks_of_it():
    """NON-VACUITY for the positive case: a fixture that lost its backboard or a
    cable level would still validate."""
    doc = fixture()
    floor = doc["site"]["buildings"][0]["floors"][0]
    spaces = floor["spaces"]
    devices = [d for s in spaces for d in s.get("devices", [])]
    assert len(spaces) == 2
    assert [r["rack"] for s in spaces for r in s.get("racks", [])] == ["r1"]
    [board] = [b for s in spaces for b in s.get("surfaces", [])]
    assert board["kind"] == "backboard" and len(board["devices"]) == 1
    assert sorted(d["ref"] for d in devices).count("zorb/faceplate-2") == 2
    assert [d["ref"] for d in devices].count("zorb/access-point") == 1
    assert len(doc["site"]["buildings"][0]["pathways"]["segments"]) == 3
    assert len(room(doc)["cables"]) == 1                      # rack to outlet, in the room
    assert len(doc["site"]["buildings"][0]["cables"]) == 1    # closet to closet, in the building
    rack = json.loads(RACK_FILE.read_text(encoding="utf-8"))
    assert rack["racks"][0]["cables"], "the in-rack level is the rack file's own cables"


def test_a_cable_stored_above_the_lowest_level_holding_both_ends_is_refused():
    """Planted: a cable whose two ends are in one rack, stored in the room. It
    belongs in the rack file."""
    doc = fixture()
    room(doc)["cables"].append({
        "id": "cb-9", "guid": "0Zorb0000000000000009a",
        "a": {"rack": "rk-1", "item": "i2", "path": "port-1", "view": "front"},
        "b": {"rack": "rk-1", "item": "i1", "path": "slot-2/module/p0", "view": "front"}})
    assert schema_errors(doc) == [], "the placement rule is the checker's, not the schema's"
    got = findings(doc)
    assert any("cb-9" in f and "rack file" in f for f in got), got


def test_a_cable_between_two_spaces_stored_in_one_of_them_is_refused():
    """The rule from below as well: a room cannot hold a cable with an end in
    another room. Planted: the closet-to-closet stub moved into the room."""
    doc = fixture()
    stub = doc["site"]["buildings"][0]["cables"].pop()
    room(doc)["cables"].append(stub)
    got = findings(doc)
    assert any("cb-2" in f and "bldg-zorb" in f for f in got), got


def test_an_id_used_twice_anywhere_in_the_document_is_refused():
    """Planted: an outlet given the id of the placed rack."""
    doc = fixture()
    room(doc)["devices"][0]["id"] = "rk-1"
    room(doc)["cables"][0]["b"]["device"] = "rk-1"
    got = findings(doc)
    assert any("rk-1" in f and "twice" in f for f in got), got


def test_a_guid_used_twice_is_refused():
    """Planted: the access point given the outlet's GUID."""
    doc = fixture()
    closet = doc["site"]["buildings"][0]["floors"][0]["spaces"][1]
    closet["devices"][1]["guid"] = closet["devices"][0]["guid"]
    got = findings(doc)
    assert any(closet["devices"][0]["guid"] in f and "twice" in f for f in got), got


def test_an_extension_block_without_a_namespace_and_version_is_refused():
    """Planted: `ext: {"poe": {}}`, a bare key with no namespace and no version."""
    doc = fixture()
    room(doc)["devices"][0]["ext"] = {"poe": {}}
    assert any("poe" in e for e in schema_errors(doc)), schema_errors(doc)
    assert findings(doc), "the checker runs the schema too"


def test_an_unknown_well_formed_extension_block_is_valid():
    """The other half of the rule: a namespaced, versioned block this reader
    does not know is valid, and is kept."""
    doc = fixture()
    room(doc)["devices"][0]["ext"] = {"example.unheard-of@3": {"anything": [1, 2]}}
    assert schema_errors(doc) == []
    assert findings(doc) == []


def test_a_cable_end_naming_a_port_and_no_device_is_refused():
    """Planted: an end with `port` alone. An end is whole: a rack, item, path
    and view; a placed device and port; or a point outside the site."""
    doc = fixture()
    room(doc)["cables"][0]["b"] = {"port": "jack-1"}
    assert schema_errors(doc), "a port with nothing to be a port of"
    assert findings(doc)


def test_the_rack_file_a_site_places_is_byte_identical_before_and_after_the_site_is_read():
    """No plant: a hash comparison. The rack file stays one rack and is never
    rewritten by being placed."""
    before = hashlib.sha256(RACK_FILE.read_bytes()).hexdigest()
    doc = sitefile.read(FIXTURE)
    assert sitefile.check(doc, base=FIXTURE.parent) == []
    assert hashlib.sha256(RACK_FILE.read_bytes()).hexdigest() == before


def test_the_checker_does_read_the_placed_rack_file():
    """NON-VACUITY for the hash: the byte comparison proves nothing if the rack
    file is never opened. Planted: a cable end naming an item the rack lacks."""
    doc = fixture()
    room(doc)["cables"][0]["a"]["item"] = "i99"
    got = findings(doc)
    assert any("i99" in f and "r1" in f for f in got), got


@pytest.mark.parametrize("file", [
    "../../outside.rack.json", "racks/../../outside.rack.json", "/etc/outside.rack.json",
    "C:/outside.rack.json", "..\\outside.rack.json"])
def test_a_placed_rack_file_outside_the_site_folder_is_refused(tmp_path, file):
    """Planted: a placement whose `file` climbs out of the site folder, or is
    absolute. The file is refused by its path, before any read of it."""
    (tmp_path / "racks").mkdir()
    (tmp_path / "racks" / "acceptance.rack.json").write_bytes(RACK_FILE.read_bytes())
    doc = fixture()
    room(doc)["racks"][0]["file"] = file
    got = sitefile.check(doc, base=tmp_path)
    assert any("rk-1" in f and "outside the site folder" in f for f in got), got


def test_two_spellings_of_one_rack_path_are_one_rack(tmp_path):
    """Planted: the one rack placed twice, the second by a longer spelling of the
    same path. Compared as written they differ; normalised they are one rack."""
    (tmp_path / "racks").mkdir()
    (tmp_path / "racks" / "acceptance.rack.json").write_bytes(RACK_FILE.read_bytes())
    doc = fixture()
    placements = room(doc)["racks"]
    placements[0]["file"] = "racks/acceptance.rack.json"
    again = copy.deepcopy(placements[0])
    again.update(id="rk-2", guid="1Nn1GUFhPU_8QfqTLh$Yw2", x=3000,
                 file="./racks/../racks/./acceptance.rack.json")
    placements.append(again)
    got = sitefile.check(doc, base=tmp_path)
    assert any("rk-1" in f and "rk-2" in f and "one place" in f for f in got), got


def test_a_pathway_segment_with_one_node_at_both_ends_is_refused():
    """Planted: a segment whose `a` and `b` are the same node. JSON Schema
    cannot compare two properties of one object, so the checker refuses it."""
    doc = fixture()
    seg = doc["site"]["buildings"][0]["pathways"]["segments"][0]
    seg["b"] = seg["a"]
    assert schema_errors(doc) == [], "the schema cannot state it; the checker does"
    got = findings(doc)
    assert any(seg["id"] in f and seg["a"] in f and "both ends" in f for f in got), got


def test_the_note_and_the_schema_both_require_name():
    """Planted: the file without `name` is refused by the schema, and the note's
    sentence on the required keys names `name` among them."""
    doc = fixture()
    del doc["name"]
    assert any("name" in e for e in schema_errors(doc)), schema_errors(doc)
    note = (ROOT / "docs/site-file-design.md").read_text(encoding="utf-8")
    required = [s for s in note.replace("\n", " ").split(". ") if "are required" in s and "`format`" in s]
    assert required and "`name`" in required[0] and "optional" not in required[0].split("`name`")[0], required


def test_version_1_is_refused_with_both_versions_named(tmp_path):
    """Planted: the fixture with `version: 1`. The reader refuses it whole and
    reads none of it."""
    doc = fixture()
    doc["version"] = 1
    newer = tmp_path / "newer.site.json"
    newer.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(sitefile.SiteVersionError) as err:
        sitefile.read(newer)
    assert "version 1" in str(err.value) and "version 0" in str(err.value), str(err.value)


def test_another_format_is_refused(tmp_path):
    doc = copy.deepcopy(fixture())
    doc["format"] = "portrayal-rack"
    other = tmp_path / "rack.json"
    other.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="portrayal-site"):
        sitefile.read(other)
