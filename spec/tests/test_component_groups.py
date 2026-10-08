"""A card's ports carry a group and a role (#511, step A).

Groups used to exist only in a DEVICE's `groups:`, so a port on a module seated
in a bay - a routing engine's console, a sled's QSFP28 - could never say what it
was for: it was drawn with no `data-group` and no `data-group-role`, and the DCIM
module export could not mark a management port `mgmt_only`. A component now
declares `groups:` in the device shape and a part joins one with `group:`.

What these hold:

  - the schema: the component's `$defs/group` IS the device's group item (the
    two schemas are validated standalone, so the definition is copied - and
    this equality is what stops the copy drifting);
  - the drawing: a grouped part carries exactly group_side_attrs for its group,
    its own attrs winning, at any nesting depth - checked on the four built
    devices the brief names, where the RE/sled sits in a device bay (mx10008,
    asr-9903, amx3200) or in a bay of a bay (mx960: SCB -> RE);
  - a nested cage: an optic seated in a card cage takes the card group's side,
    and that difference is exactly the cage's published `occupant-attrs`;
  - the DCIM module export: a card port is typed from its EFFECTIVE attrs and a
    `management` group makes it mgmt_only;
  - lint: L17, L22, L23 and L37 read a component's groups, as warnings.
"""
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export, lint
from portrayal import render as render_mod

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
RENDER = SPEC / "tools/portrayal/render.py"

# The step-A components: the routing engines and control boards whose
# ports are management, and the AMX sled whose ports are traffic.
MIGRATED = [
    "juniper/jnp10k-re1@2", "juniper/re-s-1300@1",
    "juniper/mx2000-cb-re-v@1", "juniper/mx2008-rcb-v@1", "juniper/jnp10003-rcb@1",
    "juniper/jnp304-re@1", "juniper/mx104-re@1", "cisco/a99-rp-f@1",
    "edgecore/amx-3200-sled400@1",
]

# device -> the data-path prefixes of the seated modules migrated above.
SEATED = {
    "juniper/mx960": ("scb0/module/re/module/", "scb1/module/re/module/"),
    "juniper/mx10008": ("cb0/module/", "cb1/module/"),
    "cisco/asr-9903": ("rp-0/module/", "rp-1/module/"),
    "edgecore/amx3200": ("sled-1/module/", "sled-2/module/"),
}


def _contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}"
                           / "contract.yaml").read_text())


def _build(device_yaml, out, libs=(LIB,)):
    cmd = [sys.executable, str(RENDER), str(device_yaml), "--out", str(out)]
    for root in libs:
        cmd += ["--library", str(root)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return yaml.safe_load(Path(device_yaml).read_text())["name"]


# --- the schema -------------------------------------------------------------

def test_the_component_group_is_the_device_group():
    dev = json.loads((SPEC / "schemas/device.schema.json").read_text())
    comp = json.loads((SPEC / "schemas/component.schema.json").read_text())
    assert comp["$defs"]["group"] == dev["properties"]["groups"]["additionalProperties"]
    assert comp["properties"]["groups"]["additionalProperties"] == {"$ref": "#/$defs/group"}
    assert comp["properties"]["parts"]["items"]["properties"]["group"]["$ref"] == \
        "#/$defs/segment"


@pytest.mark.parametrize("ref", MIGRATED)
def test_every_port_part_of_a_migrated_component_joins_a_declared_group(ref):
    lib = render_mod.Library([str(LIB)])
    c = _contract(ref)
    groups = c.get("groups") or {}
    assert groups, f"{ref} declares no groups"
    ports = [p for p in c["parts"] if lib.resolve(p["ref"])[0].get("class") == "port"]
    assert ports, f"{ref} has no port part - vacuous"
    for p in ports:
        assert p.get("group") in groups, (ref, p["id"])
        assert groups[p["group"]].get("role"), (ref, p["group"])


# --- the drawing ------------------------------------------------------------

@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("built")
    names = {}
    for dev in SEATED:
        names[dev] = _build(LIB / "devices" / dev / "device.yaml", out / dev)
    return out, names


def _ports(svg):
    root = ET.parse(svg).getroot()
    return [el for el in root.iter() if el.get("data-class") == "port"]


@pytest.mark.parametrize("dev", sorted(SEATED))
def test_every_top_level_port_on_the_seated_card_carries_its_group(built, dev):
    out, names = built
    svg = out / dev / f"{names[dev]}.front.svg"
    lib = render_mod.Library([str(LIB)])
    checked = 0
    for el in _ports(svg):
        path = el.get("data-path") or ""
        prefix = next((p for p in SEATED[dev] if path.startswith(p)), None)
        if prefix is None or el.get("data-inner"):
            continue
        rest = path[len(prefix):]
        if "/" in rest:
            continue                    # a port of a port of the card - inner
        ref = el.get("data-ref").split(":")[0]
        module = next(m for m in root_modules(svg) if m.get("data-path") == prefix[:-1])
        contract = lib.resolve(module.get("data-ref").split(":")[0])[0]
        part = next(q for q in contract["parts"] if q["id"] == rest)
        grp = contract["groups"][part["group"]]
        own = render_mod.data_attrs(part.get("attrs"))
        want = {k: v for k, v in render_mod.group_side_attrs(part["group"], grp).items()
                if k not in own}
        for k, v in want.items():
            assert el.get(k) == v, (dev, path, k, el.get(k), v)
        assert el.get("data-group") and el.get("data-group-role"), (dev, path, ref)
        checked += 1
    assert checked >= 8, f"{dev}: only {checked} card ports found - vacuous"


def root_modules(svg):
    root = ET.parse(svg).getroot()
    return [el for el in root.iter()
            if el.get("data-path", "").endswith("/module") and el.get("data-ref")]


def test_the_timing_and_console_media_are_corrected(built):
    """The media correction rides with the groups: a console is rj45-serial,
    a ToD jack rj45-tod and a BITS jack rj48, where each used to inherit the
    housing's `rj45`."""
    out, names = built
    got = {}
    for el in _ports(out / "cisco/asr-9903" / f"{names['cisco/asr-9903']}.front.svg"):
        if el.get("data-path", "").startswith("rp-0/module/") and not el.get("data-inner"):
            got[el.get("data-path").rsplit("/", 1)[-1]] = el.get("data-media")
    assert got["console"] == got["aux"] == "rj45-serial"
    assert got["tod"] == "rj45-tod"
    assert got["sync-0"] == got["sync-1"] == "rj48"
    assert got["mgt-lan-0"] == "rj45"


def _card_lib(tmp_path, groups, parts):
    """A Library whose `local/card@1` is a hand-built card, everything else
    the real library."""
    lib = render_mod.Library([str(LIB)])
    skins = tmp_path / "skins"
    skins.mkdir()
    (skins / "default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><rect id="body" width="60" height="20"/></svg>')
    lib.cache["local/card@1"] = ({
        "format": 1, "kind": "module", "name": "card", "version": "1.0.0",
        "class": "line-card", "size": {"w": 60, "h": 20}, "skins": ["default"],
        "groups": groups, "parts": parts}, skins)
    return lib


def test_a_parts_own_attrs_win_over_its_group(tmp_path):
    groups = {"sfp28": {"term": "Port", "role": "traffic",
                        "attrs": {"media": "sfp28", "speed": "25g"},
                        "description": "the SFP28 block"}}
    parts = [{"ref": "std/sfp@1", "id": "p0", "at": [2, 2], "group": "sfp28"},
             {"ref": "std/sfp@1", "id": "p1", "at": [20, 2], "group": "sfp28",
              "attrs": {"speed": "10g"}},
             {"ref": "std/sfp@1", "id": "p2", "at": [40, 2]}]
    lib = _card_lib(tmp_path, groups, parts)
    g, _ = render_mod.instance_group(lib, "local/card@1", "card", [0, 0], None, None,
                                     None, None)
    by = {el.get("data-path"): el for el in g.iter() if el.get("data-path")}
    p0, p1, p2 = by["card/p0"], by["card/p1"], by["card/p2"]
    assert (p0.get("data-media"), p0.get("data-speed")) == ("sfp28", "25g")
    assert p0.get("data-group") == "sfp28" and p0.get("data-group-role") == "traffic"
    assert p0.get("data-description") == "the SFP28 block"
    assert p1.get("data-speed") == "10g", "the part's own speed must win"
    assert p1.get("data-media") == "sfp28"
    assert p2.get("data-group") is None and p2.get("data-group-role") is None
    assert p2.get("data-speed") is None


def test_a_card_group_is_the_same_map_a_device_group_writes(tmp_path):
    """ONE MAPPING: the attributes a card group writes on its part are the
    attributes the same group, declared on a device, writes on the same part
    placed there. Built both ways and compared, rather than listed."""
    groups = {"mgmt": {"term": "Port", "role": "management", "index-origin": 0,
                       "attrs": {"media": "rj45", "speed": "1g"},
                       "description": "out-of-band"}}
    part = {"ref": "common/rj45-eth@1", "id": "mgmt", "at": [2, 2], "group": "mgmt"}
    lib = _card_lib(tmp_path, groups, [part])
    g, _ = render_mod.instance_group(lib, "local/card@1", "card", [0, 0], None, None,
                                     None, None)
    on_card = next(el for el in g.iter() if el.get("data-path") == "card/mgmt")
    device = {"name": "t", "manufacturer": "Test", "model": "T", "version": "1.0.0",
              "groups": groups,
              "chassis": {"width": 60, "height": 20},
              "views": {"front": {"components": {"placements": [
                  {**part, "group": "mgmt"}]}}}}
    svg = render_mod.render_view(device, "front", device["views"]["front"], lib)
    on_device = next(el for el in svg.iter() if el.get("data-path") == "mgmt")
    keys = {"data-media", "data-speed", "data-group", "data-group-role", "data-description"}
    assert {k: on_card.get(k) for k in keys} == {k: on_device.get(k) for k in keys}
    assert on_card.get("data-group-role") == "management"


# --- a nested cage ----------------------------------------------------------

AMX = LIB / "devices/edgecore/amx3200"
SLED = LIB / "components/edgecore/amx-3200-sled400/v1"


def _seat_on_the_sled(tmp_path, drop_groups):
    """amx3200 with an optic in sled-1's port-3 on every configuration; with
    `drop_groups`, built against a copy of the sled whose groups are removed
    (a library root searched first)."""
    dev = tmp_path / "amx3200" / "device.yaml"
    shutil.copytree(AMX, dev.parent)
    d = yaml.safe_load(dev.read_text())
    for cfg in d["configurations"].values():
        cfg["occupants"] = {"sled-1/port-3": "generic/qsfp-lc@1"}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    libs = [LIB]
    if drop_groups:
        over = tmp_path / "over"
        tgt = over / "components/edgecore/amx-3200-sled400/v1"
        shutil.copytree(SLED, tgt)
        c = yaml.safe_load((tgt / "contract.yaml").read_text())
        c.pop("groups", None)
        for p in c["parts"]:
            p.pop("group", None)
        (tgt / "contract.yaml").write_text(yaml.safe_dump(c, sort_keys=False))
        libs = [over, LIB]
    name = _build(dev, tmp_path / "out", libs)
    root = ET.parse(tmp_path / "out" / f"{name}.front.svg").getroot()
    return dict(next(el for el in root.iter()
                     if el.get("data-path") == "sled-1/module/port-3-occupant").attrib)


def test_an_optic_in_a_card_cage_takes_exactly_the_published_occupant_attrs(tmp_path):
    grouped = _seat_on_the_sled(tmp_path / "a", drop_groups=False)
    bare = _seat_on_the_sled(tmp_path / "b", drop_groups=True)
    host_side = {k: v for k, v in grouped.items()
                 if k.startswith("data-") and bare.get(k) != v}
    lib = render_mod.Library([str(LIB)])
    contract = lib.resolve("edgecore/amx-3200-sled400@1")[0]
    [cage] = [c for c in render_mod.component_cages(
        contract, lib, render_mod._pluggable_families(),
        render_mod._pluggable_candidates([str(LIB)])) if c["id"] == "port-3"]
    assert host_side, "nothing differs - the check below would pass vacuously"
    assert host_side == cage["occupant-attrs"]
    assert cage["occupant-attrs"]["data-media"] == "qsfp28"
    assert grouped["data-group-role"] == "traffic"


# --- the DCIM module export -------------------------------------------------

def _module(ref):
    c = _contract(ref)
    return dcim_export.build_module({**c, "ns": ref.split("/")[0]}, "Vendor")


def test_a_card_management_port_is_mgmt_only():
    doc = _module("juniper/jnp10k-re1@2")
    by = {i["name"]: i for i in doc["interfaces"]}
    assert by["mgmt"] == {"name": "mgmt", "type": "1000base-t", "mgmt_only": True}
    # typed from the EFFECTIVE attrs: sfp at 1g is a 1G SFP, not the cage default
    assert by["mgmt-sfp"]["type"] == "1000base-x-sfp" and by["mgmt-sfp"]["mgmt_only"]
    assert by["xge-0"]["type"] == "10gbase-x-sfpp"
    # A TIMING JACK IS NOT A MANAGEMENT INTERFACE, even in a management group:
    # it exports as `other` with its function, and a device's `build` lists
    # such jacks apart from its ports and never marks them.
    for name in ("tod", "bits-0", "pps-in", "mhz-out"):
        assert by[name]["type"] == "other" and "mgmt_only" not in by[name], by[name]


def test_a_card_traffic_port_is_not_mgmt_only():
    doc = _module("edgecore/amx-3200-sled400@1")
    ifaces = doc["interfaces"]
    assert len(ifaces) == 10
    assert not any(i.get("mgmt_only") for i in ifaces)
    assert {i["type"] for i in ifaces if i["name"] not in ("port-1", "port-2")} == \
        {"100gbase-x-qsfp28"}


def test_an_ungrouped_card_exports_as_it_did():
    """A card with no groups takes no new path: its parts are its parts."""
    c = _contract("juniper/mic3-3d-10xge-sfpp@2")
    assert not c.get("groups")
    doc = _module("juniper/mic3-3d-10xge-sfpp@2")
    assert doc["interfaces"] and not any(i.get("mgmt_only") for i in doc["interfaces"])


# --- lint -------------------------------------------------------------------

def _lint(data):
    with lint.collecting() as got:
        lint.lint_component_groups("x.yaml", data, [str(LIB)])
        return list(got.errors), list(got.warnings)


def test_component_group_findings_are_warnings():
    data = {"groups": {"mgmt": {"term": "Port",
                                "attrs": {"media": "sfp-plus"}},
                       "spare": {"term": "Port", "role": "traffic"}},
            "parts": [
                {"ref": "common/rj45-eth@1", "id": "eth", "at": [0, 0], "group": "mgmt"},
                {"ref": "std/rj45@2", "id": "con", "at": [0, 0], "group": "nope"},
                {"ref": "std/usb-a@1", "id": "usb", "at": [0, 0]},
            ]}
    errors, warnings = _lint(data)
    assert errors == []
    codes = sorted(w.split("[")[1].split("]")[0] for w in warnings)
    text = "\n".join(warnings)
    assert "parts/con: group 'nope' is not declared" in text          # L17
    assert "parts/usb: a port part in no group" in text               # L17
    assert "group 'mgmt' declares media 'sfp-plus'" in text           # L22
    assert "group mgmt does not say what it is for" in text           # L37
    assert "group spare is declared and no part joins it" in text     # L37
    assert codes == ["L17", "L17", "L22", "L37", "L37"], codes


def test_a_component_with_no_groups_is_silent():
    errors, warnings = _lint({"parts": [{"ref": "std/usb-a@1", "id": "usb", "at": [0, 0]}]})
    assert errors == [] and warnings == []


@pytest.mark.parametrize("ref", MIGRATED)
def test_the_migrated_components_lint_clean(ref):
    errors, warnings = _lint(_contract(ref))
    assert errors == [] and warnings == [], warnings
