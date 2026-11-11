"""What the PRO4X guides and per-SKU data sheets add to the Smart POPS 4T16A, Switched 4F16A and Smart 4C16A.

What is true of the library: each device says, in its own gap and provenance text, what the PRO4X User Guide and
Quick Setup Guide document about the controller, which end the per-SKU data sheets number outlet 1 from, and what
the maker prints on the controller's jacks against the ids the controller part gives them. The family-faces gap
stays, because a photograph of the family's own unit is still not held.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "servertech"

NAMES = ["pro4x-smart-pops-4t16a", "pro4x-switched-4f16a", "pro4x-smart-4c16a"]


def _device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text(encoding="utf-8"))


def _gap(name, what):
    return next(g for g in _device(name)["gaps"] if g["what"] == what)


def _flat(text):
    return re.sub(r"\s+", " ", text)


@pytest.mark.parametrize("name", NAMES)
def test_family_faces_says_what_the_guides_document_and_stays_a_gap(name):
    note = _flat(_gap(name, "family-faces")["note"])
    assert "Quick Setup Guide" in note and "User Guide" in note
    assert "iX9" in note
    assert "port locations" in note
    assert "no held document shows a different controller" in note
    assert "front" in _gap(name, "family-faces")["scope"]


@pytest.mark.parametrize("name", NAMES)
def test_numbering_names_both_ends_the_data_sheets_state(name):
    note = _flat(_device(name)["provenance"]["numbering"]["note"])
    assert "BD2FE1" in note and "opposite the power input" in note
    assert "BD2EE1" in note and "at the power input" in note


@pytest.mark.parametrize("name", NAMES)
def test_port_names_says_what_the_maker_prints_against_the_ids(name):
    note = _flat(_gap(name, "port-names")["note"])
    for printed in ("ETH 1", "ETH 2", "USB-A 1", "USB-A 2", "USB-B", "PDU LINK", "SENSOR"):
        assert printed in note, printed
    assert "eth0" in note and "eth1" in note and "from 0" in note
    assert "page" in note
