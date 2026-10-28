"""Fabric boards for the Juniper MX and Cisco ASR 9000 families, and the chassis bays that take them.

Reached in this change: the SCBE3-MX (`juniper/scbe3-mx`) and the SCBE2-MX (`juniper/scbe2-mx`), each for every SCB bay of
the MX240, MX480 and MX960 that already accepts `juniper/scb-mx@3`. The MX2000-SFB3, MX2000-SFB2-S, A99-SFC2 and SCBE-MX are
NOT modelled here and no bay accepts them (see the last test).

Figures are Juniper's MX960 Universal Routing Platform Hardware Guide (PDF dated 2025-08-19): SCBE3-MX description with
Figure 49 (PDF pp. 217-226, printed 198-207), SCBE2-MX description with Figure 50 (PDF pp. 226-232), and the MX480 guide's
SCB tables. PDF pages run 19 above the printed ones.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import devicelock

import libdata

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
COMPONENTS = LIBRARY / "components/juniper"
EXPORTS = LIBRARY / "exports"

OLD = "juniper/scb-mx@3"
MX = ["juniper/mx240", "juniper/mx480", "juniper/mx960"]

BOARDS = {
    "scbe3-mx": dict(model="SCBE3-MX", max_w=425, fabric=["1 Tbps", "1.5 Tbps"],
                     power_figures=["425", "400", "385", "295", "280", "265", "275", "260", "245"],
                     re_bay=False),
    "scbe2-mx": dict(model="SCBE2-MX", max_w=185, fabric=["480 Gbps", "340 Gbps"],
                     power_figures=["185", "160", "155"], re_bay=True),
}
NOT_REACHED = ["scbe-mx", "mx2000-sfb3-v", "mx2000-sfb2-v", "a99-sfc2"]


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def skin(name):
    return (COMPONENTS / name / "v1/skins/default.svg").read_text()


def device(slug):
    return dict(libdata.devices())[slug]


def bays(node):
    if isinstance(node, dict):
        if "id" in node and "accepts" in node:
            yield node
        for v in node.values():
            yield from bays(v)
    elif isinstance(node, list):
        for v in node:
            yield from bays(v)


def bay_ids_accepting(slug, ref):
    return {b["id"] for b in bays(device(slug).get("views", device(slug))) if ref in b["accepts"]}


@pytest.fixture(params=sorted(BOARDS))
def board(request):
    return request.param


# ---- identity, envelope, figures

def test_each_board_is_a_supervisor_module_at_1_0_0_with_its_model_as_printed(board):
    c = contract(board)
    assert (c["kind"], c["class"], c["behaviour"], c["profile"]) == ("module", "supervisor", "fills", "networking")
    assert c["version"] == "1.0.0"
    assert c["attrs"]["model"] == BOARDS[board]["model"]


def test_no_other_component_carries_the_model(board):
    owners = [ref for ref, _, doc in libdata.components() if (doc.get("attrs") or {}).get("model") == BOARDS[board]["model"]]
    assert owners == [f"juniper/{board}"]


def test_the_envelope_is_the_scb_bay_envelope_and_the_guide_figures_are_declared(board):
    c = contract(board)
    scb =yaml.safe_load((COMPONENTS / "scb-mx/v3/contract.yaml").read_text())
    assert (c["size"]["w"], c["size"]["h"]) == (scb["size"]["w"], scb["size"]["h"]) == (413.5, 29.5)
    assert c["size-confidence"] == {"w": "drawing", "h": "estimated"}
    note = c["provenance"]["size"]
    assert "datasheet" not in c["size-confidence"].values()
    for word in ("413.5", "396"):
        assert word in note


def test_scbe3_guide_size_is_stated_against_the_bay():
    note = contract("scbe3-mx")["provenance"]["size"]
    for figure in ("15.7 in", "39.87 cm", "21.2 in", "1.2 in", "13.6 lb", "6.2 kg"):
        assert figure in note, figure


def test_scbe2_guide_size_is_stated_against_the_bay():
    note = contract("scbe2-mx")["provenance"]["size"]
    for figure in ("17 in", "43.2 cm", "22 in", "1.25 in", "9.6 lb", "4.4 kg"):
        assert figure in note, figure


def test_power_max_is_the_highest_printed_figure_and_every_figure_is_declared(board):
    c = contract(board)
    assert c["attrs"]["power-draw-max-w"] == BOARDS[board]["max_w"]
    for w in BOARDS[board]["power_figures"]:
        assert w in c["provenance"]["power"], w


def test_scbe3_power_conflicts_are_named():
    note = contract("scbe3-mx")["provenance"]["power"]
    for word in ("MX960", "MX480", "MX240", "SCB 0", "SCB 1", "Power Requirements for Switch Control Boards"):
        assert word in note, word


def test_fabric_bandwidth_is_stated(board):
    c = contract(board)
    for f in BOARDS[board]["fabric"]:
        assert f in c["attrs"]["fabric-bandwidth"], f


def test_the_cli_names_and_releases_are_recorded():
    assert "SCBE3-MX-S" in contract("scbe3-mx")["provenance"]["software"]
    assert "18.4R1" in contract("scbe3-mx")["provenance"]["software"]
    assert "SCBE2" in contract("scbe2-mx")["provenance"]["software"]
    assert "13.3R1" in contract("scbe2-mx")["provenance"]["software"]


# ---- the Routing Engine slot

def test_the_scbe3_re_slot_holds_nothing_and_says_why():
    c = contract("scbe3-mx")
    assert "bays" not in c
    text = yaml.safe_dump(c)
    assert "re-s-1300@" not in text and "re-s-2000@" not in text
    note = c["provenance"]["re-bay"]
    assert "RE-S-1800" in note and "RE-S-X6" in note and "not in the library" in note
    for slug in MX:
        gaps = [g for g in device(slug)["gaps"] if g["what"] == "re-bay"]
        assert len(gaps) == 1, slug
        note = " ".join(gaps[0]["note"].split())
        assert "SCBE3-MX's Routing Engine slot holds nothing" in note
        assert "RE-S-1800 and RE-S-X6" in note and "never accepted in it" in note


def test_the_scbe2_re_bay_takes_the_two_routing_engines_the_guide_lists_that_the_library_has():
    bay = contract("scbe2-mx")["bays"]["re"]
    assert bay["accepts"] == ["juniper/re-s-1300@2", "juniper/re-s-2000@2"]
    assert bay["default"] == "juniper/re-s-1300@2"
    assert "RE-S-1800" in contract("scbe2-mx")["provenance"]["re-bay"]
    assert "RE-S-X6" in contract("scbe2-mx")["provenance"]["re-bay"]


# ---- the face

def lamp_ids(name):
    import re
    return re.findall(r'id="(led-[a-z0-9-]+)"', skin(name))


def test_scbe3_face_has_the_figure_49_lamps_ports_and_levers():
    c, svg = contract("scbe3-mx"), skin("scbe3-mx")
    assert sorted(lamp_ids("scbe3-mx")) == sorted(
        ["led-ok-fail", "led-fabric-active", "led-fabric-only", "led-link-0", "led-link-1", "led-gps"])
    refs = [p["ref"] for p in c["parts"]]
    assert refs.count("std/sfp@1") == 2 and refs.count("std/rj45@2") == 1 and len(refs) == 3
    assert 'id="lever-left"' in svg and 'id="lever-right"' in svg
    assert {"lever-left", "lever-right"} <= set(c["elements"])
    assert "estimated" in c["provenance"]["face"]


def test_scbe2_face_has_the_figure_50_lamps_ports_and_levers():
    c, svg = contract("scbe2-mx"), skin("scbe2-mx")
    assert sorted(lamp_ids("scbe2-mx")) == sorted(
        ["led-ok-fail", "led-fabric-active", "led-fabric-only", "led-link-0", "led-link-1",
         "led-bits", "led-gps", "led-uti"])
    refs = [p["ref"] for p in c["parts"]]
    assert refs.count("std/sfp@1") == 2 and refs.count("std/rj45@2") == 1 and len(refs) == 3
    assert 'id="lever-left"' in svg and 'id="lever-right"' in svg
    assert "estimated" in c["provenance"]["face"]


def test_ports_sit_inside_the_envelope_at_the_right_hand_end(board):
    c = contract(board)
    for p in c["parts"]:
        x, y = p["at"]
        assert 300 < x < 413.5 - 8 and 0 <= y < 29.5, p["id"]


@pytest.mark.parametrize("name", sorted(BOARDS))
def test_the_skin_draws_no_vendor_mark_and_uses_the_model_text_only(name):
    svg = skin(name)
    assert "<image" not in svg and "data:image" not in svg
    assert "JUNIPER" not in svg.upper()
    assert BOARDS[name]["model"] in svg
    assert contract(name)["elements"]["logo-zone"]["class"] == "label"


# ---- which bays take the boards

@pytest.mark.parametrize("slug", MX)
def test_every_scb_bay_takes_each_new_board_and_still_the_old_one(slug, board):
    old = bay_ids_accepting(slug, OLD)
    assert old, slug
    assert bay_ids_accepting(slug, f"juniper/{board}@1") == old


@pytest.mark.parametrize("slug", MX)
def test_defaults_are_unchanged(slug):
    for b in bays(device(slug).get("views", device(slug))):
        for board in BOARDS:
            assert b.get("default") != f"juniper/{board}@1"


def test_no_other_device_accepts_a_new_board():
    for slug, doc in libdata.devices():
        if slug in MX:
            continue
        for b in bays(doc.get("views", doc)):
            for board in BOARDS:
                assert f"juniper/{board}@1" not in b["accepts"], (slug, b["id"])


@pytest.mark.parametrize("slug", MX)
def test_line_card_re_and_power_bays_do_not_take_a_board(slug):
    scb = bay_ids_accepting(slug, OLD)
    shared = {"scb1-dpc0", "fpc6"}
    for b in bays(device(slug).get("views", device(slug))):
        if b["id"] in scb and b["id"] not in shared:
            continue
        # the shared slots take a line card too: the board is there by the guide, not by being a line card
        listed = {a for a in b["accepts"] if any(a.startswith(f"juniper/{n}@") for n in BOARDS)}
        assert listed == (set(f"juniper/{n}@1" for n in BOARDS) if b["id"] in scb else set()), b["id"]


@pytest.mark.parametrize("slug", MX)
def test_every_bay_that_took_a_board_before_still_takes_it(slug):
    assert bay_ids_accepting(slug, OLD)


def test_the_not_reached_boards_are_not_modelled_and_no_bay_accepts_them():
    for name in NOT_REACHED:
        for ns in ("juniper", "cisco"):
            assert not (LIBRARY / "components" / ns / name).exists(), name
    text = " ".join(str(doc) for _, doc in libdata.devices())
    for name in NOT_REACHED:
        assert f"/{name}@" not in text, name


# ---- what the chassis say

@pytest.mark.parametrize("slug", ["juniper/mx240", "juniper/mx480"])
def test_the_chassis_no_longer_says_only_the_scb_mx_is_accepted(slug):
    d = device(slug)
    gap = [g for g in d["gaps"] if g["what"] == "current-generation-frus"]
    assert len(gap) == 1
    assert "only the SCB-MX is accepted" not in " ".join(gap[0]["wanted"].split())
    assert "SCBE2-MX and SCBE3-MX" in " ".join(gap[0]["wanted"].split())


@pytest.mark.parametrize("slug", MX)
def test_the_chassis_says_pairing_and_no_mixing_are_not_enforced(slug):
    d = device(slug)
    gap = [g for g in d["gaps"] if g["what"] == "scb-generation-pairing"]
    assert len(gap) == 1
    note = gap[0]["note"]
    assert "not enforced" in note.lower()
    assert "SCBE3-MX" in note and "previous generation" in note and "SCBE2-MX" in note


@pytest.mark.parametrize("slug", MX)
def test_chassis_versions_and_locks(slug):
    d = device(slug)
    assert d["version"] == VERSIONS[slug]
    assert [f for f in devicelock.check(LIBRARY) if f[0] == slug] == []


VERSIONS = {"juniper/mx240": "6.1.0", "juniper/mx480": "7.1.0", "juniper/mx960": "5.1.0"}


# ---- the DCIM exports

@pytest.mark.parametrize("tree", ["netbox", "nautobot"])
def test_one_module_type_per_board(tree, board):
    f = EXPORTS / tree / "module-types/Juniper" / f"{BOARDS[board]['model']}.yaml"
    assert f.exists()
    assert yaml.safe_load(f.read_text())["model"] == BOARDS[board]["model"]


@pytest.mark.parametrize("tree", ["netbox", "nautobot"])
@pytest.mark.parametrize("slug", MX)
def test_the_device_type_export_lists_the_boards_in_the_scb_bays(tree, slug):
    chassis = slug.split("/")[1].upper()
    doc = yaml.safe_load((EXPORTS / tree / "device-types/Juniper" / f"{chassis}.yaml").read_text())
    scb = bay_ids_accepting(slug, OLD)
    seen = 0
    for b in doc["module-bays"]:
        if b["position"] in scb:
            assert "scb-mx" in b["description"]
            if "more)" in b["description"]:   # the shared slots' long lists are cut by the exporter
                continue
            seen += 1
            for board in BOARDS:
                assert board in b["description"].removeprefix("Accepts: ").split(", ")
    assert seen >= 1
