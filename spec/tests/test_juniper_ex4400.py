"""The Juniper EX4400 switches against the hardware guide: the copper 24T, 24P, 48T and 48P, and
then the fibre 24X and 48F and the multigigabit 24MP and 48MP.

Every figure here is the one the EX4400 Switch Hardware Guide prints (PDF created 2026-07-22), with
the table that prints it named beside it. The tests read the manifests and the committed DCIM
exports and need no build.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library/devices/juniper"
COMPONENTS = ROOT / "library/components/juniper"
EXPORTS = ROOT / "library/exports"

# model -> (RJ-45 ports, PoE, shipped supply, shipped supply watts, orderable configurations)
# Tables 7 to 28 of the guide: the 24T and 48T ship a 550 W AC supply, the 24P a 1050 W and the
# 48P a 1600 W one. Only the non-PoE models are sold in back-to-front and DC builds.
MODELS = {
    "ex4400-24t": dict(ports=24, poe=False, psu="jpsu-550-c-ac-afo", watts=550,
                       configs={"ac": "EX4400-24T", "afi": "EX4400-24T-AFI", "dc": "EX4400-24T-DC",
                                "dc-afi": "EX4400-24T-DC-AFI", "s": "EX4400-24T-S"}),
    "ex4400-24p": dict(ports=24, poe=True, psu="jpsu-1050-c-ac-afo", watts=1050,
                       configs={"ac": "EX4400-24P", "s": "EX4400-24P-S"}),
    "ex4400-48t": dict(ports=48, poe=False, psu="jpsu-550-c-ac-afo", watts=550,
                       configs={"ac": "EX4400-48T", "afi": "EX4400-48T-AFI", "dc": "EX4400-48T-DC",
                                "dc-afi": "EX4400-48T-DC-AFI", "s": "EX4400-48T-S"}),
    "ex4400-48p": dict(ports=48, poe=True, psu="jpsu-1600-c-ac-afo", watts=1600,
                       configs={"ac": "EX4400-48P", "s": "EX4400-48P-S"}),
}
NAMES = sorted(MODELS)
COPPER_PREFIXES = ("EX4400-24T", "EX4400-24P", "EX4400-48T", "EX4400-48P")

EXTENSION_MODULES = ["ex4400-em-1c", "ex4400-em-4s", "ex4400-em-4y"]


def load(name):
    return yaml.safe_load((DEVICES / name / "device.yaml").read_text())


def component(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def view_parts(device, face):
    comps = (device["views"][face].get("components") or {})
    return comps.get("placements") or [], comps.get("bays") or []


def bay(device, bay_id):
    for b in view_parts(device, "rear")[1] + view_parts(device, "front")[1]:
        if b["id"] == bay_id:
            return b
    raise KeyError(bay_id)


def seated(device, cfg_name, bay_id):
    """The component name in a bay for one configuration - '' for an open bay."""
    over = (device["configurations"][cfg_name].get("bays") or {})
    ref = over[bay_id] if bay_id in over else bay(device, bay_id).get("default", "")
    return ref.split("/")[-1].split("@")[0] if ref else ""


@pytest.mark.parametrize("name", NAMES)
def test_envelope_is_the_guides_table_38(name):
    d = load(name)
    c = d["chassis"]
    # Table 38: 1.72 in (4.37 cm) high, 17.39 in (44.17 cm) wide, 15.71 in (39.9 cm) deep with
    # no supply, fan module or extension module fitted.
    assert c["width"] == pytest.approx(441.7, abs=0.05)
    assert c["height"] == pytest.approx(43.7, abs=0.05)
    assert c["depth"] == pytest.approx(399.0, abs=0.05)
    assert c["ru"] == 1
    for face, (w, h) in {"front": (441.7, 43.7), "rear": (441.7, 43.7), "left": (399.0, 43.7),
                         "right": (399.0, 43.7), "top": (441.7, 399.0), "bottom": (441.7, 399.0)}.items():
        size = d["views"][face]["size"]
        assert (size["w"], size["h"]) == pytest.approx((w, h), abs=0.05), face
    assert d["manufacturer"] == "Juniper" and d["model"] == name.upper()
    assert d["portfolio"] == {"line": "EX Series", "family": "EX4400"}


@pytest.mark.parametrize("name", NAMES)
def test_front_jacks_count_pitch_and_numbering(name):
    d = load(name)
    want = MODELS[name]["ports"]
    placements, _ = view_parts(d, "front")
    jacks = [p for p in placements if p["ref"] == "common/rj45-ganged-eth@1"]
    assert len(jacks) == want
    by_id = {p["id"]: p for p in jacks}
    assert sorted(by_id) == sorted(f"port-{n}" for n in range(want))   # printed 0 to N-1
    for n in range(want):
        p = by_id[f"port-{n}"]
        assert p["rel-pos"] == n and p["group"] == "rj45"
        # Figure 50 - the upper jack of a column carries the even number and is turned 180
        assert (p.get("rotate", 0) == 180) == (n % 2 == 0)
    # Table 9 and its siblings: 24 jacks are two blocks of six columns, 48 are four blocks, on the
    # registry's 13.97 mm ganged pitch with one gutter between blocks
    xs = sorted({round(p["at"][0], 2) for p in jacks})
    assert len(xs) == want // 2
    steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
    assert steps.count(13.97) == len(steps) - (want // 12 - 1)
    assert all(s in (13.97, 19.41) for s in steps)
    # every jack has a punched cutout of its own
    cut = {c["id"] for c in d["views"]["front"]["panel"]["cutouts"]}
    assert set(by_id) <= cut
    # a printed numeral for each port, and the arrows pointing at it
    marks = d["views"]["front"]["silkscreen"]
    assert {m["text"] for m in marks if m.get("for", "").startswith("port-") and "text" in m} \
        == {str(n) for n in range(want)}
    assert sum(1 for m in marks if "path" in m and m.get("for", "").startswith("port-")) == want


@pytest.mark.parametrize("name", NAMES)
def test_front_has_the_status_block_and_the_extension_slot(name):
    d = load(name)
    placements, bays = view_parts(d, "front")
    ids = {p["id"] for p in placements}
    lamps = {"led-sys", "led-alm", "led-mst", "led-cld", "led-spd", "led-dx", "led-en"}
    if MODELS[name]["poe"]:
        lamps.add("led-poe")      # Figure 6 labels a fourth port mode lamp POE on the PoE models
    assert lamps <= ids and ("led-poe" in ids) == MODELS[name]["poe"]
    assert {"usb-c", "mode-button"} <= ids
    assert [b["id"] for b in bays] == ["ext-module"]
    mods = {a.split("/")[-1].split("@")[0] for a in bays[0]["accepts"]}
    # Table 5 lists three extension modules, and the shipped cover for the empty slot
    assert mods == set(EXTENSION_MODULES) | {"ex4400-em-cover"}
    assert bays[0]["default"] == "juniper/ex4400-em-cover@1"


@pytest.mark.parametrize("name", ["ex4400-24t", "ex4400-48t"])
def test_front_wordmark_sits_left_of_the_usb_c_port(name):
    """Figures 8 and 31 (g022643, g022662) print EX4400 at 374.3 to 385.2 mm, centre about 379.8.

    The USB-C port is centred at 393.7, so the wordmark is up and to the left of it, not over it.
    """
    d = load(name)
    marks = [s for s in d["views"]["front"]["silkscreen"] if s.get("text") == "EX4400"]
    assert len(marks) == 1 and marks[0]["anchor"] == "middle"
    assert marks[0]["at"][0] == pytest.approx(379.8, abs=0.5)
    assert marks[0]["at"][0] < 393.7 - 10


@pytest.mark.parametrize("name", NAMES)
def test_rear_ports_and_slots(name):
    d = load(name)
    placements, bays = view_parts(d, "rear")
    qsfp = [p for p in placements if p["ref"] == "std/qsfp28@1"]
    assert sorted(p["id"] for p in qsfp) == ["qsfp-0", "qsfp-1"]       # 100GbE QSFP28 ports: 2
    assert d["groups"]["qsfp28"]["attrs"]["speed"] == "100g"
    ids = {p["id"] for p in placements}
    assert {"con", "mgmt", "usb", "reset", "ground-mark", "esd-jack"} <= ids
    # Figure 7 callout 14 - a two-hole protective earthing terminal, two dark holes on a plate
    decor = {x["id"] for x in d["views"]["rear"]["panel"]["decor"]}
    assert {"ground-plate", "ground-hole-1", "ground-hole-2"} <= decor
    # four lamps for each QSFP28 port, in two rows of two (Figure 55)
    assert sum(1 for p in placements if p["id"].startswith("led-qsfp-")) == 8
    assert [b["id"] for b in bays] == ["fan-0", "fan-1", "psu-0", "psu-1"]   # slots numbered 0 and 1
    sizes = {b["id"]: (b["size"]["w"], b["size"]["h"]) for b in bays}
    # Table 39 (fan 1.65 in square) and Table 40 (supply 3.27 x 1.59 in)
    assert sizes["fan-0"] == pytest.approx((41.8, 41.8), abs=0.1)
    assert sizes["psu-0"] == pytest.approx((83.06, 40.39), abs=0.05)


@pytest.mark.parametrize("name", NAMES)
def test_configurations_and_their_part_numbers(name):
    d = load(name)
    cfgs = d["configurations"]
    orderable = {k: v for k, v in cfgs.items() if v["kind"] == "orderable"}
    assert {k: sorted(v["part-numbers"]) for k, v in orderable.items()} \
        == {k: [v] for k, v in MODELS[name]["configs"].items()}
    assert [k for k, v in cfgs.items() if v.get("default")] == ["ac"]
    assert all(v["kind"] == "example" for k, v in cfgs.items() if k not in orderable)


@pytest.mark.parametrize("name", NAMES)
def test_shipped_configuration_seats_the_supply_and_fans_the_guide_ships(name):
    d = load(name)
    m = MODELS[name]
    # Tables 8, 11, 20 and 26: one supply, two fan modules, a cover on the empty supply slot
    assert seated(d, "ac", "psu-0") == m["psu"]
    assert seated(d, "ac", "psu-1") == "ex4400-psu-cover"
    assert seated(d, "ac", "fan-0") == seated(d, "ac", "fan-1") == "ex4400-fan-afo"
    assert component(m["psu"])["attrs"]["power-output-w"] == m["watts"]
    # a spare ships with neither supplies nor fan modules
    for b in ("fan-0", "fan-1", "psu-0", "psu-1"):
        assert seated(d, "s", b) == ""


@pytest.mark.parametrize("name", NAMES)
def test_every_orderable_seats_parts_of_the_airflow_and_feed_it_states(name):
    d = load(name)
    for cfg_name in MODELS[name]["configs"]:
        cfg = d["configurations"][cfg_name]
        airflow = cfg.get("airflow") or d["chassis"].get("airflow")
        for bay_id in ("fan-0", "fan-1", "psu-0"):
            part = seated(d, cfg_name, bay_id)
            if not part:
                assert cfg_name == "s"
                continue
            c = component(part)
            assert c["attrs"]["airflow"] == airflow, (cfg_name, bay_id, part)
            if bay_id == "psu-0":
                assert c["attrs"]["role"] == f"{cfg['power']}-power-supply", (cfg_name, part)
    # the guide names handle colours by direction: orange for AIR OUT, blue for AIR IN
    afo, afi = component("ex4400-fan-afo"), component("ex4400-fan-afi")
    assert afo["attrs"]["airflow"] == "front-to-back" and afi["attrs"]["airflow"] == "back-to-front"
    assert afo["relief"]["features"][0]["color"] != afi["relief"]["features"][0]["color"]
    assert afi["relief"]["features"][0]["color"] == "#2a8bd8"


def test_the_poe_models_have_no_back_to_front_or_dc_orderable():
    # the guide lists no -AFI, -DC or -DC-AFI for the 24P or the 48P; their only DC supply is the
    # 2000 W one of the -S spare
    for name in ("ex4400-24p", "ex4400-48p"):
        d = load(name)
        assert sorted(k for k, v in d["configurations"].items() if v["kind"] == "orderable") == ["ac", "s"]
        accepted = {a.split("/")[-1].split("@")[0] for a in bay(d, "psu-0")["accepts"]}
        assert "jpsu-2000-c-dc-afo" in accepted
        assert not {"jpsu-550-c-ac-afo", "jpsu-550-c-ac-afi"} & accepted


def test_the_psu_and_fan_parts_are_named_by_their_juniper_part_numbers():
    parts = {
        "jpsu-550-c-ac-afo": "JPSU-550-C-AC-AFO", "jpsu-550-c-ac-afi": "JPSU-550-C-AC-AFI",
        "jpsu-550-c-dc-afo": "JPSU-550-C-DC-AFO", "jpsu-550-c-dc-afi": "JPSU-550-C-DC-AFI",
        "jpsu-1050-c-ac-afo": "JPSU-1050-C-AC-AFO", "jpsu-1600-c-ac-afo": "JPSU-1600-C-AC-AFO",
        "jpsu-2000-c-dc-afo": "JPSU-2000-C-DC-AFO"}
    for name, pn in parts.items():
        c = component(name)
        assert c["class"] == "psu" and c["kind"] == "module"
        assert c["part-numbers"] == {pn: {"part": pn}}
        # Table 40 - 3.27 x 1.59 x 8.88 in
        assert (c["size"]["w"], c["size"]["h"], c["size"]["d"]) == pytest.approx((83.06, 40.39, 225.55), abs=0.05)
        assert c["attrs"]["power-output-w"] == int(pn.split("-")[1])


@pytest.mark.parametrize("name", EXTENSION_MODULES)
def test_extension_modules_have_the_ports_the_guide_lists(name):
    c = component(name)
    assert c["class"] == "line-card"
    ports = [p for p in c["parts"] if p["id"].startswith("port-")]
    want = {"ex4400-em-4s": (4, "std/sfp-ganged@1", "sfp-plus", "10g"),
            "ex4400-em-4y": (4, "std/sfp-ganged@1", "sfp28", "25g"),
            "ex4400-em-1c": (1, "std/qsfp28@1", "qsfp28", "100g")}[name]
    assert len(ports) == want[0] and {p["ref"] for p in ports} == {want[1]}
    assert c["groups"][want[2]]["attrs"]["speed"] == want[3]
    # Table 5 - the module fills the slot at the front right
    assert (c["size"]["w"], c["size"]["h"]) == (74.0, 23.5)


@pytest.mark.parametrize("name", NAMES)
def test_extension_slot_example_seats_a_module(name):
    d = load(name)
    ex = d["configurations"]["em-4y"]
    assert ex["kind"] == "example" and ex["bays"] == {"ext-module": "juniper/ex4400-em-4y@1"}


def device_type_files(target):
    return sorted((EXPORTS / target / "device-types/Juniper").glob("EX4400-*.yaml"))


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_dcim_exports_one_device_type_per_orderable_configuration(target):
    want = {pn for m in MODELS.values() for pn in m["configs"].values()}
    got = {}
    for f in device_type_files(target):
        doc = yaml.safe_load(f.read_text())
        if doc["model"].startswith(COPPER_PREFIXES):     # the later models are held to their own table below
            got[doc["model"]] = doc
    assert set(got) == want
    for model, doc in got.items():
        assert doc["manufacturer"] == "Juniper"
        assert doc["u_height"] == 1.0          # Table 38 - 1.72 in, one rack unit
    # 24 or 48 RJ-45 jacks, two QSFP28 ports on the rear
    for model, doc in got.items():
        ports = [i for i in doc["interfaces"] if i["type"] == "1000base-t" and i["name"].startswith("port-")]
        n = 24 if "24" in model else 48
        assert len(ports) == n
        assert sum(1 for i in doc["interfaces"] if i["type"] == "100gbase-x-qsfp28") == 2


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_dcim_exports_each_powered_module_type_once(target):
    files = sorted((EXPORTS / target / "module-types/Juniper").glob("*.yaml"))
    models = {yaml.safe_load(f.read_text())["model"] for f in files}
    assert {"JPSU-550-C-AC-AFO", "JPSU-550-C-AC-AFI", "JPSU-550-C-DC-AFO", "JPSU-550-C-DC-AFI",
            "JPSU-1050-C-AC-AFO", "JPSU-1600-C-AC-AFO", "JPSU-2000-C-DC-AFO"} <= models


# ---------------------------------------------------------------------------------------------
# The rest of the fixed line - the fibre 24X and 48F and the multigigabit 24MP and 48MP.
#
# model -> what its front carries (Tables 14 to 36 and Table 114), the supply it ships, and the
# orderable configurations of its tables. The 24X lists no -S spare in Tables 14 and 16 (its weight
# row prints one), so none is modelled; the 48F-S takes a 550 W VDC supply this library has no part
# for, so its bays are left open and the VDC part is a named gap.
LATER = {
    "ex4400-24x": dict(
        cage="std/sfp-ganged@1", ports=24, groups={"sfp-plus": (range(24), "sfp-plus", "10g")},
        poe=False, jacks=0, qsfp_on="front", psu="jpsu-550-c-ac-afo", watts=550,
        accepts_psu={"jpsu-550-c-ac-afo", "jpsu-550-c-ac-afi", "jpsu-550-c-dc-afo", "jpsu-550-c-dc-afi"},
        configs={"ac": "EX4400-24X", "afi": "EX4400-24X-AFI", "dc": "EX4400-24X-DC",
                 "dc-afi": "EX4400-24X-DC-AFI"},
        throughput="540 Gbps"),
    "ex4400-48f": dict(
        cage="std/sfp-ganged@1", ports=48,
        groups={"sfp": (range(0, 36), "sfp", "1g"), "sfp-plus": (range(36, 48), "sfp-plus", "10g")},
        poe=False, jacks=0, qsfp_on="rear", psu="jpsu-550-c-ac-afo", watts=550,
        accepts_psu={"jpsu-550-c-ac-afo", "jpsu-550-c-ac-afi", "jpsu-550-c-dc-afo", "jpsu-550-c-dc-afi"},
        configs={"ac": "EX4400-48F", "afi": "EX4400-48F-AFI", "dc": "EX4400-48F-DC",
                 "dc-afi": "EX4400-48F-DC-AFI", "s": "EX4400-48F-S"},
        throughput="348 Gbps"),
    "ex4400-24mp": dict(
        cage=None, ports=24, groups={"rj45": (range(24), "rj45", "10g")},
        poe=True, jacks=24, qsfp_on="rear", psu="jpsu-1050-c-ac-afo", watts=1050,
        accepts_psu={"jpsu-1050-c-ac-afo", "jpsu-1600-c-ac-afo", "jpsu-2000-c-dc-afo"},
        configs={"ac": "EX4400-24MP", "s": "EX4400-24MP-S"},
        throughput="540 Gbps"),
    "ex4400-48mp": dict(
        cage=None, ports=48,
        groups={"rj45-2g5": (range(0, 36), "rj45", "2.5g"), "rj45-10g": (range(36, 48), "rj45", "10g")},
        poe=True, jacks=48, qsfp_on="rear", psu="jpsu-1600-c-ac-afo", watts=1600,
        accepts_psu={"jpsu-1600-c-ac-afo", "jpsu-2000-c-dc-afo"},
        configs={"ac": "EX4400-48MP", "s": "EX4400-48MP-S"},
        throughput="510 Gbps"),
}
LATER_NAMES = sorted(LATER)
LATER_PREFIXES = ("EX4400-24X", "EX4400-48F", "EX4400-24MP", "EX4400-48MP")


def front_ports(d, name):
    placements, _ = view_parts(d, "front")
    ref = LATER[name]["cage"] or "common/rj45-ganged-eth@1"
    return [p for p in placements if p["ref"] == ref and p["id"].startswith("port-")]


@pytest.mark.parametrize("name", LATER_NAMES)
def test_later_envelope_is_the_guides_table(name):
    d = load(name)
    c = d["chassis"]
    # Tables 15, 18, 30 and 33: 1.72 in (4.37 cm) high, 17.39 in (44.17 cm) wide, 15.71 in (39.9 cm)
    # deep with no supply, fan module or extension module fitted - the same for all four
    assert (c["width"], c["height"], c["depth"], c["ru"]) == pytest.approx((441.7, 43.7, 399.0, 1), abs=0.05)
    for face, (w, h) in {"front": (441.7, 43.7), "rear": (441.7, 43.7), "left": (399.0, 43.7),
                         "right": (399.0, 43.7), "top": (441.7, 399.0), "bottom": (441.7, 399.0)}.items():
        size = d["views"][face]["size"]
        assert (size["w"], size["h"]) == pytest.approx((w, h), abs=0.05), face
    assert d["manufacturer"] == "Juniper" and d["model"] == name.upper()
    assert d["portfolio"] == {"line": "EX Series", "family": "EX4400"}


@pytest.mark.parametrize("name", LATER_NAMES)
def test_later_front_ports_count_cage_and_numbering(name):
    d = load(name)
    m = LATER[name]
    ports = front_ports(d, name)
    assert sorted(p["id"] for p in ports) == sorted(f"port-{n}" for n in range(m["ports"]))
    by_id = {p["id"]: p for p in ports}
    for n in range(m["ports"]):
        p = by_id[f"port-{n}"]
        assert p["rel-pos"] == n
        # the upper port of a column carries the even number (Figure 50 and the SFP legends "0 up 1 down")
        # and the lower cage or jack is the turned one
        if m["cage"]:
            assert (p.get("rotate", 0) == 180) == (n % 2 == 1), n      # belly to belly: the lower cage is turned
        else:
            assert (p.get("rotate", 0) == 180) == (n % 2 == 0), n      # the jack stack of the copper models
    for group, (nums, media, speed) in m["groups"].items():
        assert d["groups"][group]["attrs"]["speed"] == speed and d["groups"][group]["attrs"]["media"] == media
        assert {by_id[f"port-{n}"]["group"] for n in nums} == {group}
    cut = {c["id"] for c in d["views"]["front"]["panel"]["cutouts"]}
    assert set(by_id) <= cut
    # a printed numeral for every port
    marks = d["views"]["front"]["silkscreen"]
    assert {x["text"] for x in marks if x.get("for", "").startswith("port-") and "text" in x} \
        == {str(n) for n in range(m["ports"])}
    assert sum(1 for x in marks if "path" in x and x.get("for", "").startswith("port-")) == m["ports"]


@pytest.mark.parametrize("name", ["ex4400-24x", "ex4400-48f"])
def test_fibre_columns_pitch_and_lamps(name):
    d = load(name)
    ports = front_ports(d, name)
    xs = sorted({round(p["at"][0], 2) for p in ports})
    assert len(xs) == len(ports) // 2
    steps = {round(b - a, 2) for a, b in zip(xs, xs[1:])}
    if name == "ex4400-24x":
        # Figure 14 (g022907) - twelve columns each its own cage pair, 21.0 mm apart with vents between
        assert len(xs) == 12 and all(s == pytest.approx(21.03, abs=0.05) for s in steps)
    else:
        # Figure 19 (g022661) - four blocks of six columns on the 14.25 mm ganged pitch
        assert len(xs) == 24 and 14.25 in steps
        gutter_steps = [s for s in steps if s != 14.25]
        assert gutter_steps and all(s == pytest.approx(17.6, abs=0.1) for s in gutter_steps)   # 14.25 + 3.35
    # Figures 51 to 53 - each port has a link activity and a status lamp in the belly between the cages
    placements, _ = view_parts(d, "front")
    lamps = [p for p in placements if p["id"].startswith("led-port-")]
    assert len(lamps) == 2 * len(ports)
    for n in range(len(ports)):
        assert {f"led-port-{n}-link", f"led-port-{n}-status"} <= {p["id"] for p in lamps}


def test_24x_carries_its_console_management_and_uplinks_on_the_front():
    # Table 114 and Figure 16: the console, management, USB-A and reset sit left of the cages and the two
    # QSFP28 ports (PIC 1) right of them, on the front panel, because Virtual Chassis ports are not the
    # rear pair of the other models
    d = load("ex4400-24x")
    front, _ = view_parts(d, "front")
    ids = {p["id"] for p in front}
    # the two uplinks are named for their job, because on this face the ports are all `port-N`
    assert {"con", "mgmt", "usb", "reset", "uplink-0", "uplink-1"} <= ids
    q = [p for p in front if p["id"].startswith("uplink-")]
    assert sorted(p["id"] for p in q) == ["uplink-0", "uplink-1"] and {p["ref"] for p in q} == {"std/qsfp-ganged@1"}
    assert {p["group"] for p in q} == {"qsfp28"} and d["groups"]["qsfp28"]["attrs"]["speed"] == "100g"
    assert sum(1 for p in front if p["id"].startswith("led-uplink-")) == 8       # four lamps above each port
    rear, bays = view_parts(d, "rear")
    assert not {p["id"] for p in rear} & {"con", "mgmt", "usb", "reset", "uplink-0", "uplink-1", "qsfp-0", "qsfp-1"}
    assert [b["id"] for b in bays] == ["fan-0", "fan-1", "psu-0", "psu-1"]


@pytest.mark.parametrize("name", ["ex4400-48f", "ex4400-24mp", "ex4400-48mp"])
def test_the_rear_of_the_others_is_the_family_rear(name):
    d = load(name)
    placements, bays = view_parts(d, "rear")
    ids = {p["id"] for p in placements}
    assert {"con", "mgmt", "usb", "reset", "qsfp-0", "qsfp-1", "ground-mark", "esd-jack"} <= ids
    assert [b["id"] for b in bays] == ["fan-0", "fan-1", "psu-0", "psu-1"]
    sizes = {b["id"]: (b["size"]["w"], b["size"]["h"]) for b in bays}
    assert sizes["fan-0"] == pytest.approx((41.8, 41.8), abs=0.1)
    assert sizes["psu-0"] == pytest.approx((83.06, 40.39), abs=0.05)


@pytest.mark.parametrize("name", LATER_NAMES)
def test_later_status_block_and_extension_slot(name):
    d = load(name)
    placements, bays = view_parts(d, "front")
    ids = {p["id"] for p in placements}
    assert {"led-sys", "led-alm", "led-mst", "led-cld", "led-spd", "led-dx", "led-en", "usb-c", "mode-button"} <= ids
    assert ("led-poe" in ids) == LATER[name]["poe"]
    assert [b["id"] for b in bays if b["id"] == "ext-module"] == ["ext-module"]
    ext = [b for b in bays if b["id"] == "ext-module"][0]
    assert {a.split("/")[-1].split("@")[0] for a in ext["accepts"]} == set(EXTENSION_MODULES) | {"ex4400-em-cover"}
    assert ext["default"] == "juniper/ex4400-em-cover@1"
    # Figures 14, 19, 37 and 41 print the model number or the MG PoE++ name beside the USB-C port
    text = " ".join(s["text"] for s in d["views"]["front"]["silkscreen"] if "text" in s and s.get("for") == "chassis")
    assert {"ex4400-24x": "EX4400-24X", "ex4400-48f": "EX4400-48F",
            "ex4400-24mp": "MG PoE++", "ex4400-48mp": "MG PoE++"}[name] in text


@pytest.mark.parametrize("name", LATER_NAMES)
def test_later_configurations_and_their_part_numbers(name):
    d = load(name)
    cfgs = d["configurations"]
    orderable = {k: v for k, v in cfgs.items() if v["kind"] == "orderable"}
    assert {k: sorted(v["part-numbers"]) for k, v in orderable.items()} \
        == {k: [v] for k, v in LATER[name]["configs"].items()}
    assert [k for k, v in cfgs.items() if v.get("default")] == ["ac"]
    assert all(v["kind"] == "example" for k, v in cfgs.items() if k not in orderable)
    assert cfgs["em-4y"]["bays"] == {"ext-module": "juniper/ex4400-em-4y@1"}


@pytest.mark.parametrize("name", LATER_NAMES)
def test_later_shipped_configuration_seats_the_supply_and_fans_the_guide_ships(name):
    d = load(name)
    m = LATER[name]
    # Tables 14, 17, 29 and 32: one supply, two front-to-back fan modules, a cover on the empty slot
    assert seated(d, "ac", "psu-0") == m["psu"]
    assert seated(d, "ac", "psu-1") == "ex4400-psu-cover"
    assert seated(d, "ac", "fan-0") == seated(d, "ac", "fan-1") == "ex4400-fan-afo"
    assert component(m["psu"])["attrs"]["power-output-w"] == m["watts"]
    accepted = {a.split("/")[-1].split("@")[0] for a in bay(d, "psu-0")["accepts"]}
    assert accepted == m["accepts_psu"] | {"ex4400-psu-cover"}
    if "s" in m["configs"]:
        for b in ("fan-0", "fan-1", "psu-0", "psu-1"):
            assert seated(d, "s", b) == ""


@pytest.mark.parametrize("name", LATER_NAMES)
def test_later_every_orderable_seats_parts_of_its_airflow_and_feed(name):
    d = load(name)
    for cfg_name in LATER[name]["configs"]:
        cfg = d["configurations"][cfg_name]
        airflow = cfg.get("airflow") or d["chassis"].get("airflow")
        for bay_id in ("fan-0", "fan-1", "psu-0"):
            part = seated(d, cfg_name, bay_id)
            if not part:
                assert cfg_name == "s"
                continue
            c = component(part)
            assert c["attrs"]["airflow"] == airflow, (cfg_name, bay_id, part)
            if bay_id == "psu-0":
                assert c["attrs"]["role"] == f"{cfg['power']}-power-supply", (cfg_name, part)
    if name in ("ex4400-24x", "ex4400-48f"):
        # Tables 14 and 17 - the -AFI builds are back to front with blue handles, the DC builds take DC supplies
        assert seated(d, "afi", "fan-0") == "ex4400-fan-afi" and seated(d, "afi", "psu-0") == "jpsu-550-c-ac-afi"
        assert seated(d, "dc", "psu-0") == "jpsu-550-c-dc-afo"
        assert seated(d, "dc-afi", "psu-0") == "jpsu-550-c-dc-afi"
    else:
        # Tables 29 and 32 list no back-to-front or DC build of the multigigabit models
        assert sorted(k for k, v in d["configurations"].items() if v["kind"] == "orderable") == ["ac", "s"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_later_dcim_exports_one_device_type_per_orderable_configuration(target):
    want = {pn: n for n, m in LATER.items() for pn in m["configs"].values()}
    got = {}
    for f in device_type_files(target):
        doc = yaml.safe_load(f.read_text())
        if doc["model"].startswith(LATER_PREFIXES):
            got[doc["model"]] = doc
    assert set(got) == set(want)
    for model, doc in got.items():
        assert doc["manufacturer"] == "Juniper"
        assert doc["u_height"] == 1.0          # Tables 15, 18, 30, 33 - 1.72 in, one rack unit
        types = [i["type"] for i in doc["interfaces"] if i["name"].startswith("port-")]
        base = want[model]
        if base == "ex4400-24x":
            assert types == ["10gbase-x-sfpp"] * 24
        elif base == "ex4400-48f":
            assert types.count("1000base-x-sfp") == 36 and types.count("10gbase-x-sfpp") == 12
        elif base == "ex4400-24mp":
            assert types == ["10gbase-t"] * 24
        else:
            assert types.count("2.5gbase-t") == 36 and types.count("10gbase-t") == 12
        assert sum(1 for i in doc["interfaces"] if i["type"] == "100gbase-x-qsfp28") == 2
