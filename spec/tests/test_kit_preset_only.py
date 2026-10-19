"""A kit configuration may state a preset with no depth range (roc-ops/Portrayal#904,
decided 2026-10-18).

A source can print a factory setting and no range: the COR550 rail's 630, the
first Smartoptics band's 600. A configuration states AT LEAST ONE of `depth` and
`preset`. A preset alone reads as "factory setting known, range unknown":
nothing refuses it, nothing invents a range from it, and the missing range is a
`gaps` entry on the kit that lint L157 asks for. A telescoping kit states a
`preset` on at least one configuration (L158).

This is a one-way change to the kit format. No kit in the library uses it yet,
so every fixture is built here on tmp_path, as test_kind_kit.py builds its own.
"""
import copy
import json
import subprocess
import sys

import pytest

from portrayal import lint, render

from test_kind_kit import (KIT, PART, ROOT, _codes, _kit_findings, _schema_errors,  # noqa: F401
                           _write, lib)

GAP = {"what": "depth", "scope": ["factory"], "reason": "vendor-silent",
       "wanted": "the range the rail extends to"}
PRESET_ONLY = {"id": "factory", "racks": ["4-post"], "parts": ["inner"], "preset": 630}


def _preset_only(**over):
    """A telescoping kit whose one configuration states a preset and no depth,
    and the gap that says so."""
    doc = {k: copy.deepcopy(v) for k, v in KIT.items() if k != "travel"}
    doc.update(motion="telescoping", configurations=[copy.deepcopy(PRESET_ONLY)], gaps=[GAP])
    doc.update(over)
    return doc


def _config(**config):
    doc = _preset_only()
    doc["configurations"] = [{"id": "factory", "racks": ["4-post"], "parts": ["inner"], **config}]
    return doc


# --- the schema -----------------------------------------------------------------

@pytest.mark.parametrize("config", [
    {"preset": 630},
    {"depth": [600, 900]},
    {"depth": [600, 900], "preset": 630},
    {"depth": {"square": [631, 868]}, "preset": 650}])
def test_a_configuration_states_a_depth_a_preset_or_both(config):
    assert _schema_errors(_config(**config)) == []


def test_a_configuration_with_neither_depth_nor_preset_is_refused_naming_both():
    errs = _schema_errors(_config(tolerance=2))
    assert errs and all("configurations/0" in e for e in errs)
    assert any("depth" in e and "preset" in e for e in errs), errs


@pytest.mark.parametrize("config", [{"preset": 0}, {"preset": "630"}, {"preset": [630, 630]}])
def test_a_preset_is_still_one_positive_number(config):
    assert _schema_errors(_config(**config))


def test_a_kit_may_carry_gaps_and_a_component_may_not():
    assert _schema_errors(_preset_only()) == []
    assert _schema_errors({**PART, "gaps": [GAP]})
    assert _schema_errors(_preset_only(gaps=[{"what": "depth", "reason": "no-reason",
                                              "wanted": "x"}]))


# --- lint -----------------------------------------------------------------------

def test_L157_a_preset_only_configuration_with_its_gap_is_clean(lib):
    assert _kit_findings(lib, _preset_only()) == []


@pytest.mark.parametrize("gaps", [
    [],
    [{**GAP, "what": "airflow"}],
    [{**GAP, "scope": ["another"]}],
    [{k: v for k, v in GAP.items() if k != "scope"}]])
def test_L157_asks_for_the_gap_when_it_is_missing(lib, gaps):
    found = _kit_findings(lib, _preset_only(gaps=gaps))
    assert _codes(found) == ["L157"], found
    assert "gaps" in found[0] and "configuration factory:" in found[0], found


def test_L157_a_gap_for_a_configuration_that_has_a_range_is_not_needed(lib):
    doc = _preset_only(gaps=[])
    doc["configurations"][0]["depth"] = [600, 700]
    assert _kit_findings(lib, doc) == []


def test_L157_one_gap_covers_each_preset_only_configuration_it_lists(lib):
    doc = _preset_only()
    doc["configurations"].append({"id": "second", "racks": ["4-post"], "parts": ["outer"],
                                  "preset": 700})
    found = _kit_findings(lib, doc)
    assert _codes(found) == ["L157"] and len(found) == 1 and "configuration second:" in found[0]
    doc["gaps"] = [{**GAP, "scope": ["factory", "second"]}]
    assert _kit_findings(lib, doc) == []


@pytest.mark.parametrize("depth", [[630, 630], [900, 600]])
def test_L157_still_refuses_a_range_that_is_a_single_figure_or_swapped(lib, depth):
    doc = _preset_only(gaps=[])
    doc["configurations"][0]["depth"] = depth
    assert _codes(_kit_findings(lib, doc)) == ["L157"]


def test_L158_a_telescoping_kit_with_no_preset_is_refused(lib):
    doc = _preset_only(gaps=[])
    doc["configurations"] = copy.deepcopy(KIT["configurations"][:1])
    found = _kit_findings(lib, doc)
    assert _codes(found) == ["L158"] and "preset" in found[0], found


def test_L158_one_preset_among_a_telescoping_kits_configurations_is_enough(lib):
    """The Smartoptics kit has seven bands and the manual prints a single
    figure for the first only; the others are ranges."""
    doc = _preset_only()
    doc["configurations"].append({"id": "second", "racks": ["4-post"], "parts": ["outer"],
                                  "depth": [700, 900]})
    assert _kit_findings(lib, doc) == []


@pytest.mark.parametrize("motion", ["fixed", "sliding", "shelf"])
def test_L158_no_other_motion_needs_a_preset(lib, motion):
    doc = {k: copy.deepcopy(v) for k, v in KIT.items() if k != "travel"}
    doc.update(motion=motion, configurations=copy.deepcopy(KIT["configurations"][:1]))
    assert _kit_findings(lib, doc) == []


def test_L157_and_L158_are_still_kit_rules():
    assert lint.RULES["L157"][0] == lint.RULES["L158"][0] == "kit"


# --- the readers ----------------------------------------------------------------

def _index(lib, tmp_path):
    out = tmp_path / "dist"
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/components_index.py"),
                        "--library", str(lib), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads((out / "kits.json").read_text())["kits"]


def test_kits_json_publishes_a_preset_only_configuration_without_a_depth(lib, tmp_path):
    """Never `null`, never `[630, 630]`: the configuration is published as the
    contract writes it, and the gap says the range is unknown."""
    _write(lib, "acme/slide@1", _preset_only())
    k = _index(lib, tmp_path)[0]
    assert k["configurations"] == [PRESET_ONLY]
    assert "depth" not in k["configurations"][0]
    assert k["gaps"] == [GAP]


def test_kits_json_carries_an_empty_gaps_list_for_a_kit_with_none(lib, tmp_path):
    _write(lib, "acme/slide@1", KIT)
    assert _index(lib, tmp_path)[0]["gaps"] == []


def _published(lib, kits):
    return render.published_kits(kits, render.Library([str(lib)]))


def test_configs_json_publishes_a_preset_only_configuration_without_a_depth(lib):
    _write(lib, "acme/rail@1", _preset_only(name="rail"))
    row = _published(lib, [{"ref": "acme/rail@1", "supply": "in-box"}])[0]
    assert row["configurations"] == [PRESET_ONLY]
    assert "depth" not in row["configurations"][0]


def _device(kits):
    return {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
            "manufacturer": "M", "model": "M", "maturity": "modelled", "profile": "networking",
            "chassis": {"width": 440.0, "height": 44.45, "depth": 500.0, "ru": 1, "kits": kits},
            "views": {"front": {"size": {"w": 440.0, "h": 44.45}}}}


def _device_findings(lib, kits):
    with lint.collecting() as found:
        lint.lint_device_kits(lib / "devices" / "d.yaml", _device(kits), [str(lib)])
    return found.errors + found.warnings


def test_a_device_listing_a_preset_only_kit_is_clean(lib):
    _write(lib, "acme/rail@1", _preset_only(name="rail"))
    assert _device_findings(lib, [{"ref": "acme/rail@1", "supply": "in-box"}]) == []


def test_a_device_may_give_a_preset_only_configuration_a_range_of_its_own(lib):
    """The override is the device's own source: it replaces a `depth` the kit
    left out as it replaces one the kit states, and L163 has no shape to hold
    it to."""
    _write(lib, "acme/rail@1", _preset_only(name="rail"))
    kits = [{"ref": "acme/rail@1", "supply": "in-box",
             "depth": {"config": "factory", "range": [600, 700]}}]
    assert _device_findings(lib, kits) == []
    assert _published(lib, kits)[0]["configurations"][0] == {**PRESET_ONLY, "depth": [600, 700]}
