"""The five Catalyst 2960-S: the console end's shapes and the RPS connector's chamfered cells.

Each shape is read off the NetBox front elevations at 11.345 px per mm (one pixel is 0.09 mm) and the cells' chamfer off
the NetBox rear photograph of the WS-C2960S-48LPD-L at 3.41 px per mm (one pixel is 0.29 mm).
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/cisco"
RPS = ROOT / "library/components/cisco/rps2300-connector"
NAMES = ["ws-c2960s-48fpd", "ws-c2960s-48lpd", "ws-c2960s-48td", "ws-c2960s-24pd", "ws-c2960s-24td"]
TEAL, CHARCOAL = "#255e6d", "#404040"


def device(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def decor(d, view="front"):
    return {x["id"]: x for x in d["views"][view]["panel"].get("decor") or [] if x.get("id")}


def silk(d, view="front"):
    return {x["id"]: x for x in d["views"][view].get("silkscreen") or [] if x.get("id")}


def placed(d, view="front"):
    return {p["id"]: p for p in d["views"][view]["components"]["placements"] if p.get("id")}


def numbers(path):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", path)]


@pytest.mark.parametrize("name", NAMES)
def test_console_surround_and_panel_step_up_over_the_rj45_jack_and_the_port_lamp_stands_below(name):
    d = device(name)
    dc = decor(d)
    top, foot = dc["console-surround"], dc["console-surround-foot"]
    # the stencil's surround ends at 24.42 mm under the mini-B and 21.24 mm under the RJ-45 jack, the step at 402.1 mm
    assert top["at"][1] + top["size"][1] == pytest.approx(21.24, abs=0.1)
    assert foot["at"][1] + foot["size"][1] == pytest.approx(24.42, abs=0.1)
    assert foot["at"][0] + foot["size"][0] == pytest.approx(402.1, abs=0.1)
    assert top["fill"] == foot["fill"] == "#bad4d7"
    inner, inner_foot = dc["console-panel"], dc["console-panel-foot"]
    assert inner["at"][1] + inner["size"][1] == pytest.approx(20.14, abs=0.1), "the ring is 1.1 mm thick"
    assert inner_foot["at"][0] + inner_foot["size"][0] == pytest.approx(401.0, abs=0.1)
    assert inner["fill"] == inner_foot["fill"] == CHARCOAL
    lamps = [p for i, p in placed(d).items() if i.startswith("led-port-") and 412 < p["at"][0] < 418 and p["at"][1] > 22]
    assert len(lamps) == 1, "the second uplink's lamp is the arrow under the surround"
    assert lamps[0]["at"][1] >= top["at"][1] + top["size"][1], "it stands below the surround's step, on the panel"
    assert lamps[0]["skin"] == "down"


@pytest.mark.parametrize("name", NAMES)
def test_legend_band_ends_in_the_stencils_slope(name):
    d = device(name)
    band, cut = decor(d)["legend-band"], silk(d)["legend-band-slope"]
    assert band["at"][0] == pytest.approx(384.2, abs=0.1), "the band begins where the slope's top does"
    assert band["at"][0] + band["size"][0] == pytest.approx(442.6, abs=0.1), "its right end is unchanged"
    pts = numbers(cut["path"])
    # M 0 0 L dx dy H 0 Z: the dark triangle under the slope, from (384.2, 2.1) to (394.5, 4.6) mm
    assert cut["fill"] == CHARCOAL
    assert cut["at"][0] + pts[2] == pytest.approx(394.5, abs=0.1)
    assert cut["at"][1] + pts[3] == pytest.approx(band["size"][1], abs=0.1)
    assert cut["at"][1] == pytest.approx(2.1, abs=0.1)


@pytest.mark.parametrize("name", NAMES)
def test_dark_panel_top_right_corner_is_rounded_over_a_teal_corner(name):
    dc = decor(device(name))
    teal, panel = dc["panel-corner-ne-teal"], dc["panel-corner-ne"]
    assert panel["rx"] == pytest.approx(2.2, abs=0.2)
    assert panel["fill"] == CHARCOAL and teal["fill"] == TEAL
    assert panel["at"][0] + panel["size"][0] == pytest.approx(440.5, abs=0.1), "the panel's right edge is the bezel's"
    assert panel["at"][1] == pytest.approx(4.6, abs=0.1), "under the legend band"
    order = list(dc)
    assert order.index("legend-band") < order.index("panel-corner-ne-teal") < order.index("panel-corner-ne")


@pytest.mark.parametrize("name", NAMES)
def test_mini_b_lower_corners_are_covered_in_the_surrounds_teal(name):
    d = device(name)
    wedges, jack = silk(d)["console-usb-wedges"], placed(d)["console-usb"]
    assert wedges["at"] == jack["at"], "the triangles are the part's own corners"
    assert wedges["fill"] == decor(d)["console-usb-surround"]["fill"] == TEAL
    assert len(re.findall("M", wedges["path"])) == 2


def test_the_rps_cells_are_chamfered_at_their_lower_corners_and_the_contract_gives_the_scale():
    v = 2
    svg = (RPS / f"v{v}/skins/default.svg").read_text()
    group = re.search(r'<g fill="#7d7464">(.*?)</g>', svg, re.S).group(1)
    cells = re.findall(r'<path d="([^"]+)"', group)
    assert len(cells) == 22
    for d in cells:
        # M x+r y, H, Q (upper right), V y+h-0.7, L x+w-0.4 y+h, H x+0.4, L x y+h-0.7, V, Q (upper left): a 3.5 by 3.7 cell
        # whose two lower corners are each cut 0.4 across by 0.7 down
        n = [float(v) for v in re.findall(r"[\d.]+", d)]
        assert len(n) == 18, d
        top, left, right, shoulder, foot_r, bottom, foot_l, shoulder_l = n[1], n[11], n[3], n[7], n[8], n[9], n[10], n[12]
        assert abs((right - left) - 3.5) < 0.011 and abs((bottom - top) - 3.7) < 0.011, d
        assert abs((bottom - shoulder) - 0.7) < 0.011 and abs(shoulder - shoulder_l) < 0.011, d
        assert abs((right - foot_r) - 0.4) < 0.011 and abs((foot_l - left) - 0.4) < 0.011, d
    c = yaml.safe_load((RPS / f"v{v}/contract.yaml").read_text())
    text = " ".join(c["provenance"]["cavities"].split())
    assert "3.41 px per mm" in text and "0.3 mm" in text and "0.4 mm across by 0.7 mm down" in text
    assert "chamfered lower corners of the cells are not drawn" not in text
    assert c["version"].startswith(f"{v}.") and c["version"] != f"{v}.0.0", "the redraw is a bump of the contract's own version"
    assert "chamfered lower corners of the cavities" in " ".join(c["description"].split())


@pytest.mark.parametrize("name", NAMES)
def test_the_rps_gap_no_longer_says_the_chamfers_are_missing(name):
    gaps = {g["what"]: g for g in device(name).get("gaps") or []}
    wanted = " ".join(gaps["rps-connector-part"]["wanted"].split())
    assert "does not draw the chamfered lower corners" not in wanted
    assert "chamfered lower corners" in wanted
    assert "front-console-end" in device(name)["provenance"]
