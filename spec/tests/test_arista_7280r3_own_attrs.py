"""The A builds of the 7280CR3-36S and the 7280SR3-48YC8 state their own figures.

The DCS-7280CR3K-36A and DCS-7280SR3K-48YC8A are builds of a base model's chassis that draw more power
and carry an eight-core CPU. Each is a configuration with its own part numbers, so each states what it
does differently in `attrs`, and a DCIM shows its own description and its own figures:

  - the 7280R3 Series Quick Start Guide (DOC-07041-01), Table 4: 262 W / 437 W for the 36A (254 W / 423 W
    for the 36S builds) and 162 W / 338 W for the 48YC8A (155 W / 325 W for the 48YC8 builds);
  - the 7280R3 Series Data Sheet (03-0045-59), the model comparisons: "Eight-Core x86", an SSD of
    120 GB (and no flash) and a minimum EOS of 4.27.2 for each A build, and 64 Gigabytes of memory for the
    K and A builds of the 48YC8 against 8 for the base model.

The tests read the YAML a contributor edits and the generated exports a DCIM user imports.
"""
import pathlib
import re

import pytest
import yaml

from portrayal import manifest

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# device -> the A configurations (part number), the guide's figures for them, the model the DCIM names
A_BUILDS = {
    "7280cr3-36s": dict(
        model="7280CR3K-36A", power=(262, 437), other=(254, 423),
        configs={"k-a-f": "DCS-7280CR3K-36A-F", "k-a-r": "DCS-7280CR3K-36A-R"}),
    "7280sr3-48yc8": dict(
        model="7280SR3K-48YC8A", power=(162, 338), other=(155, 325),
        configs={"k-a-f": "DCS-7280SR3K-48YC8A-F", "k-a-r": "DCS-7280SR3K-48YC8A-R"}),
}
CASES = [(dev, name) for dev, x in A_BUILDS.items() for name in x["configs"]]
# the 48YC8's six orderable builds, each with its part number and the memory the data sheet gives that model
MEMORY_48 = {"f": ("DCS-7280SR3-48YC8-F", "8 GB"), "r": ("DCS-7280SR3-48YC8-R", "8 GB"),
             "k-f": ("DCS-7280SR3K-48YC8-F", "64 GB"), "k-r": ("DCS-7280SR3K-48YC8-R", "64 GB"),
             "k-a-f": ("DCS-7280SR3K-48YC8A-F", "64 GB"), "k-a-r": ("DCS-7280SR3K-48YC8A-R", "64 GB")}


def load(dev):
    return yaml.safe_load((LIB / "devices/arista" / dev / "device.yaml").read_text())


def exported(target, pn):
    return yaml.safe_load((LIB / "exports" / target / "device-types/Arista" / f"{pn}.yaml").read_text())


def facts(doc):
    """The `- section.key: value` lines of an export's comments, as a dict."""
    return dict(line[2:].split(": ", 1) for line in doc["comments"].splitlines() if re.match(r"- \w+\.[\w-]+: ", line))


@pytest.mark.parametrize("dev,name", CASES)
def test_an_a_build_states_the_guides_power_figure(dev, name):
    d = load(dev)
    power = manifest.config_attrs(d, d["configurations"][name])["power"]
    assert (power["power-typical-w"], power["power-max-w"]) == A_BUILDS[dev]["power"]


@pytest.mark.parametrize("dev,name", CASES)
def test_an_a_build_states_the_data_sheets_cpu_ssd_and_minimum_eos(dev, name):
    d = load(dev)
    a = manifest.config_attrs(d, d["configurations"][name])
    assert a["platform"]["cpu"] == "Eight-Core x86"
    assert a["platform"]["storage"].startswith("120 GB SSD")
    assert "minimum EOS 4.27.2" in a["features"]["eos-license"]
    assert ("4.29.1" in a["features"]["eos-license"]) == (dev == "7280cr3-36s" and name == "k-a-r")


@pytest.mark.parametrize("name", sorted(MEMORY_48))
def test_each_build_of_the_48yc8_states_its_own_memory(name):
    d = load("7280sr3-48yc8")
    assert manifest.config_attrs(d, d["configurations"][name])["platform"]["memory"] == MEMORY_48[name][1]


@pytest.mark.parametrize("dev,name", CASES)
def test_an_a_build_has_an_export_description_that_names_it_and_fits(dev, name):
    text = load(dev)["configurations"][name]["export-description"]
    assert text.startswith(f"Arista {A_BUILDS[dev]['model']} - ")
    assert len(text) <= 200


@pytest.mark.parametrize("dev,name", CASES)
def test_no_description_of_an_a_build_states_a_power_its_attrs_contradict(dev, name):
    d = load(dev)
    cfg = d["configurations"][name]
    own = set(A_BUILDS[dev]["power"])
    for text in (cfg["description"], cfg["export-description"]):
        assert {int(n) for n in re.findall(r"(\d+) ?W\b", text)} <= own, text


@pytest.mark.parametrize("dev", sorted(A_BUILDS))
def test_the_figures_moved_out_of_prose_so_the_gap_is_closed(dev):
    assert not [g for g in load(dev)["gaps"] if g["what"] == "config-scoped-device-attrs"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("dev,name", CASES)
def test_the_exported_a_type_carries_its_own_description_and_figures(dev, name, target):
    x = A_BUILDS[dev]
    doc = exported(target, x["configs"][name])
    assert doc["description"] == load(dev)["configurations"][name]["export-description"]
    f = facts(doc)
    assert (f["power.power-typical-w"], f["power.power-max-w"]) == tuple(str(n) for n in x["power"])
    assert f["platform.cpu"] == "Eight-Core x86"
    assert "minimum EOS 4.27.2" in f["features.eos-license"]
    assert not {str(n) for n in x["other"]} & set(re.findall(r"(\d+) W\b", doc["comments"]))


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("name", sorted(MEMORY_48))
def test_the_exported_types_of_the_48yc8_carry_their_own_memory(name, target):
    pn, memory = MEMORY_48[name]
    assert facts(exported(target, pn))["platform.memory"] == memory
