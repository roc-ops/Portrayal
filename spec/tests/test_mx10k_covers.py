"""MX10004 / MX10008 / MX10016 base configurations ship slot covers.

Juniper's configuration tables ship a cover in every power supply slot and every
routing-and-control-board slot a base leaves unfilled, as well as in every
line-card slot. A base that seats all its supplies and boards is a different
box from the one the vendor sells. These tests hold the covers (sized from the
aperture they fill, named by their part number) and the base counts per chassis.
SFBs are not visible from outside the chassis and no SFB bay is drawn, so their
covers are not part of this slice.
"""
import os
import pathlib
import re

import pytest

from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
COMP = LIB / "components" / "juniper"

PWR = "juniper/jnp10k-pwr-blnk@2"
AC2 = "juniper/jnp10k-pwr-ac2@2"
RE = "juniper/jnp10k-re-blnk@1"
LC = "juniper/jnp10k-lc-blank@1"

# chassis -> boards and supplies seated, and the covers beside them
COUNTS = {
    "mx10004": dict(re=1, re_cover=1, psu=2, psu_cover=1),
    "mx10008": dict(re=1, re_cover=1, psu=3, psu_cover=3),
    # the MX10016 table lists no RCB cover; the second slot is covered as on the other two
    "mx10016": dict(re=1, re_cover=1, psu=5, psu_cover=5),
}


def device(name):
    return load_yaml(LIB / "devices" / "juniper" / name / "device.yaml")


def contract(name, major=1):
    return load_yaml(COMP / name / f"v{major}" / "contract.yaml")


def bays(dev, view, prefix):
    found = dev["views"][view]["components"]["bays"]
    return [b for b in found if re.fullmatch(prefix + r"\d+", b["id"])]


def seated(dev, view, prefix):
    """{bay id: ref} for the base configuration; a bay it does not name keeps its default."""
    over = dev["configurations"]["base"].get("bays") or {}
    return {b["id"]: over.get(b["id"], b.get("default")) for b in bays(dev, view, prefix)}


def rcb_prefix(name):
    return "re" if name == "mx10004" else ("cb")


@pytest.mark.parametrize("part,major,model", [("jnp10k-pwr-blnk", 2, "JNP10K-PWR-BLNK"),
                                              ("jnp10k-re-blnk", 1, "JNP10K-RE-BLNK")])
def test_cover_carries_its_part_number_in_provenance(part, major, model):
    c = contract(part, major)
    assert c["attrs"]["model"] == model
    assert model in c["provenance"]["part-number"]
    assert c["provenance"]["part-number"].startswith("vendor")
    assert c["provenance"]["face"].startswith("estimated")
    assert c["class"] == "blank"


def test_re_cover_is_the_size_of_the_rcb_aperture_in_all_three():
    c = contract("jnp10k-re-blnk")["size"]
    for name in COUNTS:
        sizes = {(b["size"]["w"], b["size"]["h"]) for b in bays(device(name), "front", rcb_prefix(name))}
        assert sizes == {(c["w"], c["h"])}, name


def _num(v):
    return float(v.replace("mm", ""))


def _translate(tf):
    x = y = 0.0
    for a, b in re.findall(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)", tf or ""):
        x += float(a)
        y += float(b)
    return x, y


@pytest.fixture(scope="module")
def rear_rects(tmp_path_factory):
    """{chassis: {bay id: (opening rect, occupant face rect, occupant ref)}} read from the
    rendered base rear view, in the drawing's own millimetres."""
    import subprocess
    import sys
    import xml.etree.ElementTree as ET
    out = {}
    for name in COUNTS:
        dest = tmp_path_factory.mktemp(name)
        subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"),
                        str(LIB / "devices" / "juniper" / name / "device.yaml"),
                        "--library", str(LIB), "--out", str(dest)],
                       check=True, capture_output=True,
                       env={**os.environ,"PYTHONPATH": str(ROOT / "spec/tools")})
        root = ET.parse(dest / f"{name}.base.rear.svg").getroot()
        byid = {e.get("id"): e for e in root.iter() if e.get("id")}
        found = {}
        for bid in [b["id"] for b in bays(device(name), "rear", "psu")]:
            op = byid[f"{bid}--opening"]
            mod = byid[f"{bid}--module"]
            face = byid[f"{bid}--module--face"]
            tx, ty = _translate(mod.get("transform"))
            o = (_num(op.get("x")), _num(op.get("y")), _num(op.get("width")), _num(op.get("height")))
            f = (tx + _num(face.get("x")), ty + _num(face.get("y")),
                 _num(face.get("width")), _num(face.get("height")))
            found[bid] = (o, f, mod.get("data-ref").split(":")[0])
        out[name] = found
    return out


@pytest.mark.heavy
@pytest.mark.parametrize("name", sorted(COUNTS))
def test_pwr_cover_fills_its_bay_as_the_supply_does(name, rear_rects):
    """Read from the rendered rear view. The supply is the size of its bay, 91.4 x 88.9 mm; the
    cover takes the same size, so it fills the opening exactly and leaves no band of it showing,
    and stands on the same edges as the supply."""
    found = rear_rects[name]
    supplies = [v for v in found.values() if v[2] == AC2]
    covers = [v for v in found.values() if v[2] == PWR]
    assert supplies and covers, name
    for o, f, _ in covers:
        # the cover's face covers the whole opening: no black band above or below
        assert f[0] <= o[0] + 0.01 and f[1] <= o[1] + 0.01, (name, o, f)
        assert f[0] + f[2] >= o[0] + o[2] - 0.01 and f[1] + f[3] >= o[1] + o[3] - 0.01, (name, o, f)
        # and stands proud of the opening by exactly what the supply does: the same edges
        so, sf, _ = supplies[0]
        assert abs((f[1] - o[1]) - (sf[1] - so[1])) <= 0.01, (name, o, f, so, sf)
        assert abs(f[2] - sf[2]) <= 0.01 and abs(f[3] - sf[3]) <= 0.01, (name, f, sf)


def test_pwr_cover_provenance_says_where_its_size_comes_from():
    """Juniper's guides give the supply's envelope but no figure for the cover, so the size is
    derived from the supply and the bay and must be marked so, not as a datasheet figure."""
    c = contract("jnp10k-pwr-blnk", 2)
    size = " ".join(c["provenance"]["size"].split())
    assert size.startswith("derived")
    assert "JNP10K-PWR-AC2" in size and "88.9" in size
    assert "datasheet" not in size.split(" - ")[0]
    assert (c["size"]["w"], c["size"]["h"]) == (91.4, 88.9)
    supply = contract("jnp10k-pwr-ac2", 2)["size"]
    assert (c["size"]["w"], c["size"]["h"]) == (supply["w"], supply["h"])
    assert set(c["size-confidence"].values()) == {"estimated"}
    old = contract("jnp10k-pwr-blnk", 1)
    assert old["superseded-by"] == "juniper/jnp10k-pwr-blnk@2"
    assert (old["size"]["w"], old["size"]["h"]) == (84.0, 97.0)


@pytest.mark.parametrize("name", sorted(COUNTS))
def test_chassis_accepts_the_covers_where_juniper_seats_one(name):
    dev = device(name)
    for b in bays(dev, "rear", "psu"):
        assert PWR in b["accepts"], (name, b["id"])
    for b in bays(dev, "front", rcb_prefix(name)):
        assert RE in b["accepts"], (name, b["id"])
        # the default stays the board: the cover is a choice, not what is drawn in a full box
        assert b["default"] == "juniper/jnp10k-re1@2"


@pytest.mark.parametrize("name", sorted(COUNTS))
def test_base_seats_the_vendor_counts(name):
    dev, want = device(name), COUNTS[name]
    psus = list(seated(dev, "rear", "psu").values())
    assert sum(1 for r in psus if r and r.startswith("juniper/jnp10k-pwr-ac")) == want["psu"]
    assert psus.count(PWR) == want["psu_cover"]
    res = list(seated(dev, "front", rcb_prefix(name)).values())
    assert res.count("juniper/jnp10k-re1@2") == want["re"]
    assert res.count(RE) == want["re_cover"]
    # every line-card slot keeps its cover
    fpcs = seated(dev, "front", "fpc")
    assert fpcs and set(fpcs.values()) == {LC}


@pytest.mark.parametrize("name", sorted(COUNTS))
def test_base_source_records_no_outstanding_difference(name):
    src = " ".join(device(name)["configurations"]["base"]["source"].split())
    assert "NOT YET FULLY FAITHFUL" not in src
    assert "are not modelled yet" not in src
    assert "JNP10K-PWR-BLNK" in src


def test_mx10016_premium_is_orderable_with_two_rcbs_and_ten_supplies():
    dev = device("mx10016")
    cfg = dev["configurations"]["premium"]
    assert cfg["kind"] == "orderable"
    assert cfg.get("default") is not True
    over = cfg.get("bays") or {}
    cbs = {b["id"]: over.get(b["id"], b["default"]) for b in bays(dev, "front", "cb")}
    assert list(cbs.values()) == ["juniper/jnp10k-re1@2"] * 2
    psus = {b["id"]: over.get(b["id"], b["default"]) for b in bays(dev, "rear", "psu")}
    assert list(psus.values()) == [AC2] * 10
    fpcs = {b["id"]: over.get(b["id"]) for b in bays(dev, "front", "fpc")}
    assert set(fpcs.values()) == {LC} and len(fpcs) == 16
