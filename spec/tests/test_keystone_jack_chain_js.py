"""SPIKE for #1069: a keystone jack seated in a clip cage on a FAPM6 in an FHD-1UBE
bay, then a cable landed on the jack's RJ45 port, by the rack kit
(spec/tests/js/keystone-jack-chain.mjs).

Four levels: enclosure bay, FAPM6, clip cage, jack occupant, RJ45 port. The
jack, the blank and a clip with a `keystone` interface do not exist in the
library; the script stands them in for itself and nothing under library/ is
added. The FHD-1UBE's configs.json and the whole components.json are the real
ones, built here the way test_nested_slots_js builds its own: the component
indexer over this tree, and the one device rendered into a tmp copy. It reads
no library/dist, so it needs no build.

The checks that pass today are plain assertions; the ones that fail are
`todo` tests in the script, each naming the line of kit/rack/ports.js where
the walk stops. A failing todo does not fail the run, so this wrapper fails
when one of them starts to pass: that gap is closed, and the test becomes a
plain assertion."""
import os
import re
import shutil
import subprocess

import pytest

import onebuild
from test_lifted_seat_js import SPEC
from test_nested_slots_js import render

JS = SPEC / "tests/js/keystone-jack-chain.mjs"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@needs_node
def test_a_cable_lands_on_a_jack_seated_in_a_clip_cage_on_a_fapm6(tmp_path):
    dist = tmp_path / "dist"
    onebuild.components_index_into(dist)
    out, name = render(tmp_path, "fs/fhd-1ube", {})
    shutil.copy(out / f"{name}.configs.json", dist / f"{name}.configs.json")
    p = subprocess.run(["node", "--test", "--test-reporter=tap", str(JS)], capture_output=True, text=True,
                       cwd=str(JS.parent), env={**os.environ, "PORTRAYAL_DIST": str(dist)})
    assert p.returncode == 0, p.stdout[-6000:] + p.stderr[-2000:]
    print(p.stdout)   # (the gaps' diagnostics: pytest -rP shows what each call returned)
    gaps = re.findall(r"^\s*(not ok|ok) \d+ - (.*?) # TODO", p.stdout, re.M)
    assert gaps, "the script records no gap: its todo tests are gone"
    closed = [t for ok, t in gaps if ok == "ok"]
    assert not closed, f"a recorded gap now passes; make it a plain test: {closed}"
