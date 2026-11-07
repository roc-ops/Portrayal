"""The 300CB08 has a view with the breaker covers taken off, so the ratings show.

Every breaker ships wearing `amphenol-ns/touch-guard-1ru@1`, which covers the
breaker face, so `populated` draws sixteen identical covers. `populated-guards-off`
seats `breaker-bare-1ru`, the same breaker with no guard, with the same ratings,
in the same sixteen bays. It seats nothing inside a part (no `occupants`), because
shipped models stay bare. It is a view, not a part number: it carries none and so
exports nothing. The library half reads the device; the
render half draws the device into a temporary folder and reads the front face
of each configuration, so nothing here reads library/dist.
"""
import json
import pathlib
import re
import sys

import pytest
import yaml

import warmrender
from portrayal.artifacts import face_file

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec" / "tools" / "portrayal" / "render.py"
DEVICE = LIB / "devices" / "amphenol-ns" / "300cb08" / "device.yaml"
VIEW = "populated-guards-off"
BREAKER = "amphenol-ns/breaker-1ru@1"
BARE = "amphenol-ns/breaker-bare-1ru@1"
BLANK ="amphenol-ns/breaker-blank-1ru@1"
GUARD = "amphenol-ns/touch-guard-1ru@1"
BAYS = [f"breaker-{side}{n}" for side in "ab" for n in range(1, 9)]


def configurations():
    return yaml.safe_load(DEVICE.read_text())["configurations"]


def test_the_view_exists_and_is_an_example_with_no_part_number():
    cfg = configurations()[VIEW]
    assert cfg["kind"] == "example"
    assert "part-numbers" not in cfg
    assert not cfg.get("default")


def test_the_view_seats_a_bare_breaker_in_all_sixteen_bays():
    assert configurations()[VIEW]["bays"] == {bay: BARE for bay in BAYS}


def test_the_view_seats_no_part_inside_another():
    assert "occupants" not in configurations()[VIEW]


def test_the_view_differs_from_populated_only_in_its_covers():
    cfgs = configurations()
    for key in ("bay-attrs", "component-attrs"):
        assert cfgs[VIEW][key] == cfgs["populated"][key]
    assert set(cfgs["populated"]["bays"].values()) == {BREAKER}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("guards-off")
    r = warmrender.run([sys.executable, str(RENDER), str(DEVICE), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return out


def front(built, config):
    svg = face_file(built, "300cb08", config, "front")
    assert svg is not None, f"300cb08 {config} draws no front"
    elements = json.loads(svg.with_name(svg.name[:-len(".svg")] + ".elements.json").read_text())
    return svg.read_text(), elements["components"]


@pytest.mark.heavy
def test_the_built_view_seats_no_touch_guard(built):
    _, components = front(built, VIEW)
    assert BARE in components
    assert GUARD not in components


@pytest.mark.heavy
def test_the_built_view_prints_each_rating_on_its_handle(built):
    svg, _ = front(built, VIEW)
    drawn = dict(re.findall(r'id="(breaker-[ab]\d)--module--rating"[^>]*>(\d+)<', svg))
    want = {bay: str(a["rating"]) for bay, a in configurations()[VIEW]["bay-attrs"].items()}
    assert len(want) == 16
    assert drawn == want


@pytest.mark.heavy
def test_populated_still_wears_its_covers_and_base_still_ships_blanks(built):
    _, populated = front(built, "populated")
    assert BREAKER in populated and GUARD in populated
    _, base = front(built, "base")
    assert BLANK in base
    assert BREAKER not in base and GUARD not in base
