"""What the 3D explorer is handed, held to REAL builds (B3 Task 10c).

viewer3d.js cuts its scene out of compiled drawings the kit rewrites first,
so every choice the explorer makes has to be in those drawings, exactly as
the build would have drawn it, before relief.js reads a single attribute.
Three drawings carry a choice:

  - every FACE of the device (seatViews: the faces the map touches, and every
    face with a rear hole, each through seatFace), which is where a front
    slot's occupant, a swapped module and its caps' `data-for`, and a
    plug's cable anchors (`data-cp-on`) live;
  - each module's OWN BACK drawing (`body.sides.rear`), which is what 3D
    builds a cassette's back from - never the rear face's projection, which
    is flat. seatBack seats the map's keys under the module's bay into it:
    every rear key, whether or not its bay was swapped;
  - and, read off both, which parts come out as FRUs (relief.js bodyRole).

HELD TO REAL BUILDS. Tmp copies of fs/fhd-1ufce and smartoptics/dcp-r-34d-cs
are rendered with configurations that ask the build for what the explorer is
asked to do, and components.json and the component skins are built in tmp.
A face the kit seats from the shipped build is compared, element for element
and attribute for attribute, with the build's face for the same request; a
back the kit seats is compared with render.py's instance_group for that back
given the same occupants - the call components_index makes to draw the
back's standalone skin, which the test first proves reproduces the compiled
skin exactly.

THE FRU RULING (docs/pluggables-caps-design.md, "The kit", 2026-09-23): an
occupant is a part of its own, pulled by its own path - the rule #484 gave
an optic on a card, now for every depth, so a Smartoptics bore's cap is
`xc01/tx-occupant` and not the whole `xc01` adapter. On a module's BACK an
occupant is not a FRU: the back is drawn inside the module's own FRU, in the
back component's namespace, and rides out with the module.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal import render as R
from test_lifted_seat_js import LIB, RENDER, SPEC, build_components, numbers, skin_file, spec_of

SCRIPT = SPEC / "tests/js/explorer-3d.mjs"
SWAP = SPEC.parent / "kit/swap.js"
RELIEF = SPEC.parent / "kit/relief.js"
PLUG, SIMPLEX = "generic/lc-duplex-plug@2", "generic/lc-plug@2"
SFP = "generic/sfp-lc@1"
DCAP, CAP = "common/lc-duplex-dust-cap@2", "common/lc-dust-cap@1"
MCAP, MPO12, MPO24 = "common/mpo-dust-cap@2", "generic/mpo12-plug@1", "generic/mpo24-plug@1"
CASS6, CASS12, SHUT = "fs/fhd-1mtp6lcd-os2-a@4", "fs/fhd-2mtp12-lc-os2-a@4", "fs/fhd-3mtp18-lc-os2-a@1"
POP = {"bay-1": CASS6, "bay-2": CASS6, "bay-3": CASS6, "bay-4": CASS6}
MIX = {"bay-1": CASS12, "bay-2": CASS12, "bay-3": SHUT, "bay-4": CASS6}
SKINS = [PLUG, SIMPLEX, DCAP, CAP, MCAP, MPO12, MPO24, CASS6, CASS12, SHUT]
BODY_CLASSES = {"psu", "fan", "tab", "power", "cooling"}

# configuration -> (bays, occupants) in a tmp copy of the FHD, and the map the
# explorer holds for the same request, starting from `populated`
FHD = {
    "plug": (POP, {"bay-1/lc1": PLUG},
             {"bay-1/module/lc1": PLUG}),
    "simplex": (POP, {"bay-1/lc1": "", "bay-1/lc1/tx": SIMPLEX},
                {"bay-1/module/lc1": "", "bay-1/module/lc1/tx": SIMPLEX}),
    # a cassette swapped in carries its caps, and the shuttered adapter's and
    # the v-adapter's mate markers carry `data-cp-on` (rename's)
    "swapplug": ({**POP, "bay-2": CASS12}, {"bay-2/lc01": PLUG},
                 {"bay-2": CASS12, "bay-2/module/lc01": PLUG}),
    # A REAR KEY ON A BAY NOBODY SWAPPED (10b review, Minor 4)
    "rearkey": (POP, {"bay-4/mtp": MPO12},
                {"bay-4/module/mtp": MPO12}),
    "rearplug": (MIX, {"bay-1/mtp1": MPO12, "bay-2/mtp2": "", "bay-3/mtp2": MPO24},
                 {"bay-1": CASS12, "bay-2": CASS12, "bay-3": SHUT,
                  "bay-1/module/mtp1": MPO12, "bay-2/module/mtp2": "",
                  "bay-3/module/mtp2": MPO24}),
    # front and back of one swapped cassette, and a back nobody swapped
    "mixed": ({**POP, "bay-2": CASS12}, {"bay-2/lc01": PLUG, "bay-2/mtp1": MPO24, "bay-4/mtp": MPO12},
              {"bay-2": CASS12, "bay-2/module/lc01": PLUG, "bay-2/module/mtp1": MPO24,
               "bay-4/module/mtp": MPO12}),
}
DCP = {
    "tx": ({"xc01/tx": SIMPLEX}, {"xc01/tx": SIMPLEX}),
    "duplex": ({"xc01/tx": "", "xc01/rx": "", "xc01": PLUG},
               {"xc01/tx": "", "xc01/rx": "", "xc01": PLUG}),
}

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def render(tmp, device, extra):
    vendor, name = device.split("/")
    dev = tmp / name / "src" / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    d.setdefault("configurations", {"default": {"default": True}})
    for cfg, (bays, occ) in extra.items():
        d["configurations"][cfg] = {"kind": "example", "description": "B3 Task 10c test",
                                    **({"bays": dict(bays)} if bays else {}),
                                    "occupants": dict(occ)}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / name / "out"
    r = subprocess.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return out, name


def render_merged(tmp, device, cfg, occupants):
    """A tmp copy of `device` with `occupants` merged into its configuration
    `cfg`, rendered; the front face of that configuration."""
    vendor, name = device.split("/")
    dev = tmp / f"{name}-merged" / "src" / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    c = d["configurations"][cfg]
    c["occupants"] = {**(c.get("occupants") or {}), **occupants}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = dev.parent.parent / "out"
    r = subprocess.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    meta = json.loads((out / f"{name}.configs.json").read_text())
    return ET.parse(out / f"{name}.{cfg}.front.svg").getroot(), meta


def node(mode, payload, swap=None, relief=None):
    env = {**os.environ, **({"SWAP_MODULE": str(swap)} if swap else {}),
           **({"RELIEF_MODULE": str(relief)} if relief else {})}
    p = subprocess.run(["node", str(SCRIPT), mode], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=str(SCRIPT.parent), env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def got(out, name):
    g = out[name]
    assert not (isinstance(g, dict) and "error" in g), g.get("error")
    return g


_lib = R.Library([str(LIB)])


def built_back(ref, bay, occupants=None):
    """render.py's drawing of the back `ref` of the module in `bay`, given the
    configuration's `occupants` keyed as a configuration keys them
    (`bay-1/mtp1`) - the instance_group call draw_placement makes for a
    `rear:` hole before the projection strips its relief - then read in the
    back's own namespace, as components_index draws the compiled skin
    (test_the_build_draws_the_compiled_back holds the two equal unconfigured).
    Every key the call takes is asserted taken."""
    name = ref.split("/")[-1].split("@")[0]
    used = set()
    g, _ = R.instance_group(_lib, ref, f"{bay}-rear", [0, 0], None, None, None, None,
                            skin_name="default", palette={}, resolved={}, path=f"{bay}/module",
                            occupants=occupants or None, occ_used=used)
    assert used == set(occupants or {}), (ref, used)
    idh, ph = f"{bay}-rear", f"{bay}/module"
    for e in g.iter():
        for k, v in list(e.attrib.items()):
            if k in ("id", "data-cp-on"):
                v = name if v == idh else name + v[len(idh):] if v.startswith(idh + "--") else v
            elif k in ("data-path", "data-for"):
                v = " ".join(name if t == ph else name + t[len(ph):] if t.startswith(ph + "/") else t
                             for t in v.split())
            elif "url(#" in v:
                v = v.replace(f"url(#{idh}--", f"url(#{name}--")
            e.set(k, v)
    return g


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("explorer-3d")
    dist = tmp / "dist"
    comps = build_components(dist)
    fhd_out, fhd = render(tmp, "fs/fhd-1ufce", {k: v[:2] for k, v in FHD.items()})
    dcp_out, dcp = render(tmp, "smartoptics/dcp-r-34d-cs",
                          {k: (None, v[0]) for k, v in DCP.items()})
    faces = {}
    for cfg in ["populated", *FHD]:
        for view in ("front", "rear"):
            faces[f"fhd:{cfg}:{view}"] = ET.parse(fhd_out / f"{fhd}.{cfg}.{view}.svg").getroot()
    for cfg in ["default", *DCP]:
        faces[f"dcp:{cfg}:front"] = ET.parse(dcp_out / f"{dcp}.{cfg}.front.svg").getroot()
    # an optic that declares its depth, seated on a card: the eject pin's
    # reference for "a part with a depth travels as it always did"
    faces["dcp2:sfp:front"], dcp2_meta = render_merged(tmp, "smartoptics/dcp-2", "ila-node",
                                                       {"slot-1/sfp-1": SFP})
    meta = {n: json.loads((o / f"{n}.configs.json").read_text())
            for o, n in ((fhd_out, fhd), (dcp_out, dcp))}
    meta["dcp-2"] = dcp2_meta
    idx = json.loads((dist / "components.json").read_text())["components"]
    backs = {r: comps[r]["faces"]["rear"] for r in (CASS6, CASS12, SHUT)}
    skins = {r: ET.parse(skin_file(dist, comps[r])).getroot() for r in SKINS + list(backs.values())}
    return {"faces": faces, "meta": meta, "idx": idx, "comps": comps, "backs": backs,
            "skins": skins, "fhd": fhd, "dcp": dcp,
            "skin_text": {r: json.dumps(spec_of(s)) for r, s in skins.items()}}


def face_payload(world):
    fm, dm = world["meta"][world["fhd"]], world["meta"][world["dcp"]]
    cases = [{"name": f"fhd:{c}", "map": v[2], "bays": fm["bays"], "cages": fm["cages"],
              "faces": {view: spec_of(world["faces"][f"fhd:populated:{view}"])
                        for view in ("front", "rear")}} for c, v in FHD.items()]
    cases += [{"name": f"dcp:{c}", "map": v[1], "bays": dm["bays"], "cages": dm["cages"],
               "faces": {"front": spec_of(world["faces"]["dcp:default:front"])}}
              for c, v in DCP.items()]
    return {"components": world["idx"], "skins": world["skin_text"], "cases": cases}


@pytest.fixture(scope="module")
def seated_faces(world):
    payload = face_payload(world)
    return payload, node("faces", payload)


# ------------------------------------------------------------ comparing trees

def _tree(spec):
    """`<style>` left out: the kit brings a skin's stylesheet along with what it
    imports, where the build states the rules once for the drawing."""
    return {"t": spec["t"], "a": spec["a"],
            "c": [_tree(k) for k in spec["c"] if k["t"] != "style"]}


def _keyed(kids):
    """Children matched by id, not by position: the kit appends what it seats
    after its host's parts, where the build draws in slot order."""
    seen, out = {}, {}
    for c in kids:
        k = c["a"].get("id") or (f"cp:{c['a']['data-cp']}" if "data-cp" in c["a"] else f"<{c['t']}>")
        seen[k] = seen.get(k, 0) + 1
        out[f"{k}#{seen[k]}"] = c
    return out


def tree_diff(kit, build, skip_root=()):
    """Every difference between the kit's drawing (a fake-dom spec) and the
    build's (ElementTree), as readable strings. EQUAL, element for element
    and attribute for attribute - every `data-z-*` and `data-cp*` as the
    string the build writes - with a transform compared as numbers of the
    same shape (the kit writes `16`, the build `16.0`)."""
    out = []

    def attrs(where, ka, ba, skip=()):
        for k in sorted((set(ka) | set(ba)) - set(skip)):
            a, b = ka.get(k), ba.get(k)
            if a == b:
                continue
            if k == "transform" and a and b and len(numbers(a)) == len(numbers(b)) \
                    and all(abs(x - y) < 1e-6 for x, y in zip(numbers(a), numbers(b))) \
                    and re.sub(r"[-\d.e]+", "#", a) == re.sub(r"[-\d.e]+", "#", b):
                continue
            out.append(f"{where} [{k}]: kit {a!r} build {b!r}")

    def same(where, k, b, skip=()):
        if k["t"] != b["t"]:
            out.append(f"{where}: <{k['t']}> vs <{b['t']}>")
            return
        attrs(where, k["a"], b["a"], skip)
        kk, bk = _keyed(k["c"]), _keyed(b["c"])
        for x in sorted(set(kk) ^ set(bk)):
            out.append(f"{where}: child {x} only in the {'kit' if x in kk else 'build'}")
        for x in sorted(set(kk) & set(bk)):
            same(f"{where}/{x}", kk[x], bk[x])

    same(build.get("id") or "svg", _tree(kit), _tree(spec_of(build)), skip_root)
    return out


def count(el, pred):
    return sum(1 for e in el.iter() if pred(e.attrib))


# ------------------------------------------------------- the FRU ruling

def instances(root):
    """Every instance (`data-ref`) of a drawing outside a projection, which is
    flat, with the marks extractRelief reads - relief.js bodyBehaviour decides
    which come out (what `fills` or `occupies`, a legacy body class, and an
    occupant that declares no behaviour: a plug)."""
    parents = {c: p for p in root.iter() for c in p}

    def projected(e):
        n = e
        while n is not None:
            if n.get("data-projection"):
                return True
            n = parents.get(n)
        return False
    return [{"ref": e.get("data-ref"), "path": e.get("data-path") or "",
             "behaviour": e.get("data-behaviour"), "for": e.get("data-for"),
             "cls": e.get("data-class")}
            for e in root.iter() if e.get("data-ref") and not projected(e)]


@pytest.fixture(scope="module")
def roles(world):
    sets = {"dcp": {"back": False, "nodes": instances(world["faces"]["dcp:default:front"])},
            "fhd": {"back": False, "nodes": instances(world["faces"]["fhd:populated:front"])},
            "cassette": {"back": False, "nodes": instances(world["skins"][CASS12])},
            # a PLUG in a front slot: on a bore of an adapter on the device,
            # and in a cassette's duplex slot
            "dcp:tx": {"back": False, "nodes": instances(world["faces"]["dcp:tx:front"])},
            "fhd:plug": {"back": False, "nodes": instances(world["faces"]["fhd:plug:front"])}}
    for r, back in world["backs"].items():
        for as_back in (True, False):
            sets[f"{back}|{as_back}"] = {"back": as_back, "nodes": instances(world["skins"][back])}
    return sets, node("roles", {"sets": sets})


@needs_node
def test_a_smartoptics_bore_cap_is_its_own_part(roles):
    """dcp-r-34d-cs ships 72 bore caps at `xcNN/tx-occupant` / `rx-occupant`
    (and on port-1510/port-line): each is a FRU keyed by its own path, not by
    the adapter it sits in - which pulled both caps of an adapter, 36 times."""
    sets, out = roles
    g = got(out, "dcp")
    caps = [r for r in g["roles"] if r["behaviour"] == "occupies"]
    assert len(caps) == 72 and all(re.fullmatch(r"[\w-]+/(tx|rx)-occupant", c["path"]) for c in caps)
    for c in caps:
        assert c["role"] == {"fru": c["path"], "nested": True}, c
    assert len({c["role"]["fru"] for c in caps}) == 72
    # nothing is pulled by the name of a part that is not removable
    adapters = {c["path"].split("/")[0] for c in caps}
    assert len(adapters) == 36 and not adapters & set(g["frus"]), sorted(adapters & set(g["frus"]))


@needs_node
def test_every_fru_on_a_real_face_is_a_removable_part(roles):
    """Every FRU key names a part that comes out: an occupant's own path, or
    the bay a fills module sits in (`bay-1/module` pulls as `bay-1`)."""
    sets, out = roles
    for name in ("dcp", "fhd", "cassette", "dcp:tx", "fhd:plug"):
        g = got(out, name)
        own = {r["path"] for r in g["roles"] if r["behaviour"] == "occupies"}
        bays = {r["path"].split("/")[0] for r in g["roles"] if r["behaviour"] != "occupies"}
        assert g["frus"] and set(g["frus"]) <= own | bays, (name, sorted(set(g["frus"]) - own - bays))
        assert own <= set(g["frus"]), (name, sorted(own - set(g["frus"])))


@needs_node
def test_a_plug_in_a_front_slot_is_its_own_part(roles):
    """A plug declares no behaviour (class `port`, by its own ruling), and was
    never collected: the cap it replaced came out, the plug did not. It is an
    occupant - `data-for` its slot, at `<slot>-occupant` - and is pulled by
    its own path like the cap (the controller's ruling, B3 Task 10c)."""
    _, out = roles
    for name, path, ref in (("dcp:tx", "xc01/tx-occupant", SIMPLEX),
                            ("fhd:plug", "bay-1/module/lc1-occupant", PLUG)):
        g = got(out, name)
        [r] = [r for r in g["roles"] if r["path"] == path]
        assert r["raw"] is None and r["behaviour"] == "occupies", r
        assert r["role"] == {"fru": path, "nested": True}, r
        assert path in g["frus"], (name, g["frus"])
    # the cap beside it on the same adapter is still its own part
    assert "xc01/rx-occupant" in got(out, "dcp:tx")["frus"]


@needs_node
def test_the_fhd_front_keeps_its_cassettes_and_its_caps_apart(roles):
    _, out = roles
    g = got(out, "fhd")
    assert sorted(f for f in g["frus"] if "/" not in f) == ["bay-1", "bay-2", "bay-3", "bay-4"]
    caps = [f for f in g["frus"] if f.endswith("-occupant")]
    assert len(caps) == 24 and all(re.fullmatch(r"bay-[1-4]/module/lc[1-6]-occupant", c) for c in caps)


@needs_node
def test_a_cassette_back_holds_no_fru(roles, world):
    """The back's own drawing is what 3D builds a cassette's back from, inside
    the cassette's FRU. Read as a back, its caps are no FRU: they ride out with
    the cassette. Read as a lone drawing, each is keyed by its own path - never
    by the back's name, which pulled the whole back as a "cap"."""
    sets, out = roles
    checked = 0
    for back in world["backs"].values():
        name = back.split("/")[-1].split("@")[0]
        as_back, alone = got(out, f"{back}|True"), got(out, f"{back}|False")
        caps = [r for r in as_back["roles"] if r["behaviour"] == "occupies"]
        assert caps, back
        assert as_back["frus"] == [] and all(c["role"] is None for c in caps), (back, as_back["frus"])
        assert name not in alone["frus"], (back, alone["frus"])
        assert sorted(alone["frus"]) == sorted(c["path"] for c in caps), (back, alone["frus"])
        checked += len(caps)
    assert checked == 1 + 2 + 3, checked


# ------------------------------------------------------- the faces 3D is cut from

def _check_face(world, seated, case, view, cfg):
    out = got(seated, case)
    return tree_diff(out["faces"][view], world["faces"][f"{cfg}:{view}"])


@needs_node
@pytest.mark.parametrize("case", sorted(f"fhd:{c}" for c in FHD) + sorted(f"dcp:{c}" for c in DCP))
def test_the_faces_3d_is_cut_from_are_the_builds(world, seated_faces, case):
    """seatViews from the SHIPPED build, given the explorer's map, equals the
    build of the configuration asking for the same thing - on every face,
    front and rear. What the relief pass reads is in this: a plug's
    `data-cp-on` (named for the occupant, not for the plug's own skin), each
    `data-z-*` string, and a swapped cassette's caps and markers."""
    payload, out = seated_faces
    g = got(out, case)
    views = sorted(g["faces"])
    dev, cfg = case.split(":")
    bad = []
    for view in views:
        want = world["faces"][f"{dev}:{cfg}:{view}"]
        bad += [f"{view}: {b}" for b in tree_diff(g["faces"][view], want, skip_root=SVG_ROOT_SKIP)]
    assert not bad, f"{len(bad)} differences:\n" + "\n".join(bad[:15])
    for view, res in g["res"].items():
        assert res["refused"] == [] and res["failed"] == [], (view, res)


# The drawing's own root names the configuration it was built for; the kit's
# face is the shipped build's, and nothing in 3D reads the name
SVG_ROOT_SKIP = ("data-config",)


@needs_node
def test_every_rear_key_reaches_the_rear_face(world, seated_faces):
    """A key on a back whose bay nobody swapped is seated on the rear face as
    well as one whose bay was: viewer3d's rear pass used to rebuild only
    swapped bays' backs (seatViews runs seatFace on every face with a rear
    hole)."""
    _, out = seated_faces
    for case, key in (("fhd:rearkey", "bay-4/module/mtp"), ("fhd:mixed", "bay-4/module/mtp"),
                      ("fhd:mixed", "bay-2/module/mtp1")):
        rear = got(out, case)["faces"]["rear"]
        hits = [n for n in _walk(rear) if n["a"].get("data-for") == key
                and n["a"].get("data-of") == f"{key}-occupant"]
        assert len(hits) == 1 and hits[0]["a"].get("data-class") == "port", (case, key, hits)
        assert got(out, case)["res"]["rear"]["applied"] > 0


def _walk(spec):
    yield spec
    for c in spec["c"]:
        yield from _walk(c)


@needs_node
def test_the_plug_cable_anchors_are_named_for_the_occupant(world, seated_faces):
    """The rename gap Task 9 pinned (4 markers on the duplex plug) is closed:
    every `data-cp-on` the kit writes names a node that exists in its own
    instance group, as relief.js cablePoints looks it up."""
    _, out = seated_faces
    checked = 0
    for case in ("fhd:plug", "fhd:swapplug", "dcp:duplex", "fhd:simplex", "dcp:tx"):
        front = got(out, case)["faces"]["front"]
        for n in _walk(front):
            for mk in n["c"]:
                on = mk["a"].get("data-cp-on")
                if on is None:
                    continue
                ids = {d["a"].get("id") for d in _walk(n)}
                assert on in ids, (case, n["a"].get("id"), on)
                checked += 1
    # the duplex plug alone carries 4, twice over, and the swapped cassette's
    # adapters carry theirs
    assert checked > 8, checked


# ------------------------------------------------------- the backs 3D builds

def root_group(spec):
    """The back's instance group inside its `<svg>` - what components_index
    draws with instance_group and wraps."""
    groups = [k for k in spec["c"] if k["t"] == "g"]
    assert len(groups) == 1, [k["t"] for k in spec["c"]]
    return groups[0]


def back_cases(world):
    rp, rk, mx = FHD["rearplug"][2], FHD["rearkey"][2], FHD["mixed"][2]
    return [
        # (case, module ref, bay, map, the occupants the build is asked for)
        ("rearplug bay-1", CASS12, "bay-1", rp, {"mtp1": MPO12}),
        ("rearplug bay-2", CASS12, "bay-2", rp, {"mtp2": ""}),
        ("rearplug bay-3", SHUT, "bay-3", rp, {"mtp2": MPO24}),
        ("rearkey bay-4", CASS6, "bay-4", rk, {"mtp": MPO12}),
        ("mixed bay-2", CASS12, "bay-2", mx, {"mtp1": MPO24}),
        ("mixed bay-4", CASS6, "bay-4", mx, {"mtp": MPO12}),
        ("nothing keyed under bay-1", CASS12, "bay-1", rk, {}),
        ("a front key is no back key", CASS12, "bay-2", {"bay-2/module/lc01": PLUG}, {}),
        ("an unloadable plug", CASS6, "bay-4", {"bay-4/module/mtp": "generic/no-such-plug@1"}, {}),
        ("a key naming nothing on the back", CASS12, "bay-1",
         {"bay-1/module/mtp9": MPO12, "bay-1/module/mtp1": MPO12}, {"mtp1": MPO12}),
        ("a back with no root", CASS12, "bay-1", {"bay-1/module/mtp1": MPO12}, None),
    ]


@pytest.fixture(scope="module")
def seated_backs(world):
    cases = back_cases(world)
    payload = {"components": world["idx"], "skins": world["skin_text"],
               "cases": [{"name": n, "back": (spec_of(world["skins"][world["backs"][mod]])
                                              if occ is not None else rootless(world["skins"][world["backs"][mod]])),
                          "bay": bay, "moduleRef": mod, "map": mp}
                         for n, mod, bay, mp, occ in cases]}
    return cases, payload, node("backs", payload)


def rootless(skin):
    """The back skin with its instance's `data-ref` taken off: a drawing the
    kit cannot read a back's slots from."""
    spec = spec_of(skin)
    for k in spec["c"]:
        k["a"].pop("data-ref", None)
    return spec


def test_the_build_draws_the_compiled_back(world):
    """The reference is honest: the back render.py draws in a bay, read in the
    back's namespace, IS the compiled back skin the kit starts from, element
    for element - so a difference below is the seat, and nothing else."""
    for mod, back in world["backs"].items():
        built = built_back(back, "bay-1")
        skin = next(k for k in world["skins"][back] if k.tag.endswith("}g"))
        assert spec_of(built) == spec_of(skin), back


@needs_node
def test_a_back_the_kit_seats_is_the_back_the_build_draws(world, seated_backs):
    """seatBack puts every key the map holds under a bay into that module's
    OWN back drawing - the one relief.js builds the back from - exactly as
    render.py draws the back given the same occupants: the occupant at the
    slot's lift (3.5), its `out`s absolute as published, its ids and paths in
    the back's namespace, the shipped cap gone where it was replaced."""
    cases, _, out = seated_backs
    for name, mod, bay, mp, occ in cases:
        if occ is None:
            continue
        back = world["backs"][mod]
        bname = back.split("/")[-1].split("@")[0]
        g = got(out, name)
        want = built_back(back, bay, {f"{bay}/{k}": v for k, v in occ.items()})
        bad = tree_diff(root_group(g["back"]), want)
        assert not bad, f"{name}: {len(bad)} differences:\n" + "\n".join(bad[:12])
        if occ:
            assert g["res"]["applied"] == len(occ), (name, g["res"])
            for slot, ref in occ.items():
                occs = [e for e in want.iter() if e.get("data-for") == f"{bname}/{slot}"
                        and (e.get("data-path") or "").endswith("-occupant")]
                assert len(occs) == (1 if ref else 0), (name, slot)
                if ref:
                    assert occs[0].get("data-z-lift") == "3.5", (name, occs[0].attrib)
                    assert occs[0].get("data-ref").split(":")[0] == ref


@needs_node
def test_a_back_key_that_does_not_seat_says_so(world, seated_backs):
    cases, _, out = seated_backs
    none = {"applied": 0, "refused": [], "failed": [], "dropped": []}
    assert got(out, "nothing keyed under bay-1")["res"] == none
    # a key on the module's FRONT is the face pass's, and not reported here
    assert got(out, "a front key is no back key")["res"] == none
    # a skin that does not load leaves the shipped cap and is reported by the
    # device key, as the front pass reports it
    assert got(out, "an unloadable plug")["res"] == {**none, "failed": ["bay-4/module/mtp"]}
    # a key naming no slot of the back is said, and the one beside it seats
    assert got(out, "a key naming nothing on the back")["res"] == {
        **none, "applied": 1, "dropped": ["bay-1/module/mtp9"]}
    # a drawing the back's slots cannot be read from seats nothing and says so
    assert got(out, "a back with no root")["res"] == {**none, "dropped": ["bay-1/module/mtp1"]}


# THE BACK SEAT, MUTATED: each edit to a copy of kit/swap.js must make the
# back parity fail (a mutant that crashes a case does not count as caught).
SEATED = {"rearplug bay-1", "rearplug bay-3", "rearkey bay-4", "mixed bay-2", "mixed bay-4",
          "a key naming nothing on the back"}
BACK_MUTATIONS = [
    # every case that seats a plug: the plug stands at the face, not at 3.5
    ("no lift on the back", "liftOccupant(wrap, +cage.lift || 0);", "liftOccupant(wrap, 0);", SEATED),
    # the cases whose keys sit under another bay: nothing is seated on them
    ("keys under another bay", "const head = `${bay}/module/`;", "const head = `bay-1/module/`;",
     {"rearplug bay-2", "rearplug bay-3", "rearkey bay-4", "mixed bay-2", "mixed bay-4"}),
    # every case that seats or empties anything
    ("the back's own name is not the namespace",
     "const local = `${name}/${k.slice(head.length)}`;", "const local = `${k}`;",
     SEATED | {"rearplug bay-2"}),
]


@needs_node
@pytest.mark.parametrize("label,old,new,expect", BACK_MUTATIONS, ids=[m[0] for m in BACK_MUTATIONS])
def test_a_mutated_back_seat_fails_the_parity(world, seated_backs, tmp_path, label, old, new, expect):
    cases, payload, _ = seated_backs
    src = SWAP.read_text()
    assert src.count(old) == 1, f"{label}: the anchor is not in swap.js exactly once"
    mutant = tmp_path / "swap.js"
    mutant.write_text(src.replace(old, new))
    out = node("backs", payload, swap=mutant)
    caught = set()
    for name, mod, bay, mp, occ in cases:
        g = out[name]
        assert "error" not in g, f"{label}: {name} crashed - not a catch: {g['error'][:300]}"
        if occ is None:
            continue
        back = world["backs"][mod]
        want = built_back(back, bay, {f"{bay}/{k}": v for k, v in occ.items()})
        if tree_diff(root_group(g["back"]), want):
            caught.add(name)
    assert caught == expect, (label, sorted(caught))


# THE FACES AND THE ROLES, MUTATED: each edit to a copy of the kit must fail
# the test it names, on a real build, and no case may crash instead.
FACE_MUTATIONS = [
    ("the rear holes are walked for swapped bays only",
     "if (!named.has(view) && !root.querySelector('[data-rear-of]')) continue;",
     # the rear face is named by no bay or cage of its own, so it is not
     # seated at all: every case with a swapped bay or a back key fails
     "if (!named.has(view)) continue;", ["fhd:rearkey", "fhd:rearplug", "fhd:mixed", "fhd:swapplug"]),
    ("rename leaves data-cp-on",
     "if (on && on.startsWith(name + '--')) el.setAttribute('data-cp-on', `${idHead}--${on.slice(name.length + 2)}`);",
     # every plug, and every cassette swapped in (its adapters' mate points)
     "", ["fhd:plug", "fhd:simplex", "fhd:swapplug", "fhd:rearplug", "fhd:mixed",
          "dcp:duplex", "dcp:tx"]),
    ("a swapped module's ref has no version",
     "wrap.setAttribute('data-ref', comp?.version && !String(ref).includes(':') ? `${ref}:${comp.version}` : ref);",
     "wrap.setAttribute('data-ref', ref);", ["fhd:swapplug", "fhd:rearplug", "fhd:mixed"]),
]


@needs_node
@pytest.mark.parametrize("label,old,new,cases", FACE_MUTATIONS, ids=[m[0] for m in FACE_MUTATIONS])
def test_a_mutated_face_pass_fails_the_parity(world, seated_faces, tmp_path, label, old, new, cases):
    payload, _ = seated_faces
    src = SWAP.read_text()
    assert src.count(old) == 1, f"{label}: the anchor is not in swap.js exactly once"
    mutant = tmp_path / "swap.js"
    mutant.write_text(src.replace(old, new))
    out = node("faces", payload, swap=mutant)
    failing = set()
    for case in out:
        g = out[case]
        assert "error" not in g, f"{label}: {case} crashed - not a catch: {g['error'][:300]}"
        dev, cfg = case.split(":")
        for view, spec in g["faces"].items():
            if tree_diff(spec, world["faces"][f"{dev}:{cfg}:{view}"], skip_root=SVG_ROOT_SKIP):
                failing.add(case)
    assert failing == set(cases), (label, sorted(failing))


BACKS = ("fs/fhd-1mtp6lcd-rear@3", "fs/fhd-2mtp12-lc-rear@2", "fs/fhd-3mtp18-lc-rear@1")
ROLE_MUTATIONS = [
    ("two segments are keyed by the first again",
     "if (behaviour === 'occupies' && segs.length > 1) return {fru: segs.join('/'), nested: true};",
     "if (behaviour === 'occupies' && segs.length > 2) return {fru: segs.join('/'), nested: true};",
     {"dcp", "dcp:tx", "cassette"} | {f"{b}|False" for b in BACKS}),
    ("a back's occupant is a FRU", "if (behaviour === 'occupies' && back) return null;", "",
     {f"{b}|True" for b in BACKS}),
    ("a plug is not collected",
     "if (host && /-occupant$/.test(String(path || ''))) return 'occupies';", "",
     {"dcp:tx", "fhd:plug"}),
]


def _role_ok(name, g, backs):
    """The ruling, per set: every occupant - `data-for` a slot at
    `<slot>-occupant`, a plug included - is collected as occupying and keyed
    by its own path (nested); on a back none is a FRU."""
    occ = [r for r in g["roles"] if r["for"] and r["path"].endswith("-occupant")]
    assert occ, name
    if name.endswith("|True"):
        return g["frus"] == [] and all(r["role"] is None for r in occ)
    return all(r["behaviour"] == "occupies" and r["role"] == {"fru": r["path"], "nested": True}
               and r["path"] in g["frus"] for r in occ if "/" in r["path"])


@needs_node
@pytest.mark.parametrize("label,old,new,sets", ROLE_MUTATIONS, ids=[m[0] for m in ROLE_MUTATIONS])
def test_a_mutated_body_role_breaks_the_ruling(world, roles, tmp_path, label, old, new, sets):
    payload, good = roles
    assert all(_role_ok(n, got(good, n), world["backs"]) for n in payload), "the kit's own must pass"
    src = RELIEF.read_text()
    assert src.count(old) == 1, f"{label}: the anchor is not in relief.js exactly once"
    mutant = tmp_path / "relief.js"
    mutant.write_text(src.replace(old, new))
    shutil.copy(RELIEF.parent / "fields.js", tmp_path / "fields.js")   # relief.js imports it
    out = node("roles", {"sets": payload}, relief=mutant)
    broken = set()
    for n in payload:
        assert "error" not in out[n], f"{label}: {n} crashed - not a catch"
        if not _role_ok(n, out[n], world["backs"]):
            broken.add(n)
    assert broken == set(sets), (label, sorted(broken))


# ------------------------------------------------------- how far a part is pulled

def eject_cases(world):
    """Every removable instance of four real fronts, as extractRelief measures
    it: its body (components.json), `data-body-depth`, an optic's `data-depth`,
    whether it occupies (bodyBehaviour's reading, a plug included), and its
    own features with their summed lifts. `into` is the device's depth."""
    faces = {"dcp:default": ("dcp-r-34d-cs", "dcp:default:front"),
             "dcp:tx": ("dcp-r-34d-cs", "dcp:tx:front"),
             "fhd:plug": ("fhd-1ufce", "fhd:plug:front"),
             "dcp2:sfp": ("dcp-2", "dcp2:sfp:front")}
    comps = world["comps"]
    cases = []
    for key, (dev, face) in faces.items():
        root = world["faces"][face]
        parents = {c: p for p in root.iter() for c in p}

        def lift(e):
            t, n = 0.0, e
            while n is not None:
                t += float(n.get("data-z-lift") or 0)
                n = parents.get(n)
            return t

        def projected(e):
            n = e
            while n is not None:
                if n.get("data-projection"):
                    return True
                n = parents.get(n)
            return False
        into = world["meta"][dev]["chassis"]["d"]
        for e in root.iter():
            ref = (e.get("data-ref") or "").split(":")[0]
            if not ref or projected(e):
                continue
            beh = e.get("data-behaviour")
            occ = beh == "occupies" or (bool(e.get("data-for"))
                                        and (e.get("data-path") or "").endswith("-occupant"))
            if not (occ or beh == "fills" or (beh is None and e.get("data-class") in BODY_CLASSES)):
                continue
            feats = [{"out": n.get("data-z-out"), "cyl": n.get("data-z-cyl"), "bar": n.get("data-z-bar"),
                      "uhandle": n.get("data-z-uhandle"), "lift": lift(n)} for n in e.iter()
                     if any(n.get(f"data-z-{k}") is not None for k in ("out", "cyl", "bar", "uhandle"))]
            cases.append({"name": f"{key} {e.get('data-path')}", "ref": ref,
                          "body": (comps.get(ref) or {}).get("body"),
                          "bodyDepth": float(e.get("data-body-depth")) if e.get("data-body-depth") else None,
                          "depth": float(e.get("data-depth")) if beh == "occupies" and e.get("data-depth") else None,
                          "occupies": occ, "feats": feats, "base": lift(e), "into": into})
    return cases


@pytest.fixture(scope="module")
def ejected(world):
    cases = eject_cases(world)
    return cases, node("eject", {"cases": cases})


def _old_travel(c):
    """The rule every part with a depth kept, restated from the 10b kit:
    `min(travel or depth * 1.5 + 25, into - 10)`, depth = body.depth, else
    data-body-depth, else 60, and a bay box that deep left behind."""
    d = c["body"]["depth"] if c["body"] else (c["bodyDepth"] or 60)
    captive = c["body"] and c["body"].get("travel")
    return {"pull": min(captive or d * 1.5 + 25, c["into"] - 10), "leavesBay": True, "bayDepth": d}


@needs_node
def test_a_part_that_declares_a_depth_is_pulled_as_before(ejected):
    """Optics, cards, modules and supplies that declare a body or a depth keep
    today's travel and today's bay box EXACTLY."""
    cases, out = ejected
    kept = [c for c in cases if c["body"] or c["bodyDepth"] or c["depth"] or not c["occupies"]]
    kinds = {c["ref"] for c in kept}
    # the cassettes (a body), the SFP (an optic's own depth), the DCP-R's supplies
    assert SFP in kinds and CASS6 in kinds and len(kept) >= 8, sorted(kinds)
    for c in kept:
        assert got(out, c["name"])["travel"] == _old_travel(c), c["name"]


@needs_node
def test_a_cap_or_a_plug_is_pulled_by_its_own_relief_and_leaves_its_port(ejected, world):
    """An occupant that declares no depth - every dust cap and plug - travels
    its own relief extent (its furthest `out` off its seat) plus the margin,
    and leaves no box in the port it came out of."""
    cases, out = ejected
    free = [c for c in cases if c["occupies"] and not (c["body"] or c["bodyDepth"] or c["depth"])]
    refs = {c["ref"] for c in free}
    assert {CAP, DCAP, SIMPLEX, PLUG} <= refs, sorted(refs)
    for c in free:
        g = got(out, c["name"])
        top = 0.0
        for f in c["feats"]:
            if f["out"] is not None:
                top = max(top, float(f["out"]) - c["base"])
            for k in ("cyl", "bar", "uhandle"):
                if f[k] is not None:
                    top = max(top, f["lift"] - c["base"] + float(f[k]))
        assert top > 0 and abs(g["extent"] - top) < 1e-9, (c["name"], g["extent"], top)
        assert g["travel"] == {"pull": top + 10, "leavesBay": False, "bayDepth": 0}, c["name"]
    # the extent is the part's own published figure: a simplex cap stands its
    # contract's `out` off its seat, whatever lift the seat is at
    for ref, want in ((CAP, 6.35), (DCAP, None)):
        ext = {round(got(out, c["name"])["extent"], 6) for c in free if c["ref"] == ref}
        assert len(ext) == 1, (ref, ext)
        if want is not None:
            assert ext == {want}, (ref, ext)
