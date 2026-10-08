"""The marks document has a schema, and normalise() writes nothing it refuses.

kit/marks.js defines the document an annotated drawing is - selectors, ink,
lamp states, swaps and fields - and was written so that an MCP client could
send one. A client cannot be told what to send by a function body. The schema
is that statement; this test keeps it and normalise() from drifting apart, in
the direction that matters: whatever normalise() returns is a valid document.
"""
import json
import pathlib
import shutil
import subprocess

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "spec/schemas/marks.schema.json").read_text())
SCRIPT = ROOT / "spec/tests/js/marks-schema.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(ROOT))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("case", ["empty", "minimal", "full", "junk"])
def test_normalise_writes_valid_documents(out, case):
    jsonschema.validate(out[case], SCHEMA)


def test_the_schema_refuses_what_normalise_never_writes():
    bad = {"v": 2, "device": "", "config": "", "view": "", "legend": True, "crop": None,
           "marks": [{"select": "#a", "color": "", "state": "", "label": "", "lamp": "red"}],
           "swaps": {}, "fields": {}}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, SCHEMA)
