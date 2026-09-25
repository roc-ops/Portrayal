"""The explorer's slots on a FRONT face, in 2D (B3 Task 10a).

`nestedSlots` (kit/swap.js) reads every slot on the face off the drawing: each
`[data-ref]` group whose component publishes `cages` in components.json - a
card in a bay, a cassette, an adapter composed in either, an adapter placed on
the device - that is not inside a `data-for` group (P3). Each entry carries the
drawing path as `id` and the configuration's module-less key as `key` (P1:
`bay-1/module/lc1/1` is `bay-1/lc1/1`). The explorer offers only the free
level of a duplex adapter (L115's exclusion), marks the shipped default, and
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

import warmrender
from portrayal import libwalk
from test_lifted_seat_js import (LIB, RENDER, SPEC, build_components, chain_matrix,
                                 descendants, is_occupant, mismatches, numbers, skin_file,
                                 spec_of)

SCRIPT = SPEC / "tests/js/nested-slots.mjs"
PLUG, SIMPLEX = "generic/lc-duplex-plug@2", "generic/lc-plug@2"
DCAP, CAP = "common/lc-duplex-dust-cap@2", "common/lc-dust-cap@1"
CASS6, CASS12, SHUT = "fs/fhd-1mtp6lcd-os2-a@4", "fs/fhd-2mtp12-lc-os2-a@4", "fs/fhd-3mtp18-lc-os2-a@1"
POP = {"bay-1": CASS6, "bay-2": CASS6, "bay-3": CASS6, "bay-4": CASS6}
# THE BACKS (B3 Task 10b): two 2 x MTP-12 LC cassettes and the 36-fibre
# cassette, whose back carries three MTP bulkheads, beside one single-MTP back
MCAP, MPO12, MPO24 = "common/mpo-dust-cap@2", "generic/mpo12-plug@1", "generic/mpo24-plug@1"
MIX = {"bay-1": CASS12, "bay-2": CASS12, "bay-3": SHUT, "bay-4": CASS6}
REAR_KEYS = {"bay-1/mtp1": MPO12, "bay-2/mtp2": "", "bay-3/mtp2": MPO24}

# configuration name -> (bays, occupants) added to a tmp copy of the device
FHD_CONFIGS = {
    "plug": (POP, {"bay-1/lc1": PLUG}),
    "simplex": (POP, {"bay-1/lc1": "", "bay-1/lc1/1": SIMPLEX}),
    "swapped": ({**POP, "bay-2": CASS12}, {}),
    "swapplug": ({**POP, "bay-2": CASS12}, {"bay-2/lc01": PLUG}),
    "shut": ({**POP, "bay-3": SHUT}, {}),
    "shutplug": ({**POP, "bay-3": SHUT}, {"bay-3/lc01/1": SIMPLEX}),
    "rear": (MIX, {}),
    "rearplug": (MIX, REAR_KEYS),
}
DCP_CONFIGS = {
    "tx": (None, {"xc01/1": SIMPLEX}),
    "duplex": (None, {"xc01/1": "", "xc01/2": "", "xc01": PLUG}),
}
SKINS = [PLUG, SIMPLEX, DCAP, CAP, CASS6, CASS12, SHUT, MCAP, MPO12, MPO24]

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
    r = warmrender.run([sys.executable, str(RENDER), str(dev),
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
    # the rear face: every cassette's back, drawn as a projection in its hole
    for c in ("populated", "rear", "rearplug"):
        faces[f"fhd-rear:{c}"] = ET.parse(fhd_out / f"{fhd}.{c}.rear.svg").getroot()
    meta = {n: json.loads((o / f"{n}.configs.json").read_text())
            for o, n in ((fhd_out, fhd), (dcp_out, dcp), *((o, n) for n, o in wrap.items()))}
    idx = json.loads((dist / "components.json").read_text())["components"]
    # a back's own drawing is what applyRearOverrides imports for a module
    backs = sorted({comps[r]["faces"]["rear"] for r in (CASS6, CASS12, SHUT)})
    payload = {
        "components": idx,
        "faces": {k: spec_of(faces[k]) for k in ("fhd:populated", "fhd:shut", "dcp:default",
                                                   "c40g:bdm-3plus1", "s9510-30xc:ac",
                                                   "fhd-rear:populated", "fhd-rear:rear")},
        "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot()))
                  for r in SKINS + backs},
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
    """Every difference between the kit's occupant and the build's - a plug's
    `data-cp-on` markers included, since B3 Task 10c closed the rename gap
    Task 9 pinned."""
    want = built_occupant(world["faces"][face], key)
    bad = mismatches([{"name": face, "built": {key: want}}],
                     [{"name": face, "seated": {key: have}}])
    return bad, want


def ver(world, ref):
    return f"{ref}:{world['comps'][ref]['version']}"


# ---------------------------------------------------------------- the census

@needs_node
def test_nested_slots_reads_every_slot_off_a_real_fhd_face(world):
    c = scenario(world, "census")
    duplex = [i for i in c["all"] if re.fullmatch(r"bay-[1-4]/module/lc[1-6]", i)]
    bores = [i for i in c["all"] if re.fullmatch(r"bay-[1-4]/module/lc[1-6]/(1|2)", i)]
    assert len(duplex) == 24 and len(bores) == 48 and len(c["all"]) == 72, c["all"]
    # the shipped duplex cap fills every adapter slot, so its bores are hidden
    assert sorted(c["offered"]) == sorted(duplex)
    assert c["lc1"] == {**c["lc1"], "id": "bay-1/module/lc1", "key": "bay-1/lc1", "kind": "connector",
                        "default": DCAP, "bores": ["1", "2"], "accepts": [DCAP, PLUG],
                        "modulePath": "bay-1/module", "moduleId": "bay-1--module", "carrier": CASS6}
    assert c["tx"]["key"] == "bay-1/lc1/1" and c["tx"]["carrier"] == "common/lc-duplex-v-adapter@6"
    assert c["tx"]["modulePath"] == "bay-1/module/lc1"
    assert c["helperSame"], "nestedSlots differs from the entry Task 9's parity was built on"
    assert c["alias"], "nestedCages is no longer an alias of nestedSlots"


@needs_node
def test_nested_slots_on_the_dcp_offers_the_capped_bores_not_the_adapter(world):
    c = scenario(world, "census")
    cages = world["meta"]["dcp-r-34d-cs"]["cages"]["front"]
    spanning = [g["id"] for g in cages if g.get("bores")]
    assert len(spanning) >= 36, spanning
    assert sorted(c["dcpAll"]) == sorted(f"{s}/{b}" for s in spanning for b in ("1", "2"))
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
def test_a_seated_plugs_own_slots_are_read_at_its_chained_path(world):
    """P3, amended 2026-09-24. Given an index in which the duplex plug
    publishes a boot slot on each half, nestedSlots reads them at the plug's
    chained path and keys them as the build does (`bay-1/lc1-occupant/a`,
    nested_key_host's chained segment). The same group made a non-seat -
    `data-for` the slot but not drawn at `<slot>-occupant` - is walked no
    more than an LED is."""
    s = scenario(world, "fhdPlug")
    assert s["plugParts"] >= 2
    assert sorted(s["insidePlug"]) == ["bay-1/module/lc1-occupant/a", "bay-1/module/lc1-occupant/b"]
    assert sorted(s["insideKeys"]) == ["bay-1/lc1-occupant/a", "bay-1/lc1-occupant/b"]
    assert s["insideNonSeat"] == []


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
    assert sorted(s["emptied"]) == ["bay-1/module/lc1", "bay-1/module/lc1/1", "bay-1/module/lc1/2"]
    assert sorted(s["after"]) == ["bay-1/module/lc1/1", "bay-1/module/lc1/2"]
    assert s["res"] == {"applied": 1, "refused": [], "failed": []}
    assert s["lc1"] == 0
    assert s["tx"]["count"] == 1, "a second simplex swap stacked"
    bad, _ = parity(world, "fhd:simplex", "bay-1/module/lc1/1", s["tx"])
    assert not bad, "\n".join(bad[:8])


# ------------------------------------------------------------ the DCP-R

@needs_node
def test_a_plug_in_a_lifted_dcp_bore_is_the_builds(world):
    s = scenario(world, "dcpBore")
    assert sorted(s["before"]) == ["xc01/1", "xc01/2"]
    assert s["res"] == {"applied": 1, "refused": [], "failed": []}
    bad, want = parity(world, "dcp:tx", "xc01/1", s["tx"])
    assert not bad, "\n".join(bad[:8])
    assert want["attrs"]["data-z-lift"] == "3.175"
    assert s["back"] == [ver(world, CAP)], "the plug stayed under the cap"
    assert s["final"] == 1


@needs_node
def test_a_duplex_plug_across_two_emptied_dcp_bores_is_the_builds(world):
    s = scenario(world, "dcpDuplex")
    assert sorted(s["oneEmpty"]) == ["xc01/1", "xc01/2"], "one bore still capped: no adapter level"
    assert sorted(s["bothEmpty"]) == ["xc01", "xc01/1", "xc01/2"]
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
    assert sorted(s["after"]) == ["bay-3/module/lc01/1", "bay-3/module/lc01/2"]
    bad, _ = parity(world, "fhd:shutplug", "bay-3/module/lc01/1", s["tx"])
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
    assert r["fhd-rear:rear"]["n"] == 8, "the rear face's backs are read too (Task 10b)"
    assert all(not v["diff"] for v in r.values()), {k: v["diff"][:4] for k, v in r.items()}


# --------------------------------------------------------- the reload

@needs_node
def test_accept_swaps_resolves_slot_keys_after_their_carrier(world):
    a = scenario(world, "accept")
    f = a["fhd"]
    assert f["accepted"] == {"bay-1": CASS12, "bay-1/module/lc01": PLUG,
                             "bay-3/module/lc1": None, "bay-3/module/lc1/1": SIMPLEX}
    assert sorted(f["ignored"]) == ["bay-1/module/lc1", "bay-2/module/lc1/1",
                                    "bay-4/module/lc1-occupant/a", "bay-4/module/lc1/1",
                                    "bay-4/module/lc2"]
    assert sorted(f["cages"]) == ["bay-1/module/lc01", "bay-3/module/lc1", "bay-3/module/lc1/1"]
    assert a["fhdOrderFree"]


@needs_node
def test_accept_swaps_on_the_dcp_needs_the_placement_and_holds_the_exclusion(world):
    a = scenario(world, "accept")
    assert a["dcpBore"]["accepted"] == {"xc01/1": SIMPLEX}
    assert a["dcpBoreNoRef"]["ignored"] == ["xc01/1"]
    assert a["dcpDuplexCapped"]["ignored"] == ["xc01"]
    assert a["dcpDuplexFree"]["accepted"] == {"xc01": PLUG, "xc01/2": None, "xc01/1": None}


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
    assert d["simplex"] == {"bay-1/module/lc1": None, "bay-1/module/lc1/1": SIMPLEX}
    assert d["fresh"] == {"bay-1": CASS12}, "a fresh cassette's shipped cap is no swap"
    assert d["freshEmptied"] == {"bay-1": CASS12, "bay-1/module/lc01": None}
    assert d["dcpEmptied"] == {"xc01/1": None}
    assert d["dcpCap"] == {}
    assert d["dcpDuplex"] == {"xc01": PLUG, "xc01/2": None, "xc01/1": None}


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
    assert b["fhd"] == {"bay-1/module/lc1/1": SIMPLEX, "bay-1/module/lc1": None,
                        "bay-2/module/lc3": PLUG}
    assert b["dcp"] == {"xc01/1": None, "xc01/2": None, "xc01": PLUG, "port-1510/1": SIMPLEX}


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
    ("slots inside a non-seat", "if (!modulePath || insideOccupant(mod)) continue;",
     "if (!modulePath) continue;", ["fhdPlug"], lambda o: o["fhdPlug"]["insideNonSeat"] == []),
    ("no slot on a seat", "if (n.getAttribute('data-path') !== `${f}-occupant`) return true;",
     "return true;", ["fhdPlug"], lambda o: len(o["fhdPlug"]["insidePlug"]) == 2),
    ("a slot on a slot is kept", "return !host || (host.bores || []).includes(e.cage);", "return true;",
     ["wrappers"], lambda o: o["wrappers"]["s9510-30xc:ac"]["slots"] == []),
    # ("seatFace seats the offered level only" retired 2026-09-24: seatFace
    # now re-reads the face after each pass (applyFaceOverrides' frontier),
    # so a level emptied in one pass is offered in the next and an
    # offered-only read seats the same map. test_chained_slots_js.py mutates
    # the frontier itself.)
    # the backs (Task 10b)
    ("a back has no slots", "raw.push(...backSlotsOf(back, compByRef));", ";",
     ["rearCensus"], lambda o: len(o["rearCensus"]["ids"]) == 8),
    ("an occupant on a back is unknown", "if (!ref) return isProjectedOccupant(el, slot);",
     "if (!ref) return false;", ["rearSwap"], lambda o: o["rearSwap"]["cycle"] == [1, 1, 1, 1]),
    ("a rebuilt back keeps its own data-for", "rekeyFor(el, name, `${bayId}/module`);", "",
     ["rearModule"], lambda o: o["rearModule"]["held"] == [1] * 7),
    ("a rebuilt back names no module",
     "if (ref) hole.setAttribute('data-rear-ref', ref); else hole.removeAttribute('data-rear-ref');",
     "hole.removeAttribute('data-rear-ref');",
     ["rearModule"], lambda o: o["rearModule"]["held"] == [1] * 7),
    ("a rebuilt back drops the map's keys",
     "const occ = await applyOccupantOverrides(rootEl, slots, overrides, loadSkin);",
     "const occ = {applied: 0, refused: [], failed: []};",
     ["rearSeatFace"], lambda o: _occ_class(o["rearSeatFace"]["seatFace"]["bay-1"], "bay-1/module/mtp1") == "port"),
    ("a seat on a back is no projection", "if (cage.projection) asProjection(occ);", "",
     ["rearSwap"], lambda o: _occ_class(o["rearSwap"]["backs"]["bay-1"], "bay-1/module/mtp1") == "port"),
    ("the resolver has no backs", "if (!slot) return backEntry(path, parent, name, c);",
     "if (!slot) return null;", ["rearDelta"], lambda o: o["rearDelta"]["capBack"] == {}),
]


def _occ_class(spec, slot):
    """The data-class of what the back `spec` holds in `slot`, as the build
    projects it (`data-of` `<slot>-occupant`, no data-path), else None."""
    if spec["a"].get("data-of") == f"{slot}-occupant" and "data-path" not in spec["a"]:
        return spec["a"].get("data-class")
    return next((c for c in (_occ_class(k, slot) for k in spec["c"]) if c), None)


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
    bad, _ = parity(world, "fhd:simplex", "bay-1/module/lc1/1", fhd["tx"])
    assert not bad, "\n".join(bad[:8])
    assert fhd["lc01Paths"] == 1, "the cassette's shipped cap stayed under the plug"
    assert fhd["lc1"] == 0 and fhd["lc1Paths"] == 0, "the emptied cap is still there"
    assert fhd["stale"] == 0, "an occupant still names the cassette's own namespace"
    tx = f["tx"]
    assert tx["res"] == {"applied": 1, "refused": [], "failed": []}
    bad, _ = parity(world, "dcp:tx", "xc01/1", tx["seated"])
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
            "dcp:default": ("dcp-r-34d-cs", "default"), "fhd:populated": ("fhd-1ufce", "populated"),
            "fhd-rear:populated": ("fhd-1ufce", "populated"), "fhd-rear:rear": ("fhd-1ufce", "rear")}
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
    assert "dcp:default xc01/1" in accepted and "fhd:populated bay-1/lc1/1" in accepted
    # THE BACKS (Task 10b): every MTP bulkhead the rear draws, on two 2 x
    # MTP-12 backs, the 36-fibre cassette's three and a single-MTP back - and
    # the near misses around them, which all three refuse
    rear = {k.split(" ", 1)[1] for k in accepted if k.startswith("fhd-rear:rear ")}
    assert rear == {"bay-1/mtp1", "bay-1/mtp2", "bay-2/mtp1", "bay-2/mtp2",
                    "bay-3/mtp1", "bay-3/mtp2", "bay-3/mtp3", "bay-4/mtp"}, rear
    assert {k.split(" ", 1)[1] for k in accepted if k.startswith("fhd-rear:populated ")} == \
        {"bay-1/mtp", "bay-2/mtp", "bay-3/mtp", "bay-4/mtp"}
    near = {k.split(" ", 1)[1] for k in refused if k.startswith("fhd-rear:rear ")}
    assert {"bay-1/mtp3", "bay-4/mtp1", "bay-1/mtp1/screw-left", "bay-3/mtp"} <= near, near


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
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(tmp_path / "out")], capture_output=True, text=True)
    assert r.returncode != 0, "the build seated an occupant in a wrapper's own aperture"
    assert f"occupants/{key}" in r.stderr and f"key {instead!r} instead" in r.stderr, r.stderr[-600:]
    # and the slot the message names is one the build does seat
    ok = _keyed(tmp_path / "ok", src, cfg, instead, ref)
    r = warmrender.run([sys.executable, str(RENDER), str(ok), "--library", str(LIB),
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


# HOW MANY NESTED `occupants:` KEYS THE LIBRARY HAS TODAY: none. Two devices
# carry `occupants:` at all and neither keys a path with a slash, so the census
# below walks every configuration and checks NOTHING - it cannot fail today,
# and bites only once a configuration keys a nested path (update this figure
# then, and it checks each one). The real evidence that the library keys no
# slot inside a slot is the build: the full build and lint are unchanged by
# the refusal (task-10a-report.md, fix round).
LIBRARY_NESTED_OCCUPANT_KEYS = 0


def test_no_library_configuration_keys_a_slot_inside_a_slot():
    """The census: every configuration in the library, every nested
    `occupants:` key walked by the build's resolver, none refused as a slot
    inside a slot. See LIBRARY_NESTED_OCCUPANT_KEYS: today there are none to
    walk, and the count is pinned so that stops being silent."""
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
    assert keys == LIBRARY_NESTED_OCCUPANT_KEYS, (
        f"{keys} nested occupants: keys now (pinned {LIBRARY_NESTED_OCCUPANT_KEYS}) - "
        "the census checks them; update the figure")
    assert not bad, bad


# HOW MANY OCCUPANTS IN THE LIBRARY ARE NAMED WITH AN `id:`: none. It matters
# because the build draws an occupant under its own `id:` when it has one
# (manifest.occupant_local_id) and under `<slot>-occupant` otherwise, while the
# kit finds a seated occupant - front and back, to swap it, pull it in 3D or
# carry it out with its module - by the `<slot>-occupant` NAME alone (swap.js
# occupantNames, the rear resolver, relief's OWN_FRU). An occupant with an
# `id:` would draw correctly and be invisible to all of that, with nothing
# failing. So the count is pinned: the day one appears, this fails and the kit
# has to learn to read it first.
LIBRARY_ID_OCCUPANTS = 0


def _occupant_values():
    """(where, value) for every occupant the library names: each
    configuration's `occupants:` values, and each slot's shipped `default:` -
    a component's top-level one, its `parts:` entries', and a device
    placement's. Returns (configurations walked, [(where, value)])."""
    configs, out = 0, []
    for dev in libwalk.iter_devices([str(LIB)]):
        dev = Path(dev)
        rel = str(dev.parent.relative_to(LIB))
        data = yaml.safe_load(dev.read_text()) or {}
        for name, cfg in (data.get("configurations") or {}).items():
            configs += 1
            for key, v in ((cfg or {}).get("occupants") or {}).items():
                out.append((f"{rel} {name} occupants/{key}", v))
        for vname, view in (data.get("views") or {}).items():
            for p in (((view or {}).get("components") or {}).get("placements") or []):
                if "default" in p:
                    out.append((f"{rel} {vname}/{p.get('id')} default", p["default"]))
    for f in sorted(LIB.glob("components/*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text()) or {}
        rel = str(f.parent.relative_to(LIB / "components"))
        if "default" in c:
            out.append((f"{rel} default", c["default"]))
        for q in c.get("parts") or []:
            if "default" in q:
                out.append((f"{rel} parts/{q.get('id')} default", q["default"]))
    return configs, out


def test_no_library_occupant_is_named_with_an_id():
    """The census the kit's name-based lookup rests on: see LIBRARY_ID_OCCUPANTS."""
    configs, values = _occupant_values()
    assert configs > 100, configs
    # the shipped defaults are what the walk actually meets today - the
    # configurations key no `occupants:` at all - so it must meet some
    assert len(values) > 0, "no occupant named anywhere; this census measures nothing"
    named = [(w, v) for w, v in values if isinstance(v, dict) and "id" in v]
    assert len(named) == LIBRARY_ID_OCCUPANTS, (
        f"{len(named)} occupants named with an `id:` (pinned {LIBRARY_ID_OCCUPANTS}), "
        f"which the kit cannot find by their `<slot>-occupant` name: {named}")


# THE ONE GATE, INSIDE AN OCCUPANT TOO. generic/sfp-lc-simplex@2 is an optic
# that forwards its one LC bore, so seated in a cage it is a slot at its own
# key - `front-2/xg0-occupant` - and its `bore` is not a second one. The build
# refused `front-2/xg0-occupant/bore` while nested_key_host (and so L12)
# skipped any carrier reached through a chained occupant and passed it; both
# now ask manifest.slot_in_slot_at.
INSIDE_OCCUPANT = [
    ({"front-2/xg0": "generic/sfp-lc-simplex@2",
      "front-2/xg0-occupant/bore": "generic/lc-plug@2"}, False),
    ({"front-2/xg0": "generic/sfp-lc-simplex@2",
      "front-2/xg0-occupant": "generic/lc-plug@2"}, True),
]


@pytest.mark.parametrize("occ,ok", INSIDE_OCCUPANT, ids=["the bore", "the occupant's own key"])
def test_the_build_and_l12_answer_a_key_inside_an_occupant_alike(tmp_path, occ, ok):
    from portrayal import lint
    dev = shutil.copytree(LIB / "devices/casa/c40g", tmp_path / "c40g") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["bdm-3plus1"]["occupants"] = occ
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(tmp_path / "out")], capture_output=True, text=True)
    with lint.collecting() as got:
        lint.lint_device_occupants(dev, yaml.safe_load(dev.read_text()), [str(LIB)])
    l12 = [e for e in got.errors if "[L12]" in e]
    assert (r.returncode == 0) is ok, r.stderr[-600:]
    assert (not l12) is ok, l12
    if not ok:
        want = "key 'front-2/xg0-occupant' instead"
        assert want in r.stderr and all(want in e for e in l12), (r.stderr[-400:], l12)


# =================================================== THE BACKS (Task 10b)
#
# A seated cassette's back is drawn on the rear face as a PROJECTION of the
# module (render.py `rear:`): `data-of` in place of `data-path`, and no
# `data-ref`, `data-z-*` or `data-cp*`. Its MTP bulkheads are slots all the
# same - `bay-1/module/mtp1`, keyed `bay-1/mtp1` - and the build seats their
# shipped caps and any configured plug inside the projection group, keyed as
# every other slot is. The kit reads those slots off the drawing, seats into
# them, rebuilds a swapped module's back with its caps, and is held here to
# the real rear face of the same request.

def back_of(root, bay):
    """The projection group the build drew for `bay`'s back."""
    found = [e for e in root.iter() if e.get("id") == f"{bay}-rear"]
    assert len(found) == 1, (bay, len(found))
    return found[0]


def _tree(spec):
    """A spec with its `<style>` elements left out: the kit brings a skin's own
    stylesheet along with what it imports, where the build states the rules
    once for the drawing - the allowance `descendants` makes for a front seat.
    Nothing a style holds is read by any rule here (fake-dom keeps no text)."""
    return {"t": spec["t"], "a": spec["a"],
            "c": [_tree(k) for k in spec["c"] if k["t"] != "style"]}


def back_diff(kit, build):
    """Every difference between a back the kit holds (fake-dom spec) and the
    build's (ElementTree), as readable strings. EQUAL, attribute for
    attribute and element for element, with one allowance each way: a
    `transform` is compared as numbers (the kit writes `16`, the build
    `16.0`), and the projection's own children are matched by id rather than
    by position - the kit appends a new occupant after the parts, as it does
    on a card, where the build draws them in slot order."""
    want, kit = _tree(spec_of(build)), _tree(kit)
    out = []

    def attrs(where, ka, ba):
        for k in sorted(set(ka) | set(ba)):
            a, b = ka.get(k), ba.get(k)
            if a == b:
                continue
            if k == "transform" and a and b and len(numbers(a)) == len(numbers(b)) \
                    and all(abs(x - y) < 1e-6 for x, y in zip(numbers(a), numbers(b))) \
                    and re.sub(r"[-\d.e]+", "#", a) == re.sub(r"[-\d.e]+", "#", b):
                continue
            out.append(f"{where} [{k}]: kit {a!r} build {b!r}")

    def same(where, k, b):
        if k["t"] != b["t"]:
            out.append(f"{where}: <{k['t']}> vs <{b['t']}>")
            return
        attrs(where, k["a"], b["a"])
        if len(k["c"]) != len(b["c"]):
            out.append(f"{where}: {len(k['c'])} children vs {len(b['c'])}")
            return
        for i, (x, y) in enumerate(zip(k["c"], b["c"])):
            same(f"{where}/{y['a'].get('id') or y['t'] + str(i)}", x, y)

    def keyed(kids):
        seen, out_ = {}, {}
        for c in kids:
            k = c["a"].get("id") or f"<{c['t']}>"
            seen[k] = seen.get(k, 0) + 1
            out_[f"{k}#{seen[k]}"] = c
        return out_

    where = want["a"].get("id")
    attrs(where, kit["a"], want["a"])
    kk, bk = keyed(kit["c"]), keyed(want["c"])
    for k in sorted(set(kk) ^ set(bk)):
        out.append(f"{where}: child {k} only in the {'kit' if k in kk else 'build'}")
    for k in sorted(set(kk) & set(bk)):
        same(f"{where}/{k}", kk[k], bk[k])
    return out


def backs_match(world, face, got, bays):
    bad = []
    for bay in bays:
        bad += back_diff(got[bay], back_of(world["faces"][face], bay))
    return bad


@needs_node
def test_the_build_names_the_module_a_back_is_of(world):
    """A PROJECTION STRIPS `data-ref`, so a back alone cannot say whose it is.
    The hole it is drawn in does: the build writes the module seated in the
    bay on the rear cutout as `data-rear-ref`, and each back is that hole's
    DIRECT child - which is what the kit reads (`[data-rear-ref] >
    [data-projection]`) to look up `faces.rear`. No second attribute on the
    projection says it again."""
    root = world["faces"]["fhd-rear:rear"]
    parents = {c: p for p in root.iter() for c in p}
    got = {b: parents[back_of(root, b)].get("data-rear-ref") for b in MIX}
    assert got == MIX, got
    assert all(parents[back_of(root, b)].get("data-rear-of") == b for b in MIX)
    assert all(back_of(root, b).get("data-ref") is None for b in MIX)
    assert [e for e in root.iter() if e.get("data-of-ref")] == []


def test_every_bay_that_takes_a_module_with_a_back_says_where_it_is_seen():
    """THE KIT'S DRAWING-LESS READER ASSUMES IT. configs.json publishes no
    bay's `rear:`, so slotResolver accepts a slot on a module's back under any
    device bay; the build refuses one under a bay that shows no back
    (manifest.nested_key_host). They agree while every bay that accepts a
    module with `faces.rear` also declares `rear:` - which this pins."""
    from portrayal.manifest import view_parts
    res = _resolve()
    bays = missing = 0
    for dev in libwalk.iter_devices([str(LIB)]):
        data = yaml.safe_load(Path(dev).read_text())
        for view in (data.get("views") or {}).values():
            for b in view_parts(view)["bays"]:
                backed = [r for r in b.get("accepts") or []
                          if ((res(r) or {}).get("faces") or {}).get("rear")]
                if not backed:
                    continue
                bays += 1
                if not b.get("rear"):
                    missing += 1
    assert bays > 0, "no bay in the library takes a module with a back"
    assert missing == 0, missing


@needs_node
def test_nested_slots_reads_every_mtp_on_the_rear_face(world):
    c = scenario(world, "rearCensus")
    assert c["ids"] == ["bay-1/module/mtp1", "bay-1/module/mtp2", "bay-2/module/mtp1",
                        "bay-2/module/mtp2", "bay-3/module/mtp1", "bay-3/module/mtp2",
                        "bay-3/module/mtp3", "bay-4/module/mtp"], c["ids"]
    assert c["offered"] == c["ids"], "a back's slot is not offered"
    back12 = world["comps"][CASS12]["faces"]["rear"]
    assert c["mtp1"] == {**c["mtp1"], "id": "bay-1/module/mtp1", "key": "bay-1/mtp1",
                         "kind": "connector", "default": MCAP, "accepts": [MCAP, MPO12, MPO24],
                         "modulePath": "bay-1/module", "moduleId": "bay-1-rear",
                         "carrier": back12, "moduleRef": CASS12, "projection": True}
    # the build's shipped cap is known as what each slot holds
    assert c["held"] == [1] * 8, c["held"]
    assert c["populated"] == ["bay-1/module/mtp", "bay-2/module/mtp", "bay-3/module/mtp",
                              "bay-4/module/mtp"]
    assert c["front"] == [], "the front face grew rear slots"


@needs_node
def test_a_plug_on_a_built_back_is_the_builds(world):
    """cap -> plug, and emptying one: the three backs the kit swapped on the
    `rear` build are the `rearplug` build's, element for element."""
    s = scenario(world, "rearSwap")
    assert s["res"] == [{"applied": 1, "refused": [], "failed": []}] * 3
    bad = backs_match(world, "fhd-rear:rearplug", s["backs"], ["bay-1", "bay-2", "bay-3"])
    assert not bad, "\n".join(bad[:12])


@needs_node
def test_a_second_swap_on_a_back_takes_the_first_out(world):
    """A projected occupant has no `data-ref` and no `data-behaviour` - the
    build strips both - so the kit knows it by its name, `<slot>-occupant`."""
    s = scenario(world, "rearSwap")
    assert s["cycle"] == [1, 1, 1, 1], s["cycle"]
    assert s["emptied"] == 0
    assert s["occRef"] is None, "a projected occupant names no ref"


@needs_node
def test_a_click_on_a_back_names_its_slot(world):
    c = scenario(world, "rearClick")
    assert c["cap"] == "bay-3/module/mtp2"
    assert c["screw"] == "bay-3/module/mtp2"
    assert c["bezel"] is None
    assert c["options"] == [
        {"value": "", "label": "— empty —", "selected": False},
        {"value": MCAP, "label": f"{MCAP} (ships with)", "selected": True},
        {"value": MPO12, "label": MPO12, "selected": False},
        {"value": MPO24, "label": MPO24, "selected": False}]


@needs_node
def test_a_module_swapped_in_draws_the_builds_back_caps_and_all(world):
    """THE DEFAULTS ON A SWAPPED BACK. applyRearOverrides imports the back's
    own drawing, whose flange adapters ship their caps; those caps named the
    back's own namespace (`fhd-2mtp12-lc-rear/mtp1`), so no slot of the
    device held them and the next swap stacked. Swapped from the populated
    build to the `rear` population, the three backs are the build's."""
    s = scenario(world, "rearModule")
    assert s["applied"] == 3
    caps = [f for b in s["backs"].values() for f in _fors(b)]
    assert len(caps) == 7, caps
    bad = backs_match(world, "fhd-rear:rear", s["backs"], ["bay-1", "bay-2", "bay-3"])
    assert not bad, "\n".join(bad[:12])
    assert s["held"] == [1] * 7, s["held"]


def _fors(spec):
    own = [spec["a"]["data-for"]] if "data-for" in spec["a"] else []
    return own + [f for k in spec["c"] for f in _fors(k)]


@needs_node
def test_a_swapped_back_seats_its_keys_as_the_build_does(world):
    """The whole pass a face not on screen takes (seatFace, and the faceQueue
    that calls it), handed the cassettes AND the keys on their backs - in an
    order that puts a key before its cassette - ends as the `rearplug` build."""
    s = scenario(world, "rearSeatFace")
    for name in ("seatFace", "queue"):
        bad = backs_match(world, "fhd-rear:rearplug", s[name], ["bay-1", "bay-2", "bay-3", "bay-4"])
        assert not bad, f"{name}:\n" + "\n".join(bad[:12])
    assert s["res"]["refused"] == [] and s["res"]["failed"] == []


@needs_node
def test_rear_keys_in_the_delta_the_codec_and_the_reload(world):
    d = scenario(world, "rearDelta")
    assert d["untouched"] == {}
    assert d["capBack"] == {}, "the shipped cap put back is no swap"
    assert d["plugged"] == {"bay-1/module/mtp1": MPO12}
    assert d["emptied"] == {"bay-2/module/mtp2": None}
    assert d["swap"] == "bay-1%2Fmodule%2Fmtp1~generic%2Fmpo12-plug%401,bay-2%2Fmodule%2Fmtp2~"
    assert d["back"] == {"bay-1/module/mtp1": MPO12, "bay-2/module/mtp2": None}
    # a configuration's rear keys meet the drawing's paths, and the state
    # that holds them is no swap
    assert d["built"] == {"bay-1/module/mtp1": MPO12, "bay-2/module/mtp2": None,
                          "bay-3/module/mtp2": MPO24}
    assert d["builtDelta"] == {}
    a = d["accept"]
    assert a["accepted"] == {"bay-1": CASS12, "bay-1/module/mtp2": MPO24,
                             "bay-4/module/mtp": None}, a
    assert sorted(a["ignored"]) == ["bay-1/module/mtp", "bay-1/module/mtp1/screw-left",
                                    "bay-1/module/mtp3", "bay-2/module/mtp1"], a
    assert sorted(a["cages"]) == ["bay-1/module/mtp2", "bay-4/module/mtp"]


@needs_node
def test_swapping_or_emptying_a_cassette_drops_its_rear_keys(world):
    p = scenario(world, "rearPrune")
    assert p["swapped"] == {"bay-2/module/mtp": None}, p["swapped"]
    assert "bay-1%2Fmodule%2Fmtp" not in p["swap"] and p["swap"].startswith("bay-1~")
    assert p["emptied"] == {"bay-2/module/mtp": None}
    # the build's own cassette put back holds what it ships, on its back too
    assert p["back"] == {"bay-1/module/mtp1": MCAP}, p["back"]
    assert p["queue"] == [["bay-1/module/mtp1"], ["bay-1"], ["bay-1/module/mtp1"]]
