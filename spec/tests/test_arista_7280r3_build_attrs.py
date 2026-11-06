"""Nine Arista 7280R3 builds state their own memory, CPU, storage, minimum EOS and DCIM description.

The 7280CR3-32P4, 7280CR3-96, 7280DR3-24, 7280PR3-24 and 7280SR3-40YC6 each share one front panel across a base
model and its K, K-A or E-M builds. The builds differ only in what the 7280R3 Series Data Sheet (03-0045-59) prints in
its model comparison table: system memory, CPU, flash and SSD, minimum EOS, and the "large routes" or "SyncE,
expn. mem" words of the ordering information. Each such build is a configuration with its own part number, so it states
those values in its own `attrs` and a description of its own in `export-description`.

What the data sheet does not print as one value is not stated: the base models' "8 GB (64 GB optional)" stays the
device's own line. The power draw of every build is the guide's Table 4 figure, which is the device's: the 7280CR3K-32P4A
is 535 W / 851 W there (the data sheet's 543 W / 865 W is the figure the device records as a conflict), so no build
here states a power figure.

Each test reads the YAML a contributor edits or the generated export a DCIM user imports. None reads `library/dist`.
"""
import pathlib
import re

import pytest
import yaml

from portrayal import manifest

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
LIMIT = 200

K32 = {"platform": {"cpu": "Quad-Core x86", "memory": "64 GB", "storage": "8 GB flash; 120 GB SSD"},
       "features": {"eos-license": "license group G3; minimum EOS 4.22.1"}}
K32A = {"platform": {"cpu": "Eight-Core x86", "memory": "64 GB", "storage": "120 GB SSD (no flash storage)"},
        "features": {"eos-license": "license group G3; minimum EOS 4.27.2"}}
K24 = {"platform": {"memory": "64 GB", "storage": "8 GB flash; 120 GB SSD"}}
SR3E = {"platform": {"memory": "32 GB"},
        "features": {"eos-license": "license group G2; minimum EOS 4.28.1"}}

# device -> configuration -> (the part number it exports as, the model its description names, its own attrs)
BUILDS = {
    "7280cr3-32p4": {"k-f": ("DCS-7280CR3K-32P4-F", "7280CR3K-32P4", K32),
                     "k-r": ("DCS-7280CR3K-32P4-R", "7280CR3K-32P4", K32),
                     "k-a-f": ("DCS-7280CR3K-32P4A-F", "7280CR3K-32P4A", K32A),
                     "k-a-r": ("DCS-7280CR3K-32P4A-R", "7280CR3K-32P4A", K32A)},
    "7280cr3-96": {"k-f": ("DCS-7280CR3K-96-F", "7280CR3K-96", None)},
    "7280dr3-24": {"k-f": ("DCS-7280DR3K-24-F", "7280DR3K-24", K24)},
    "7280pr3-24": {"k-f": ("DCS-7280PR3K-24-F", "7280PR3K-24", K24)},
    "7280sr3-40yc6": {"m-f": ("DCS-7280SR3E-40YC6-M-F", "7280SR3E-40YC6-M", SR3E),
                      "m-r": ("DCS-7280SR3E-40YC6-M-R", "7280SR3E-40YC6-M", SR3E)},
}
ROWS = [(d, c) + b for d, cfgs in BUILDS.items() for c, b in cfgs.items()]
IDS = [f"{d}:{c}" for d, c, *_ in ROWS]
DEVICES = sorted(BUILDS)


def load(dev):
    return yaml.safe_load((LIB / "devices/arista" / dev / "device.yaml").read_text())


def facts(doc):
    """The `comments` facts list of an exported device type, as {'section.key': value}."""
    out = {}
    for line in doc["comments"].splitlines():
        if line.startswith("- ") and ": " in line:
            k, v = line[2:].split(": ", 1)
            out[k] = v
    return out


@pytest.mark.parametrize("dev,cfg,pn,model,attrs", ROWS, ids=IDS)
def test_the_build_states_the_values_the_data_sheet_prints_for_its_model(dev, cfg, pn, model, attrs):
    c = load(dev)["configurations"][cfg]
    assert list(c["part-numbers"]) == [pn]
    assert c.get("attrs") == attrs


@pytest.mark.parametrize("dev,cfg,pn,model,attrs", ROWS, ids=IDS)
def test_the_build_describes_itself_for_a_dcim_in_200_characters_or_fewer(dev, cfg, pn, model, attrs):
    text = load(dev)["configurations"][cfg]["export-description"]
    assert len(text) <= LIMIT
    assert text.startswith(f"Arista {model} - ")
    assert not re.search(r"\d\s*W\b", text)   # a power figure belongs in `attrs`, not in prose


@pytest.mark.parametrize("dev,cfg,pn,model,attrs", ROWS, ids=IDS)
def test_the_resolved_attrs_are_the_builds_own_over_the_devices(dev, cfg, pn, model, attrs):
    d = load(dev)
    got = manifest.config_attrs(d, d["configurations"][cfg])
    for section, keys in (attrs or {}).items():
        for key, value in keys.items():
            assert got[section][key] == value
    assert got["power"] == d["attrs"]["power"]


@pytest.mark.parametrize("dev,cfg,pn,model,attrs", ROWS, ids=IDS)
def test_no_build_states_a_power_figure_of_its_own(dev, cfg, pn, model, attrs):
    assert "power" not in (attrs or {})


def test_the_32p4_builds_carry_the_guides_power_figure_not_the_data_sheets():
    """Guide Table 4 gives the 7280CR3K-32P4A 535 W / 851 W, as the base; the data sheet's 543 W / 865 W is not stated."""
    d = load("7280cr3-32p4")
    for cfg in ("k-f", "k-r", "k-a-f", "k-a-r"):
        p = manifest.config_attrs(d, d["configurations"][cfg])["power"]
        assert (p["power-typical-w"], p["power-max-w"]) == (535, 851)


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("dev,cfg,pn,model,attrs", ROWS, ids=IDS)
def test_the_exported_type_carries_the_builds_description_and_facts(dev, cfg, pn, model, attrs, target):
    path = LIB / "exports" / target / "device-types/Arista" / f"{pn}.yaml"
    doc = yaml.safe_load(path.read_text())
    assert doc["description"] == load(dev)["configurations"][cfg]["export-description"]
    got = facts(doc)
    for section, keys in (attrs or {}).items():
        for key, value in keys.items():
            assert got[f"{section}.{key}"] == value


@pytest.mark.parametrize("dev", DEVICES)
def test_the_device_no_longer_declares_the_gap_a_configuration_could_not_state(dev):
    assert not [g for g in load(dev)["gaps"] if g["what"] == "config-scoped-device-attrs"]


@pytest.mark.parametrize("dev", DEVICES)
def test_only_a_configuration_with_a_part_number_states_its_own_attrs(dev):
    for name, c in load(dev)["configurations"].items():
        if c.get("attrs") or c.get("export-description"):
            assert c.get("part-numbers"), (dev, name)
            assert c.get("kind") in ("base", "orderable", "model"), (dev, name)
