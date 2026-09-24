"""A seated plug's fibre n lies on the fibre of its adapter it mates, on a real
build, in the device frame (B3, Task 10d).

Every connector draws a node for each of its fibre positions (L112), so fibre
n of a part is at `<part>/n`. A plug and the adapter it seats in each number
their own. Seated, the two sets of nodes must land on each other the way the
fibres do. Otherwise the explorer rings the wrong fibre, and a path read off
one part names the wrong fibre on the other.

  * MPO-12, on the flange bulkhead (a cassette's back) and on the panel tile:
    plug n lies on adapter n. The flange adapter numbers the cassette's
    inside plug, seen key down through the key-up opening, so fibre 1 is
    rightmost (its `fibre-numbering`). The panel tile numbers a key-up plug
    mated from the viewer, fibre 1 again rightmost (its `fibre-markers`). A
    seated plug is seen from its boot end, so its own end face appears
    mirrored, fibre 1 at the right too.
  * MPO-24, on the 24-fibre flange bulkhead: plug n lies on adapter n + 12,
    counted round 24. That is the Inner Sequence the adapter's own
    `fibre-numbering` records ("a trunk fibre 1-12 lands on ids 13-24"): the
    trunk's key-side row faces the inside plug's other row across a key-up
    to key-down adapter.
  * LC duplex, on both duplex adapters: the plug's fibre 1 (half `a`) lies on
    bore `1`, and its fibre 2 on bore `2`.
"""
import math
import shutil
import xml.etree.ElementTree as ET

import yaml

from test_nested_occupants import LIB, device_point
from test_slot_defaults import _copy, build

FHD = "fs/fhd-1ufce"
DCP = "smartoptics/dcp-r-34d-cs"
MPO12 = "generic/mpo12-plug@1"
MPO24 = "generic/mpo24-plug@1"
DUPLEX = "generic/lc-duplex-plug@2"
TWO_MTP12 = "fs/fhd-2mtp12-lc-os2-a@4"     # back: two common/mpo-flange-adapter@2
ONE_MTP24 = "fs/fhd-1mtp24-lc-os2-a@4"     # back: one common/mpo24-flange-adapter@2
LC_CASSETTE = "fs/fhd-2mtp12-lc-os2-a@4"   # front: twelve common/lc-duplex-v-adapter@6


def _parse(svg):
    root = ET.parse(svg).getroot()
    return root, {c: p for p in root.iter() for c in p}


def _named(root, path):
    """The one element drawn at `path`, whether as data-path or, on a
    projected back, as data-of."""
    hits = [n for n in root.iter() if path in (n.get("data-path"), n.get("data-of"))]
    assert len(hits) == 1, (path, len(hits))
    return hits[0]


def centre(parents, el):
    """The centre of a fibre node - a circle or a zero-ink rect - in the
    device frame."""
    tag = el.tag.rsplit("}", 1)[-1]
    if tag == "circle":
        local = (float(el.get("cx")), float(el.get("cy")))
    elif tag == "rect":
        local = (float(el.get("x")) + float(el.get("width")) / 2,
                 float(el.get("y")) + float(el.get("height")) / 2)
    else:
        raise AssertionError(f"a fibre node drawn as <{tag}> - teach centre() its shape")
    return device_point(parents, el, local)


def fibres(root, parents, path, n):
    """{position: centre} for positions 1..n of the part drawn at `path`."""
    return {i: centre(parents, _named(root, f"{path}/{i}")) for i in range(1, n + 1)}


def misses(plug, adapter, onto):
    """{plug position: (the adapter position it should lie on, distance)} for
    every plug fibre farther than 1e-6 from its adapter fibre."""
    out = {}
    for i, p in plug.items():
        j = onto(i)
        d = math.dist(p, adapter[j])
        if d > 1e-6:
            out[i] = (j, round(d, 4))
    return out


def fhd(tmp_path, bays, occupants, lib=LIB):
    dev = shutil.copytree(LIB / "devices" / FHD, tmp_path / "fhd") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"]["base"]
    cfg["bays"] = {**(cfg.get("bays") or {}), **bays}
    cfg["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    build(dev, tmp_path / "o", lib)
    return tmp_path / "o"


def SAME(i):
    return i


def INNER_SEQUENCE(i):
    """1-12 -> 13-24 and 13-24 -> 1-12."""
    return (i + 11) % 24 + 1


def test_the_inner_sequence_is_the_one_the_24_fibre_adapter_states():
    """The map this file holds MPO-24 to is read off the adapter, not made up
    here: its note says a trunk fibre 1-12 lands on ids 13-24."""
    note = yaml.safe_load((LIB / "components/common/mpo24-flange-adapter/v2/contract.yaml")
                          .read_text())["provenance"]["fibre-numbering"]
    assert "a trunk fibre 1-12 lands on ids 13-24" in " ".join(note.split())
    assert [INNER_SEQUENCE(i) for i in (1, 12, 13, 24)] == [13, 24, 1, 12]


def test_an_mpo12_plug_meets_the_flange_bulkheads_fibres_one_for_one(tmp_path):
    out = fhd(tmp_path, {"bay-1": TWO_MTP12}, {"bay-1/mtp2": MPO12})
    root, parents = _parse(out / "fhd-1ufce.base.rear.svg")
    adapter = fibres(root, parents, "bay-1/module/mtp2", 12)
    plug = fibres(root, parents, "bay-1/module/mtp2-occupant", 12)
    assert len(plug) == len(adapter) == 12
    assert misses(plug, adapter, SAME) == {}


def test_an_mpo24_plug_meets_the_24_fibre_bulkhead_in_the_inner_sequence(tmp_path):
    out = fhd(tmp_path, {"bay-1": ONE_MTP24}, {"bay-1/mtp": MPO24})
    root, parents = _parse(out / "fhd-1ufce.base.rear.svg")
    adapter = fibres(root, parents, "bay-1/module/mtp", 24)
    plug = fibres(root, parents, "bay-1/module/mtp-occupant", 24)
    assert len(plug) == len(adapter) == 24
    assert misses(plug, adapter, INNER_SEQUENCE) == {}


def test_an_mpo12_plug_meets_the_panel_tiles_fibres_one_for_one(tmp_path):
    """common/mpo-adapter@2 is placed by nothing, so a throwaway cassette
    carries a tile on its front - the fixture test_fibre_plugs.py uses."""
    root_lib = tmp_path / "lib"

    def mpo_front(c):
        c["parts"] = [{"id": "mtp1", "ref": "common/mpo-adapter@2", "at": [20.0, 12.0]}]
        for k in ("optical", "faces"):
            c.pop(k, None)
    _copy(root_lib, "fs/fhd-1mtp12-sc-os2-a", 3, "mpo-cassette", mpo_front)
    out = fhd(tmp_path, {"bay-1": "test/mpo-cassette@1"}, {"bay-1/mtp1": MPO12}, root_lib)
    root, parents = _parse(out / "fhd-1ufce.base.front.svg")
    adapter = fibres(root, parents, "bay-1/module/mtp1", 12)
    plug = fibres(root, parents, "bay-1/module/mtp1-occupant", 12)
    assert misses(plug, adapter, SAME) == {}


def _bore_mates(root, parents, path):
    """{bore position: its mate, in the device frame} off the drawn
    `data-cp` markers - the one mate each bore carries."""
    out = {}
    for b in ("1", "2"):
        bore = _named(root, f"{path}/{b}")
        pts = [(el, [float(v) for v in el.get("data-cp-at").split()])
               for el in bore.iter() if el.get("data-cp") == "mate"]
        assert len(pts) == 1, (path, b, len(pts))
        el, at = pts[0]
        out[int(b)] = device_point(parents, el, at)
    return out


def test_a_duplex_plugs_fibres_meet_the_smartoptics_adapters_bores(tmp_path):
    dev = shutil.copytree(LIB / "devices" / DCP, tmp_path / "dcp") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    assert not d.get("configurations"), "the device now ships its own; rewrite this"
    d["configurations"] = {"default": {"kind": "base", "default": True, "occupants": {
        "port-1510": DUPLEX, "port-1510/1": "", "port-1510/2": ""}}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    build(dev, tmp_path / "o", LIB)
    root, parents = _parse(tmp_path / "o" / "dcp-r-34d-cs.default.front.svg")
    bores = _bore_mates(root, parents, "port-1510")
    plug = fibres(root, parents, "port-1510-occupant", 2)
    assert misses(plug, bores, SAME) == {}


def test_a_duplex_plugs_fibres_meet_the_fs_stacked_adapters_bores(tmp_path):
    out = fhd(tmp_path, {"bay-1": LC_CASSETTE}, {"bay-1/lc01": DUPLEX})
    root, parents = _parse(out / "fhd-1ufce.base.front.svg")
    bores = _bore_mates(root, parents, "bay-1/module/lc01")
    plug = fibres(root, parents, "bay-1/module/lc01-occupant", 2)
    assert misses(plug, bores, SAME) == {}


def test_the_check_sees_a_plug_numbered_the_wrong_way(tmp_path):
    """Non-vacuity: the MPO-12 plug read against the flange numbering
    reversed misses on every one of its twelve fibres."""
    out = fhd(tmp_path, {"bay-1": TWO_MTP12}, {"bay-1/mtp2": MPO12})
    root, parents = _parse(out / "fhd-1ufce.base.rear.svg")
    adapter = fibres(root, parents, "bay-1/module/mtp2", 12)
    plug = fibres(root, parents, "bay-1/module/mtp2-occupant", 12)
    assert len(misses(plug, adapter, lambda i: 13 - i)) == 12
