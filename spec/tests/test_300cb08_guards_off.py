"""The 300CB08 has a view with the breaker covers taken off, so the ratings show.

Every breaker ships wearing `amphenol-ns/touch-guard-1ru@1`, which covers the
breaker face, so `populated` draws sixteen identical covers. `populated-guards-off`
seats the same sixteen breakers with the same ratings and empties the cover
slot of each (`<bay>/guard: ''`). It is a view, not a part number: it
carries none and so exports nothing. The library half reads the device; the
build half reads the compiled front face of each configuration.
"""
import json
import pathlib
import re

import pytest
import yaml

from portrayal.artifacts import face_file

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "amphenol-ns" / "300cb08" / "device.yaml"
DIST = ROOT / "library" / "dist"
VIEW = "populated-guards-off"
BREAKER = "amphenol-ns/breaker-1ru@1"
BLANK = "amphenol-ns/breaker-blank-1ru@1"
GUARD = "amphenol-ns/touch-guard-1ru@1"
BAYS = [f"breaker-{side}{n}" for side in "ab" for n in range(1, 9)]


def configurations():
    return yaml.safe_load(DEVICE.read_text())["configurations"]


def test_the_view_exists_and_is_an_example_with_no_part_number():
    cfg = configurations()[VIEW]
    assert cfg["kind"] == "example"
    assert "part-numbers" not in cfg
    assert not cfg.get("default")


def test_the_view_seats_a_breaker_in_all_sixteen_bays():
    assert configurations()[VIEW]["bays"] == {bay: BREAKER for bay in BAYS}


def test_the_view_empties_the_touch_guard_of_each_breaker_and_nothing_else():
    assert configurations()[VIEW]["occupants"] == {f"{bay}/guard": "" for bay in BAYS}


def test_the_view_differs_from_populated_only_in_its_covers():
    cfgs = configurations()
    for key in ("bays", "bay-attrs", "component-attrs"):
        assert cfgs[VIEW][key] == cfgs["populated"][key]


def front(config):
    if not DIST.exists():
        pytest.skip("no library/dist: run ./build.sh first")
    svg = face_file(DIST, "300cb08", config, "front")
    assert svg is not None, f"300cb08 {config} draws no front"
    elements = json.loads(svg.with_name(svg.name[:-len(".svg")] + ".elements.json").read_text())
    return svg.read_text(), elements["components"]


@pytest.mark.heavy
def test_the_built_view_seats_no_touch_guard():
    _, components = front(VIEW)
    assert BREAKER in components
    assert GUARD not in components


@pytest.mark.heavy
def test_the_built_view_prints_each_rating_on_its_handle():
    svg, _ = front(VIEW)
    drawn = dict(re.findall(r'id="(breaker-[ab]\d)--module--rating"[^>]*>(\d+)<', svg))
    want = {bay: str(a["rating"]) for bay, a in configurations()[VIEW]["bay-attrs"].items()}
    assert len(want) == 16
    assert drawn == want


@pytest.mark.heavy
def test_populated_still_wears_its_covers_and_base_still_ships_blanks():
    _, populated = front("populated")
    assert BREAKER in populated and GUARD in populated
    _, base = front("base")
    assert BLANK in base
    assert BREAKER not in base and GUARD not in base
