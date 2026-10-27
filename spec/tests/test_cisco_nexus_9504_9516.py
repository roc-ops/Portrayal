"""The Cisco Nexus 9504 and 9516 chassis and the parts only they take (Nexus 9500 chassis, batch 2).

Every figure here is Cisco's N9504 or N9516 NX-OS Mode Switch Hardware Installation Guide: Appendix A "Switch
Dimensions" for the envelopes, the "Overview" for the slots and what each takes, and the chassis's own table in
"Planning for Power Requirements" for the power figures (the guide's first table is a copy of the 9508's). Pages
are PDF pages, and the printed page is six lower. The line cards are a later batch, so each line-card slot takes
only the line-card blank here. The eleven parts shared with the 9508 are referenced by id, never redrawn.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/cisco"
COMPONENTS = ROOT / "library/components/cisco"
EXPORTS = ROOT / "library/exports"

IN = 25.4

SUPERVISORS = ["n9k-sup-a", "n9k-sup-a-plus", "n9k-sup-b", "n9k-sup-b-plus"]
SUPPLIES = ["n9k-pac-3000w-b", "n9k-puv-3000w-b", "n9k-puv2-3000w-b", "n9k-pdc-3000w-b"]
SHARED = SUPERVISORS + ["n9k-sc-a"] + SUPPLIES + ["n9k-psu-blank", "n9k-c9500-lc-cv"]

FANS = {"9504": ["n9k-c9504-fan", "n9k-c9504-fan2"], "9516": ["n9k-c9516-fan"]}
FABRICS = {"9504": ["n9k-c9504-fm", "n9k-c9504-fm-s", "n9k-c9504-fm-e", "n9k-c9504-fm-g", "n9k-c9504-fm-r"],
           "9516": ["n9k-c9516-fm", "n9k-c9516-fm-e", "n9k-c9516-fm-e2"]}
BLANKS = {"9504": ["n9k-c9504-fm-cv", "n9k-c9504-fan-pwr"], "9516": ["n9k-c9516-fm-cv", "n9k-c9516-fm-z"]}
NEW = {k: FANS[k] + FABRICS[k] + BLANKS[k] for k in FANS}

LINE_CARDS = {"9504": 4, "9516": 16}
SUPPLY_BAYS = {"9504": 4, "9516": 10}
HEIGHT = {"9504": 7 * 44.45, "9516": 21 * 44.45}      # 311.15 and 933.45 mm: the guide's own RU counts


@pytest.fixture(scope="module", params=["9504", "9516"])
def chassis(request):
    return request.param


def load(chassis):
    return yaml.safe_load((DEVICES / f"n9k-c{chassis}/device.yaml").read_text())


@pytest.fixture(scope="module")
def device(chassis):
    return load(chassis)


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def bays(device, face):
    return device["views"][face]["components"]["bays"]


def by_id(device, face):
    return {b["id"]: b for b in bays(device, face)}


def refs(names):
    return {f"cisco/{n}@1" for n in names}


def seated(device, config):
    out = {}
    for face in ("front", "rear"):
        for b in bays(device, face):
            if b.get("default"):
                out[b["id"]] = b["default"]
    for bay, ref in (device["configurations"][config].get("bays") or {}).items():
        out[bay] = ref
    return {b: r for b, r in out.items() if r}


# ---- the chassis envelope

def test_envelope_is_the_guides_dimension_table(device, chassis):
    c = device["chassis"]
    assert c["width"] == pytest.approx(17.5 * IN, abs=0.1)
    assert c["height"] == pytest.approx(HEIGHT[chassis], abs=0.01)
    assert c["ru"] == (7 if chassis == "9504" else 21)
    # 9504: 33.15 in (84.20 cm) "for chassis and handles"; 9516: 31.76 in (80.67 cm), the same wording
    assert c["depth"] == pytest.approx((33.15 if chassis == "9504" else 31.76) * IN, abs=0.1)


def test_chassis_weight_is_the_weights_table(device, chassis):
    # 9504 PDF p120 (printed 114): 84.0 lb (38.2 kg); 9516 PDF p116 (printed 110): 192.0 lb (87.3 kg)
    assert device["chassis"]["weight-kg"] == (38.2 if chassis == "9504" else 87.3)


def test_the_fully_loaded_figure_is_an_attribute_not_the_chassis_weight(device, chassis):
    # 9504 PDF p34 (printed 28), the lift tool: "a maximum of 255 pounds [116 kg]"; 9516 PDF p35 (printed 29): 568 lb
    kg = device["attrs"]["physical"]["weight-fully-loaded-kg"]
    assert kg == (116 if chassis == "9504" else 258)
    assert kg != device["chassis"]["weight-kg"]


def test_identity_follows_the_nexus_naming(device, chassis):
    assert device["manufacturer"] == "Cisco"
    assert device["model"] == f"N9K-C{chassis}"
    assert {"name": f"Nexus {chassis}", "kind": "marketing"} in device["aliases"]
    assert device["portfolio"] == {"line": "Nexus 9000", "family": "Nexus 9500", "series": "Nexus 9500 Series"}
    assert [r for r in device["views"]["front"]["regions"] if r["id"] == "logo-zone"]


def test_no_ear_is_drawn_and_the_shipped_position_is_flush(device):
    placed = [p["ref"] for v in device["views"].values()
              for p in (v.get("components") or {}).get("placements", [])]
    assert "common/rack-ear@1" not in placed
    positions = device["chassis"]["ears"]["positions"]
    assert [p["name"] for p in positions if p.get("default")] == ["flush"]
    assert all("at" not in p for p in positions), "no figure gives the bracket's depth position"
    assert "kits" not in device["chassis"], "the rack kit is a follow-up: the shared kit still says unplaced"


def test_the_gaps_the_reviews_asked_for_are_recorded(device):
    whats = {g["what"] for g in device["gaps"]}
    assert {"bracket-width", "rack-kit", "dc-supply-input-lamps", "supervisor-and-controller-slot-blanks",
            "no-flat-views"} <= whats
    bracket = next(g for g in device["gaps"] if g["what"] == "bracket-width")
    assert "19.2 in" in bracket["note"]


# ---- the sale status, where a notice says so

def test_chassis_sale_status_is_stated_only_where_a_notice_says_so():
    # the support page has no Nexus 9504 entry: unknown, so the device states nothing
    assert "eol" not in load("9504")["attrs"].get("lifecycle", {})
    nine516 = load("9516")["attrs"]["lifecycle"]
    assert nine516["eol"] == "announced"
    assert nine516["eol-announcement"].endswith("n9500-cloud-16-slot-chassis-comp-eol.html")
    assert "end-of-sale" not in nine516, "the notice's date is not held"


def test_part_sale_status_is_stated_only_where_the_notice_says_so():
    eos = {"n9k-c9504-fm", "n9k-c9504-fm-s", "n9k-c9516-fm"}
    for name in NEW["9504"] + NEW["9516"]:
        want = "end-of-sale" if name in eos else "unknown"
        assert contract(name)["attrs"]["eol"] == want, name


# ---- slot and bay counts, numbering, per face

def test_front_slots_and_numbering(device, chassis):
    front = by_id(device, "front")
    n_lc, n_ps = LINE_CARDS[chassis], SUPPLY_BAYS[chassis]
    assert [i for i in front if i.startswith("lc-")] == [f"lc-{n}" for n in range(1, n_lc + 1)]
    assert [i for i in front if i.startswith("sup-")] == ["sup-1", "sup-2"]
    assert [i for i in front if i.startswith("ps-")] == [f"ps-{n}" for n in range(1, n_ps + 1)]
    assert len(front) == n_lc + 2 + n_ps                  # 10 and 28
    ys = [front[f"lc-{n}"]["at"][1] for n in range(1, n_lc + 1)]
    assert ys == sorted(ys), "the line cards run top to bottom"
    assert front["sup-1"]["at"][0] < front["sup-2"]["at"][0], "SUP 1 is left of SUP 2"
    xs = [front[f"ps-{n}"]["at"][0] for n in range(1, n_ps + 1)]
    assert xs == sorted(xs), "the supplies run left to right"


def test_rear_slots_and_numbering(device):
    rear = by_id(device, "rear")
    assert [i for i in rear if i.startswith("fan-")] == ["fan-1", "fan-2", "fan-3"]
    assert [i for i in rear if i.startswith("fm-")] == [f"fm-{n}" for n in range(1, 7)]
    assert [i for i in rear if i.startswith("sc-")] == ["sc-1", "sc-2"]
    assert len(rear) == 11
    for prefix, n in (("fan", 3), ("fm", 6), ("sc", 2)):
        xs = [rear[f"{prefix}-{k}"]["at"][0] for k in range(1, n + 1)]
        assert xs == sorted(xs), f"{prefix} numbering runs left to right"


def test_the_dcim_bay_counts(chassis, device):
    assert len(bays(device, "front")) + len(bays(device, "rear")) == (21 if chassis == "9504" else 39)


def test_a_fabric_slot_sits_behind_the_fan_tray_that_covers_it(device):
    rear = by_id(device, "rear")
    for k in range(1, 7):
        fan = rear[f"fan-{(k + 1) // 2}"]
        fm = rear[f"fm-{k}"]
        assert fm["under"] == f"fan-{(k + 1) // 2}"
        assert fan["at"][0] <= fm["at"][0] and fm["at"][0] + fm["size"]["w"] <= fan["at"][0] + fan["size"]["w"]


def test_each_face_has_its_groups_in_index_origin_one(device):
    for g in ("line-cards", "supervisors", "system-controllers", "fabric", "fan-trays", "power-supplies"):
        assert device["groups"][g]["index-origin"] == 1


def test_the_fan_tray_group_is_two_plus_one(device):
    # 9504 PDF p96 (printed 90) and 9516 PDF p89 (printed 83): "can operate with two fan trays while you replace one"
    assert device["groups"]["fan-trays"]["attrs"]["redundancy"] == "2+1"


# ---- what each slot accepts, and each module's envelope

def test_each_slot_accepts_what_the_guide_lists(device, chassis):
    front, rear = by_id(device, "front"), by_id(device, "rear")
    for n in range(1, LINE_CARDS[chassis] + 1):
        assert set(front[f"lc-{n}"]["accepts"]) == {"cisco/n9k-c9500-lc-cv@1"}   # line cards: a later batch
    for n in (1, 2):
        assert set(front[f"sup-{n}"]["accepts"]) == refs(SUPERVISORS)
        assert set(rear[f"sc-{n}"]["accepts"]) == {"cisco/n9k-sc-a@1"}
    for n in range(1, SUPPLY_BAYS[chassis] + 1):
        assert set(front[f"ps-{n}"]["accepts"]) == refs(SUPPLIES + ["n9k-psu-blank"])
    for n in range(1, 4):
        assert set(rear[f"fan-{n}"]["accepts"]) == refs(FANS[chassis])
    for n in range(1, 7):
        assert set(rear[f"fm-{n}"]["accepts"]) == refs(FABRICS[chassis] + BLANKS[chassis])


def test_every_bay_reserves_room_for_everything_it_accepts(device):
    for face in ("front", "rear"):
        for b in bays(device, face):
            turned = b.get("rotate") in (90, 270)
            bw, bh = (b["size"]["h"], b["size"]["w"]) if turned else (b["size"]["w"], b["size"]["h"])
            for ref in b["accepts"]:
                size = contract(ref.split("/")[1].split("@")[0])["size"]
                assert size["w"] <= bw + 0.01 and size["h"] <= bh + 0.01, (b["id"], ref)


def test_the_reused_parts_are_the_9508_batchs_and_are_not_redrawn():
    for name in SHARED:
        assert (COMPONENTS / name / "v1/contract.yaml").exists(), name
    for chassis in ("9504", "9516"):
        for name in NEW[chassis]:
            assert name.startswith(f"n9k-c{chassis}-"), "a part number of these chassis, never a twin of a shared part"


@pytest.mark.parametrize("name", FANS["9504"])
def test_9504_fan_tray_envelope(name):
    s = contract(name)["size"]
    assert s["w"] == pytest.approx(5.05 * IN, abs=0.05)      # 5.05 in (12.81 cm); the 9508 and 9516 print 5.04 in
    assert s["h"] == pytest.approx(10.6 * IN, abs=0.1)       # with mounting brackets (9.0 in without)
    assert s["d"] == pytest.approx(5.47 * IN, abs=0.1)


def test_9516_fan_tray_envelope():
    s = contract("n9k-c9516-fan")["size"]
    assert s["w"] == pytest.approx(5.04 * IN, abs=0.05)
    assert s["h"] == pytest.approx(32.08 * IN, abs=0.1)      # with mounting brackets (30.5 in without)
    assert s["d"] == pytest.approx(3.87 * IN, abs=0.1)


@pytest.mark.parametrize("chassis_id,high", [("9504", 9.4), ("9516", 30.4)])
def test_fabric_module_envelope(chassis_id, high):
    for name in FABRICS[chassis_id] + BLANKS[chassis_id]:      # the blanks take the fabric module's slot envelope
        s = contract(name)["size"]
        assert s["w"] == pytest.approx(2.46 * IN, abs=0.05), name
        assert s["h"] == pytest.approx(high * IN, abs=0.1), name
        assert s["d"] == pytest.approx(11.7 * IN, abs=0.1), name


def test_the_shared_parts_envelopes_equal_what_these_guides_print():
    for name in SUPERVISORS:
        s = contract(name)["size"]
        assert (s["w"], s["h"], s["d"]) == pytest.approx((8.0 * IN, 1.75 * IN, 20.67 * IN), abs=0.5), name
    s = contract("n9k-sc-a")["size"]
    assert (s["w"], s["h"], s["d"]) == pytest.approx((7.81 * IN, 1.42 * IN, 10.74 * IN), abs=0.5)
    s = contract("n9k-c9500-lc-cv")["size"]
    assert (s["w"], s["h"]) == pytest.approx((17.0 * IN, 1.75 * IN), abs=0.05)
    for name in SUPPLIES:
        s = contract(name)["size"]
        assert (s["w"], s["h"], s["d"]) == pytest.approx((1.75 * IN, 5.25 * IN, 17.75 * IN), abs=0.1), name


def test_the_front_stack_adds_up_to_the_chassis_height(device, chassis):
    front = by_id(device, "front")
    bottom = max(b["at"][1] + b["size"]["h"] for b in front.values())
    assert bottom == pytest.approx(device["chassis"]["height"], abs=0.1)         # 311.15 and 933.45 mm
    top = front["lc-1"]["at"][1]
    assert top == pytest.approx(0 if chassis == "9504" else 44.45, abs=0.01)     # the 9516 has a lamp band above


def test_the_rear_stack_fits_inside_the_chassis(device):
    rear = by_id(device, "rear")
    for b in rear.values():
        assert b["at"][0] >= 0 and b["at"][0] + b["size"]["w"] <= device["chassis"]["width"] + 0.01, b["id"]
        assert b["at"][1] >= 0 and b["at"][1] + b["size"]["h"] <= device["chassis"]["height"] + 0.01, b["id"]
    assert rear["fan-1"]["at"][1] + rear["fan-1"]["size"]["h"] <= rear["sc-1"]["at"][1], "the controllers sit below"


def test_9504_supplies_lie_flat_in_two_rows_of_two_either_side_of_the_lamp_panel():
    device = load("9504")
    front = by_id(device, "front")
    for n in range(1, 5):
        ps = front[f"ps-{n}"]
        assert ps["rotate"] in (90, 270)
        assert (ps["size"]["w"], ps["size"]["h"]) == pytest.approx((5.25 * IN, 1.75 * IN), abs=0.05)
    assert front["ps-1"]["at"][0] == front["ps-2"]["at"][0] < front["ps-3"]["at"][0] == front["ps-4"]["at"][0]
    assert front["ps-1"]["at"][1] == front["ps-3"]["at"][1] < front["ps-2"]["at"][1] == front["ps-4"]["at"][1]
    # the centre panel between them is 17.5 - 2 x 5.25 = 7.0 in wide
    assert front["ps-3"]["at"][0] - (front["ps-1"]["at"][0] + 5.25 * IN) == pytest.approx(7.0 * IN, abs=0.1)
    lamps = [p for p in device["views"]["front"]["components"]["placements"] if p["group"] == "leds"]
    assert len(lamps) == 7
    assert all(front["ps-1"]["at"][0] + 5.25 * IN <= p["at"][0] <= front["ps-3"]["at"][0] for p in lamps)


def test_9516_supplies_stand_on_end_across_the_chassis_width():
    front = by_id(load("9516"), "front")
    xs = [front[f"ps-{n}"]["at"][0] for n in range(1, 11)]
    assert xs == pytest.approx([44.45 * k for k in range(10)], abs=0.01)
    assert xs[-1] + 44.45 == pytest.approx(444.5, abs=0.01)
    assert all("rotate" not in front[f"ps-{n}"] for n in range(1, 11))


# ---- configurations, part numbers, supplies, fans and airflow

def test_base_is_the_default_and_names_the_chassis_part_number(device, chassis):
    cfgs = device["configurations"]
    assert [k for k, v in cfgs.items() if v.get("default")] == ["base"]
    assert cfgs["base"]["kind"] == "base"
    assert list(cfgs["base"]["part-numbers"]) == [f"N9K-C{chassis}"]
    assert not [k for k, v in cfgs.items() if v["kind"] != "base" and v["kind"] != "example"], "no bundle codes"
    assert "derived" in cfgs["base"]["source"]


def test_9504_base_is_the_guides_planning_example():
    s = seated(load("9504"), "base")          # PDF p21 (printed 15): 2 SUP-B, 2 SC, 4 LC, six FM-G, three FAN2
    assert s["sup-1"] == s["sup-2"] == "cisco/n9k-sup-b@1"
    assert s["sc-1"] == s["sc-2"] == "cisco/n9k-sc-a@1"
    assert [s[f"fan-{n}"] for n in (1, 2, 3)] == ["cisco/n9k-c9504-fan2@1"] * 3
    assert [s[f"fm-{n}"] for n in range(1, 7)] == ["cisco/n9k-c9504-fm-g@1"] * 6
    assert [s[f"ps-{n}"] for n in range(1, 5)] == ["cisco/n9k-pac-3000w-b@1"] * 4      # 9,256 W over 3,000 W
    assert {s[f"lc-{n}"] for n in range(1, 5)} == {"cisco/n9k-c9500-lc-cv@1"}


def test_9516_base_is_the_guides_planning_example():
    s = seated(load("9516"), "base")          # PDF p20 (printed 14): 2 SUP-A, 2 SC, 16 LC, six FM, three FAN
    assert s["sup-1"] == s["sup-2"] == "cisco/n9k-sup-a@1"
    assert s["sc-1"] == s["sc-2"] == "cisco/n9k-sc-a@1"
    assert [s[f"fan-{n}"] for n in (1, 2, 3)] == ["cisco/n9k-c9516-fan@1"] * 3
    assert [s[f"fm-{n}"] for n in range(1, 7)] == ["cisco/n9k-c9516-fm@1"] * 6
    assert [s[f"ps-{n}"] for n in range(1, 6)] == ["cisco/n9k-pac-3000w-b@1"] * 5      # Step 2: five supplies
    assert [s[f"ps-{n}"] for n in range(6, 11)] == ["cisco/n9k-psu-blank@1"] * 5
    assert {s[f"lc-{n}"] for n in range(1, 17)} == {"cisco/n9k-c9500-lc-cv@1"}


@pytest.mark.parametrize("config,supply", [("psu-universal", "n9k-puv-3000w-b"),
                                           ("psu-dual-input", "n9k-puv2-3000w-b"),
                                           ("psu-dc", "n9k-pdc-3000w-b")])
def test_supply_builds_seat_the_bases_supply_count_of_one_supply(device, chassis, config, supply):
    s = seated(device, config)
    n = SUPPLY_BAYS[chassis] if chassis == "9504" else 5
    assert [s[f"ps-{k}"] for k in range(1, n + 1)] == [f"cisco/{supply}@1"] * n
    assert device["configurations"][config]["kind"] == "example"


def test_the_dc_build_declares_a_dc_feed(device):
    assert device["configurations"]["psu-dc"]["power"] == "dc"
    assert device["configurations"]["base"]["power"] == "ac"


def test_9504_has_no_fm_z_and_the_even_slot_blank_is_a_gap():
    device = load("9504")
    for face in ("front", "rear"):
        for b in bays(device, face):
            assert not [a for a in b["accepts"] if a.endswith("-fm-z@1")]
    assert not (COMPONENTS / "n9k-c9504-fm-z").exists(), "the guide names no N9K-C9504-FM-Z"
    assert "even-fabric-slot-blank" in {g["what"] for g in device["gaps"]}
    for cfg in device["configurations"]:
        s = seated(device, cfg)
        assert not [r for r in s.values() if "fm-z" in r]


def test_9516_has_no_fan2_and_no_fan_power_card():
    device = load("9516")
    for b in bays(device, "rear"):
        assert not [a for a in b["accepts"] if "fan2" in a or "fan-pwr" in a]
    for name in ("n9k-c9516-fan2", "n9k-c9516-fan-pwr", "n9k-c9516-fm-g", "n9k-c9516-fm-s", "n9k-c9516-fm-r"):
        assert not (COMPONENTS / name).exists()


def test_9504_fm_g_build_pairs_fan2_and_an_empty_slot_takes_the_fan_power_card():
    device = load("9504")
    s = seated(device, "fabric-g-five")           # PDF p9 (printed 3): empty slots take FAN-PWR with FM-G
    assert [s[f"fan-{n}"] for n in (1, 2, 3)] == ["cisco/n9k-c9504-fan2@1"] * 3
    assert [s[f"fm-{n}"] for n in range(2, 7)] == ["cisco/n9k-c9504-fm-g@1"] * 5
    assert s["fm-1"] == "cisco/n9k-c9504-fan-pwr@1"


def test_an_empty_odd_fabric_slot_defaults_to_the_fm_cv_in_every_build(device, chassis):
    # 9504 PDF p9 (printed 3) and p118 (printed 112); 9516 PDF p9 (printed 3): FM 1, 3, 5 take N9K-C95xx-FM-CV
    for cfg in device["configurations"]:
        s = seated(device, cfg)
        for k in (1, 3, 5):
            held = s.get(f"fm-{k}")
            assert not held or "fm-z" not in held, (cfg, k)
            if held and held.split("/")[1].split("@")[0] in BLANKS[chassis]:
                assert held in (f"cisco/n9k-c{chassis}-fm-cv@1", "cisco/n9k-c9504-fan-pwr@1"), (cfg, k)
    # both blanks stay accepted in every fabric bay
    for n in range(1, 7):
        assert refs(BLANKS[chassis]) <= set(by_id(device, "rear")[f"fm-{n}"]["accepts"])


def test_9516_three_module_build_blanks_the_odd_slots_with_the_fm_cv():
    s = seated(load("9516"), "fabric-three")       # PDF p9 (printed 3): three modules in FM 2, 4, 6
    assert [s[f"fm-{n}"] for n in (2, 4, 6)] == ["cisco/n9k-c9516-fm-e2@1"] * 3
    assert [s[f"fm-{n}"] for n in (1, 3, 5)] == ["cisco/n9k-c9516-fm-cv@1"] * 3


def test_five_module_builds_blank_fm_1_with_the_fm_cv():
    for chassis, cfg, fm in (("9504", "fabric-e", "n9k-c9504-fm-e"), ("9516", "fabric-e", "n9k-c9516-fm-e")):
        s = seated(load(chassis), cfg)       # five FM-E must be in FM 2 to 6 (9504 PDF p9, 9516 PDF p9)
        assert [s[f"fm-{n}"] for n in range(2, 7)] == [f"cisco/{fm}@1"] * 5
        assert s["fm-1"] == f"cisco/n9k-c{chassis}-fm-cv@1"


def test_the_empty_build_seats_no_module_in_the_rear_and_the_supervisor_slots(device, chassis):
    s = seated(device, "empty")
    assert not [b for b in s if b.startswith(("sup-", "sc-", "fan-", "fm-"))]
    assert {s[f"lc-{n}"] for n in range(1, LINE_CARDS[chassis] + 1)} == {"cisco/n9k-c9500-lc-cv@1"}
    assert {s[f"ps-{n}"] for n in range(1, SUPPLY_BAYS[chassis] + 1)} == {"cisco/n9k-psu-blank@1"}


def test_airflow_is_front_to_back_and_every_supply_fan_and_fabric_says_port_side_intake(device, chassis):
    assert device["chassis"]["airflow"] == "front-to-back"
    for name in SUPPLIES + FANS[chassis]:
        assert contract(name)["attrs"]["airflow"] == "port-side intake", name


def test_supply_ratings_are_the_guides():
    power = {n: contract(n)["attrs"]["power-output-w"] for n in SUPPLIES}
    assert power == {"n9k-pac-3000w-b": 3000, "n9k-puv-3000w-b": 3000,
                     "n9k-puv2-3000w-b": 3150, "n9k-pdc-3000w-b": 3000}


# 9504's own table, PDF pp17-18 (printed 11-12) - the guide prints the maximum before the typical
POWER_9504 = {"n9k-c9504-fm": (95, 131), "n9k-c9504-fm-e": (234, 313), "n9k-c9504-fm-s": (171, 251),
              "n9k-c9504-fm-g": (270, 504),
              "n9k-c9504-fan": (95, 129), "n9k-c9504-fan2": (105, 600),
              # the only fan-power row (PDF p20, printed 14) names N9K-C9508-FAN-PWR: 45 W typical, 90 W maximum
              "n9k-c9504-fan-pwr": (45, 90)}
# 9516's own table, PDF pp19-20 (printed 13-14)
POWER_9516 = {"n9k-c9516-fm": (330, 504), "n9k-c9516-fan": (330, 600),
              # FM-E and FM-E2 share one row printed on two lines; they are read BY LINE ORDER, FM-E first, and no
              # worked example confirms either: FM-E 980 W typical / 1320 W maximum, FM-E2 439 W / 900 W
              "n9k-c9516-fm-e": (980, 1320), "n9k-c9516-fm-e2": (439, 900)}


@pytest.mark.parametrize("name,figures", list({**POWER_9504, **POWER_9516}.items()))
def test_new_module_power_figures_are_the_chassis_own_planning_table(name, figures):
    a = contract(name)["attrs"]
    assert (a["power-draw-typical-w"], a["power-draw-max-w"]) == figures, name


def test_9504_fm_r_carries_the_maximum_only_and_the_typical_is_a_gap():
    # the FM-R row (PDF p18, printed 12) prints 130 W maximum and 140 W typical: typical above maximum, a slip,
    # which lint refuses, so only the maximum is carried
    a = contract("n9k-c9504-fm-r")["attrs"]
    assert a["power-draw-max-w"] == 130
    assert "power-draw-typical-w" not in a
    assert "140 W" in contract("n9k-c9504-fm-r")["provenance"]["power"]
    assert "fm-r-typical-draw" in {g["what"] for g in load("9504")["gaps"]}


def test_blanks_without_a_power_row_state_no_draw():
    for name in ("n9k-c9504-fm-cv", "n9k-c9516-fm-cv", "n9k-c9516-fm-z"):
        assert "power-draw-max-w" not in contract(name)["attrs"], name


def test_the_fan_power_card_names_the_9508_part_in_its_provenance():
    assert "N9K-C9508-FAN-PWR" in contract("n9k-c9504-fan-pwr")["provenance"]["power"]


def test_blank_model_names_name_the_family():
    for name in ("n9k-psu-blank",):
        assert contract(name)["attrs"]["model"].startswith("Nexus 9500 ")
    assert "supervisor-and-controller-slot-blanks" in {g["what"] for g in load("9504")["gaps"]}


def test_the_9516_supervisor_draw_differs_from_the_shared_parts_and_is_recorded():
    note = " ".join(g.get("note", "") for g in load("9516")["gaps"])
    assert "80 W" in note and "90 W" in note
    assert contract("n9k-sup-a")["attrs"]["power-draw-max-w"] == 90        # shared part, not edited here


# ---- the DCIM export

@pytest.mark.parametrize("chassis_id,u", [("9504", 7), ("9516", 21)])
def test_device_type_exports_with_the_guides_u_height(chassis_id, u):
    files = list((EXPORTS / "netbox/device-types/Cisco").glob(f"N9K-C{chassis_id}*.yaml"))
    assert files, f"run dcim_export.py for n9k-c{chassis_id}"
    doc = yaml.safe_load(files[0].read_text())
    assert doc["u_height"] == u
    assert doc["model"] == f"N9K-C{chassis_id}"
    assert doc["manufacturer"] == "Cisco"
    assert doc["airflow"] == "front-to-rear"
    assert len(doc["module-bays"]) == (21 if chassis_id == "9504" else 39)


@pytest.mark.parametrize("name", NEW["9504"] + NEW["9516"])
def test_module_types_export(name):
    file = contract(name)["attrs"]["model"] + ".yaml"     # a module is exported under its model
    assert (EXPORTS / "netbox/module-types/Cisco" / file).exists(), f"no NetBox module type for {name}"
    assert (EXPORTS / "nautobot/module-types/Cisco" / file).exists()
