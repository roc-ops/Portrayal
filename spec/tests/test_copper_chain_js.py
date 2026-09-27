"""The copper SFP chain in the kit (#649): SFP cage -> generic/sfp-rj45@1 ->
generic/rj45-plug@1 in its jack -> common/rj45-boot@1 on the plug, seated by
swap.js exactly where render.py draws it.

The build's side is test_copper_sfp_chain.py. The kit's stopped one link
short: test_chained_tier_js.py holds a boot on a plug in a device-level jack
(eps201) and an LC plug in a single-bore optic, but nothing held the copper
SFP's jack - a slot the SFP PRESENTS, turned 180 in its own frame
(`jack` at rotate 180) - with a plug in it and a boot on that, nor any of it
in a cage the device draws at rotate 180. #648 put the whole chain in the
explorer.

HELD TO A REAL BUILD. A tmp copy of edgecore/agr560 is rendered with three
configurations on two of its direct SFP+ cages - `port-0` upright and
`port-1` drawn at rotate 180 (the stack's lower cage):
  sfp   the copper SFP alone in each;
  plug  plus the plug, keyed `port-N-occupant`;
  boot  plus the boot, keyed `port-N-occupant-occupant`;
and what the kit seats is compared with what render.py drew, attribute for
attribute and matrix for matrix (test_lifted_seat_js's `mismatches`, through
test_chained_slots_js's `parity`).
"""
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from urllib.parse import quote

import pytest
import yaml

import warmrender
from test_chained_slots_js import needs_node, scenario
from test_lifted_seat_js import LIB, RENDER, SPEC, build_components, mismatches, skin_file, spec_of
from test_nested_slots_js import built_occupant
from portrayal.artifacts import face_file

SCRIPT = SPEC / "tests/js/copper-chain.mjs"
DEVICE = "edgecore/agr560"
SFP, PLUG, BOOT = "generic/sfp-rj45@1", "generic/rj45-plug@1", "common/rj45-boot@1"
REFS = (SFP, PLUG, BOOT)
PORTS = ("port-0", "port-1")        # port-1 is drawn at rotate 180
TURNED = "port-1"


def tiers(p):
    """A link's key per port: the cage, the SFP's jack, the plug's boot. A
    device placement's key is its drawing path, so these are both."""
    return (p, f"{p}-occupant", f"{p}-occupant-occupant")


SFPS = {p: SFP for p in PORTS}
PLUGS = {tiers(p)[1]: PLUG for p in PORTS}
BOOTS = {tiers(p)[2]: BOOT for p in PORTS}
CONFIGS = {"sfp": SFPS, "plug": {**SFPS, **PLUGS}, "boot": {**SFPS, **PLUGS, **BOOTS}}
FACES = ("base", *CONFIGS)
TO = ("sfp", "plug", "boot")        # the configuration that asks for link i
ALL = CONFIGS["boot"]
# the explorer's `swap=` form, written out here and not by the kit: sorted
# keys, `key~ref`, each side encodeURIComponent'd, entries joined by `,`
LINK = "?device=agr560&config=base&swap=" + ",".join(
    f"{quote(k, safe='')}~{quote(ALL[k], safe='')}" for k in sorted(ALL))


def render(tmp):
    name = DEVICE.split("/")[1]
    work = tmp / name
    dev = work / "src" / "device.yaml"
    shutil.copytree(LIB / "devices" / DEVICE, dev.parent)
    d = yaml.safe_load(dev.read_text())
    for cfg, occ in CONFIGS.items():
        d["configurations"][cfg] = {"kind": "example", "power": "ac",
                                    "description": "#649 test", "occupants": dict(occ)}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = work / "out"
    r = warmrender.run([sys.executable, str(RENDER), str(dev),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return out, name


def node(stdin, swap=None):
    env = {**os.environ, **({"SWAP_MODULE": str(swap)} if swap else {})}
    p = subprocess.run(["node", str(SCRIPT), "scenarios"], input=stdin, capture_output=True,
                       text=True, cwd=str(SCRIPT.parent), env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("copper-chain")
    dist = tmp / "dist"
    comps = build_components(dist)
    out, name = render(tmp)
    faces = {c: ET.parse(face_file(out, name, c, "front")).getroot() for c in FACES}
    meta = json.loads((out / f"{name}.configs.json").read_text())
    payload = {
        "components": json.loads((dist / "components.json").read_text())["components"],
        "faces": {k: spec_of(v) for k, v in faces.items()},
        "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot()))
                  for r in REFS},
        "cages": {name: meta["cages"]["front"]},
        "configs": {name: meta["configs"]},
        "link": LINK,
    }
    stdin = json.dumps(payload)
    return {"faces": faces, "comps": comps, "stdin": stdin,
            "out": node(stdin) if shutil.which("node") else None}


def parity(world, face, key, have):
    want = built_occupant(world["faces"][face], key)
    return mismatches([{"name": face, "built": {key: want}}],
                      [{"name": face, "seated": {key: have}}])


def clean(world, face, seated):
    """Every key in `seated` is seated once and is the build's."""
    bad = []
    for key, have in seated.items():
        bad += parity(world, face, key, have)
    return bad


# ---------------------------------------------------------------- the build

def test_the_build_draws_the_chain_in_both_cages(world):
    """The premise: each link `data-for` the one below, siblings in the
    device's group, and the turned cage's links really turned - so a kit
    that dropped the host's turn could not match the build by accident."""
    root = world["faces"]["boot"]
    for p in PORTS:
        occ = [built_occupant(root, k) for k in tiers(p)]
        assert [o["ref"] for o in occ] == list(REFS)
        assert [o["attrs"]["data-path"] for o in occ] == [f"{k}-occupant" for k in tiers(p)]
        lifts = [float(o["attrs"].get("data-z-lift") or 0) for o in occ]
        assert lifts[2] > lifts[1] > lifts[0], (p, lifts)
        turned = [("rotate(180" in (o["transform"] or "")) for o in occ]
        # the SFP turns with its cage; the plug in its 180 jack turns back
        assert turned[0] == (p == TURNED), (p, [o["transform"] for o in occ])
    a, b = (built_occupant(root, tiers(p)[1])["transform"] for p in PORTS)
    assert ("rotate(180" in a) != ("rotate(180" in b), (a, b)


# ---------------------------------------------------------------- the kit

@needs_node
def test_each_face_offers_the_next_link(world):
    """The SFP's jack is a slot once the SFP is seated, the plug's boot point
    once the plug is; the chained entry stands on the sum of the lifts and
    carries its host's turn."""
    c = scenario(world, "census")
    for p in PORTS:
        cage, jack, boot = tiers(p)
        assert set(c["base"]) >= {cage} and jack not in c["base"]
        assert jack in c["sfp"] and boot not in c["sfp"]
        assert c["sfp"][jack]["host"] == cage and c["sfp"][jack]["accepts"] == [PLUG]
        assert c["plug"][boot]["host"] == jack and c["plug"][boot]["accepts"] == [BOOT]
        assert c["boot"][boot]["lift"] > c["boot"][jack]["lift"] > 0
    rot = {p: c["boot"][tiers(p)[1]]["rotate"] for p in PORTS}
    assert rot[TURNED] != rot["port-0"], rot


@needs_node
@pytest.mark.parametrize("port", PORTS)
@pytest.mark.parametrize("tier", [0, 1, 2], ids=["sfp", "plug", "boot"])
def test_a_link_the_explorer_seats_is_the_builds(world, port, tier):
    """One slot at a time (shell.js seat), each from the build of the link
    below it, on the upright cage and on the one drawn at 180."""
    s = scenario(world, "links")
    key = tiers(port)[tier]
    assert s["res"][key] == {"applied": 1, "refused": [], "failed": []}, s["res"][key]
    bad = parity(world, TO[tier], key, s["seated"][key])
    assert not bad, "\n".join(bad[:8])


@needs_node
def test_the_whole_chain_in_one_map_is_the_builds(world):
    """seatFace on the bare face - the pass 3D and the faces not on screen
    take - seats all six links, tier by tier, each the build's."""
    s = scenario(world, "chain")
    assert s["res"] == {"applied": 6, "refused": [], "failed": [], "dropped": []}, s["res"]
    bad = clean(world, "boot", s["seated"])
    assert not bad, "\n".join(bad[:8])


@needs_node
def test_a_swap_link_reaches_the_boot(world):
    """The explorer's `swap=`: read raw off the search, decoded, through the
    reload's gate against the configuration's build, and seated - every link
    to the boot survives, and lands where the build draws it."""
    s = scenario(world, "link")
    assert LINK.endswith("swap=" + s["encoded"]), (LINK, s["encoded"])
    assert s["swaps"] == ALL
    assert s["accepted"] == ALL and s["ignored"] == [], s
    assert s["res"] == {"applied": 6, "refused": [], "failed": []}, s["res"]
    bad = clean(world, "boot", s["seated"])
    assert not bad, "\n".join(bad[:8])


# THE CHAIN, MUTATED. Each edit is applied to a copy of kit/swap.js and must
# turn its property back to a defect with every scenario it reads still
# running (test_nested_slots_js's rule) - so none of the checks above can
# pass on a kit that does not do the thing they check.
def _links_clean(world, o, keys):
    s = o["links"]
    return not any(parity(world, TO[t], k, s["seated"][k])
                   for t in range(3) for p in PORTS for k in [tiers(p)[t]] if k in keys)


MUTATIONS = [
    # the jack's offset from the SFP's centre is not turned with the cage:
    # only the 180 cage's plug moves, so the upright case alone passes
    ("the jack does not turn with its cage",
     "const [dx, dy] = turn([p.mate[0] - cx, p.mate[1] - cy], s.rotate);",
     "const [dx, dy] = turn([p.mate[0] - cx, p.mate[1] - cy], 0);",
     ["links"], lambda w, o: _links_clean(w, o, {tiers(TURNED)[1], tiers(TURNED)[2]})),
    # the chained tier takes the jack's own turn and drops its host's
    ("the chained tier drops its host's turn",
     "((+s.rotate || 0) + (+p.rotate || 0)) % 360",
     "(+p.rotate || 0) % 360",
     ["links"], lambda w, o: _links_clean(w, o, {tiers(TURNED)[1], tiers(TURNED)[2]})),
    # the plug stands on the jack's lift alone, not the SFP's plus the jack's
    ("the lifts are not summed",
     "lift: (+s.lift || 0) + (+p.lift || 0),",
     "lift: (+p.lift || 0),",
     ["chain"], lambda w, o: not clean(w, "boot", o["chain"]["seated"])),
    # the reload's gate knows no chained key: the link loses plug and boot
    ("the gate reads no chained tier",
     "const p = host?.isCage ? comp(occRef(hostPath, host))?.presents : null;",
     "const p = null;",
     ["link"], lambda w, o: o["link"]["accepted"] == ALL),
]


@needs_node
@pytest.mark.parametrize("label,old,new,scen,holds", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_a_mutated_chain_fails(world, tmp_path, label, old, new, scen, holds):
    src = (SPEC.parent / "kit/swap.js").read_text()
    assert src.count(old) == 1, f"{label}: the anchor {old!r} is not in swap.js exactly once"
    assert holds(world, world["out"]), f"{label}: the property does not hold on the real kit"
    mutant = tmp_path / "swap.js"
    mutant.write_text(src.replace(old, new))
    got = node(world["stdin"], swap=mutant)
    crashed = {n: got[n]["error"][:200] for n in scen if isinstance(got[n], dict) and "error" in got[n]}
    assert not crashed, f"{label}: the mutant crashed a scenario rather than flipping it: {crashed}"
    assert not holds(world, got), f"{label}: the mutated kit still passes"
