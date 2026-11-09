"""A bay can say what is seen through its opening when it is empty.

A bay's opening is painted over the panel decor, so a bar standing behind a
frame or a spool inside a tray, drawn as decor, is hidden at every slot mouth.
`seen-through` on the bay carries it instead: drawn in the opening when the bay
is empty, hidden when a part is seated, and shown again when the bay is emptied.

The two halves that must agree are render.py (which writes the mark and hides it
for a configuration that seats the bay) and kit/swap.js (which toggles the same
attribute when a bay is swapped). The last test here renders a real device and
hands the bay's own drawing to the kit.
"""
import functools
import json
import pathlib
import re
import subprocess
import xml.etree.ElementTree as ET

import pytest
import yaml

from portrayal import libwalk, render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"
NODE = ROOT / "spec/tests/js/bay-seen-through.mjs"


@functools.lru_cache(maxsize=1)
def _devices():
    out = []
    for f in libwalk.iter_devices([LIB]):
        doc = yaml.safe_load(f.read_text())
        for vname, view in (doc.get("views") or {}).items():
            for b in ((view.get("components") or {}).get("bays") or []):
                if b.get("seen-through"):
                    out.append((f"{f.parent.parent.name}/{f.parent.name}", vname, doc, view, b))
    return out


def _render(doc, vname, view, bays=None):
    lib = render.Library([str(LIB)])
    out = render.render_view(doc, vname, view, lib, config={"bays": bays or {}})
    root = ET.fromstring(out) if isinstance(out, str) else out
    return root


def _seen(root, bay_id):
    return [g for g in root.iter(f"{SVG}g")
            if g.get("id") == f"{bay_id}--seen-through"]


@pytest.mark.heavy
def test_some_device_says_what_its_empty_bay_shows():
    carrying = {d[0] for d in _devices()}
    assert {"fibrain/xpu", "fs/fhd-1ufmt-n"} <= carrying


@pytest.mark.heavy
def test_each_mark_is_drawn_in_its_own_opening_and_lies_in_it():
    assert _devices()
    for slug, vname, doc, view, b in _devices():
        op = b.get("opening") or b["size"]
        x0 = b["at"][0] + (b["size"]["w"] - op["w"]) / 2
        y0 = b["at"][1] + (b["size"]["h"] - op["h"]) / 2
        for it in b["seen-through"]:
            ax, ay = it["at"]
            aw, ah = it["size"]
            assert ax < x0 + op["w"] and ax + aw > x0 and ay < y0 + op["h"] and ay + ah > y0, \
                f"{slug} {b['id']} {it.get('id')}: lies outside the opening"
            assert it.get("source"), f"{slug} {b['id']} {it.get('id')}: no source"


@pytest.mark.heavy
def test_an_empty_bay_draws_its_mark_over_the_hole_and_under_a_part():
    assert _devices()
    for slug, vname, doc, view, b in _devices():
        base = (doc.get("configurations") or {}).get("base") or {}
        if (base.get("bays") or {}).get(b["id"]):
            continue
        root = _render(doc, vname, view)
        gs = _seen(root, b["id"])
        assert len(gs) == 1, (slug, b["id"])
        assert gs[0].get("display") is None, (slug, b["id"], "hidden on an empty bay")
        bay_g = next(g for g in root.iter(f"{SVG}g") if g.get("id") == b["id"]
                     or g.get("data-path") == b["id"])
        kids = list(bay_g)
        assert kids.index(gs[0]) > [k.get("id") for k in kids].index(f"{b['id']}--opening")
        n_items = sum(1 for _ in gs[0].iter()
                      if (_.get("id") or "").startswith(f"{b['id']}--seen-")
                      and not (_.get("id") or "").startswith(f"{b['id']}--seen-through"))
        assert n_items == len(b["seen-through"]), (slug, b["id"])


@pytest.mark.heavy
def test_a_configuration_that_seats_the_bay_hides_the_mark_and_only_that_bay():
    assert _devices()
    for slug, vname, doc, view, b in _devices():
        ref = (b.get("accepts") or [None])[0]
        sibling = [o for o in view["components"]["bays"] if o is not b and o.get("seen-through")]
        root = _render(doc, vname, view, {b["id"]: ref})
        assert _seen(root, b["id"])[0].get("display") == "none", (slug, b["id"])
        for o in sibling:
            assert _seen(root, o["id"])[0].get("display") is None, (slug, o["id"])


@pytest.mark.heavy
def test_the_kit_hides_and_shows_the_same_mark_the_build_writes():
    """The build's own bay drawing goes to kit/swap.js: seating hides the mark,
    emptying shows it again, with the attribute the build wrote."""
    slug, vname, doc, view, b = next(d for d in _devices() if d[0] == "fibrain/xpu")
    root = _render(doc, vname, view)
    bay_g = next(g for g in root.iter(f"{SVG}g") if g.get("data-path") == b["id"])

    def spec(n):
        return {"t": n.tag.replace(SVG, ""), "a": dict(n.attrib), "c": [spec(c) for c in n]}

    payload = {"bay": b["id"], "svg": spec(bay_g), "ref": b["accepts"][0]}
    p = subprocess.run(["node", str(NODE)], input=json.dumps(payload), text=True,
                       capture_output=True, check=True)
    got = json.loads(p.stdout)
    assert got == {"before": None, "seated": "none", "emptied": None, "unknown": None}
