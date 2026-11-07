"""The gap behind a tray's floor (#966, docs/cable-lay-design.md section 1.3,
rule 1): a way up or down for a cable beside the tray's front edge, found by
the router from the floor boxes rack.json publishes for a tray, and used by the
automatic route only. The kit's node test holds the router to it
(spec/tests/js/rack-tray-gap.mjs); this holds the floors it reads to the
drawing, so that the 48.8 mm it finds is the FHD-CMP5DR's and not a figure
typed into the router."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parent / "js"
ROOT = Path(__file__).resolve().parents[2]
CAT = json.loads((JS / "cable-solids-catalogue.json").read_text())["devices"]
KIT = ROOT / "kit" / "rack"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_router_takes_the_gap_by_length_and_only_by_itself():
    p = subprocess.run(["node", "--test", str(JS / "rack-tray-gap.mjs")], capture_output=True, text=True, cwd=str(JS))
    assert p.returncode == 0, p.stdout[-4000:] + p.stderr[-2000:]


def test_the_cmp5dr_publishes_the_floor_its_gap_is_found_from():
    """The strip is 61.2 deep from the front edge and the part is 110 deep, so
    48.8 is left between the strip and the rail; the arms (10.5 wide, 33.4
    deep, behind the strip) stand at its ends, in the gap's band. Nothing here
    states 48.8: it is the part's depth less the strip's."""
    e = CAT["fhd-cmp5dr"]
    (tray,) = e["trays"]
    strip = max(tray["floor"], key=lambda b: b["w"] * b["d"])
    arms = [b for b in tray["floor"] if b is not strip]
    assert (strip["z"], strip["d"], e["d"]) == (0.0, 61.2, 110.0)
    assert round(e["d"] - (strip["z"] + strip["d"]), 1) == 48.8
    assert len(arms) == 2 and all(a["z"] == strip["d"] and a["w"] == 10.5 for a in arms)


def test_no_figure_of_the_gap_is_typed_into_the_router():
    """The router reads the gap off the floors (solids.js gapsOf): the width of
    the FHD-CMP5DR's gap, its depth or its arms' appear in no kit source."""
    for f in ("solids.js", "route.js"):
        text = (KIT / f).read_text()
        assert not re.search(r"\b48\.8\b|\b61\.2\b|\b213\.7\b", text), f


def test_no_saved_key_names_a_gap():
    """Decided 2026-10-18: the gap is used by the automatic route only, and
    this change adds no key to the rack file. A `lay` entry still names a
    pathway (`item`, `via`), a position and a face, and nothing else: a gap
    pinned later would be one more value there (docs/rack-file-v4-design.md
    section 3.9), which `item` and `via` already point at."""
    schema = json.loads((ROOT / "spec" / "schemas" / "rack.schema.json").read_text())
    assert sorted(schema["$defs"]["layEntry"]["properties"]) == ["face", "item", "position", "via"]
    assert schema["$defs"]["layEntry"]["properties"]["face"]["enum"] == ["top", "underside"]
    assert "gap" not in json.dumps(schema).lower()
