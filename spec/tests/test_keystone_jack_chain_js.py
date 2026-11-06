"""A keystone jack seated in a clip cage on a FAPM6 in an FHD-1UBE bay, then a
cable landed on the jack's RJ45 port, by the rack kit
(spec/tests/js/keystone-jack-chain.mjs).

Four levels: enclosure bay, FAPM6, clip cage, jack occupant, RJ45 port. The
parts are the library's own: the FAPM6, its clip, the jack and the blank. The
FHD-1UBE's configs.json and the whole components.json are built here the way
test_nested_slots_js builds its own: the component indexer over this tree, and
the one device rendered into a tmp copy. It reads no library/dist, so it needs
no build."""
import os
import shutil
import subprocess

import pytest

import onebuild
from test_lifted_seat_js import SPEC
from test_nested_slots_js import render

JS = SPEC / "tests/js/keystone-jack-chain.mjs"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.mark.heavy
@needs_node
def test_a_cable_lands_on_a_jack_seated_in_a_clip_cage_on_a_fapm6(tmp_path):
    dist = tmp_path / "dist"
    onebuild.components_index_into(dist)
    out, name = render(tmp_path, "fs/fhd-1ube", {})
    shutil.copy(out / f"{name}.configs.json", dist / f"{name}.configs.json")
    p = subprocess.run(["node", "--test", "--test-reporter=tap", str(JS)], capture_output=True, text=True,
                       cwd=str(JS.parent), env={**os.environ, "PORTRAYAL_DIST": str(dist)})
    assert p.returncode == 0, p.stdout[-6000:] + p.stderr[-2000:]
