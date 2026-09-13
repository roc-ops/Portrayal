"""The connector components this plan adds, checked against their own claims.

Each connector declares a fibre capacity that plan 1's `optical` rules read, and
a size that is the panel aperture. These tests pin the facts other contracts will
compose against - a wrong `positions` silently mis-models every module using it.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def contract(ref):
    name, major = ref.split("@")
    p = LIB / "components" / name / f"v{major}" / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_the_mpo_aperture_exists_and_conforms():
    c = contract("std/mpo@1")
    assert c is not None, "std/mpo@1 not built"
    assert c["conforms"] == "mpo-adapter"
    assert c["class"] == "port"


def test_the_mpo_adapter_presents_twelve_fibres_by_default():
    c = contract("common/mpo-adapter@1")
    assert c is not None, "common/mpo-adapter@1 not built"
    assert (c.get("optical") or {}).get("positions") == 12, (
        "an MPO-12 is twelve fibres; every module composing it inherits this")


def test_the_mpo_standard_records_the_measured_pitch():
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    s = std["standards"]["mpo-adapter"]
    assert s["pitch"] == 13.8
    assert s["pitch-confidence"] == "measured"
    assert "35510" in s["registry"], (
        "the registry entry must name the image the pitch was measured from")


def test_the_sc_duplex_adapter_presents_two_fibres():
    c = contract("common/sc-duplex-adapter@1")
    assert c is not None, "common/sc-duplex-adapter@1 not built"
    assert (c.get("optical") or {}).get("positions") == 2


def test_the_sc_standard_names_where_its_pitch_came_from():
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    s = std["standards"]["sc-duplex-adapter"]
    assert s["pitch-confidence"] in ("measured", "estimated")
    assert "57058" in s["registry"] or "61754-4" in s["registry"], (
        "name the image or the standard the pitch came from")
