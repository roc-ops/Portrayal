"""The receptacle shells on a GeForce Founders Edition bracket face never overlap or touch.

Each port is an element of class `connector` on the card's contract and a group
in the bracket skin. A real bracket has a gap between every receptacle, so two
shells that overlap or share an edge are a drawing fault, not a reading of the
card. The check is on the contract's elements and on the skin's drawn shells,
since the two are written by hand and drift apart.
"""
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SVG = "{http://www.w3.org/2000/svg}"


def _has_ports(path):
    doc = yaml.safe_load(path.read_text())
    return any(el.get("class") == "connector" for el in (doc.get("elements") or {}).values())


# only the cards that draw receptacles, with a bracket skin beside the contract
CARDS = [p for p in sorted((ROOT / "library/components/nvidia").glob("rtx-*-fe/v1/contract.yaml"))
         if _has_ports(p) and (p.parent / "skins/default.svg").exists()]


def _contract_shells(path):
    doc = yaml.safe_load(path.read_text())
    out = {}
    for name, el in (doc.get("elements") or {}).items():
        if el.get("class") == "connector":
            x, y = el["at"]
            w, h = el["size"]
            out[name] = (x, y, x + w, y + h)
    return out


def _skin_shells(path):
    """The bounding box of each port group's outer path in the bracket skin."""
    root = ET.parse(path).getroot()
    out = {}
    for g in root.iter(SVG + "g"):
        gid = g.get("id", "")
        if not (gid.startswith("display-port-") or gid == "hdmi"):
            continue
        d = g.find(SVG + "path").get("d")
        xs, ys = [], []
        for cmd, args in re.findall(r"([MLA])([^MLAZ]*)", d):
            n = [float(v) for v in args.replace(",", " ").split()]
            # an arc's last two numbers are its end point; the rest are flags and radii
            x, y = (n[-2], n[-1])
            xs.append(x)
            ys.append(y)
        out[gid] = (min(xs), min(ys), max(xs), max(ys))
    return out


def _gaps(shells):
    """(a, b, gap) for each pair of shells; a gap of 0 or less is an overlap or a touch."""
    names = sorted(shells)
    found = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ax0, ay0, ax1, ay1 = shells[a]
            bx0, by0, bx1, by1 = shells[b]
            gx = max(bx0 - ax1, ax0 - bx1)
            gy = max(by0 - ay1, ay0 - by1)
            found.append((a, b, max(gx, gy)))
    return found


def test_the_checker_sees_an_overlap_and_a_touch():
    """The check has to fail on the two faults it exists for."""
    assert _gaps({"a": (0, 0, 10, 5), "b": (9, 0, 19, 5)})[0][2] < 0
    assert _gaps({"a": (0, 0, 10, 5), "b": (10, 0, 20, 5)})[0][2] == 0
    assert _gaps({"a": (0, 0, 10, 5), "b": (10.5, 0, 20, 5)})[0][2] > 0


def test_there_are_cards_to_check():
    assert any(p.parent.parent.name == "rtx-4080-super-fe" for p in CARDS)


@pytest.mark.parametrize("path", CARDS, ids=lambda p: p.parent.parent.name)
def test_no_two_port_shells_overlap_or_touch(path):
    shells = _contract_shells(path)
    bad =[f"{a} / {b} ({g:+.2f} mm)" for a, b, g in _gaps(shells) if g <= 0]
    assert not bad, f"{path.parent.parent.name}: shells overlap or touch: {bad}"


@pytest.mark.parametrize("path", CARDS, ids=lambda p: p.parent.parent.name)
def test_the_skin_draws_the_shells_apart_and_where_the_contract_puts_them(path):
    shells = _contract_shells(path)
    drawn = _skin_shells(path.parent / "skins/default.svg")
    bad = [f"{a} / {b} ({g:+.2f} mm)" for a, b, g in _gaps(drawn) if g <= 0]
    assert not bad, f"{path.parent.parent.name}: drawn shells overlap or touch: {bad}"
    for name, (x0, _y0, x1, _y1) in shells.items():
        gx0, _, gx1, _ = drawn[name]
        assert abs(gx0 - x0) < 0.2 and abs(gx1 - x1) < 0.2, \
            f"{path.parent.parent.name}: {name} is drawn at {gx0:.2f}..{gx1:.2f}, the contract has {x0:.2f}..{x1:.2f}"
