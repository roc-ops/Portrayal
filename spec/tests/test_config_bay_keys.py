"""A configuration's nested bay key reaches the explorer.

device.yaml keys a bay inside a seated module WITHOUT the `/module` steps -
the dcp-2 ila-node seats `slot-1/ppm-1` - and that is the form render.py's
seating and lint's L8 both read. The drawing, and so every bay id the kit
works with, puts them in: `slot-1/module/ppm-1`. `kit/shell.js` copied the
configuration's map verbatim and looked the occupant up by the drawing's id,
so every nested key missed. The face was right - the build seated the
PPM-AD1-1510 - and the occupant picker beside it said the dummy cover.

L8 already refuses a nested key that names no bay, including one written the
drawing's way (`module` is not a bay). What nothing checked was that the build
and the kit agree on the translation, so this runs the kit's own
`configBayPath` over real compiled output: every nested key must name a bay in
that configuration's faces, and the module seated there must be the one the
configuration asked for.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from portrayal import libwalk

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
RENDER = SPEC / "tools/portrayal/render.py"
SCRIPT = SPEC / "tests/js/config-bay-keys.mjs"


def nested_devices():
    out = []
    for f in libwalk.iter_devices([LIB]):
        d = yaml.safe_load(f.read_text())
        if any("/" in k for c in (d.get("configurations") or {}).values()
               for k in ((c or {}).get("bays") or {})):
            out.append(f)
    return out


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_every_nested_configuration_key_names_a_seated_bay_in_the_drawing(tmp_path):
    devs = nested_devices()
    assert devs, "no configuration keys a nested bay, so this checks nothing"
    for f in devs:
        r = subprocess.run([sys.executable, str(RENDER), str(f),
                            "--library", str(LIB), "--out", str(tmp_path)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr

    p = subprocess.run(["node", str(SCRIPT), str(tmp_path)], capture_output=True,
                       text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    rows = [r for r in json.loads(p.stdout.strip().splitlines()[-1])
            if "/" in r["key"]]
    assert rows, "the index carried none of the nested keys the manifests declare"

    missing = [f"{r['device']}:{r['config']} {r['key']} -> {r['path']}"
               for r in rows if not r["bay"]]
    assert not missing, f"no bay in the drawing at the kit's path: {missing}"

    # an empty string is a deliberately empty bay: nothing seated at all
    wrong = [f"{r['device']}:{r['config']} {r['key']} wants {r['ref']!r}, "
             f"drawing seats {r['seated']}"
             for r in rows
             if set(r["seated"]) != ({r["ref"]} if r["ref"] else set())]
    assert not wrong, wrong


def test_the_ila_node_is_the_case_that_found_it():
    """The one configuration that seats something other than a bay's default in
    a nested bay. If it stops, the check above can pass on defaults alone,
    where a dropped key and an honoured one draw the same module."""
    d = yaml.safe_load((LIB / "devices/smartoptics/dcp-2/device.yaml").read_text())
    bays = d["configurations"]["ila-node"]["bays"]
    assert bays.get("slot-1/ppm-1") == "smartoptics/ppm-ad1-1510@1", bays
