"""The UfiSpace S9500-30XS grounding landing is one two-hole landing, not one nominal stud.

Its hardware installation guide ships one accessory two-hole lug with two M4 screws and draws, in
Figure 22, two designated locations, each a pair of tapped holes under the lug's plate. The device
draws one landing: a `common/ground-stud-pair-5-8-m4@1` host centred where Figure 22 puts the
rearward location's two holes. Which flank the figure shows is not stated, so the flank is a gap.

Held to the real library: nothing is rendered and nothing reads library/dist.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import render as render_mod
from test_coax_slots import _contract

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
HOST = "common/ground-stud-pair-5-8-m4@1"
# Figure 22 reads the rearward location's holes 192.5 and 208.4 mm from the front end of the
# chassis bar and its centre line 22.4 mm below the top edge; the host is centred on them
CENTRE = (200.45, 22.4)


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load((LIB / "devices/ufispace/s9500-30xs/device.yaml").read_text())


def _right(device):
    return device["views"]["right"]["components"]["placements"]


def test_the_landing_is_one_pair_host_centred_on_the_figures_two_holes(device):
    [p] = [p for p in _right(device) if p["ref"] == HOST]
    assert p["id"] == "ground-screws" and p["attrs"] == {"stud-size": "M4"}
    assert p.get("rotate") is None
    c = _contract(HOST)
    want = render_mod.seat_point(p["at"], c["size"], None, c["connection-points"]["mate"]["at"])
    assert want == pytest.approx(list(CENTRE), abs=0.06)


def test_no_nominal_lug_is_left_beside_the_pair(device):
    refs = [p["ref"] for view in device["views"].values()
            for p in ((view or {}).get("components") or {}).get("placements") or []]
    assert "common/ground-lug@1" not in refs and refs.count(HOST) == 1


def test_the_earth_mark_and_legend_follow_the_pair(device):
    marks = [s for s in device["views"]["right"]["silkscreen"] if s.get("for", "").startswith("ground")]
    assert marks and {s["for"] for s in marks} == {"ground-screws"}


def test_the_reading_and_the_flank_are_recorded_as_what_they_are(device):
    note = device["provenance"]["ground-pair"]["note"]
    assert "Figure 22" in note and "0.68 mm" in note and "15.875" in note
    gaps = {g["what"]: g for g in device["gaps"]}
    assert set(gaps) >= {"grounding-flank", "ground-pair-pitch"}
    assert gaps["grounding-flank"]["scope"] == ["ground-screws"]
