"""The Raritan PX4's HDOT Cx outlet has its own connector key, `raritan-hdot-cx`.

What is true of the library once the key is in it: the registry names the key and cites the
PX4 data sheet, raritan/px4-cx-outlet presents it at a mate point, and the C14 and C20 plugs
name it among the outlets they enter.
"""
import pathlib

import yaml

from portrayal.manifest import mates_of

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "library" / "components"
KEY = "raritan-hdot-cx"


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _contract(ns_name):
    return _load(COMPONENTS / ns_name / "v1" / "contract.yaml")


def test_the_registry_names_the_key_and_cites_the_px4_data_sheet():
    registry = _load(ROOT / "spec" / "schemas" / "connectors.yaml")
    note = registry["interfaces"][KEY]["note"]
    assert "PX4" in note and "data sheet" in note
    assert "raritan/px4-cx-outlet@1" in note
    assert "generic/c14-plug@1" in note and "generic/c20-plug@1" in note


def test_the_cx_outlet_presents_the_key_at_a_mate_point():
    contract = _contract("raritan/px4-cx-outlet")
    assert contract["interface"] == KEY
    assert contract["attrs"]["outlet"] == KEY
    assert "mate" in contract["connection-points"]
    assert "unmated" not in contract


def test_the_c14_and_c20_plugs_mate_the_key():
    for plug in ("generic/c14-plug", "generic/c20-plug"):
        assert KEY in mates_of(_contract(plug)), plug


def test_the_contract_says_where_the_key_and_the_mate_point_come_from():
    provenance = _contract("raritan/px4-cx-outlet")["provenance"]
    assert KEY in provenance["interface"]
    assert "mate" in provenance
    assert "estimated" in provenance["mate"]
