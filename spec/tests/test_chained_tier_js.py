"""The chained tier in the kit (#611): a boot on a swapped plug, and a plug in
a single-bore optic, seated by the explorer exactly as the build seats them.

The build has always taken a chained key: `{port-1: plug, port-1-occupant:
boot}` draws the boot beside the plug, `data-for` it, turned with it and
standing on the sum of the lifts. The kit swapped cages only
(`builtOccupants`: "a chained tier is the build's business"), so a consumer
seating connectors through swaps got the plug's cable point and no boot.
Now a seated occupant that presents something (components.json `presents`,
render.component_presents) is a slot at its own path (swap.js chainedSlots).

HELD TO REAL BUILDS, attribute for attribute and matrix for matrix
(test_lifted_seat_js's `mismatches`), on two shapes:
  card    casa/c100g with casa/smm-300gm@1 in front-6: a single-bore optic in
          the card's cage `xg0`, a generic/lc-plug@2 at its own key, and a
          common/lc-boot@1 on the plug - two chained tiers inside a card;
  device  edgecore/eps201's `port-1`: generic/rj45-plug@1 in a device-level
          jack and common/rj45-boot@1 on it - the copper half, #610's.
"""
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

import warmrender
from test_lifted_seat_js import LIB, RENDER, SPEC, build_components, mismatches, skin_file, spec_of
from test_nested_slots_js import built_occupant

SCRIPT = SPEC / "tests/js/chained-tier.mjs"
SIMPLEX, LCPLUG, LCBOOT = "generic/sfp-lc-simplex@2", "generic/lc-plug@2", "common/lc-boot@1"
RJPLUG, RJBOOT = "generic/rj45-plug@1", "common/rj45-boot@1"

# module-less configuration keys, and the drawing paths the kit keys by
CARD_KEYS = {"optic": "front-6/xg0", "plug": "front-6/xg0-occupant",
             "boot": "front-6/xg0-occupant-occupant"}
CARD = {k: v.replace("front-6/", "front-6/module/") for k, v in CARD_KEYS.items()}
DEV = {"plug": "port-1", "boot": "port-1-occupant"}
# the issue's own example: a QSFP optic in a device cage, a plug in its tx
# bore, and the boot keyed `port-1-occupant/tx-occupant` - a tier chained
# INSIDE the optic's own group, beside the plug
QSFP = "generic/qsfp-lc@2"
UP = {"optic": "port-1", "plug": "port-1-occupant/tx", "boot": "port-1-occupant/tx-occupant"}

DEVICES = {
    "c100g": ("casa/c100g", {"front-6": "casa/smm-300gm@1"}, {
        "optic": {CARD_KEYS["optic"]: SIMPLEX},
        "plugged": {CARD_KEYS["optic"]: SIMPLEX, CARD_KEYS["plug"]: LCPLUG},
        "booted": {CARD_KEYS["optic"]: SIMPLEX, CARD_KEYS["plug"]: LCPLUG,
                   CARD_KEYS["boot"]: LCBOOT},
    }),
    "as7726": ("edgecore/as7726-32x", {}, {
        "plugged": {UP["optic"]: QSFP, UP["plug"]: LCPLUG},
        "booted": {UP["optic"]: QSFP, UP["plug"]: LCPLUG, UP["boot"]: LCBOOT},
    }),
    "eps201": ("edgecore/eps201", {}, {
        "bare": {},
        "plugged": {DEV["plug"]: RJPLUG},
        "booted": {DEV["plug"]: RJPLUG, DEV["boot"]: RJBOOT},
    }),
}

SCENARIOS = [
    # one tier at a time, each from the build of the tier below
    {"name": "cardPlug", "dev": "c100g", "from": "optic",
     "overrides": {CARD["plug"]: LCPLUG}, "keys": [CARD["plug"]]},
    {"name": "cardBoot", "dev": "c100g", "from": "plugged",
     "overrides": {CARD["boot"]: LCBOOT}, "keys": [CARD["boot"]]},
    # the whole chain in one map, from the optic alone: tier by tier
    {"name": "cardChain", "dev": "c100g", "from": "optic",
     "overrides": {CARD["plug"]: LCPLUG, CARD["boot"]: LCBOOT},
     "keys": [CARD["plug"], CARD["boot"]]},
    # the census and the clicks on the build's own three tiers
    {"name": "cardCensus", "dev": "c100g", "from": "booted",
     "click": [CARD["plug"] + "-occupant", CARD["boot"] + "-occupant", CARD["optic"] + "-occupant"]},
    # emptying the plug takes the boot with it
    {"name": "cardUnplug", "dev": "c100g", "from": "booted",
     "overrides": {CARD["plug"]: None},
     "keys": [CARD["plug"], CARD["boot"]],
     "empty": [CARD["plug"] + "-occupant", CARD["boot"] + "-occupant"]},
    {"name": "upBoot", "dev": "as7726", "from": "plugged",
     "overrides": {UP["boot"]: LCBOOT}, "keys": [UP["boot"]]},
    {"name": "devBoot", "dev": "eps201", "from": "plugged",
     "overrides": {DEV["boot"]: RJBOOT}, "keys": [DEV["boot"]]},
    {"name": "devChain", "dev": "eps201", "from": "bare",
     "overrides": {DEV["plug"]: RJPLUG, DEV["boot"]: RJBOOT},
     "keys": [DEV["plug"], DEV["boot"]]},
]

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def render(tmp, key, spec):
    dev_ref, bays, configs = spec
    name = dev_ref.split("/")[1]
    dev = tmp / key / "src" / "device.yaml"
    shutil.copytree(LIB / "devices" / dev_ref, dev.parent)
    d = yaml.safe_load(dev.read_text())
    for cfg, occ in configs.items():
        d["configurations"][cfg] = {"kind": "example", "description": "#611 test",
                                    **({"bays": dict(bays)} if bays else {}),
                                    **({"occupants": dict(occ)} if occ else {})}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / key / "out"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    faces = {c: ET.parse(out / f"{name}.{c}.front.svg").getroot() for c in configs}
    meta = json.loads((out / f"{name}.configs.json").read_text())
    return faces, meta["cages"]["front"]


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("chained-tier")
    dist = tmp / "dist"
    comps = build_components(dist)
    built = {k: render(tmp, k, v) for k, v in DEVICES.items()}
    payload = {
        "components": json.loads((dist / "components.json").read_text())["components"],
        "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot()))
                  for r in (SIMPLEX, LCPLUG, LCBOOT, RJPLUG, RJBOOT, QSFP)},
        "devices": {k: {"faces": {c: spec_of(f) for c, f in faces.items()}, "cages": cages}
                    for k, (faces, cages) in built.items()},
        "scenarios": SCENARIOS,
    }
    out = None
    if shutil.which("node"):
        p = subprocess.run(["node", str(SCRIPT), "scenarios"], input=json.dumps(payload),
                           capture_output=True, text=True, cwd=str(SCRIPT.parent), env=dict(os.environ))
        assert p.returncode == 0, p.stderr
        out = json.loads(p.stdout.strip().splitlines()[-1])
    return {"faces": {k: v[0] for k, v in built.items()}, "comps": comps, "out": out}


def scenario(world, name):
    got = world["out"][name]
    assert "error" not in got, got.get("error")
    return got


def parity(world, dev, face, key, have):
    want = built_occupant(world["faces"][dev][face], key)
    return mismatches([{"name": face, "built": {key: want}}],
                      [{"name": face, "seated": {key: have}}])


# ---------------------------------------------------------------- the build

def test_the_build_chains_siblings_turned_with_their_host_on_summed_lifts(world):
    """The premise, read off the build: each tier `data-for` the one below,
    in the same group, with the host's turn, lifts stacking."""
    root = world["faces"]["c100g"]["booted"]
    plug = built_occupant(root, CARD["plug"])
    boot = built_occupant(root, CARD["boot"])
    assert plug["ref"] == LCPLUG and boot["ref"] == LCBOOT
    assert plug["parent"] == boot["parent"] == "front-6/module"
    lift = lambda o: float(o["attrs"].get("data-z-lift") or 0)
    assert lift(boot) > lift(plug) > 0, (lift(plug), lift(boot))


# ---------------------------------------------------------------- the kit

@needs_node
@pytest.mark.parametrize("name,dev,face", [
    ("cardPlug", "c100g", "plugged"), ("cardBoot", "c100g", "booted"),
    ("cardChain", "c100g", "booted"), ("devBoot", "eps201", "booted"),
    ("devChain", "eps201", "booted"), ("upBoot", "as7726", "booted")])
def test_a_tier_the_kit_seats_is_the_builds(world, name, dev, face):
    s = scenario(world, name)
    assert s["res"]["refused"] == [] and s["res"]["failed"] == [], s["res"]
    for key, have in s["seated"].items():
        assert have["count"] == 1, (key, have["count"])
        bad = parity(world, dev, face, key, have)
        assert not bad, "\n".join(bad[:8])


@needs_node
def test_the_chained_slots_are_published_and_offered(world):
    s = scenario(world, "cardCensus")
    by = {e["id"]: e for e in s["chained"]}
    assert set(by) == {CARD["plug"], CARD["boot"]}, sorted(by)
    assert by[CARD["plug"]]["host"] == CARD["optic"] and by[CARD["plug"]]["accepts"] == [
        "common/lc-dust-cap@1", LCPLUG]
    assert by[CARD["boot"]]["host"] == CARD["plug"] and by[CARD["boot"]]["accepts"] == [LCBOOT]
    assert by[CARD["plug"]]["key"] == CARD_KEYS["plug"] and by[CARD["boot"]]["key"] == CARD_KEYS["boot"]
    assert {CARD["plug"], CARD["boot"]} <= set(s["offered"])


@needs_node
def test_a_click_on_a_tier_names_the_slot_it_sits_in(world):
    """A chained slot's id is its seat's path, so a click on the plug must
    still name what the plug is IN - the optic's own slot - and not the boot's
    slot the plug now also is. The explorer offers the boot beside it."""
    c = scenario(world, "cardCensus")["clicks"]
    assert c[CARD["optic"] + "-occupant"] == CARD["optic"]
    assert c[CARD["plug"] + "-occupant"] == CARD["plug"]
    assert c[CARD["boot"] + "-occupant"] == CARD["boot"]


@needs_node
def test_emptying_a_plug_takes_its_boot_with_it(world):
    """A boot is a sibling of its plug, so the plug going leaves it in the air
    unless it goes too (swap.js removeSeat)."""
    s = scenario(world, "cardUnplug")
    assert s["res"]["applied"] >= 1, s["res"]
    assert s["gone"] == {CARD["plug"] + "-occupant": 0, CARD["boot"] + "-occupant": 0}, s["gone"]
    assert CARD["boot"] not in {e["id"] for e in s["chained"]}


# ---------------------------------------------------------------- the index

def test_only_a_part_that_mates_publishes_what_it_presents(world):
    """components.json `presents` (render.component_presents): the slot at a
    seated part's own key, in its own frame. A plug and a single-bore optic
    carry it; a card, a port wrapper and a cassette do not - they are never a
    seat, and their slots are published where they are placed. A plug nothing
    in the library mates (the SC and MPO plugs: no boot is modelled) offers
    nothing, so carries nothing."""
    comps = world["comps"]
    have = {r for r, c in comps.items() if c.get("presents")}
    assert {LCPLUG, RJPLUG, SIMPLEX, "generic/sfp-rj45@1"} <= have, sorted(have)
    assert all(comps[r].get("mates") or comps[r].get("class") in ("port", "transceiver")
               for r in have)
    for r in ("casa/smm-300gm@1", "common/rj45-eth@1", "common/lc-duplex-v-adapter@6",
              "generic/sc-plug@1", LCBOOT):
        assert not comps[r].get("presents"), r


@pytest.mark.parametrize("ref,iface,accepts", [
    (LCPLUG, "lc-plug", [LCBOOT]),
    (RJPLUG, "rj45-plug", [RJBOOT]),
    (SIMPLEX, "lc", ["common/lc-dust-cap@1", LCPLUG]),
])
def test_what_a_part_presents_is_what_the_build_seats_on(world, ref, iface, accepts):
    """The build's own numbers, read through the same core: the presented
    point and its `out`, which is the lift the next tier stands on above this
    one (the boot at 22.5 on a plug at 10 is the plug's 12.5)."""
    from portrayal import render as R
    from portrayal.manifest import presented_interface
    lib = R.Library([str(LIB)])
    res = lambda r: lib.resolve(r)[0]
    p = world["comps"][ref]["presents"]
    want_iface, want_at, want_lift = presented_interface(res(ref), res)
    assert (p["interface"], p["mate"], p["lift"], p["accepts"]) == (
        iface, list(want_at), float(want_lift), accepts)
    assert iface == want_iface
