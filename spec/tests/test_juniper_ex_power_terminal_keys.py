"""The EX4100-H terminal pad and the EX2200 RPS port present a registered interface.

Two parts of the Juniper EX power set drew a connector and presented no interface, so nothing could be
seated on them:

  juniper/ex4100-h-terminal-pad@1   the twelve wire terminals behind the terminal door of the EX4100-H-24MP
                                    and -24F. The guide draws a crimped ring lug under each screw head
                                    (Figures 109 and 110) and its text says the wire goes into the slot behind
                                    the screw. The pad presents `terminal-stud`, which generic/ring-lug@1 mates.
  juniper/ex2200-rps-port@1         the RPS port of the four EX2200. The RPS hardware guide says each EX2200 and
                                    EX3300 has a built-in RPS connector and shows one cable going into an EX2200,
                                    so the port presents `ex3300-rps`, which juniper/ex3300-rps-plug@1 mates.

These run against the real library and need no build.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/juniper"

PAD = "juniper/ex4100-h-terminal-pad@1"
LUG = "generic/ring-lug@1"
RPS_PORT = "juniper/ex2200-rps-port@1"
RPS_PLUG = "juniper/ex3300-rps-plug@1"

EX4100H = ["ex4100-h-24f", "ex4100-h-24mp"]
EX2200 = ["ex2200-24p", "ex2200-24t", "ex2200-48p", "ex2200-48t"]
PAD_IDS = {f"psu-{s}-{t}" for s in (0, 1) for t in ("l", "n", "g-ac", "dc-plus", "dc-minus", "g-dc")}


def contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / f"components/{ns}/{name}/v{major}/contract.yaml").read_text())


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def slots(name, view):
    d = device(name)
    lib = render_mod.Library([str(LIB)])
    return {s["id"]: s for s in render_mod.cage_entries(
        d, view, lib, render_mod._pluggable_families(), render_mod._pluggable_candidates([str(LIB)]), {},
        render_mod._connector_registry())}


def prov(ref):
    return "\n".join(str(v) for v in contract(ref)["provenance"].values())


# --- the pad ----------------------------------------------------------------------------------------

def test_the_pad_presents_terminal_stud_at_its_centre_and_its_drawing_is_unchanged():
    c = contract(PAD)
    assert c["interface"] == "terminal-stud"
    assert c["connection-points"]["mate"] == {"at": [2.0, 2.0], "direction": "front"}
    assert c["size"] == {"w": 4.0, "h": 4.0}
    assert c["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert c["elements"] == {"pad": {"at": [0.0, 0.0], "size": [4.0, 4.0], "class": "connector"}}
    assert c["class"] == "inlet" and c["attrs"] == {"media": "power-terminal"}


def test_the_pad_records_both_statements_of_the_guide_and_the_torque():
    c = contract(PAD)
    text = " ".join(c["provenance"]["interface"].split())
    for needed in ("Figures 109 and 110", "ring lug", "slots behind the screws", "7 +/- 0.5 Lb.in", "claims none"):
        assert needed in text, needed
    assert " ".join(c["provenance"]["mate"].split()).startswith("derived")


def test_the_ring_lug_mates_the_key_the_pad_presents():
    assert contract(LUG)["mates"] == contract(PAD)["interface"]


@pytest.mark.parametrize("name", EX4100H)
def test_each_of_the_twelve_pads_is_a_connector_slot_that_takes_a_ring_lug(name):
    got = slots(name, "front")
    pads = {i: s for i, s in got.items() if i in PAD_IDS}
    assert set(pads) == PAD_IDS
    for i, s in pads.items():
        assert s["kind"] == "connector" and s["interface"] == "terminal-stud", i
        assert s["mate"] is not None and LUG in s["accepts"], i


# --- the EX2200 RPS port ----------------------------------------------------------------------------

def test_the_ex2200_port_presents_the_ex3300_key_with_a_mate_at_the_centre_of_its_opening():
    c = contract(RPS_PORT)
    assert c["interface"] == "ex3300-rps"
    el = c["elements"]["opening"]
    assert c["connection-points"]["mate"] == {"at": pytest.approx([el["at"][i] + el["size"][i] / 2 for i in (0, 1)],
                                                                   abs=1e-6), "direction": "front"}
    # what 1.0.0 drew is unchanged
    assert c["size"] == {"w": 67.9, "h": 14.6, "d": 20.0}
    assert el == {"at": [11.7, 2.9], "size": [44.5, 8.9], "class": "slot"}
    assert c["class"] == "inlet" and c["behaviour"] == "mounts" and c["attrs"] == {"media": "rps"}


def test_the_ex2200_port_says_the_key_is_a_reading_from_one_cable():
    text = " ".join(prov(RPS_PORT).split())
    for needed in ("READING FROM ONE CABLE", "Figure 16", "Figure 17", "names no connector type"):
        assert needed in text, needed
    note = render_mod._connector_registry()["ex3300-rps"]["note"]
    assert RPS_PORT in note and "juniper/ex3300-rps-port@1 presents it" in note and f"{RPS_PLUG} mates it" in note


@pytest.mark.parametrize("name", EX2200)
def test_each_ex2200_rps_placement_is_a_connector_slot_that_accepts_the_rps_plug(name):
    got = slots(name, "rear")
    assert got["rps"]["kind"] == "connector" and got["rps"]["interface"] == "ex3300-rps"
    assert got["rps"]["mate"] is not None and RPS_PLUG in got["rps"]["accepts"]


@pytest.mark.parametrize("name", EX2200)
def test_each_ex2200_still_declares_the_rps_connector_gap(name):
    doc = yaml.safe_load((DEVICES / name / "layout.yaml").read_text())
    gap = next(g for g in doc["gaps"] if g["what"] == "rps-port-connector")
    assert "connector type" in gap["wanted"] and "nothing mates it" not in gap["wanted"]
