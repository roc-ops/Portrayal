"""Juniper's DPC and SCB slot blank is one part, DPC-SCB-BLANK, and the library models it once.

Juniper's MX480 and MX960 hardware guides each list one blank, DPC-SCB-BLANK, for the DPC and SCB slots (Table 5 of each).
The library drew two: one with a printed 0/1 rotary legend beside the left knob, as the MX480 photograph shows, and one
without it, as the MX960 photograph shows. The plate, the knobs and the slot are the same on both photographs, so the
two printings are one part: a single component, exported once, with the unmarked printing as a second skin.

These run against the real library: the contracts and skins on disk, the devices' manifests, and the components index
the build runs. They read no library/dist and render nothing.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild
from portrayal import dcim_export as dx

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
BLANK = "juniper/mx-dpc-blank@2"
RETIRED = "juniper/mx960-blank@1"
PART_NUMBER = "DPC-SCB-BLANK"
DEVICES = ("mx240", "mx480", "mx960")


def folder(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((folder(ref) / "contract.yaml").read_text())


def manifest(device):
    return yaml.safe_load((LIB / "devices" / "juniper" / device / "device.yaml").read_text())


def live_contracts():
    return {str(p.parent.parent.relative_to(LIB / "components")) + "/" + p.parent.name: yaml.safe_load(p.read_text())
            for p in (LIB / "components").glob("*/*/v*/contract.yaml")}


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_one_live_contract_carries_the_part_number():
    carriers = [ref for ref, c in live_contracts().items()
                if PART_NUMBER in [m for m, _pn in dx.module_names(c)]]
    assert carriers == [f"{BLANK.split('@')[0]}/v2"], carriers


def test_the_blank_is_exported_under_its_part_number_and_not_its_description():
    names = [m for m, _pn in dx.module_names(contract(BLANK))]
    assert names == [PART_NUMBER], names
    described = [ref for ref, c in live_contracts().items()
                 if "MX Series DPC slot blank" in [m for m, _pn in dx.module_names(c)]]
    assert described == [], described


@pytest.mark.parametrize("device", DEVICES)
def test_a_blank_is_what_each_chassis_seats_in_its_empty_slots(device):
    configs = manifest(device)["configurations"]
    seated = {ref for cfg in configs.values() for ref in (cfg.get("bays") or {}).values()}
    assert BLANK in seated, seated


def test_the_two_printings_are_two_skins_of_the_part():
    c = contract(BLANK)
    assert c["skins"] == ["default", "plain"]
    skins = folder(BLANK) / "skins"
    marked = (skins / "default.svg").read_text()
    plain = (skins / "plain.svg").read_text()
    assert re.search(r">0</text>", marked) and re.search(r">1</text>", marked)
    assert "silkscreen" not in plain
    for node in ('id="plate"', 'id="knob-left"', 'id="knob-right"'):
        assert node in marked and node in plain


def test_the_mx960_prints_no_mark_and_the_others_keep_the_one_the_mx480_photograph_shows():
    for device in DEVICES:
        for name, cfg in manifest(device)["configurations"].items():
            chosen = (cfg.get("skins") or {}).get("mx-dpc-blank")
            if device == "mx960":
                assert chosen == "plain", (device, name, chosen)
            else:
                assert chosen in (None, "default"), (device, name, chosen)


def test_a_saved_rack_that_names_the_retired_blank_is_sent_to_the_survivor(index):
    claims = {c["ref"]: c for c in index[BLANK]["supersedes"]}
    assert RETIRED in claims, claims
