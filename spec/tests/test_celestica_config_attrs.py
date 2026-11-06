"""The Celestica ES1000 and DS4000 state each build's own figures on the build.

Both devices are one chassis sold under several part numbers that differ in
power, CPU, memory and storage. A configuration's `attrs` and `export-description`
carry what a build states differently, `manifest.config_attrs` resolves them over
the device's, and the DCIM export prints the result for that build's device type.

Sources, by maker and title as printed:
  - Celestica ES1000 hardware guide: Key System Specifications (power consumption),
    Table of Attributes (CPU, memory and SSD per SKU), PSU Power Options (supplies
    and the PoE budget tables), and the ES1000 datasheet (features, order information).
  - Celestica DS4000/DS4001 Installation Guide: What's in the Box, Table 1 (the six
    DS4000 chassis SKUs with CPU, memory and SSD).
"""
import pathlib

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import manifest

LIB = pathlib.Path(__file__).resolve().parents[2] / "library"


def load(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


ES1000 = load("celestica/es1000")
DS4000 = load("celestica/ds4000")

ARM = ("integrated ARM A55, 2C 1.5 GHz", "8 GB DDR4", "32 GB eMMC")
COME = ("Intel Denverton x86 4C 2.1 GHz (COMe)", "8 GB DDR4 (16 GB option)", "32 GB M.2 SSD (64 GB option)")

# configuration: (sku name, power-max-w, poe-budget-w or None, (cpu, memory, storage))
ES1000_BUILDS = {
    "24-f2b": ("ES1000-24", "550", None, ARM),
    "24-b2f": ("ES1000-24", "550", None, ARM),
    "24p-f2b": ("ES1000-24P", "3200", "1550", ARM),
    "24p-b2f": ("ES1000-24P", "3200", "1550", ARM),
    "48-f2b": ("ES1000-48", "550", None, ARM),
    "48-b2f": ("ES1000-48", "550", None, ARM),
    "48p-f2b": ("ES1000-48P", "3200", "2910", ARM),
    "48p-b2f": ("ES1000-48P", "3200", "2910", ARM),
    "48c-f2b": ("ES1000-48C", "550", None, COME),
    "48c-b2f": ("ES1000-48C", "550", None, COME),
    "48cp-f2b": ("ES1000-48CP", "3200", "2910", COME),
    "48cp-b2f": ("ES1000-48CP", "3200", "2910", COME),
}

D1627 = "Intel Xeon D-1627 4-core"
D1649N = "Intel Xeon D-1649N 8-core"
DS4000_BUILDS = {
    "f2b": (D1627, "16 GB DDR4 ECC (1 x 16 GB)", "64 GB M.2 SSD"),
    "f2b-2x16g-128g": (D1627, "32 GB DDR4 ECC (2 x 16 GB)", "128 GB M.2 SSD"),
    "f2b-8c-256g": (D1649N, "32 GB DDR4 ECC (2 x 16 GB)", "256 GB M.2 SSD"),
    "b2f": (D1627, "16 GB DDR4 ECC (1 x 16 GB)", "64 GB M.2 SSD"),
    "b2f-2x16g-128g": (D1627, "32 GB DDR4 ECC (2 x 16 GB)", "128 GB M.2 SSD"),
    "b2f-8c-256g": (D1649N, "32 GB DDR4 ECC (2 x 16 GB)", "256 GB M.2 SSD"),
}


def facts(device, name):
    """The `- section.key: value` lines the export prints for one configuration."""
    cfg = device["configurations"][name]
    out = dx.build(device, name, cfg, None)
    return [ln for ln in out["comments"].splitlines() if ln.startswith("- ")]


def test_the_tables_cover_every_configuration_that_exports():
    for device, builds in ((ES1000, ES1000_BUILDS), (DS4000, DS4000_BUILDS)):
        exporting = {n for n, c in device["configurations"].items()
                     if c.get("part-numbers") and c.get("kind") != "example"}
        assert exporting == set(builds), exporting ^ set(builds)


@pytest.mark.parametrize("name", sorted(ES1000_BUILDS))
def test_an_es1000_build_states_its_own_power(name):
    _, power_max, poe, _ = ES1000_BUILDS[name]
    power = manifest.config_attrs(ES1000, ES1000["configurations"][name])["power"]
    assert power["power-max-w"] == power_max
    if poe:
        assert power["poe-budget-w"] == poe


@pytest.mark.parametrize("name", sorted(ES1000_BUILDS))
def test_an_es1000_build_states_its_own_cpu_memory_and_storage(name):
    _, _, _, (cpu, memory, storage) = ES1000_BUILDS[name]
    plat = manifest.config_attrs(ES1000, ES1000["configurations"][name])["platform"]
    assert (plat["cpu"], plat["memory"], plat["storage"]) == (cpu, memory, storage)
    assert f"- power.power-max-w: {ES1000_BUILDS[name][1]}" in facts(ES1000, name)


@pytest.mark.parametrize("name", sorted(ES1000_BUILDS))
def test_an_es1000_type_describes_its_own_model(name):
    sku, _, poe, _ = ES1000_BUILDS[name]
    cfg = ES1000["configurations"][name]
    text = cfg["export-description"]
    assert len(text) <= 200
    assert f"{sku} " in text and "24 or 48" not in text
    assert ("PoE++" in text) == bool(poe)
    assert dx.build(ES1000, name, cfg, None)["description"] == text


@pytest.mark.parametrize("name", sorted(DS4000_BUILDS))
def test_a_ds4000_build_states_its_own_control_plane(name):
    cpu, memory, storage = DS4000_BUILDS[name]
    plat = manifest.config_attrs(DS4000, DS4000["configurations"][name])["platform"]
    assert (plat["cpu"], plat["memory"], plat["storage"]) == (cpu, memory, storage)
    lines = facts(DS4000, name)
    assert f"- platform.cpu: {cpu}" in lines
    assert not [ln for ln in lines if "(per SKU)" in ln]


def test_the_ds4000_figure_drawings_state_no_build():
    """The two illustration fronts name no SKU, so they carry no build's figures."""
    for name in ("f2b-2sfp", "f2b-kr"):
        cfg = DS4000["configurations"][name]
        assert cfg["kind"] == "example" and not cfg.get("part-numbers")
        assert "attrs" not in cfg and "export-description" not in cfg
