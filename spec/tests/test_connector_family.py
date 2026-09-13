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


import pytest  # noqa: E402


ESTIMATED = [
    ("common/st-simplex-adapter@1", 1),
    ("common/fc-simplex-adapter@1", 1),
    ("common/lsh-simplex-adapter@1", 1),
    ("common/mdc-adapter@1", 4),
    ("common/keystone-clip@1", 0),
]


@pytest.mark.parametrize("ref,positions", ESTIMATED)
def test_each_estimated_connector_exists_with_its_fibre_count(ref, positions):
    c = contract(ref)
    assert c is not None, f"{ref} not built"
    got = (c.get("optical") or {}).get("positions")
    if positions == 0:
        assert got is None, (
            "a keystone clip is a mechanical opening, not a fibre connector - "
            "it must declare no optical positions at all")
    else:
        assert got == positions


@pytest.mark.parametrize("ref,_positions", ESTIMATED)
def test_every_estimated_connector_says_it_is_estimated(ref, _positions):
    """The whole point of this task.

    These five were built from three-quarter renders because no face-on image
    exists. A dimension that does not say so reads exactly like one that was
    measured, and the next person cannot tell them apart.
    """
    c = contract(ref)
    prov = c.get("provenance") or {}
    assert prov.get("size"), f"{ref} states no size provenance"
    blob = " ".join(str(v) for v in prov.values()).upper()
    assert "ESTIMATE" in blob, (
        f"{ref}'s provenance never says its dimensions are estimated")
    assert "FACE-ON" in blob or "THREE-QUARTER" in blob or "RENDER" in blob, (
        f"{ref}'s provenance does not say what imagery it rests on")
