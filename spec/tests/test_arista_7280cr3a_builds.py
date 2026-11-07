"""The M, K and K-S builds of the 7280CR3A-24D12, -48D6 and -72 state what differs in them.

The Arista 7280R3A Series Data Sheet (04-0040-26) prints, in each model comparison table, "Encryption"
as "All Ports" for the 7280CR3AM and 7280CR3AK and a dash for the 7280CR3A; its overview names the
7280R3AK as the model with over 5M IPv4 routes; and its ordering information marks only the
DCS-7280CR3AK-24D12-S builds "secure boot enabled". Every other row of those tables (power, memory,
CPU, SSD, minimum EOS, licence group) is one value for the three builds of a model, so a build does
not restate it. Each build is a configuration with its own part number, so it exports as a device
type of its own and carries what it states in `attrs` and `export-description`.

Each test reads the YAML a contributor edits, or the generated export a DCIM user imports.
"""
import pathlib

import pytest
import yaml

from portrayal import manifest

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
EXPORTS = LIB / "exports"

# device -> {configuration: (part number, model as the data sheet prints it)}
BUILDS = {
    "7280cr3a-24d12": {
        "m-f": ("DCS-7280CR3AM-24D12-F", "7280CR3AM-24D12"),
        "m-r": ("DCS-7280CR3AM-24D12-R", "7280CR3AM-24D12"),
        "k-f": ("DCS-7280CR3AK-24D12-F", "7280CR3AK-24D12"),
        "k-r": ("DCS-7280CR3AK-24D12-R", "7280CR3AK-24D12"),
        "ks-f": ("DCS-7280CR3AK-24D12-S-F", "7280CR3AK-24D12-S"),
        "ks-r": ("DCS-7280CR3AK-24D12-S-R", "7280CR3AK-24D12-S"),
    },
    "7280cr3a-48d6": {
        "m-f": ("DCS-7280CR3AM-48D6-F", "7280CR3AM-48D6"),
        "m-r": ("DCS-7280CR3AM-48D6-R", "7280CR3AM-48D6"),
        "k-f": ("DCS-7280CR3AK-48D6-F", "7280CR3AK-48D6"),
        "k-r": ("DCS-7280CR3AK-48D6-R", "7280CR3AK-48D6"),
    },
    "7280cr3a-72": {
        "m-f": ("DCS-7280CR3AM-72-F", "7280CR3AM-72"),
        "m-r": ("DCS-7280CR3AM-72-R", "7280CR3AM-72"),
        "k-f": ("DCS-7280CR3AK-72-F", "7280CR3AK-72"),
        "k-r": ("DCS-7280CR3AK-72-R", "7280CR3AK-72"),
    },
}
CASES = [(dev, name, pn, model) for dev, cfgs in BUILDS.items() for name, (pn, model) in cfgs.items()]
IDS = [f"{dev}/{name}" for dev, name, _, _ in CASES]
TARGETS = ["netbox", "nautobot"]


def load(dev):
    return yaml.safe_load((LIB / "devices/arista" / dev / "device.yaml").read_text())


def resolved(dev, name):
    d = load(dev)
    return manifest.config_attrs(d, d["configurations"][name])


def exported(target, pn):
    path = EXPORTS / target / "device-types/Arista" / f"{pn}.yaml"
    return yaml.safe_load(path.read_text())


def facts(doc):
    """The `- section.key: value` lines of an exported type's comments, as a dict."""
    out = {}
    for line in doc["comments"].splitlines():
        if line.startswith("- ") and ": " in line:
            key, value = line[2:].split(": ", 1)
            out[key] = value
    return out


@pytest.mark.parametrize("dev,name,pn,model", CASES, ids=IDS)
def test_every_build_states_that_it_encrypts_on_all_ports(dev, name, pn, model):
    enc = resolved(dev, name)["features"]["encryption"]
    assert enc.startswith("all ports") and "MACsec" in enc and "IPsec" in enc and "VXLANsec" in enc
    assert "none" not in enc


@pytest.mark.parametrize("dev,name,pn,model", CASES, ids=IDS)
def test_only_the_k_builds_say_large_routes_and_only_the_s_builds_secure_boot(dev, name, pn, model):
    feats = resolved(dev, name)["features"]
    assert "large-routes" not in feats and "secure-boot" not in feats, "no new key: the description says it"
    desc = " ".join(load(dev)["configurations"][name]["export-description"].split())
    assert ("large routes" in desc) == name.startswith("k")
    assert ("secure boot" in desc) == name.startswith("ks")


@pytest.mark.parametrize("dev,name,pn,model", CASES, ids=IDS)
def test_a_build_states_no_figure_the_data_sheet_gives_alike_to_every_build(dev, name, pn, model):
    own = load(dev)["configurations"][name]["attrs"]
    assert set(own) == {"features"}, "power, memory, CPU, storage, EOS and licence group are one value per model"


@pytest.mark.parametrize("dev,name,pn,model", CASES, ids=IDS)
def test_every_build_has_an_export_description_that_names_its_model(dev, name, pn, model):
    desc = load(dev)["configurations"][name]["export-description"]
    assert len(desc) <= 200
    assert desc.startswith(f"Arista {model} - ")


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("dev,name,pn,model", CASES, ids=IDS)
def test_the_exported_type_carries_the_builds_description_and_facts(dev, name, pn, model, target):
    doc = exported(target, pn)
    want = load(dev)["configurations"][name]["export-description"]
    assert " ".join(doc["description"].split()) == " ".join(want.split())
    got = facts(doc)
    own = resolved(dev, name)["features"]
    for key in ("encryption",):
        if key in own:
            assert got[f"features.{key}"] == own[key], key
        else:
            assert f"features.{key}" not in got, key
    assert "features.large-routes" not in got and "features.secure-boot" not in got


@pytest.mark.parametrize("dev", sorted(BUILDS))
def test_the_gap_the_builds_stated_is_closed(dev):
    d = load(dev)
    assert not [g for g in d["gaps"] if g["what"] == "config-scoped-device-attrs"]
    assert "config-scoped-device-attrs" not in " ".join(d["provenance"]["configurations"]["note"].split())
