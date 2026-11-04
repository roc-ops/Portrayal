"""The Cisco Nexus 9508 chassis and its common equipment (Nexus 9500 chassis, batch 1).

Every figure here is Cisco's N9508 NX-OS Mode Switch Hardware Installation Guide: Appendix A "Switch
Dimensions" for the envelopes, the "Overview" for the slots and what each takes, "Planning for Power
Requirements" for the power figures. Each line-card slot takes the line-card blank and the nine line cards
modelled in test_cisco_nexus_9500_line_cards.py and test_cisco_nexus_9500_line_cards_2.py.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/cisco/n9k-c9508/device.yaml"
COMPONENTS = ROOT / "library/components/cisco"
EXPORTS = ROOT / "library/exports"

IN = 25.4

SUPERVISORS = ["n9k-sup-a", "n9k-sup-a-plus", "n9k-sup-b", "n9k-sup-b-plus"]
SUPPLIES = ["n9k-pac-3000w-b", "n9k-puv-3000w-b", "n9k-puv2-3000w-b", "n9k-pdc-3000w-b"]
FANS = ["n9k-c9508-fan", "n9k-c9508-fan2"]
FABRICS = ["n9k-c9508-fm", "n9k-c9508-fm-s", "n9k-c9508-fm-e", "n9k-c9508-fm-e2",
           "n9k-c9508-fm-g", "n9k-c9508-fm-r", "n9k-c9508-fm-r2"]
FABRIC_BLANKS = ["n9k-c9508-fm-z", "n9k-c9508-fm-cv", "n9k-c9508-fan-pwr"]
LINE_CARDS = ["n9k-x9736c-fx", "n9k-x97160yc-ex", "n9k-x9732c-fx", "n9k-x9716d-gx",
              "n9k-x9736c-ex", "n9k-x9732c-ex", "n9k-x9736c-fx3", "n9k-x9736q-fx", "n9k-x9408pc-cfp2"]
EVERY_MODULE = (SUPERVISORS + ["n9k-sc-a"] + SUPPLIES + ["n9k-psu-blank"] + FANS + FABRICS
                + FABRIC_BLANKS + ["n9k-c9500-lc-cv"])


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load(DEVICE.read_text())


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def bays(device, face):
    return device["views"][face]["components"]["bays"]


def by_id(device, face):
    return {b["id"]: b for b in bays(device, face)}


def refs(names):
    return {f"cisco/{n}@1" for n in names}


# ---- the chassis envelope

def test_envelope_is_the_guides_dimension_table(device):
    c = device["chassis"]
    assert c["width"] == pytest.approx(17.5 * IN, abs=0.1)        # 17.5 in (44.5 cm)
    assert c["depth"] == pytest.approx(31.76 * IN, abs=0.1)       # 31.76 in (80.67 cm), chassis and handles
    assert c["height"] == pytest.approx(13 * 44.45, abs=0.01)     # 13 RU, 57.78 cm
    assert c["ru"] == 13


def test_identity_follows_the_nexus_naming(device):
    assert device["manufacturer"] == "Cisco"
    assert device["model"] == "N9K-C9508"
    assert device["portfolio"]["line"] == "Nexus 9000"
    assert device["portfolio"]["family"] == "Nexus 9500"
    assert [r for r in device["views"]["front"]["regions"] if r["id"] == "logo-zone"]


def test_no_ear_is_drawn_and_the_shipped_position_is_flush(device):
    placed = [p["ref"] for v in device["views"].values()
              for p in (v.get("components") or {}).get("placements", [])]
    assert "common/rack-ear@1" not in placed
    positions = device["chassis"]["ears"]["positions"]
    assert [p["name"] for p in positions if p.get("default")] == ["flush"]
    assert all("at" not in p for p in positions), "no figure dimensions the bracket"
    assert "kits" not in device["chassis"], "the rack kit waits for tooling that copes with a kit contract"


# ---- slot and bay counts, numbering, per face

def test_front_slots_and_numbering(device):
    front = by_id(device, "front")
    assert [i for i in front if i.startswith("lc-")] == [f"lc-{n}" for n in range(1, 9)]
    assert [i for i in front if i.startswith("sup-")] == ["sup-1", "sup-2"]
    assert [i for i in front if i.startswith("ps-")] == [f"ps-{n}" for n in range(1, 9)]
    assert len(front) == 18
    ys = [front[f"lc-{n}"]["at"][1] for n in range(1, 9)]
    assert ys == sorted(ys), "LC 1 to LC 8 run top to bottom"
    assert front["sup-1"]["at"][0] < front["sup-2"]["at"][0], "SUP 1 is left of SUP 2"
    xs = [front[f"ps-{n}"]["at"][0] for n in range(1, 9)]
    assert xs == sorted(xs), "PS 1 to PS 8 run left to right"


def test_rear_slots_and_numbering(device):
    rear = by_id(device, "rear")
    assert [i for i in rear if i.startswith("fan-")] == ["fan-1", "fan-2", "fan-3"]
    assert [i for i in rear if i.startswith("fm-")] == [f"fm-{n}" for n in range(1, 7)]
    assert [i for i in rear if i.startswith("sc-")] == ["sc-1", "sc-2"]
    assert len(rear) == 11
    for prefix, n in (("fan", 3), ("fm", 6), ("sc", 2)):
        xs = [rear[f"{prefix}-{k}"]["at"][0] for k in range(1, n + 1)]
        assert xs == sorted(xs), f"{prefix} numbering runs left to right"


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


# ---- what each slot accepts, and each module's envelope

def test_each_slot_accepts_what_the_guide_lists(device):
    front, rear = by_id(device, "front"), by_id(device, "rear")
    for n in range(1, 9):
        assert set(front[f"lc-{n}"]["accepts"]) == {"cisco/n9k-c9500-lc-cv@1"} | refs(LINE_CARDS)
    for n in (1, 2):
        assert set(front[f"sup-{n}"]["accepts"]) == refs(SUPERVISORS)
        assert set(rear[f"sc-{n}"]["accepts"]) == {"cisco/n9k-sc-a@1"}
    for n in range(1, 9):
        assert set(front[f"ps-{n}"]["accepts"]) == refs(SUPPLIES + ["n9k-psu-blank"])
    for n in range(1, 4):
        assert set(rear[f"fan-{n}"]["accepts"]) == refs(FANS)
    for n in range(1, 7):
        assert set(rear[f"fm-{n}"]["accepts"]) == refs(FABRICS + FABRIC_BLANKS)


def test_every_bay_reserves_room_for_everything_it_accepts(device):
    for face in ("front", "rear"):
        for b in bays(device, face):
            for ref in b["accepts"]:
                size = contract(ref.split("/")[1].split("@")[0])["size"]
                assert size["w"] <= b["size"]["w"] + 0.01 and size["h"] <= b["size"]["h"] + 0.01, (b["id"], ref)


@pytest.mark.parametrize("name", SUPERVISORS)
def test_supervisor_envelope(name):
    s = contract(name)["size"]
    assert s["w"] == pytest.approx(8.0 * IN, abs=0.05)       # 8.0 in with brackets
    assert s["h"] == pytest.approx(1.75 * IN, abs=0.05)
    assert s["d"] == pytest.approx(20.67 * IN, abs=0.5)      # inside the chassis


def test_system_controller_envelope():
    s = contract("n9k-sc-a")["size"]
    assert s["w"] == pytest.approx(7.81 * IN, abs=0.05)
    assert s["h"] == pytest.approx(1.42 * IN, abs=0.05)
    assert s["d"] == pytest.approx(10.74 * IN, abs=0.5)


@pytest.mark.parametrize("name", FANS)
def test_fan_tray_envelope(name):
    s = contract(name)["size"]
    assert s["w"] == pytest.approx(5.04 * IN, abs=0.05)
    assert s["h"] == pytest.approx(18.08 * IN, abs=0.1)      # with mounting brackets
    assert s["d"] == pytest.approx(5.12 * IN, abs=0.1)


@pytest.mark.parametrize("name", FABRICS)
def test_fabric_module_envelope(name):
    s = contract(name)["size"]
    assert s["w"] == pytest.approx(2.46 * IN, abs=0.05)
    assert s["h"] == pytest.approx(16.4 * IN, abs=0.1)
    assert s["d"] == pytest.approx(11.7 * IN, abs=0.1)


@pytest.mark.parametrize("name", SUPPLIES)
def test_power_supply_envelope_stands_on_end(name):
    s = contract(name)["size"]
    assert s["w"] == pytest.approx(1.75 * IN, abs=0.05)      # the figures stand the supply on end
    assert s["h"] == pytest.approx(5.25 * IN, abs=0.05)
    assert s["d"] == pytest.approx(17.75 * IN, abs=0.1)


def test_line_card_blank_takes_the_line_card_face():
    s = contract("n9k-c9500-lc-cv")["size"]
    assert s["w"] == pytest.approx(17.0 * IN, abs=0.05)
    assert s["h"] == pytest.approx(1.75 * IN, abs=0.05)


def test_the_front_stack_adds_up_to_the_chassis_height(device):
    front = by_id(device, "front")
    assert front["lc-1"]["at"][1] == pytest.approx(1.75 * IN, abs=0.01)       # one RU of lamps above
    bottom = front["ps-1"]["at"][1] + front["ps-1"]["size"]["h"]
    assert bottom == pytest.approx(device["chassis"]["height"], abs=0.1)


# ---- configurations, part numbers, supplies, fans and airflow

def test_base_is_the_default_and_names_the_chassis_part_number(device):
    cfgs = device["configurations"]
    assert [k for k, v in cfgs.items() if v.get("default")] == ["base"]
    assert cfgs["base"]["kind"] == "base"
    assert list(cfgs["base"]["part-numbers"]) == ["N9K-C9508"]
    assert not [k for k, v in cfgs.items() if v["kind"] == "orderable"], "the guide prints no bundle codes"


def seated(device, config):
    out = {}
    for face in ("front", "rear"):
        for b in bays(device, face):
            if b.get("default"):
                out[b["id"]] = b["default"]
    for bay, ref in (device["configurations"][config].get("bays") or {}).items():
        out[bay] = ref
    return {b: r for b, r in out.items() if r}


def test_base_seats_the_common_equipment(device):
    s = seated(device, "base")
    assert s["sup-1"] == s["sup-2"] == "cisco/n9k-sup-b-plus@1"
    assert s["sc-1"] == s["sc-2"] == "cisco/n9k-sc-a@1"
    assert [s[f"fan-{n}"] for n in (1, 2, 3)] == ["cisco/n9k-c9508-fan@1"] * 3
    assert [s[f"fm-{n}"] for n in range(2, 7)] == ["cisco/n9k-c9508-fm-e2@1"] * 5
    # an empty odd fabric slot takes the FM-CV (PDF p10, pp113-116); the FM-Z is for an empty even slot (p135)
    assert s["fm-1"] == "cisco/n9k-c9508-fm-cv@1"
    assert [s[f"ps-{n}"] for n in range(1, 5)] == ["cisco/n9k-pac-3000w-b@1"] * 4
    assert [s[f"ps-{n}"] for n in range(5, 9)] == ["cisco/n9k-psu-blank@1"] * 4
    assert {s[f"lc-{n}"] for n in range(1, 9)} == {"cisco/n9k-c9500-lc-cv@1"}


@pytest.mark.parametrize("config,supply", [("psu-universal", "n9k-puv-3000w-b"),
                                           ("psu-dual-input", "n9k-puv2-3000w-b"),
                                           ("psu-dc", "n9k-pdc-3000w-b")])
def test_supply_builds_seat_four_of_one_supply(device, config, supply):
    s = seated(device, config)
    assert [s[f"ps-{n}"] for n in range(1, 5)] == [f"cisco/{supply}@1"] * 4
    assert device["configurations"][config]["kind"] == "example"


def test_the_dc_build_declares_a_dc_feed(device):
    assert device["configurations"]["psu-dc"]["power"] == "dc"
    assert device["configurations"]["base"]["power"] == "ac"


def test_fm_g_build_pairs_fan2_and_the_fan_power_card_as_table_1(device):
    s = seated(device, "fabric-g")
    assert [s[f"fan-{n}"] for n in (1, 2, 3)] == ["cisco/n9k-c9508-fan2@1"] * 3
    assert [s[f"fm-{n}"] for n in range(2, 7)] == ["cisco/n9k-c9508-fm-g@1"] * 5
    assert s["fm-1"] == "cisco/n9k-c9508-fan-pwr@1"


def test_the_empty_build_seats_no_module_in_the_rear_and_the_supervisor_slots(device):
    s = seated(device, "empty")
    assert not [b for b in s if b.startswith(("sup-", "sc-", "fan-", "fm-"))]
    assert {s[f"lc-{n}"] for n in range(1, 9)} == {"cisco/n9k-c9500-lc-cv@1"}
    assert {s[f"ps-{n}"] for n in range(1, 9)} == {"cisco/n9k-psu-blank@1"}


def test_airflow_is_front_to_back_and_every_supply_and_fan_says_port_side_intake(device):
    assert device["chassis"]["airflow"] == "front-to-back"
    for name in SUPPLIES + FANS:
        assert contract(name)["attrs"]["airflow"] == "port-side intake", name


def test_supply_ratings_are_the_guides():
    power = {n: contract(n)["attrs"]["power-output-w"] for n in SUPPLIES}
    assert power == {"n9k-pac-3000w-b": 3000, "n9k-puv-3000w-b": 3000,
                     "n9k-puv2-3000w-b": 3150, "n9k-pdc-3000w-b": 3000}


def test_module_power_figures_are_the_planning_table():
    want = {"n9k-sup-a": (69, 90), "n9k-sup-a-plus": (69, 90), "n9k-sup-b": (75, 90),
            "n9k-sup-b-plus": (75, 90), "n9k-sc-a": (14, 25),
            "n9k-c9508-fan": (176, 250), "n9k-c9508-fan2": (450, 900),
            "n9k-c9508-fm": (176, 251), "n9k-c9508-fm-s": (340, 400),
            "n9k-c9508-fm-e2": (266, 420), "n9k-c9508-fm-g": (685, 936),
            "n9k-c9508-fm-r": (240, 250), "n9k-c9508-fm-r2": (280, 320),
            "n9k-c9508-fan-pwr": (45, 90),                           # PDF p19; the FM-G example counts two at 180 W
            # FM-E 455/570 W is the first of the two lines in the shared FM-E/FM-E2 row (PDF p17), read by line
            # order; only the FM-E2 line is confirmed, by the Step 2 example at 420 W
            "n9k-c9508-fm-e": (455, 570)}
    for name, (typ, top) in want.items():
        a = contract(name)["attrs"]
        assert (a["power-draw-typical-w"], a["power-draw-max-w"]) == (typ, top), name


def test_sale_status_is_stated_only_where_the_notice_says_so():
    eos = {"n9k-sup-a", "n9k-sup-b", "n9k-c9508-fm", "n9k-c9508-fm-s", "n9k-c9508-fm-e"}
    for name in SUPERVISORS + FABRICS:
        want = "end-of-sale" if name in eos else "unknown"
        assert contract(name)["attrs"]["eol"] == want, name


# ---- the DCIM export

def test_device_type_exports_with_u_height_13():
    files = list((EXPORTS / "netbox/device-types/Cisco").glob("N9K-C9508*.yaml"))
    assert files, "run dcim_export.py for n9k-c9508"
    doc = yaml.safe_load(files[0].read_text())
    assert doc["u_height"] == 13
    assert doc["model"] == "N9K-C9508"
    assert doc["manufacturer"] == "Cisco"
    assert doc["airflow"] == "front-to-rear"
    assert len(doc["module-bays"]) == 29, "18 on the front, 11 on the rear"


@pytest.mark.parametrize("name", EVERY_MODULE)
def test_module_types_export(name):
    file = contract(name)["attrs"]["model"] + ".yaml"     # a module is exported under its model
    assert (EXPORTS / "netbox/module-types/Cisco" / file).exists(), f"no NetBox module type for {name}"
    assert (EXPORTS / "nautobot/module-types/Cisco" / file).exists()
