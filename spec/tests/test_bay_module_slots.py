"""A module in a bay forwards nothing: its one jack is its own slot (#610).

render._forwarded_part reads a contract with no interface of its own and
exactly one interface-bearing part as a WRAPPER, and component_cages then
hid that part as the wrapper's aperture. That is right for a port wrapper and
for an optic in a cage (a slot at its own key; manifest.slot_in_slot_at
refuses its bore). It was wrong for a CARD: the build never treats a module in
a bay as a placed slot, so it seated a plug at `front-6/console` while the
index - and so the kit - published no such slot.

Registering `rj45` (#619) exposed five RJ45 jacks this hid, and the same rule
had been hiding one LC duplex adapter on a CommScope coupler. These pin both
halves: the index publishes them now, and the build seats a plug at each key
it publishes.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

import onebuild
import warmrender

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
INDEXER = ROOT / "spec/tools/portrayal/components_index.py"
RENDER = ROOT / "spec/tools/portrayal/render.py"

# (card, its one jack, the plug that mates it)
CARD_JACKS = [
    ("casa/smm-2x10g@1", "console", "generic/rj45-plug@1"),
    ("casa/smm-8x10g@1", "console", "generic/rj45-plug@1"),
    ("casa/smm-sw-bdm-a@1", "psu-monitor", "generic/rj45-plug@1"),
    ("casa/smm-sw-bdm-b@1", "psu-monitor", "generic/rj45-plug@1"),
    ("oscilloquartz/irig-b@1", "rs-422-out", "generic/rj45-plug@1"),
    ("commscope/bp-f2-al@1", "optical", "generic/lc-duplex-plug@2"),
]


@pytest.fixture(scope="module")
def comps(tmp_path_factory):
    # the indexer the build runs, over this tree, once per session (onebuild)
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


@pytest.mark.parametrize("ref,jack,plug", CARD_JACKS)
def test_a_cards_one_jack_is_its_own_slot(comps, ref, jack, plug):
    slot = next((c for c in comps[ref].get("cages") or [] if c["id"] == jack), None)
    assert slot is not None, f"{ref} hides {jack} as if it were a wrapper's aperture"
    assert slot["kind"] == "connector" and plug in slot["accepts"], slot


@pytest.mark.parametrize("ref", ["generic/sfp-lc-simplex@2", "generic/sfp-rj45@1"])
def test_an_optic_still_forwards_its_one_aperture(comps, ref):
    """THE ONE GATE IS UNCHANGED. An optic is an occupant, not a module in a
    bay: seated in a cage it is a slot at its own key (`xg0-occupant`) and the
    build refuses a key on its bore, so the index publishes none."""
    assert not comps[ref].get("cages"), comps[ref].get("cages")


def _render_with(tmp_path, dev, cfg, bays, occupants):
    d_dir = shutil.copytree(LIB / "devices" / dev, tmp_path / Path(dev).name)
    f = d_dir / "device.yaml"
    d = yaml.safe_load(f.read_text())
    c = d["configurations"][cfg]
    c.setdefault("bays", {}).update(bays)
    c.setdefault("occupants", {}).update(occupants)
    f.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "out"
    r = warmrender.run([sys.executable, str(RENDER), str(f), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return "".join(p.read_text() for p in out.glob(f"{Path(dev).name}.{cfg}.*.svg"))


@pytest.mark.parametrize("dev,cfg,bay,ref,jack,plug", [
    ("casa/c100g", "bdm2m-11plus1", "front-6", "casa/smm-8x10g@1", "console",
     "generic/rj45-plug@1"),
    ("commscope/ch3000", "base", "rear-3", "commscope/bp-f2-al@1", "optical",
     "generic/lc-duplex-plug@2"),
])
def test_the_build_seats_a_plug_at_the_key_the_index_publishes(
        tmp_path, comps, dev, cfg, bay, ref, jack, plug):
    """The agreement this fixes, measured on the build rather than assumed: a
    plug keyed `<bay>/<jack>` is drawn in the card, where the index now says
    the slot is."""
    assert any(c["id"] == jack for c in comps[ref].get("cages") or [])
    svg = _render_with(tmp_path, dev, cfg, {bay: ref}, {f"{bay}/{jack}": plug})
    want = f'data-path="{bay}/module/{jack}-occupant"'
    assert want in svg, f"the build drew no {plug} at {bay}/{jack}"
    tag = svg[svg.index(want):svg.index(">", svg.index(want))]
    assert f'data-ref="{plug}:' in tag, tag
