"""The rack kit's catalogue-only answer for a port under a bay, held to the build.

`kit/rack/ports.js` `seatedPort` says whether a cable end names a port of what
a bay holds, from `configs.json` and `components.json` alone (#1019). Where it
says yes it overrules a page that found no such port in a drawing, so a yes
has to be true of the built library, every configuration of every device:

- every port the build drew under a bay is one the kit says yes to, or says
  nothing about. It never says there is none.
- every port the kit says yes to is drawn on that panel. That includes a bay
  the configuration has and does not list, which holds its default. A device
  may give a bay to some configurations only (`only-in`, published in
  `configs.json`, #1022); in the others the kit says nothing of it, and the
  build has drawn nothing there.

One kind of yes has no drawing and is right: the back of a part in a host that
draws no back for that bay (an enclosure with a closed rear). It is counted
apart and has to be exactly that.

The script is js/seated-ports-sweep.mjs.
"""
import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
SCRIPT = ROOT / "spec/tests/js/seated-ports-sweep.mjs"


@pytest.fixture(scope="module")
def sweep():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    if not (DIST / "devices.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    p = subprocess.run(["node", str(SCRIPT), str(DIST)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr[-2000:]
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_sweep_read_the_library(sweep):
    assert sweep["devices"] > 200 and sweep["configs"] > 500, (sweep["devices"], sweep["configs"])
    assert sweep["drawn"] > 5000, "almost no port under a bay was read off the faces"
    assert sweep["asked"] > 10000, "almost no port of a seated part was asked about"


def test_no_drawn_port_is_denied(sweep):
    assert sweep["denied"] == [], sweep["denied"][:10]
    assert sweep["yes"] > 3000, f"the kit answered for {sweep['yes']} of {sweep['drawn']} drawn ports"
    assert sweep["yes"] + sweep["unsaid"] == sweep["drawn"]


def test_every_yes_is_drawn(sweep):
    assert sweep["phantom"] == [], sweep["phantom"][:10]
    assert sweep["said"] > 2000, f"the kit said yes to {sweep['said']} ports"
    assert sweep["shown"] + sweep["closed"] == sweep["said"]
    # a yes by a slot (a supply inlet, a ground stud, #1045) has a part drawn at
    # its path too, and the library has more than a hundred in listed bays
    # a slot of the device itself lands only where this configuration draws its
    # part: asked of every slot the device lists on any panel, in every
    # configuration, an undrawn one that landed would be in `phantom` above
    assert sweep["undrawn"] > 500, f"only {sweep['undrawn']} undrawn slot paths were asked about"
    assert sweep["own"] > 300, f"only {sweep['own']} of the devices' own slots landed"
    assert sweep["slots"] > 100, f"the kit said yes to {sweep['slots']} slots that take a cable end"


def test_a_bay_the_configuration_has_and_does_not_list_gets_an_answer(sweep):
    # asked of every part of its default, each answer held to the drawing above
    assert sweep["unspoken"] > 4000, "no bay left to its default was asked about"


def test_a_bay_the_configuration_does_not_have_gets_no_answer(sweep):
    # the ch3000's double-width bays, in the configurations that lack them: nothing
    # was answered for them, and nothing was drawn there (both are in `phantom`)
    assert sweep["absent"] > 1000, f"only {sweep['absent']} ports of absent bays were asked about"
