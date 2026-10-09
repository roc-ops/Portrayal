"""The rack file schema (spec/schemas/rack.schema.json) against the racks the
Rack Builder ships.

The fixtures are version 1 files as the Rack Builder's tests write them
(spec/tests/fixtures/racks/); the schema describes the current version, which
`parseDoc` reads them up to. So each is read through the kit's own `parseDoc`
and `serialize` (node) and the result is validated here, by a second validator
than the kit's own.
"""
import json
import shutil
import subprocess
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "spec/schemas/rack.schema.json").read_text())
FIXTURES = sorted((ROOT / "spec/tests/fixtures/racks").glob("*.json"))

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

READ = """
import {readFileSync} from 'node:fs';
const M = await import(process.argv[1]);
process.stdout.write(M.serialize(M.parseDoc(readFileSync(process.argv[2], 'utf8'))));
"""


def current(path):
    p = subprocess.run(["node", "--input-type=module", "-e", READ, (ROOT / "kit/rack/model.js").as_uri(), str(path)],
                       capture_output=True, text=True, check=True)
    return json.loads(p.stdout)


def errors(doc):
    return [f"{'/'.join(map(str, e.absolute_path))}: {e.message}"
            for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(doc)]


def test_there_are_fixtures_to_check():
    assert {p.name for p in FIXTURES} >= {"acceptance.rack.json", "doc-cable-fixture.json"}


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.name)
def test_every_fixture_rack_validates(path):
    assert errors(current(path)) == []


def test_a_manager_on_unit_0_is_refused():
    doc = current(ROOT / "spec/tests/fixtures/racks/doc-cable-fixture.json")
    host = doc["racks"][0]["items"][0]
    doc["racks"][0]["items"].append({"id": "i99", "ref": "fhd-cmp5dr", "cfg": "base", "label": "mgr", "ru": host["ru"],
                                     "face": "front", "turned": False, "swaps": {}, "fields": {},
                                     "on": host["id"], "unit": 1})
    assert errors(doc) == []                    # unit 1 is the host's bottom unit
    doc["racks"][0]["items"][-1]["unit"] = 0
    bad = errors(doc)
    assert bad and any("unit" in e for e in bad), bad


def test_a_version_the_schema_does_not_describe_is_refused():
    doc = current(ROOT / "spec/tests/fixtures/racks/doc-export-empty.json")
    doc["version"] = 4
    assert errors(doc)


def test_a_bundle_validates_and_a_malformed_one_is_refused():
    """Version 3 (#921): `bundles` on a rack, checked here by a second validator."""
    doc = current(ROOT / "spec/tests/fixtures/racks/doc-cable-fixture.json")
    assert doc["version"] == 3
    rack = doc["racks"][0]
    ids = [c["id"] for c in rack["cables"]]
    assert len(ids) >= 2
    rack["bundles"] = [{"id": "b1", "number": 1, "label": "", "members": [{"cable": ids[0]},
                        {"cable": ids[1], "b": {"lane": "left-front", "ru": 4}}],
                        "route": [{"lane": "left-front", "ru": 2}, {"lane": "left-front", "ru": 8}],
                        "straps": {"every": {"value": 12, "unit": "in"}}}]
    assert errors(doc) == []
    rack["bundles"][0]["straps"] = {"every": None}
    assert errors(doc) == []
    rack["bundles"][0]["straps"] = {"every": {"value": 12, "unit": "cm"}}
    rack["bundles"][0]["number"] = 0
    bad = errors(doc)
    assert any("unit" in e for e in bad) and any("number" in e for e in bad), bad
