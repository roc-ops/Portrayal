"""The first library builds that state their own attributes and export description.

A DCIM device type is made for each orderable configuration that has a part
number, and until now every one of them showed the device's first sentence and
the device's figures. Three builds say something of their own:

  - the Cisco ASR 9001-S is the 60 Gbps variant of the ASR 9001: the device
    states the 9001's 120 Gbps once, and the -S states its own fabric bandwidth
    and the description a DCIM shows for it;
  - the Arista 7280DR3AM-54 and 7280DR3AK-54 are the 7280DR3A-54 with TunnelSec
    (and, for the K, large routes): the data sheet prints the same power, memory,
    CPU and software release for all three, so only the description is theirs.

What these pin is what is true of the library: the resolved figure, the text a
DCIM shows, and that the committed device types carry both. The device's own
figure and the drawing are not read here.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import manifest

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
EXPORTS = LIB / "exports"

ASR = "cisco/asr-9001"
DR3A = "arista/7280dr3a-54"

# (device, configuration, exported device type) for each build with its own text
TYPES = [
    (ASR, "asr-9001-s", "Cisco/ASR 9001-S Router with 2 x 10 GE.yaml"),
    (DR3A, "ac-m", "Arista/DCS-7280DR3AM-54-F.yaml"),
    (DR3A, "ac-k", "Arista/DCS-7280DR3AK-54-F.yaml"),
]


def dev(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


def cfg(slug, name):
    return dev(slug)["configurations"][name]


# --- the ASR 9001-S ------------------------------------------------------------

def test_the_9001_s_states_its_own_fabric_bandwidth():
    d = dev(ASR)
    got = manifest.config_attrs(d, d["configurations"]["asr-9001-s"])
    assert got["performance"]["fabric-bandwidth"] == "60 Gbps"


def test_the_full_9001_keeps_the_devices_fabric_bandwidth():
    d = dev(ASR)
    got = manifest.config_attrs(d, d["configurations"]["asr-9001"])
    assert got["performance"]["fabric-bandwidth"] == "120 Gbps"


def test_the_9001_s_changes_only_the_fabric_bandwidth_of_its_section():
    d = dev(ASR)
    got = manifest.config_attrs(d, d["configurations"]["asr-9001-s"])["performance"]
    assert got["integrated-interfaces"] == d["attrs"]["performance"]["integrated-interfaces"]
    assert got["modular-port-adapters"] == d["attrs"]["performance"]["modular-port-adapters"]


def test_the_9001_s_facts_list_reads_60_and_not_120():
    d = dev(ASR)
    body = dx.comments_for(d, "asr-9001-s", d["configurations"]["asr-9001-s"])
    assert "- performance.fabric-bandwidth: 60 Gbps" in body
    assert "fabric-bandwidth: 120 Gbps" not in body


def test_the_full_9001_facts_list_still_reads_120():
    d = dev(ASR)
    body = dx.comments_for(d, "asr-9001", d["configurations"]["asr-9001"])
    assert "- performance.fabric-bandwidth: 120 Gbps" in body


def test_the_9001_s_description_says_9001_s_and_not_120():
    text = cfg(ASR, "asr-9001-s")["export-description"]
    assert "9001-S" in text and "60 Gbps" in text
    assert "120 Gbps of" not in text


def test_the_9001_s_text_no_longer_says_it_cannot_carry_the_figure():
    text = " ".join(cfg(ASR, "asr-9001-s")["description"].split())
    assert "cannot carry" not in text and "cannot mark" not in text
    assert "STILL CANNOT SAY" not in text


# --- the 7280DR3AM-54 and 7280DR3AK-54 ----------------------------------------

@pytest.mark.parametrize("name,model", [("ac-m", "7280DR3AM-54"), ("ac-k", "7280DR3AK-54")])
def test_each_build_names_itself(name, model):
    text = cfg(DR3A, name)["export-description"]
    assert text.startswith(f"Arista {model} - "), text
    assert "TunnelSec" in text


def test_only_the_k_build_says_large_routes():
    assert "large-routes" in cfg(DR3A, "ac-k")["export-description"]
    assert "large" not in cfg(DR3A, "ac-m")["export-description"]


def test_the_plain_build_keeps_the_devices_description():
    assert "export-description" not in cfg(DR3A, "ac")


# --- the exported device types -------------------------------------------------

@pytest.mark.parametrize("slug,name,file", TYPES)
def test_every_description_fits_the_exporters_limit(slug, name, file):
    text = cfg(slug, name)["export-description"]
    assert len(text) <= dx.LIMIT and dx.fit(text) == text


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("slug,name,file", TYPES)
def test_the_committed_type_shows_the_builds_description(target, slug, name, file):
    out = yaml.safe_load((EXPORTS / target / "device-types" / file).read_text())
    assert out["description"] == cfg(slug, name)["export-description"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_committed_9001_s_type_lists_60_gbps(target):
    out = yaml.safe_load(
        (EXPORTS / target / "device-types" / TYPES[0][2]).read_text())
    assert "- performance.fabric-bandwidth: 60 Gbps" in out["comments"]
    assert "fabric-bandwidth: 120 Gbps" not in out["comments"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_committed_full_9001_type_is_not_changed_to_60(target):
    out = yaml.safe_load(
        (EXPORTS / target / "device-types" / "Cisco/ASR 9001 Router.yaml").read_text())
    assert "- performance.fabric-bandwidth: 120 Gbps" in out["comments"]
