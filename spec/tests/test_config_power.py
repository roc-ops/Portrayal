"""A configuration's power feed is a field, and the whitebox HCL states it (#513).

#513 asked for two things on every `configs[]` entry: airflow and power. Airflow
was already a field (`chassis.airflow`, and a configuration's own where it
differs - L91) and test_config_airflow.py pins it. Power was not a field at all.
A tool filtering the whitebox switches by feed recovered it from configuration
names - `ac`, `ac-psu`, `dc48-f2b` - or from whichever of eight attrs spellings
(`input-dc`, `psu-dc-input`, `power-input-dc`, a bare `input`...) a device
happened to use, and a name says nothing about a device whose only build is
called `base`.

`power` now has airflow's shape: `chassis.power` where the box has one feed, a
configuration's own `power` where its build differs (L118). It resolves through
`manifest.config_power`, beside `config_airflow`, into the drawing's
`data-power`, `configs[].power` and `options.power` in configs.json, and
`options` in devices.json, so none of them can disagree.

These pin that shape, the three rules, and the census the field was added for:
every Edgecore, UfiSpace and Celestica device states a feed for every build.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from portrayal import comparable, lint
from portrayal.manifest import config_power, device_options, OFFERED_KINDS

SPEC = Path(__file__).resolve().parents[1]
ROOT = SPEC.parent
LIB = ROOT / "library"
DIST = LIB / "dist"
RENDER = SPEC / "tools/portrayal/render.py"

# an AC and a DC build of each airflow - the device #513 names as its example
FOUR = LIB / "devices/edgecore/as7326-56x/device.yaml"
# one feed, on the chassis, for a box with no supply bay to read it from
FIXED = LIB / "devices/edgecore/csr180/device.yaml"
# both inlets fitted at once - the one build that is fed two ways
BOTH = LIB / "devices/edgecore/ecs4120-28fv2-i/device.yaml"

WHITEBOX = ("edgecore", "ufispace", "celestica")
# A PCIe add-in card, powered from its host's slot. It has no supply and no
# feed a buyer chooses, which is why L119 does not ask it for one.
NO_FEED = {"ufispace/n3100-4c"}

POWER_ATTR = re.compile(r'<svg\b[^>]*?\sdata-power="([^"]*)"')
SVG_ROOT = re.compile(r"<svg\b[^>]*>")


def load(p):
    return yaml.safe_load(Path(p).read_text())


def whitebox():
    for ns in WHITEBOX:
        for f in sorted((LIB / "devices" / ns).glob("*/device.yaml")):
            yield f"{ns}/{f.parent.name}", f


def render(device_yaml, tmp_path):
    r = subprocess.run([sys.executable, str(RENDER), str(device_yaml),
                        "--library", str(LIB), "--out", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return load(device_yaml)["name"]


# ---- the resolver ----------------------------------------------------------

def test_a_configuration_overrides_the_chassis_and_the_answer_is_a_list():
    dev = {"chassis": {"power": "ac"}}
    assert config_power(dev, {}) == ["ac"]
    assert config_power(dev, {"power": "dc"}) == ["dc"]
    assert config_power(dev, {"power": ["dc", "ac"]}) == ["ac", "dc"]
    assert config_power({}, {}) == []


def test_options_are_the_offered_builds_only():
    dev = {"chassis": {"airflow": "front-to-back"},
           "configurations": {
               "ac": {"kind": "orderable", "power": "ac"},
               "dc": {"kind": "orderable", "power": "dc", "airflow": "back-to-front"},
               # an illustration may not widen what the box is sold with
               "demo": {"kind": "example", "power": "hvdc"}}}
    assert device_options(dev) == {"power": ["ac", "dc"],
                                   "airflow": ["back-to-front", "front-to-back"]}
    assert "orderable" in OFFERED_KINDS and "example" not in OFFERED_KINDS


# ---- the three rules -------------------------------------------------------

def findings(fn, doc, code):
    with lint.collecting() as found:
        fn("device.yaml", doc)
    return [m for m in found.errors + found.warnings if f"[{code}]" in m]


def test_L118_a_configuration_restating_the_chassis_is_refused():
    doc = {"chassis": {"power": "dc"},
           "configurations": {"base": {"kind": "base", "power": "dc"}}}
    assert findings(lint.lint_device_power_home, doc, "L118")


def test_L118_one_feed_on_every_build_belongs_on_the_chassis():
    doc = {"chassis": {}, "configurations": {"a": {"power": "ac"}, "b": {"power": "ac"}}}
    assert findings(lint.lint_device_power_home, doc, "L118")
    doc["configurations"]["b"]["power"] = "dc"
    assert not findings(lint.lint_device_power_home, doc, "L118")


def _with_psu_bay(configs, default):
    return {"groups": {"psus": {"term": "PSU"}},
            "views": {"rear": {"components": {"bays": [
                {"id": "psu-0", "default": default, "group": "psus"}]}}},
            "configurations": configs}


def test_L119_a_device_with_supplies_and_no_feed_is_asked_for_one():
    doc = _with_psu_bay({"base": {"kind": "base"}}, "common/psu-ac-650@3")
    assert findings(lint.lint_device_power_stated, doc, "L119")
    doc["chassis"] = {"power": "ac"}
    assert not findings(lint.lint_device_power_stated, doc, "L119")


def test_L119_a_device_without_supplies_is_not_asked():
    assert not findings(lint.lint_device_power_stated,
                        {"configurations": {"base": {"kind": "base"}}}, "L119")


def test_L120_a_feed_that_contradicts_the_seated_supply_is_reported():
    doc = _with_psu_bay({"ac": {"kind": "orderable", "power": "ac"},
                         "dc": {"kind": "orderable", "power": "dc"}},
                        "common/psu-ac-650@3")
    got = findings(lint.lint_device_power_stated, doc, "L120")
    assert len(got) == 1 and "'dc'" in got[0]
    # the DC build seating its own supply is consistent
    doc["configurations"]["dc"]["bays"] = {"psu-0": "common/psu-dc-650@2"}
    assert not findings(lint.lint_device_power_stated, doc, "L120")


def test_L120_reads_the_feed_off_supply_names_the_library_uses():
    feed = lint._supply_feed
    assert feed("common/psu-ac-650@3") == "ac"
    assert feed("ufispace/psu-132-crps-dc@1") == "dc"
    assert feed("edgecore/amx-3200-48v-psu@1") == "dc"
    assert feed("edgecore/eps201-psu-150w@1") is None      # names no feed
    assert feed("edgecore/dcs240-psu-ac@1") == "ac"        # `dcs` is not `dc`


# ---- the census #513 was opened for ----------------------------------------

def test_every_whitebox_build_states_its_feed():
    """Every offered configuration of every Edgecore, UfiSpace and Celestica
    device resolves a feed - the filter the HCL runs has nothing to parse."""
    n = 0
    silent = []
    for slug, f in whitebox():
        if slug in NO_FEED:
            continue
        d = load(f)
        cfgs = d.get("configurations") or {"default": {}}
        for name, c in cfgs.items():
            n += 1
            if not config_power(d, c):
                silent.append(f"{slug}:{name}")
        assert device_options(d)["power"], slug
    assert not silent, silent
    assert n > 150, f"measured only {n} configurations"


def test_every_whitebox_device_states_airflow_or_says_why_not():
    """Airflow is stated wherever a source gives it. The three that do not are
    the Edgecore ECS campus switches, whose documents say nothing about fans,
    and each records that search as an `airflow-direction` gap."""
    missing = []
    for slug, f in whitebox():
        if slug in NO_FEED:
            continue
        d = load(f)
        if device_options(d)["airflow"]:
            continue
        if any(g.get("what") == "airflow-direction" for g in d.get("gaps") or []):
            continue
        missing.append(slug)
    assert not missing, missing


# ---- the published artifacts ----------------------------------------------

def svg_powers(outdir, device, cfg):
    got = set()
    for f in outdir.glob(f"{device}.{cfg}.*.svg"):
        m = POWER_ATTR.search(SVG_ROOT.search(f.read_text()).group(0))
        got.add(m.group(1) if m else None)
    return got


def test_configs_json_carries_power_per_build_and_the_options(tmp_path):
    name = render(FOUR, tmp_path)
    idx = json.loads((tmp_path / f"{name}.configs.json").read_text())
    got = {c["name"]: (c["power"], c["airflow"]) for c in idx["configs"]}
    assert got == {"ac-f2b": (["ac"], "front-to-back"),
                   "ac-b2f": (["ac"], "back-to-front"),
                   "dc-f2b": (["dc"], "front-to-back"),
                   "dc-b2f": (["dc"], "back-to-front")}
    assert idx["options"] == {"power": ["ac", "dc"],
                              "airflow": ["back-to-front", "front-to-back"]}
    for c in idx["configs"]:
        assert svg_powers(tmp_path, name, c["name"]) == {" ".join(c["power"])}


def test_a_chassis_feed_is_inherited_by_every_build(tmp_path):
    name = render(FIXED, tmp_path)
    idx = json.loads((tmp_path / f"{name}.configs.json").read_text())
    assert idx["chassis"]["power"] == "dc"
    assert {tuple(c["power"]) for c in idx["configs"]} == {("dc",)}
    assert idx["options"]["power"] == ["dc"]


def test_a_build_fed_two_ways_lists_both(tmp_path):
    name = render(BOTH, tmp_path)
    idx = json.loads((tmp_path / f"{name}.configs.json").read_text())
    assert idx["options"]["power"] == ["ac", "dc"]
    assert svg_powers(tmp_path, name, idx["configs"][0]["name"]) == {"ac dc"}


def test_comparable_reads_the_structured_fields():
    """The comparable `airflow` read only attrs prose, so a device stating it
    properly compared as if it said nothing."""
    facts = comparable.resolve(load(FOUR))
    assert {r["value"] for r in facts["airflow"]["readings"]} == {
        "front-to-back", "back-to-front"}
    assert {r["value"] for r in facts["power-feed"]["readings"]} == {"ac", "dc"}


def test_comparable_cites_the_override_where_only_a_build_states_it():
    """A back-to-front build of a front-to-back chassis: the chassis does not
    say back-to-front, so that reading must not cite it."""
    doc = {"chassis": {"airflow": "front-to-back", "power": "ac"},
           "configurations": {
               "f2b": {"kind": "orderable"},
               "b2f": {"kind": "orderable", "airflow": "back-to-front",
                       "power": "dc"}}}
    facts = comparable.resolve(doc)
    cited = {f: {r["value"]: r["from"] for r in facts[f]["readings"]}
             for f in ("airflow", "power-feed")}
    assert cited["airflow"] == {"front-to-back": "chassis.airflow",
                                "back-to-front": "configurations.*.airflow"}
    assert cited["power-feed"] == {"ac": "chassis.power",
                                   "dc": "configurations.*.power"}


@pytest.mark.skipif(not (DIST / "devices.json").is_file(),
                    reason="dist/ not built; run ./publish.sh --no-images")
def test_devices_json_publishes_the_options():
    entries = json.loads((DIST / "devices.json").read_text())["devices"]
    by = {e["name"]: e for e in entries}
    assert all("options" in e for e in entries)
    assert by["as7326-56x"]["options"]["power"] == ["ac", "dc"]
    stated = sum(1 for e in entries if e["options"]["power"])
    assert stated > 80, f"only {stated} devices publish a feed"
