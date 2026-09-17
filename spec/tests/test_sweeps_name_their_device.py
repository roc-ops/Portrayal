"""A failing sweep should name the device and the rule, not hand you a list.

1,286 tests, ~29 of them library-wide invariants - and most looped inside one
test and asserted on a list of slugs:

    assert unstated == [], unstated

A contributor saw `['juniper/mx240']` and a test name, then had to open the test
to learn what "stated" meant. And there was no `pytest -k <slug>` path at all:
`./build.sh --device X` existed and nothing equivalent did for the suite (#184).

`libdata.each_device()` is the mechanism - every device as a pytest param with
its slug as the id - so the failure names the device in the id, the message
names the rule, and `-k juniper/mx204` runs every sweep against one device.
"""
import pathlib
import subprocess
import sys

import libdata

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_the_mechanism_ids_every_device_by_its_slug():
    params = libdata.each_device()
    assert len(params) == len(libdata.library())
    ids = [p.id for p in params]
    assert ids == sorted(ids), "ids are the walk's order, which libwalk sorts"
    assert all("/" in i for i in ids), ids[:3]
    assert "juniper/mx204" in ids


def test_each_param_carries_the_slug_the_path_and_the_document():
    slug, path, doc = libdata.each_device()[0].values
    assert "/" in slug
    assert path.name == "device.yaml" and path.exists()
    assert doc.get("kind") == "device"


def test_components_have_the_same_mechanism():
    params = libdata.each_component()
    assert len(params) == len(libdata.components())
    assert all("/" in p.id for p in params)


def test_k_selects_one_device_across_every_parametrised_sweep():
    """THE CLAUSE THE ISSUE IS ABOUT, run rather than asserted. `-k <slug>` has
    to select something, or the mechanism is decoration."""
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "spec/tests", "-q", "--collect-only",
         "-k", "juniper/mx204"],
        capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-600:]
    selected = [l for l in r.stdout.splitlines() if "juniper/mx204" in l]
    assert len(selected) >= 2, (
        f"-k juniper/mx204 selected {len(selected)} test(s); the sweeps are not "
        "parametrised by slug")


def test_contributing_shows_the_path():
    body = (ROOT / "CONTRIBUTING.md").read_text()
    assert "-k juniper/mx204" in body
    assert "each_device" in body
