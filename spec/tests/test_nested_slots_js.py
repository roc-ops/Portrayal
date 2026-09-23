"""The explorer's slots on a FRONT face, in 2D (B3 Task 10a).

`nestedSlots` (kit/swap.js) reads every slot on the face off the drawing: each
`[data-ref]` group whose component publishes `cages` in components.json - a
card in a bay, a cassette, an adapter composed in either, an adapter placed on
the device - that is not inside a `data-for` group (P3). Each entry carries the
drawing path as `id` and the configuration's module-less key as `key` (P1:
`bay-1/module/lc1/tx` is `bay-1/lc1/tx`). The explorer offers only the free
level of a duplex adapter (L111's exclusion), marks the shipped default, and
takes a swap through the one seating path the build is held to.

HELD TO REAL BUILDS. Tmp copies of fs/fhd-1ufce and smartoptics/dcp-r-34d-cs
are rendered with extra configurations that ask the build for what the kit is
asked to do - a duplex plug in place of the FHD's shipped cap, a simplex plug
in an emptied adapter's bore, a plug in a DCP-R bore at lift 3.175, a duplex
plug across two emptied DCP-R bores, a cassette in a bay the build filled with
another, a plug on a shuttered 36-fibre cassette - and what the kit seats into
the SHIPPED face is compared with what render.py drew (Task 9's `mismatches`).

Two defects this pins, found by Tasks 8 and 9:
  - a plug carries no `data-behaviour="occupies"`, so the kit never took one
    out and a second swap stacked (the kit now knows an occupant by
    `data-for` plus a ref its slot accepts - isOccupantOf);
  - a module swapped in by the explorer kept its compiled skin's own
    `data-for` (`fhd-2mtp12-lc-os2-a/lc01`), so its shipped caps named no slot
    of the device and a swap on it stacked too (rename now re-keys it).
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

from portrayal import libwalk
from test_lifted_seat_js import (LIB, RENDER, SPEC, build_components, chain_matrix,
                                 descendants, is_occupant, mismatches, skin_file, spec_of)

SCRIPT = SPEC / "tests/js/nested-slots.mjs"
PLUG, SIMPLEX = "generic/lc-duplex-plug@2", "generic/lc-plug@2"
DCAP, CAP = "common/lc-duplex-dust-cap@2", "common/lc-dust-cap@1"
CASS6, CASS12, SHUT = "fs/fhd-1mtp6lcd-os2-a@3", "fs/fhd-2mtp12-lc-os2-a@3", "fs/fhd-3mtp18-lc-os2-a@1"
POP = {"bay-1": CASS6, "bay-2": CASS6, "bay-3": CASS6, "bay-4": CASS6}

# configuration name -> (bays, occupants) added to a tmp copy of the device
FHD_CONFIGS = {
    "plug": (POP, {"bay-1/lc1": PLUG}),
    "simplex": (POP, {"bay-1/lc1": "", "bay-1/lc1/tx": SIMPLEX}),
    "swapped": ({**POP, "bay-2": CASS12}, {}),
    "swapplug": ({**POP, "bay-2": CASS12}, {"bay-2/lc01": PLUG}),
    "shut": ({**POP, "bay-3": SHUT}, {}),
    "shutplug": ({**POP, "bay-3": SHUT}, {"bay-3/lc01/tx": SIMPLEX}),
}
DCP_CONFIGS = {
    "tx": (None, {"xc01/tx": SIMPLEX}),
    "duplex": (None, {"xc01/tx": "", "xc01/rx": "", "xc01": PLUG}),
}
SKINS = [PLUG, SIMPLEX, DCAP, CAP, CASS6, CASS12, SHUT]

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def render(tmp, device, extra):
    vendor, name = device.split("/")
    work = tmp / name
    dev = work / "src" / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    d.setdefault("configurations", {"default": {"default": True}})
    for cfg, (bays, occ) in extra.items():
        d["configurations"][cfg] = {"kind": "example", "description": "B3 Task 10a test",
                                    **({"bays": dict(bays)} if bays else {}),
                                    "occupants": dict(occ)}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = work / "out"
    r = subprocess.run([sys.executable, str(RENDER), str(dev),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return out, name


def built_occupant(root, key):
    """The build's occupant for `key`, in test_lifted_seat_js's shape."""
    parents = {c: p for p in root.iter() for c in p}

    def chain(el):
        tfs, n = [], el
        while n is not None:
            tfs.append(n.get("transform"))
            n = parents.get(n)
        return chain_matrix(list(reversed(tfs)))
    found = [e for e in root.iter() if e.get("data-for") == key and is_occupant(e.attrib)]
    assert len(found) == 1, (key, len(found))
    occ = found[0]
    return {"ref": occ.get("data-ref").split(":")[0], "parent": parents[occ].get("data-path"),
            "transform": occ.get("transform"),
            "attrs": {k: v for k, v in occ.attrib.items() if k.startswith("data-") or k == "id"},
            "children": descendants(occ), "device": chain(occ), "parentDevice": chain(parents[occ])}


def module_rows(root, path):
    mod = next(e for e in root.iter() if e.get("data-path") == path)
    return sorted([e.get("data-path"), e.get("data-for"), e.get("id")] for e in mod.iter()
                  if e.get("data-path") or e.get("data-for"))


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("nested-slots")
    dist = tmp / "dist"
    comps = build_components(dist)
    fhd_out, fhd = render(tmp, "fs/fhd-1ufce", FHD_CONFIGS)
    dcp_out, dcp = render(tmp, "smartoptics/dcp-r-34d-cs", DCP_CONFIGS)
    wrap = {n: render(tmp, d, {})[0] for n, d in (("c40g", "casa/c40g"),
                                                    ("s9510-30xc", "ufispace/s9510-30xc"))}

    def face(out, name, cfg):
        return ET.parse(out / f"{name}.{cfg}.front.svg").getroot()
    faces = {f"fhd:{c}": face(fhd_out, fhd, c) for c in ["populated", *FHD_CONFIGS]}
    faces.update({f"dcp:{c}": face(dcp_out, dcp, c) for c in ["default", *DCP_CONFIGS]})
    faces["c40g:bdm-3plus1"] = face(wrap["c40g"], "c40g", "bdm-3plus1")
    faces["s9510-30xc:ac"] = face(wrap["s9510-30xc"], "s9510-30xc", "ac")
    meta = {n: json.loads((o / f"{n}.configs.json").read_text())
            for o, n in ((fhd_out, fhd), (dcp_out, dcp), *((o, n) for n, o in wrap.items()))}
    idx = json.loads((dist / "components.json").read_text())["components"]
    payload = {
        "components": idx,
        "faces": {k: spec_of(faces[k]) for k in ("fhd:populated", "fhd:shut", "dcp:default",
                                                   "c40g:bdm-3plus1", "s9510-30xc:ac")},
        "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot())) for r in SKINS},
        "cages": {n: m["cages"]["front"] for n, m in meta.items()},
        "bays": {n: [b for v in m["bays"].values() for b in v] for n, m in meta.items()},
        "configs": {n: m["configs"] for n, m in meta.items()},
    }
    devices = {n: tmp / n / "src" / "device.yaml" for n in meta}
    return {"faces": faces, "comps": comps, "meta": meta, "devices": devices,
            "stdin": json.dumps(payload), "out": node(json.dumps(payload))}


def node(stdin, swap=None):
    env = {**os.environ, **({"SWAP_MODULE": str(swap)} if swap else {})}
    p = subprocess.run(["node", str(SCRIPT), "scenarios"], input=stdin, capture_output=True,
                       text=True, cwd=str(SCRIPT.parent), env=env)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def scenario(world, name):
    got = world["out"][name]
    assert not (isinstance(got, dict) and "error" in got), got.get("error")
    return got


def parity(world, face, key, have):
    """Every difference between the kit's occupant and the build's, except the
    plug's `data-cp-on` markers - the rename gap Task 9 pinned, which is 10c's
    (3D cable anchors) and is held to exactly that attribute here."""
    want = built_occupant(world["faces"][face], key)
    gaps = []
    bad = mismatches([{"name": face, "built": {key: want}}],
                     [{"name": face, "seated": {key: have}}], gaps)
    # `mismatches` files a difference under `gaps` only for data-cp-on on a plug
    assert all(k == key for k, _, _ in gaps), gaps
    return bad, want


def ver(world, ref):
    return f"{ref}:{world['comps'][ref]['version']}"


# ---------------------------------------------------------------- the census

@needs_node
def test_nested_slots_reads_every_slot_off_a_real_fhd_face(world):
    c = scenario(world, "census")
    duplex = [i for i in c["all"] if re.fullmatch(r"bay-[1-4]/module/lc[1-6]", i)]
    bores = [i for i in c["all"] if re.fullmatch(r"bay-[1-4]/module/lc[1-6]/(tx|rx)", i)]
    assert len(duplex) == 24 and len(bores) == 48 and len(c["all"]) == 72, c["all"]
    # the shipped duplex cap fills every adapter slot, so its bores are hidden
    assert sorted(c["offered"]) == sorted(duplex)
    assert c["lc1"] == {**c["lc1"], "id": "bay-1/module/lc1", "key": "bay-1/lc1", "kind": "connector",
                        "default": DCAP, "bores": ["tx", "rx"], "accepts": [DCAP, PLUG],
                        "modulePath": "bay-1/module", "moduleId": "bay-1--module", "carrier": CASS6}
    assert c["tx"]["key"] == "bay-1/lc1/tx" and c["tx"]["carrier"] == "common/lc-duplex-v-adapter@5"
    assert c["tx"]["modulePath"] == "bay-1/module/lc1"
    assert c["helperSame"], "nestedSlots differs from the entry Task 9's parity was built on"
    assert c["alias"], "nestedCages is no longer an alias of nestedSlots"


@needs_node
def test_nested_slots_on_the_dcp_offers_the_capped_bores_not_the_adapter(world):
    c = scenario(world, "census")
    cages = world["meta"]["dcp-r-34d-cs"]["cages"]["front"]
    spanning = [g["id"] for g in cages if g.get("bores")]
    assert len(spanning) >= 36, spanning
    assert sorted(c["dcpAll"]) == sorted(f"{s}/{b}" for s in spanning for b in ("tx", "rx"))
    assert c["dcpHelperSame"]
    offered = set(c["dcpOffered"])
    assert not offered & set(spanning), "an adapter offered while both its bores hold caps"
    assert set(c["dcpAll"]) <= offered


# ------------------------------------------------------- the plug, swapped

@needs_node
def test_a_duplex_plug_in_place_of_the_fhd_cap_is_the_builds(world):
    s = scenario(world, "fhdPlug")
    assert s["first"] == {"applied": 1, "refused": [], "failed": []}
    bad, _ = parity(world, "fhd:plug", "bay-1/module/lc1", s["plug"])
    assert not bad, "\n".join(bad[:8])


@needs_node
def test_a_second_swap_takes_the_plug_out(world):
    """THE STACKING DEFECT. A plug carries no data-behaviour, so the kit took
    nothing out when the next swap came: cap -> plug -> cap left the plug AND
    the cap in the slot."""
    s = scenario(world, "fhdPlug")
    assert s["afterCap"] == [ver(world, DCAP)]
    assert s["afterTwoPlugs"] == [ver(world, PLUG)]
    assert s["occRef"] == PLUG
    assert s["emptied"]["applied"] == 1 and s["left"] == 0
    # the plug fills the adapter's slot, so its bores are not offered
    lc1 = [i for i in s["offeredWithPlug"] if i.startswith("bay-1/module/lc1")]
    assert lc1 == ["bay-1/module/lc1"], lc1


@needs_node
def test_no_slot_is_read_inside_a_seated_plug(world):
    """P3. The plug's halves are instances with a `data-ref`; given an index
    in which they publish boot slots, nestedSlots still reads none of them."""
    s = scenario(world, "fhdPlug")
    assert s["plugParts"] >= 2
    assert s["insidePlug"] == []


@needs_node
def test_a_click_on_the_plug_names_its_slot(world):
    s = scenario(world, "clickPlug")
    assert s["plugPart"] == "bay-1/module/lc1"
    assert s["bore"] == "bay-1/module/lc1", "a hidden bore names the level that is offered"
    assert s["options"] == [
        {"value": "", "label": "— empty —", "selected": False},
        {"value": DCAP, "label": f"{DCAP} (ships with)", "selected": False},
        {"value": PLUG, "label": PLUG, "selected": True}]


@needs_node
def test_emptying_the_adapter_offers_its_bores_and_a_simplex_plug_is_the_builds(world):
    s = scenario(world, "fhdSimplex")
    assert s["before"] == ["bay-1/module/lc1"]
    assert sorted(s["emptied"]) == ["bay-1/module/lc1", "bay-1/module/lc1/rx", "bay-1/module/lc1/tx"]
    assert sorted(s["after"]) == ["bay-1/module/lc1/rx", "bay-1/module/lc1/tx"]
    assert s["res"] == {"applied": 1, "refused": [], "failed": []}
    assert s["lc1"] == 0
    assert s["tx"]["count"] == 1, "a second simplex swap stacked"
    bad, _ = parity(world, "fhd:simplex", "bay-1/module/lc1/tx", s["tx"])
    assert not bad, "\n".join(bad[:8])


# ------------------------------------------------------------ the DCP-R

@needs_node
def test_a_plug_in_a_lifted_dcp_bore_is_the_builds(world):
    s = scenario(world, "dcpBore")
    assert sorted(s["before"]) == ["xc01/rx", "xc01/tx"]
    assert s["res"] == {"applied": 1, "refused": [], "failed": []}
    bad, want = parity(world, "dcp:tx", "xc01/tx", s["tx"])
    assert not bad, "\n".join(bad[:8])
    assert want["attrs"]["data-z-lift"] == "3.175"
    assert s["back"] == [ver(world, CAP)], "the plug stayed under the cap"
    assert s["final"] == 1


@needs_node
def test_a_duplex_plug_across_two_emptied_dcp_bores_is_the_builds(world):
    s = scenario(world, "dcpDuplex")
    assert sorted(s["oneEmpty"]) == ["xc01/rx", "xc01/tx"], "one bore still capped: no adapter level"
    assert sorted(s["bothEmpty"]) == ["xc01", "xc01/rx", "xc01/tx"]
    assert s["res"] == {"applied": 1, "refused": [], "failed": []}
    assert s["after"] == ["xc01"]
    assert s["click"] == "xc01"
    bad, _ = parity(world, "dcp:duplex", "xc01", s["xc01"])
    assert not bad, "\n".join(bad[:8])


# --------------------------------------------------- a swapped-in module

@needs_node
def test_a_module_swapped_in_carries_the_devices_keys(world):
    """THE RE-KEYING DEFECT. The compiled cassette face names its caps'
    slots in its own namespace; seated in bay-2 they must name bay-2's."""
    s = scenario(world, "rekey")
    want = module_rows(world["faces"]["fhd:swapped"], "bay-2/module")
    have = sorted(s["rows"])
    fors = [r for r in want if r[1]]
    assert len(fors) == 12, fors
    assert have == want, [r for r in have if r not in want][:6]
    for key, got in s["caps"].items():
        bad, _ = parity(world, "fhd:swapped", key, got)
        assert not bad, "\n".join(bad[:6])
    assert s["offered"] == [f"bay-2/module/lc{i:02d}" for i in range(1, 13)]
    assert s["keys"] == [f"bay-2/lc{i:02d}" for i in range(1, 13)]


@needs_node
def test_a_swap_on_a_swapped_in_module_replaces_its_shipped_cap(world):
    s = scenario(world, "rekey")
    assert s["res"] == {"applied": 1, "refused": [], "failed": []}
    assert s["lc01"] == [ver(world, PLUG)], s["lc01"]
    assert s["lc01Paths"] == [ver(world, PLUG)], "the shipped cap stayed under the plug"
    bad, _ = parity(world, "fhd:swapplug", "bay-2/module/lc01", s["plug"])
    assert not bad, "\n".join(bad[:8])


# ------------------------------------------------ the shuttered cassette

@needs_node
def test_a_shuttered_cassette_offers_plugs_and_empty_and_ships_nothing(world):
    s = scenario(world, "shuttered")
    assert s["n"] == 54 and s["filled"] == [] and s["defaults"] == [None]
    assert all("ships with" not in o["label"] for o in s["options"] + s["boreOptions"])
    assert s["options"][0] == {"value": "", "label": "— empty —", "selected": True}
    assert [o["value"] for o in s["boreOptions"][1:]] == [CAP, SIMPLEX]
    assert s["res"] == {"applied": 1, "refused": [], "failed": []}
    assert sorted(s["after"]) == ["bay-3/module/lc01/rx", "bay-3/module/lc01/tx"]
    bad, _ = parity(world, "fhd:shutplug", "bay-3/module/lc01/tx", s["tx"])
    assert not bad, "\n".join(bad[:8])


@needs_node
def test_the_select_marks_the_shipped_default(world):
    s = scenario(world, "options")
    assert s["capped"] == [
        {"value": "", "label": "— empty —", "selected": False},
        {"value": DCAP, "label": f"{DCAP} (ships with)", "selected": True},
        {"value": PLUG, "label": PLUG, "selected": False}]
    assert s["none"][0]["selected"] is True


# ------------------------------------ the drawing and the index agree

@needs_node
def test_the_resolver_reads_every_slot_the_drawing_shows(world):
    """TWO READINGS OF ONE QUESTION: nestedSlots reads the drawing, and
    slotResolver - what acceptSwaps and swapOverrides use when no face is on
    screen - reads components.json `parts`. They must name the same slots."""
    r = scenario(world, "resolver")
    assert r["fhd:populated"]["n"] == 72 and r["fhd:shut"]["n"] > 72 and r["dcp:default"]["n"] >= 72
    assert all(not v["diff"] for v in r.values()), {k: v["diff"][:4] for k, v in r.items()}


# --------------------------------------------------------- the reload

@needs_node
def test_accept_swaps_resolves_slot_keys_after_their_carrier(world):
    a = scenario(world, "accept")
    f = a["fhd"]
    assert f["accepted"] == {"bay-1": CASS12, "bay-1/module/lc01": PLUG,
                             "bay-3/module/lc1": None, "bay-3/module/lc1/tx": SIMPLEX}
    assert sorted(f["ignored"]) == ["bay-1/module/lc1", "bay-2/module/lc1/tx",
                                    "bay-4/module/lc1-occupant/a", "bay-4/module/lc1/tx",
                                    "bay-4/module/lc2"]
    assert sorted(f["cages"]) == ["bay-1/module/lc01", "bay-3/module/lc1", "bay-3/module/lc1/tx"]
    assert a["fhdOrderFree"]


@needs_node
def test_accept_swaps_on_the_dcp_needs_the_placement_and_holds_the_exclusion(world):
    a = scenario(world, "accept")
    assert a["dcpBore"]["accepted"] == {"xc01/tx": SIMPLEX}
    assert a["dcpBoreNoRef"]["ignored"] == ["xc01/tx"]
    assert a["dcpDuplexCapped"]["ignored"] == ["xc01"]
    assert a["dcpDuplexFree"]["accepted"] == {"xc01": PLUG, "xc01/rx": None, "xc01/tx": None}


# ------------------------------------------- swap=, and the 3D map

@needs_node
def test_the_delta_measures_a_slot_against_what_it_ships(world):
    d = scenario(world, "delta")
    assert d["untouched"] == {}
    assert d["emptied"] == {"bay-1/module/lc1": None}
    assert d["emptiedSwap"] == "bay-1%2Fmodule%2Flc1~"
    assert d["emptiedBack"] == {"bay-1/module/lc1": None}
    assert d["capBack"] == {}, "the shipped cap put back is no swap"
    assert d["plugged"] == {"bay-1/module/lc1": PLUG}
    assert d["simplex"] == {"bay-1/module/lc1": None, "bay-1/module/lc1/tx": SIMPLEX}
    assert d["fresh"] == {"bay-1": CASS12}, "a fresh cassette's shipped cap is no swap"
    assert d["freshEmptied"] == {"bay-1": CASS12, "bay-1/module/lc01": None}
    assert d["dcpEmptied"] == {"xc01/tx": None}
    assert d["dcpCap"] == {}
    assert d["dcpDuplex"] == {"xc01": PLUG, "xc01/rx": None, "xc01/tx": None}


@needs_node
def test_a_cassette_swapped_out_takes_its_slot_keys_with_it(world):
    p = scenario(world, "prune")
    assert p["cfgOccupants"] == {"bay-2/module/lc1": None}
    assert p["touched"] == ["bay-2/module/lc1"]
    assert p["delta"] == {"bay-1": CASS12, "bay-2/module/lc1": None}
    assert "bay-1%2Fmodule%2Flc" not in p["swap"]


@needs_node
def test_the_builds_cassette_put_back_holds_what_it_ships(world):
    p = scenario(world, "prune")
    assert p["built"] == {"bay-1/module/lc1": PLUG, "bay-1/module/lc2": None}
    assert p["back"] == {"bay-1/module/lc1": DCAP, "bay-1/module/lc2": DCAP}


@needs_node
def test_a_face_not_on_screen_forgets_what_it_held_under_a_carrier_that_left(world):
    q = scenario(world, "queue")
    assert q["calls"] == [["bay-1/module/lc01"], ["bay-1"], ["bay-1"], ["bay-1/module/lc01"]]


@needs_node
def test_a_slot_on_a_device_placement_names_its_view(world):
    v = scenario(world, "views")
    assert v["bore"] == ["front"]
    assert v["fhd"] == ["front"]


@needs_node
def test_a_configurations_deep_keys_meet_the_drawings_paths(world):
    b = scenario(world, "builtKeys")
    assert b["fhd"] == {"bay-1/module/lc1/tx": SIMPLEX, "bay-1/module/lc1": None,
                        "bay-2/module/lc3": PLUG}
    assert b["dcp"] == {"xc01/tx": None, "xc01/rx": None, "xc01": PLUG, "port-1510/tx": SIMPLEX}


@needs_node
def test_a_cage_wrappers_own_aperture_is_not_a_second_slot(world):
    """A cage wrapper publishes the aperture it composes as its own cage
    (component_cages keeps P2 to connector slots), and its host already
    publishes that aperture at the wrapper's path. Read off every [data-ref]
    group, the wrapper's would be a second select for one opening - on a
    card (`front-2/module/xg0/cage`) and on the device (`port-0/aperture`).
    A slot on a slot is kept only as one of its `bores`."""
    w = scenario(world, "wrappers")
    c40, s95 = w["c40g:bdm-3plus1"], w["s9510-30xc:ac"]
    # the c40g's card cages are every one #484's nestedCages found, and nothing else
    assert c40["oldNested"] and sorted(c40["slots"]) == sorted(c40["oldNested"])
    assert not [i for i in c40["slots"] if i.endswith("/cage")]
    assert [i for i in c40["unguarded"] if i.endswith("/cage")] == [], "a card's wrapper is caught without the device's list"
    # on the device the wrapper is caught only against the device's own list
    assert s95["device"] and s95["slots"] == []
    assert s95["unguarded"] and all(i.endswith("/aperture") for i in s95["unguarded"])


# THE FIXES, MUTATED. Each edit is applied to a copy of kit/swap.js and must
# turn the property back to the defect - with every scenario it reads still
# RUNNING: a mutant that makes a scenario throw has shown nothing about the
# property, so it does not count as caught.
MUTATIONS = [
    ("a plug is no occupant", "return !!ref && (slot.accepts || []).includes(ref);", "return false;",
     ["fhdPlug"], lambda o: len(o["fhdPlug"]["afterCap"]) == 1),
    ("rename leaves data-for", "if (to !== df) el.setAttribute('data-for', to);", "",
     ["rekey"], lambda o: o["rekey"]["lc01Paths"] == o["rekey"]["lc01"]),
    ("no exclusion", "if (filled(e)) for (const b of bores) hide.add(b.id);", "",
     ["census"], lambda o: len(o["census"]["offered"]) == 24),
    ("a slot ships nothing", "const shipped = id => R.entryAt(id)?.default ?? null;",
     "const shipped = id => null;", ["delta"], lambda o: o["delta"]["emptied"] == {"bay-1/module/lc1": None}),
    ("slots inside an occupant", "if (!modulePath || insideOccupant(mod)) continue;",
     "if (!modulePath) continue;", ["fhdPlug"], lambda o: o["fhdPlug"]["insidePlug"] == []),
    ("a slot on a slot is kept", "return !host || (host.bores || []).includes(e.cage);", "return true;",
     ["wrappers"], lambda o: o["wrappers"]["s9510-30xc:ac"]["slots"] == []),
    ("seatFace seats the offered level only", "const all = faceCages(rootEl, cages, compByRef);",
     "const all = faceCages(rootEl, cages, compByRef, {offered: true});", ["seatFace"],
     lambda o: o["seatFace"]["fhd"]["tx"]["count"] == 1 and o["seatFace"]["duplex"]["seated"]["count"] == 1),
]


@needs_node
@pytest.mark.parametrize("label,old,new,scen,holds", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_a_mutated_fix_fails(world, tmp_path, label, old, new, scen, holds):
    src = (SPEC.parent / "kit/swap.js").read_text()
    assert src.count(old) == 1, f"{label}: the anchor {old!r} is not in swap.js exactly once"
    assert holds(world["out"]), f"{label}: the property does not hold on the real kit"
    mutant = tmp_path / "swap.js"
    mutant.write_text(src.replace(old, new))
    got = node(world["stdin"], swap=mutant)
    crashed = {n: got[n]["error"][:200] for n in scen if isinstance(got[n], dict) and "error" in got[n]}
    assert not crashed, f"{label}: the mutant crashed a scenario rather than flipping it: {crashed}"
    assert not holds(got), f"{label}: the mutated kit still passes"


# ------------------------------------ seatFace: detached faces and 3D

@needs_node
def test_seat_face_seats_slot_keys_as_the_build_does(world):
    """The pass the merged tree's faces not on screen and the 3D scene run
    (seatFace -> applyFaceOverrides), given a mixed map: a cassette and a
    plug on it, one adapter level emptied and the other filled."""
    f = scenario(world, "seatFace")
    fhd = f["fhd"]
    assert fhd["res"]["refused"] == [] and fhd["res"]["failed"] == [] and fhd["res"]["dropped"] == []
    bad, _ = parity(world, "fhd:swapplug", "bay-2/module/lc01", fhd["lc01"])
    assert not bad, "\n".join(bad[:8])
    bad, _ = parity(world, "fhd:simplex", "bay-1/module/lc1/tx", fhd["tx"])
    assert not bad, "\n".join(bad[:8])
    assert fhd["lc01Paths"] == 1, "the cassette's shipped cap stayed under the plug"
    assert fhd["lc1"] == 0 and fhd["lc1Paths"] == 0, "the emptied cap is still there"
    assert fhd["stale"] == 0, "an occupant still names the cassette's own namespace"
    tx = f["tx"]
    assert tx["res"] == {"applied": 1, "refused": [], "failed": []}
    bad, _ = parity(world, "dcp:tx", "xc01/tx", tx["seated"])
    assert not bad, "\n".join(bad[:8])
    assert tx["paths"] == 1
    dx = f["duplex"]
    assert dx["res"]["refused"] == [] and dx["res"]["failed"] == []
    bad, _ = parity(world, "dcp:duplex", "xc01", dx["seated"])
    assert not bad, "\n".join(bad[:8])
    assert dx["bores"] == 0


# ------------------------- a slot inside a slot: the build and the kit agree

def _resolve():
    from portrayal.render import Library
    lib = Library([str(LIB)])

    def res(ref):
        try:
            return lib.resolve(ref)[0]
        except Exception:
            return None
    return res


@needs_node
def test_the_build_and_the_kit_answer_every_candidate_slot_alike(world):
    """ONE RULE, THREE READERS. For every slot a component publishes on a
    group these real faces draw - c40g's cards and their cage wrappers, the
    s9510's device-level wrappers, the DCP-R's adapters and bores, the FHD's
    cassettes - the kit's drawing reading (nestedSlots), its drawing-less one
    (slotResolver) and the build's (manifest.nested_key_host, which the build's
    dangling check and L12 call) accept and refuse the same keys."""
    from portrayal.manifest import nested_key_host
    res = _resolve()
    cand = scenario(world, "agree")
    cfgs = {"c40g:bdm-3plus1": ("c40g", "bdm-3plus1"), "s9510-30xc:ac": ("s9510-30xc", "ac"),
            "dcp:default": ("dcp-r-34d-cs", "default"), "fhd:populated": ("fhd-1ufce", "populated")}
    accepted, refused, differ = set(), set(), []
    for name, rows in cand.items():
        dev, cfg_name = cfgs[name]
        data = yaml.safe_load(world["devices"][dev].read_text())
        cfg = (data.get("configurations") or {"default": {}})[cfg_name] or {}
        for r in rows:
            try:
                nested_key_host(r["key"], data, cfg, res)
                build = True
            except ValueError:
                build = False
            if not (r["kit"] == r["resolver"] == build):
                differ.append((name, r["id"], r["kit"], r["resolver"], build))
            (accepted if build else refused).add(f"{name} {r['key']}")
    assert not differ, differ[:10]
    assert len(accepted) > 100 and len(refused) > 10, (len(accepted), len(refused))
    assert "s9510-30xc:ac port-0/aperture" in refused
    assert "c40g:bdm-3plus1 front-2/xg0/cage" in refused
    assert "c40g:bdm-3plus1 front-2/xg0" in accepted
    assert "dcp:default xc01/tx" in accepted and "fhd:populated bay-1/lc1/tx" in accepted


WRAPPED = [("ufispace/s9510-30xc", "ac", "port-0/aperture", "generic/qsfp-lc@1", "port-0"),
           ("casa/c40g", "bdm-3plus1", "front-2/xg0/cage", "generic/sfp-lc@1", "front-2/xg0")]


def _keyed(tmp_path, src, cfg, key, ref):
    dev = shutil.copytree(LIB / "devices" / src, tmp_path / src.split("/")[-1]) / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    d["configurations"][cfg]["occupants"] = {key: ref}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


@pytest.mark.parametrize("src,cfg,key,ref,instead", WRAPPED, ids=[w[0] for w in WRAPPED])
def test_the_build_refuses_a_key_on_a_wrappers_aperture(tmp_path, src, cfg, key, ref, instead):
    dev = _keyed(tmp_path, src, cfg, key, ref)
    r = subprocess.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(tmp_path / "out")], capture_output=True, text=True)
    assert r.returncode != 0, "the build seated an occupant in a wrapper's own aperture"
    assert f"occupants/{key}" in r.stderr and f"key {instead!r} instead" in r.stderr, r.stderr[-600:]
    # and the slot the message names is one the build does seat
    ok = _keyed(tmp_path / "ok", src, cfg, instead, ref)
    r = subprocess.run([sys.executable, str(RENDER), str(ok), "--library", str(LIB),
                        "--out", str(tmp_path / "ok-out")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]


@pytest.mark.parametrize("src,cfg,key,ref,instead", WRAPPED, ids=[w[0] for w in WRAPPED])
def test_l12_reports_a_key_on_a_wrappers_aperture(tmp_path, src, cfg, key, ref, instead):
    from portrayal import lint
    dev = _keyed(tmp_path, src, cfg, key, ref)
    with lint.collecting() as got:
        lint.lint_device_occupants(dev, yaml.safe_load(dev.read_text()), [str(LIB)])
    l12 = [e for e in got.errors if "[L12]" in e]
    assert l12 and all(f"key {instead!r} instead" in e for e in l12), l12
    ok = _keyed(tmp_path / "ok", src, cfg, instead, ref)
    with lint.collecting() as got:
        lint.lint_device_occupants(ok, yaml.safe_load(ok.read_text()), [str(LIB)])
    assert not [e for e in got.errors if "[L12]" in e]


def test_no_library_configuration_keys_a_slot_inside_a_slot():
    """The census: every configuration in the library, every nested
    `occupants:` key walked by the build's resolver, none refused as a slot
    inside a slot."""
    from portrayal.manifest import nested_key_host
    res = _resolve()
    configs = keys = 0
    bad = []
    for dev in libwalk.iter_devices([str(LIB)]):
        dev = Path(dev)
        data = yaml.safe_load(dev.read_text())
        for name, cfg in (data.get("configurations") or {}).items():
            configs += 1
            for key in ((cfg or {}).get("occupants") or {}):
                if "/" not in key:
                    continue
                keys += 1
                try:
                    nested_key_host(key, data, cfg or {}, res)
                except ValueError as e:
                    if "is the aperture the slot" in str(e):
                        bad.append((str(dev.parent.relative_to(LIB)), name, key))
    assert configs > 100, configs
    assert not bad, bad
