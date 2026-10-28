"""The Cisco Nexus 9500 line cards, batch 1, and the chassis bays that take them.

Four line cards are modelled here (five more in batch 2), each a component `cisco/<part number>`: the N9K-X9736C-FX, N9K-X97160YC-EX,
N9K-X9732C-FX and N9K-X9716D-GX. The N9K-X9788TC-FX is NOT modelled: the guides call its 48 ports an SFP+
port, a BASE-T port and just a 10G port, and no held figure shows its faceplate (see the last test).

Every figure is Cisco's N9504, N9508 or N9516 NX-OS Mode Switch Hardware Installation Guide. Pages are PDF
pages with the printed page after them, six lower. The guides' Appendix A "Switch Dimensions" has one "Line
cards" row for every card (PDF p120, printed 114, in the 9504 and 9508; PDF p116, printed 110, in the 9516):
17.0 in wide, 1.75 in high, 16.5 in deep inside the chassis, ejector levers 2.5 in outside it. No held figure
shows one of these cards' own faceplate, so every face is "text only" and its positions are estimated.
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
# printed metric figure), typical and maximum power (W), sale status
CARDS = {
    "n9k-x9736c-fx": dict(model="N9K-X9736C-FX", cages={"std/qsfp28@1": 36}, attrs={"qsfp28": 36},
                          kg=6.5, typ=607, top=900, eol="unknown", cols=18),
    "n9k-x97160yc-ex": dict(model="N9K-X97160YC-EX", cages={"std/sfp-ganged@1": 48, "std/qsfp28@1": 4},
                            attrs={"sfp28": 48, "qsfp28": 4}, kg=5.78, typ=415, top=516, eol="unknown", cols=24),
    "n9k-x9732c-fx": dict(model="N9K-X9732C-FX", cages={"std/qsfp28@1": 32}, attrs={"qsfp28": 32},
                          kg=6.8, typ=520, top=840, eol="end-of-sale", cols=16),
    "n9k-x9716d-gx": dict(model="N9K-X9716D-GX", cages={"std/qsfp-dd@1": 16}, attrs={"qsfp-dd": 16},
                          kg=6.8, typ=650, top=1680, eol="unknown", cols=8),
}
IFACE = {"n9k-x9736c-fx": {"100gbase-x-qsfp28": 36},
         "n9k-x97160yc-ex": {"25gbase-x-sfp28": 48, "100gbase-x-qsfp28": 4},
         "n9k-x9732c-fx": {"100gbase-x-qsfp28": 32},
         "n9k-x9716d-gx": {"400gbase-x-qsfpdd": 16}}

# chassis -> (bays, the cards its own guide supports). The 9516 guide's Overview says the N9K-X9716D-GX "is not
# compatible with this switch" (PDF p7, printed 1), so its bays do not accept it.
# The five cards of batch 2 (test_cisco_nexus_9500_line_cards_2.py) are accepted by all three chassis, so each
# bay accepts the blank, these four and those five.
BATCH2 = {"n9k-x9736c-ex", "n9k-x9732c-ex", "n9k-x9736c-fx3", "n9k-x9736q-fx", "n9k-x9408pc-cfp2"}
CHASSIS = {"9504": (4, set(CARDS) | BATCH2), "9508": (8, set(CARDS) | BATCH2),
           "9516": (16, (set(CARDS) - {"n9k-x9716d-gx"}) | BATCH2)}
VERSIONS = {"9504": "2.2.0", "9508": "1.2.0", "9516": "2.2.0"}


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def device(chassis):
    return yaml.safe_load((DEVICES / f"n9k-c{chassis}/device.yaml").read_text())


def lc_bays(chassis):
    return [b for b in device(chassis)["views"]["front"]["components"]["bays"] if b["id"].startswith("lc-")]


@pytest.fixture(params=sorted(CARDS))
def card(request):
    return request.param


def parts_of(c, prefix):
    return [p for p in c["parts"] if p["id"].startswith(prefix)]


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


def test_ports_sit_in_two_rows_inside_the_card_and_do_not_overlap(card):
    c = contract(card)
    w, h = c["size"]["w"], c["size"]["h"]
    boxes = []
    for p in c["parts"]:
        if p["group"] != "ports":
            continue
        ref = p["ref"].split("@")[0]
        pw = yaml.safe_load((LIBRARY / "components" / ref / "v1/contract.yaml").read_text())["size"]
        x, y = p["at"]
        assert 0 <= x and x + pw["w"] <= w and 0 <= y and y + pw["h"] <= h, p["id"]
        boxes.append((p["id"], x, y, x + pw["w"], y + pw["h"]))
    assert len({round(b[2], 2) for b in boxes}) <= 4, "two rows (the QSFP28 cages are a little taller than an SFP's)"
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


def test_the_x97160yc_ex_has_48_sfp28_then_4_qsfp28_to_the_right():
    c = contract("n9k-x97160yc-ex")
    sfp = [p for p in c["parts"] if p["ref"] == "std/sfp-ganged@1"]
    qsfp = [p for p in c["parts"] if p["ref"] == "std/qsfp28@1"]
    assert [p["id"] for p in sfp] == [f"port-{n}" for n in range(1, 49)]
    assert [p["id"] for p in qsfp] == [f"port-{n}" for n in range(49, 53)]
    assert max(p["at"][0] for p in sfp) < min(p["at"][0] for p in qsfp)


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
    for n, lamp in enumerate(lamps, 1):
        port = ports[f"port-{n}"]
        top_row = port["at"][1] < c["size"]["h"] / 2
        assert lamp["skin"] == ("up" if top_row else "down"), "each triangle points at its own port"
        # the lamp lies between the two rows, under its port's column
        port_w = yaml.safe_load((LIBRARY / "components" / port["ref"].split("@")[0] / "v1/contract.yaml").read_text())["size"]["w"]
        assert port["at"][0] - 0.01 <= lamp["at"][0] and lamp["at"][0] + 2.25 <= port["at"][0] + port_w + 0.01, lamp["id"]
        top_bottom = max(q["at"][1] + 10.15 for q in ports.values() if q["at"][1] < c["size"]["h"] / 2)
        bottom_top = min(q["at"][1] for q in ports.values() if q["at"][1] >= c["size"]["h"] / 2)
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
    # The weights are the 9504 guide's "Weights and Quantities" table (PDF pp121-122, printed 115-116). Its rows
    # print the weight BEFORE the component, so each weight is read by line order, the component on the next cell:
    # the X97160YC-EX 12.75 lb (5.78 kg), X9736C-FX 14.38 lb (6.5 kg; the 9516 guide says 14.6 lb, 6.62 kg),
    # X9732C-FX 15.0 lb (6.8 kg), X9716D-GX 15.2 lb (6.8 kg: 15.2 lb is 6.89 kg, the printed metric is used).
    # The power figures are the "Planning for Power Requirements" tables (9504 PDF pp17-20). The X97160YC-EX row
    # splits its label across two lines ("... and 4-port -" / "40/100-Gigabit ... (N9K-X97160YC-EX)"), so its
    # 415 W / 516 W is read by line order, as is the figure under each fabric-module heading row; the same card
    # is listed again under the -G heading with the same figures.


def test_the_gx_weight_is_not_the_conversion_of_its_pounds():
    # the guide prints 15.2 lb (6.8 kg); the provenance records the disagreement and the metric figure is used
    assert "15.2 lb" in contract("n9k-x9716d-gx")["provenance"]["weight"]
    assert "6.89" in contract("n9k-x9716d-gx")["provenance"]["weight"]


def test_the_fx36_weight_conflict_between_guides_is_recorded():
    p = contract("n9k-x9736c-fx")["provenance"]["weight"]
    assert "14.38 lb" in p and "14.6 lb" in p and "6.62" in p


def test_sale_status_is_stated_only_where_a_notice_says_so():
    for name, c in CARDS.items():
        p = contract(name)["provenance"]["lifecycle"]
        assert p.startswith(c["eol"]) or c["eol"] in p, name
    assert "unknown" in contract("n9k-x9736c-fx")["provenance"]["lifecycle"]
    assert "End-of-Sale and End-of-Life Announcement" in contract("n9k-x9732c-fx")["provenance"]["lifecycle"]


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
def test_line_card_bays_accept_the_blank_and_the_cards_their_guide_supports(chassis):
    n, cards = CHASSIS[chassis]
    bays = lc_bays(chassis)
    assert [b["id"] for b in bays] == [f"lc-{k}" for k in range(1, n + 1)]
    want = {BLANK} | {f"cisco/{c}@1" for c in cards}
    for b in bays:
        assert set(b["accepts"]) == want, b["id"]
        assert b["default"] == BLANK, "every bay still seats the blank"
    if chassis == "9516":
        assert not any("x9716d-gx" in a for b in bays for a in b["accepts"]), "PDF p7 (printed 1): not compatible"
    else:
        assert all("cisco/n9k-x9716d-gx@1" in b["accepts"] for b in bays)


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
def test_the_chassis_says_the_fabric_needs_are_not_enforced(chassis):
    d = device(chassis)
    assert "line-cards-not-here" not in d["provenance"]
    gap = [g for g in d["gaps"] if g["what"] == "line-card-fabric-pairing"]
    assert len(gap) == 1 and gap[0]["scope"] == ["line-cards"]
    assert "not enforced" in gap[0]["note"].lower()
    assert "ACI-mode line cards with NX-OS mode" in gap[0]["note"]
    assert "floor" not in " ".join(g["note"] for g in d["gaps"] if g["what"] == "chassis-power-figure")


def test_only_the_9504_and_9516_carry_the_fm5_note_and_the_9516_the_gx_note():
    assert "FM 5" in device("9504")["provenance"]["fabric-slots"]["note"]
    assert "X9716D-GX" in " ".join(g["note"] for g in device("9516")["gaps"] if g["what"] == "line-card-fabric-pairing")
    assert "not compatible" in device("9516")["provenance"]["line-cards"]["note"]


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


def test_module_types_export_one_per_card_and_none_for_the_card_left_out():
    for name, c in CARDS.items():
        for tree in ("netbox", "nautobot"):
            assert (EXPORTS / tree / "module-types/Cisco" / f"{c['model']}.yaml").exists(), (tree, name)
    for tree in ("netbox", "nautobot"):
        assert not (EXPORTS / tree / "module-types/Cisco/N9K-X9788TC-FX.yaml").exists()


# ---- the card left out

def test_the_x9788tc_fx_is_not_modelled_and_no_bay_accepts_it():
    # The 9504 guide calls its 48 ports "10-Gigabit Ethernet SFP+" (power table), "1/100 BASE-T" (the -G power
    # table) and "10-Gigabit Ethernet" (weights); the 9516 guide says "10-Gigabit Ethernet SFP+"; the 9508's
    # show-inventory example says "48x10G + 4x40/100G". No held figure shows its faceplate, so it is left out.
    assert not (COMPONENTS / "n9k-x9788tc-fx").exists()
    for chassis in CHASSIS:
        assert not any("x9788tc" in a for b in lc_bays(chassis) for a in b["accepts"])
