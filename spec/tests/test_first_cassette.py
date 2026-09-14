"""FHD-1MTP6LCDOS2A, and the adapter it is built from.

Measured off FS's own face-on render of SKU 57016, scaled on the 108.97 mm FHD
faceplate and validated against the 35.05 mm height to 1.02%. What makes these
assertions worth making is that they are a measurement and not a guess.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import optical as O  # noqa: E402


def contract(rel):
    p = LIB / rel / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_the_stacked_lc_adapter_presents_two_fibres():
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c is not None, "common/lc-duplex-v-adapter@1 not built"
    assert (c.get("optical") or {}).get("positions") == 2


def test_the_stacked_lc_adapter_is_the_measured_width():
    """9.28 across all six adapters on 57016, spread 0.00."""
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c["size"]["w"] == 9.28


def test_the_stacked_adapter_is_the_measured_height():
    """13.75 across all six, spread 0.00 - top edge 10.66, bottom 24.41."""
    c = contract("common/lc-duplex-v-adapter/v1")
    assert c["size"]["h"] == 13.75


def test_the_stacked_adapter_says_which_of_its_dimensions_were_measured():
    c = contract("common/lc-duplex-v-adapter/v1")
    sc = c.get("size-confidence") or {}
    assert sc.get("w") == "photo-measured", \
        "the width IS measured - six bodies, spread 0.00 - and must say so"
    assert sc.get("h") == "photo-measured", \
        "so is the height - same six bodies, same spread"
    assert sc.get("d") == "estimated", \
        "the DEPTH is the one nobody can see in a face-on render"


def test_two_stacked_bores_actually_fit_in_the_body():
    """A 6.3-tall bore twice over needs 12.6, and the body is 13.75.

    An earlier draft of this plan sized the body at 12.0, borrowed from the SC
    shell - which would have put 12.6 mm of bore into 12.0 mm of adapter and
    drawn two apertures overlapping. Measuring the height instead of borrowing
    it is what caught that, so this is the assertion that keeps it caught.
    """
    c = contract("common/lc-duplex-v-adapter/v1")
    bores = [p for p in (c.get("parts") or []) if "lc-bore" in str(p.get("ref"))]
    ys = sorted(float(p["at"][1]) for p in bores)
    assert ys[1] >= ys[0] + 6.3, f"the bores overlap: {ys}"
    assert ys[1] + 6.3 <= c["size"]["h"], \
        f"the lower bore hangs out of the body: {ys[1]} + 6.3 > {c['size']['h']}"


def test_its_two_ports_are_stacked_not_side_by_side():
    """THE REASON THIS COMPONENT EXISTS.

    `common/lc-duplex-adapter@3` puts its bores side by side. A 6x crop of
    57016.main.jpg shows one dust cap over two ports one ABOVE the other, and
    the faceplate numbers agree - evens along the top, odds along the bottom.
    If a later edit lays these out abreast, this is what says so.
    """
    c = contract("common/lc-duplex-v-adapter/v1")
    bores = [p for p in (c.get("parts") or []) if "lc-bore" in str(p.get("ref"))]
    assert len(bores) == 2, [p.get("ref") for p in c.get("parts") or []]
    xs = {round(float(p["at"][0]), 3) for p in bores}
    ys = {round(float(p["at"][1]), 3) for p in bores}
    assert len(xs) == 1, f"the two bores are at different x - abreast, not stacked: {xs}"
    assert len(ys) == 2, f"the two bores share a y - abreast, not stacked: {ys}"


def test_the_fs_cassette_pitch_is_in_the_registry_as_measured():
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())
    s = std["standards"]["fhd-lc-cassette"]
    assert s["pitch"] == 12.92
    assert s["pitch-confidence"] == "measured"
    assert "57016" in s["registry"], \
        "the registry entry must name the render the pitch came from"
