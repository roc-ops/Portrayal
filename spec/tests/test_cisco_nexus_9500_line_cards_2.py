"""The Cisco Nexus 9500 line cards, batch 2, and the chassis bays that take them.

Five line cards are modelled, each a component `cisco/<part number>`: the N9K-X9736C-EX, N9K-X9732C-EX,
N9K-X9736C-FX3, N9K-X9736Q-FX and N9K-X9408PC-CFP2. All three chassis guides list all five in their Overview
tables and none says a chassis does not take one of them (the one "not compatible" note, the 9516's, is about
the N9K-X9716D-GX of batch 1). The N9K-X9788TC-FX stays out, as in batch 1.

Every figure is Cisco's N9504, N9508 or N9516 NX-OS Mode Switch Hardware Installation Guide. Pages are PDF
pages with the printed page after them, six lower. The guides' Appendix A "Switch Dimensions" has one "Line
cards" row for every card (PDF p120, printed 114, in the 9504 and 9508; PDF p116, printed 110, in the 9516):
17.0 in wide, 1.75 in high, 16.5 in deep inside the chassis, ejector levers 2.5 in outside it. No held figure
shows one of these cards' own faceplate (the pages were viewed, not only read as text), so every face is "text
only" and its positions are estimated.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import devicelock

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
DEVICES = LIBRARY / "devices/cisco"
COMPONENTS = LIBRARY / "components/cisco"
EXPORTS = LIBRARY / "exports"

IN = 25.4
BLANK = "cisco/n9k-c9500-lc-cv@1"

# name: model, cages placed, the card attr the exporter reads for each cage family, weight (kg, the guide's
# printed metric figure), typical and maximum power (W), sale status, and the cards per row
CARDS = {
    "n9k-x9736c-ex": dict(model="N9K-X9736C-EX", cages={"std/qsfp28@1": 36}, attrs={"qsfp28": 36},
                          kg=6.7, typ=632, top=792, eol="end-of-sale", cols=18),
    "n9k-x9732c-ex": dict(model="N9K-X9732C-EX", cages={"std/qsfp28@1": 32}, attrs={"qsfp28": 32},
                          kg=5.5, typ=430, top=720, eol="end-of-sale", cols=16),
    "n9k-x9736c-fx3": dict(model="N9K-X9736C-FX3", cages={"std/qsfp28@1": 36}, attrs={"qsfp28": 36},
                           kg=6.7, typ=690, top=1075, eol="unknown", cols=18),
    # the guides call it a "36-port 40-Gigabit Ethernet QSFP28 line card": a QSFP28 cage running 40G, so the
    # card states `qsfp` (40G) and not `qsfp28`
    "n9k-x9736q-fx": dict(model="N9K-X9736Q-FX", cages={"std/qsfp28@1": 36}, attrs={"qsfp": 36},
                          kg=6.62, typ=571, top=684, eol="unknown", cols=18),
    "n9k-x9408pc-cfp2": dict(model="N9K-X9408PC-CFP2", cages={"std/cfp2@2": 8}, attrs={"cfp2": 8},
                             kg=5.92, typ=310, top=432, eol="unknown", cols=4),
}
IFACE = {"n9k-x9736c-ex": {"100gbase-x-qsfp28": 36},
         "n9k-x9732c-ex": {"100gbase-x-qsfp28": 32},
         "n9k-x9736c-fx3": {"100gbase-x-qsfp28": 36},
         "n9k-x9736q-fx": {"40gbase-x-qsfpp": 36},
         "n9k-x9408pc-cfp2": {"100gbase-x-cfp2": 8}}

# the four batch-1 cards; the 9516 guide says the N9K-X9716D-GX "is not compatible with this switch"
BATCH1 = {"n9k-x9736c-fx", "n9k-x97160yc-ex", "n9k-x9732c-fx", "n9k-x9716d-gx"}
# chassis -> (bays, the cards its own guide supports). Every guide's Overview table lists all five batch-2 cards:
# 9504 PDF pp8-9 (printed 2-3), 9508 PDF pp8-9 (printed 2-3), 9516 PDF pp7-8 (printed 1-2).
CHASSIS = {"9504": (4, BATCH1 | set(CARDS)), "9508": (8, BATCH1 | set(CARDS)),
           "9516": (16, (BATCH1 - {"n9k-x9716d-gx"}) | set(CARDS))}
VERSIONS = {"9504": "2.2.0", "9508": "1.2.0", "9516": "2.2.0"}


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def device(chassis):
    return yaml.safe_load((DEVICES / f"n9k-c{chassis}/device.yaml").read_text())


def lc_bays(chassis):
    return [b for b in device(chassis)["views"]["front"]["components"]["bays"] if b["id"].startswith("lc-")]


def cage_size(ref):
    name, major = ref.split("@")
    return yaml.safe_load((LIBRARY / "components" / name / f"v{major}/contract.yaml").read_text())["size"]


@pytest.fixture(params=sorted(CARDS))
def card(request):
    return request.param


# ---- identity and envelope

def test_each_card_is_a_line_card_module_at_1_0_0(card):
    c = contract(card)
    assert (c["kind"], c["class"], c["behaviour"], c["profile"]) == ("module", "line-card", "fills", "networking")
    assert c["version"] == "1.0.0"
    assert c["attrs"]["model"] == CARDS[card]["model"]
    assert c["attrs"]["role"] == "line-card"


def test_envelope_is_the_guides_line_card_row(card):
    c = contract(card)
    s = c["size"]
    assert s["w"] == pytest.approx(17.0 * IN, abs=0.05)       # 17.0 in (43.18 cm)
    assert s["h"] == pytest.approx(1.75 * IN, abs=0.05)       # 1.75 in (4.4 cm)
    assert s["d"] == pytest.approx(16.5 * IN, abs=0.05)       # 16.5 in (41.91 cm) inside the chassis
    assert set(c["size-confidence"].values()) == {"datasheet"}
    # the 2.5 in the ejector levers stand outside the chassis is not added to the depth, and the row is the class
    # row for every line card, not a row of this card
    assert "2.5 in" in c["provenance"]["depth"] and "ejector levers" in c["provenance"]["depth"]
    assert "class row" in c["provenance"]["size"]


def test_a_card_fits_the_blank_envelope_every_bay_reserves(card):
    blank = contract("n9k-c9500-lc-cv")["size"]
    s = contract(card)["size"]
    assert (s["w"], s["h"]) == (blank["w"], blank["h"])


# ---- ports

def test_each_card_places_the_cages_the_guide_names(card):
    c = contract(card)
    ports = [p for p in c["parts"] if p["group"] == "ports"]
    got = {}
    for p in ports:
        got[p["ref"]] = got.get(p["ref"], 0) + 1
    assert got == CARDS[card]["cages"]
    assert c["groups"]["ports"]["index-origin"] == 1
    assert [p["id"] for p in ports] == [f"port-{n}" for n in range(1, len(ports) + 1)]


def test_the_exporter_can_type_every_port(card):
    c = contract(card)
    for attr, n in CARDS[card]["attrs"].items():
        assert c["attrs"][attr] == n
    assert "media" in c["attrs"]
    # the exported module type has one interface per port, typed from the cage and the card's attrs
    doc = yaml.safe_load((EXPORTS / "netbox/module-types/Cisco" / f"{CARDS[card]['model']}.yaml").read_text())
    types = {}
    for i in doc["interfaces"]:
        types[i["type"]] = types.get(i["type"], 0) + 1
    assert types == IFACE[card]
    assert [i["name"] for i in doc["interfaces"]] == [f"{{module}}/port-{n}" for n in range(1, len(doc["interfaces"]) + 1)]
    nb = yaml.safe_load((EXPORTS / "nautobot/module-types/Cisco" / f"{CARDS[card]['model']}.yaml").read_text())
    assert [i["name"] for i in nb["interfaces"]] == [i["name"] for i in doc["interfaces"]]


def test_the_q_fx_runs_40g_in_a_qsfp28_cage_and_the_cfp2_card_has_eight_cfp2():
    q = contract("n9k-x9736q-fx")["attrs"]
    assert "qsfp28" not in q and q["qsfp"] == 36 and "40 Gigabit" in q["media"]
    assert "40-Gigabit Ethernet QSFP28" in contract("n9k-x9736q-fx")["provenance"]["ports"]
    k = contract("n9k-x9408pc-cfp2")["attrs"]
    assert k["cfp2"] == 8 and "CFP2" in k["media"]


def test_ports_sit_in_two_rows_inside_the_card_and_do_not_overlap(card):
    c = contract(card)
    w, h = c["size"]["w"], c["size"]["h"]
    boxes = []
    for p in c["parts"]:
        if p["group"] != "ports":
            continue
        pw = cage_size(p["ref"])
        x, y = p["at"]
        assert 0 <= x and x + pw["w"] <= w and 0 <= y and y + pw["h"] <= h, p["id"]
        boxes.append((p["id"], x, y, x + pw["w"], y + pw["h"]))
    assert len({round(b[2], 2) for b in boxes}) == 2, "two rows"
    assert len({round(b[1], 2) for b in boxes}) == CARDS[card]["cols"], "the columns the card says"
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[3] <= b[1] + 0.001 or b[3] <= a[1] + 0.001 or a[4] <= b[2] + 0.001 or b[4] <= a[2] + 0.001, (a[0], b[0])


def test_ports_are_numbered_down_each_column_odd_over_even(card):
    c = contract(card)
    ports = {p["id"]: p for p in c["parts"] if p["group"] == "ports"}
    for n in range(1, len(ports) + 1, 2):
        top, bottom = ports[f"port-{n}"], ports[f"port-{n + 1}"]
        assert top["at"][1] < bottom["at"][1]
        assert top["at"][0] == pytest.approx(bottom["at"][0], abs=0.01)
        assert top["ref"] == bottom["ref"]


# ---- lamps

def test_each_card_has_the_beacon_and_status_lamps_at_the_left(card):
    e = contract(card)["elements"]
    assert [s if isinstance(s, str) else s["name"] for s in e["bcn"]["states"]] == ["blue", "off"]
    assert [s["behavior"] for s in e["bcn"]["states"] if not isinstance(s, str)] == ["blinking"]   # flashing blue
    sts = e["sts"]["states"]
    assert [s if isinstance(s, str) else (s["name"], s.get("behavior")) for s in sts] == [
        ("green", None), ("red", "blinking"), ("amber", "blinking"), "off"]
    port_x = min(p["at"][0] for p in contract(card)["parts"] if p["group"] == "ports")
    assert e["bcn"]["at"][0] < port_x and e["sts"]["at"][0] < port_x
    assert e["bcn"]["class"] == e["sts"]["class"] == "led"


def test_one_link_triangle_per_port_between_the_rows(card):
    c = contract(card)
    ports = {p["id"]: p for p in c["parts"] if p["group"] == "ports"}
    lamps = [p for p in c["parts"] if p["group"] == "link-leds"]
    assert [p["id"] for p in lamps] == [f"link-{n}" for n in range(1, len(ports) + 1)]
    assert {p["ref"] for p in lamps} == {"common/led-arrow-sm@1"}
    half = c["size"]["h"] / 2
    top_bottom = max(q["at"][1] + cage_size(q["ref"])["h"] for q in ports.values() if q["at"][1] < half)
    bottom_top = min(q["at"][1] for q in ports.values() if q["at"][1] >= half)
    for n, lamp in enumerate(lamps, 1):
        port = ports[f"port-{n}"]
        top_row = port["at"][1] < half
        assert lamp["skin"] == ("up" if top_row else "down"), "each triangle points at its own port"
        # the lamp lies between the two rows, under its port's column
        assert port["at"][0] - 0.01 <= lamp["at"][0] and lamp["at"][0] + 2.25 <= port["at"][0] + cage_size(port["ref"])["w"] + 0.01, lamp["id"]
        assert top_bottom - 0.5 <= lamp["at"][1] and lamp["at"][1] + 2.0 <= bottom_top + 0.5, lamp["id"]
    g = c["groups"]["link-leds"]
    # the guide's Link lamp (PDF p136, printed 130, in the 9504 and 9508; PDF p132, printed 126, in the 9516)
    for word in ("green", "orange", "flashing orange", "off"):
        assert word in g["attrs"]["led-states"]


# ---- weight, power, sale status

def test_weight_and_power_are_the_cards_own_rows(card):
    a = contract(card)["attrs"]
    want = CARDS[card]
    assert a["weight-kg"] == want["kg"]
    assert (a["power-draw-typical-w"], a["power-draw-max-w"]) == (want["typ"], want["top"])
    assert a["eol"] == want["eol"]
    # The weights are the 9504 guide's "Weights and Quantities" table (PDF pp121-122, printed 115-116), and the
    # 9516 guide's (PDF p117, printed 111) where the two agree. Both tables print each row as one line, the
    # weight at the end, but a row whose label wraps (none of these five) would be read by line order. Weights:
    # X9736C-EX 14.77 lb (6.7 kg), X9732C-EX 12.13 lb (5.5 kg), X9736C-FX3 14.8 lb (6.7 kg), X9736Q-FX 14.6 lb
    # (6.62 kg), X9408PC-CFP2 13.05 lb (5.92 kg). The power figures are the "Planning for Power Requirements"
    # tables (9504 PDF pp18-20, printed 12-14; 9508 PDF pp18-19; 9516 PDF pp18-20). The tables put a card under
    # the heading of the fabric modules that support it, with the heading row's own figures on the line above:
    # each card's typical and maximum power is the pair on ITS row, read by line order past that heading, never the
    # heading's pair. The same card is listed again under another fabric-module heading with the same figures.


def test_the_ex36_weight_conflict_between_guides_is_recorded():
    p = contract("n9k-x9736c-ex")["provenance"]["weight"]
    assert "14.77 lb" in p and "11.2 lb" in p and "5.08" in p and "CONFLICT" in p


def test_the_fx3_support_note_slip_is_recorded():
    p = contract("n9k-x9736c-fx3")["provenance"]["chassis-compatibility"]
    assert "only supported in" in p and "FM-E2" in p and "9504" in p


def test_sale_status_is_stated_only_where_a_notice_says_so():
    for name, c in CARDS.items():
        p = contract(name)["provenance"]["lifecycle"]
        assert p.startswith(c["eol"]) or c["eol"] in p, name
    for name in ("n9k-x9736c-ex", "n9k-x9732c-ex"):
        assert "End-of-Sale and End-of-Life Announcement" in contract(name)["provenance"]["lifecycle"]
    for name in ("n9k-x9736c-fx3", "n9k-x9736q-fx", "n9k-x9408pc-cfp2"):
        assert contract(name)["provenance"]["lifecycle"].startswith("unknown"), name


# ---- what the prose says about the faces

def test_every_face_is_text_only_and_says_so(card):
    p = contract(card)["provenance"]
    assert "text only" in p["ports"].lower()
    assert "estimated" in p["ports"]
    assert "does not show this card" in p["skin"]
    assert "fabric module" in p["chassis-compatibility"] and "not enforced" in p["chassis-compatibility"]


def test_the_skin_draws_no_vendor_mark_and_reserves_the_logo(card):
    svg = (COMPONENTS / card / "v1/skins/default.svg").read_text()
    assert 'id="logo-zone"' in svg and 'id="logo-zone" ' in svg
    assert "cisco" not in svg.lower().replace("cisco/", "")
    assert "logo-zone" in contract(card)["elements"]
    assert "relief" not in contract(card)


def test_the_skin_has_both_ejector_levers_with_a_release_button(card):
    svg = (COMPONENTS / card / "v1/skins/default.svg").read_text()
    for part in ("ejector-left", "ejector-right", "release-left", "release-right", "bcn", "sts"):
        assert f'id="{part}"' in svg, part


# ---- the chassis bays

@pytest.mark.parametrize("chassis", sorted(CHASSIS))
def test_each_chassis_takes_the_batch_2_cards_its_guide_lists(chassis):
    n, cards = CHASSIS[chassis]
    bays = lc_bays(chassis)
    assert [b["id"] for b in bays] == [f"lc-{k}" for k in range(1, n + 1)]
    want = {BLANK} | {f"cisco/{c}@1" for c in cards}
    for b in bays:
        assert set(b["accepts"]) == want, b["id"]
        assert b["default"] == BLANK, "every bay still seats the blank"
        first = [BLANK] + [f"cisco/{c}@1" for c in
                           ("n9k-x9736c-fx", "n9k-x97160yc-ex", "n9k-x9732c-fx", "n9k-x9716d-gx") if c in cards]
        assert b["accepts"][:len(first)] == first, "the batch-2 cards follow batch 1's"
        for c in CARDS:
            assert f"cisco/{c}@1" in b["accepts"], (chassis, c)


@pytest.mark.parametrize("chassis", sorted(CHASSIS))
def test_the_bays_keep_their_geometry_and_every_configuration_keeps_the_blank(chassis):
    n, _ = CHASSIS[chassis]
    bays = lc_bays(chassis)
    for k, b in enumerate(bays):
        assert b["size"] == {"w": 431.8, "h": 44.45}
        assert b["at"][0] == pytest.approx(6.35)
        assert b["rel-pos"] == k and b["group"] == "line-cards"
    ys = [b["at"][1] for b in bays]
    assert ys == pytest.approx([ys[0] + k * 44.45 for k in range(n)], abs=0.01)
    for name, cfg in device(chassis)["configurations"].items():
        for bay, ref in (cfg.get("bays") or {}).items():
            if bay.startswith("lc-"):
                assert ref == BLANK, (name, bay)


@pytest.mark.parametrize("chassis", sorted(CHASSIS))
def test_the_chassis_lists_each_new_cards_fabric_pairing_as_not_enforced(chassis):
    d = device(chassis)
    gap = [g for g in d["gaps"] if g["what"] == "line-card-fabric-pairing"]
    assert len(gap) == 1 and "not enforced" in gap[0]["note"].lower()
    for model in (c["model"] for c in CARDS.values()):
        assert model in gap[0]["note"], model
        assert model in d["description"] or model in d["provenance"]["line-cards"]["note"], model


def test_the_fm5_notes_no_longer_say_a_named_card_is_not_modelled():
    for chassis in ("9504", "9516"):
        gap = [g for g in device(chassis)["gaps"] if g["what"] == "line-card-fabric-pairing"][0]["note"]
        assert "FM 5" in gap and "N9K-X9736Q-FX" in gap and "N9K-X9736C-FX3" in gap
        # the only card the notes still call not modelled is the N9K-X9788TC-FX
        for before in gap.split("not modelled")[:-1]:
            assert "N9K-X9788TC-FX" in before[-200:]


@pytest.mark.parametrize("chassis", sorted(CHASSIS))
def test_each_chassis_is_at_the_minor_the_lock_asked_for_and_the_lock_agrees(chassis):
    assert device(chassis)["version"] == VERSIONS[chassis]
    mine = [f for f in devicelock.check(LIBRARY) if f[0] == f"cisco/n9k-c{chassis}"]
    assert mine == []


# ---- the DCIM exports

@pytest.mark.parametrize("chassis", sorted(CHASSIS))
def test_the_device_type_export_lists_what_each_line_card_bay_accepts(chassis):
    _, cards = CHASSIS[chassis]
    for tree in ("netbox", "nautobot"):
        doc = yaml.safe_load((EXPORTS / tree / "device-types/Cisco" / f"N9K-C{chassis}.yaml").read_text())
        bays = [b for b in doc["module-bays"] if b["position"].startswith("lc-")]
        assert len(bays) == CHASSIS[chassis][0]
        for b in bays:
            listed = set(b["description"].removeprefix("Accepts: ").split(", "))
            assert listed == {"n9k-c9500-lc-cv"} | cards, (tree, b["position"])


def test_module_types_export_one_per_card():
    for name, c in CARDS.items():
        for tree in ("netbox", "nautobot"):
            assert (EXPORTS / tree / "module-types/Cisco" / f"{c['model']}.yaml").exists(), (tree, name)


# ---- the card left out

def test_the_x9788tc_fx_is_still_not_modelled_and_no_bay_accepts_it():
    # batch 1 left it out: the guides name its 48 ports three ways and no held figure shows its faceplate. The
    # pages viewed for this batch (9504 PDF pp91-93 and 136) show no faceplate of it either.
    assert not (COMPONENTS / "n9k-x9788tc-fx").exists()
    for chassis in CHASSIS:
        assert not any("x9788tc" in a for b in lc_bays(chassis) for a in b["accepts"])
    for tree in ("netbox", "nautobot"):
        assert not (EXPORTS / tree / "module-types/Cisco/N9K-X9788TC-FX.yaml").exists()
