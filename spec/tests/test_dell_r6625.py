"""The Dell PowerEdge R6625 (library/devices/dell/r6625), against Dell's own documents.

Every figure asserted here is one of Dell's three documents for the machine - the
Installation and Service Manual (ISM), the Technical Guide (TG) and the Spec Sheet -
named by its table or figure, so a model that drifts from what Dell publishes fails by
name. Nothing is asserted from a reseller, review or stencil.

These read the manifests and the component contracts, and the committed DCIM exports;
none needs `library/dist`.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices" / "dell" / "r6625" / "device.yaml"
EXPORTS = LIB / "exports"

DOC = yaml.safe_load(DEVICE.read_text())
VIEWS = DOC["views"]
CONFIGS = DOC["configurations"]


def contract(ref):
    """The contract of 'ns/name@major'."""
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / "components" / ns / name / f"v{major}" / "contract.yaml").read_text())


def bays(view):
    return (VIEWS[view].get("components") or {}).get("bays") or []


def placements(view):
    return (VIEWS[view].get("components") or {}).get("placements") or []


def front_of(config):
    return (CONFIGS[config].get("views") or {}).get("front", "front")


# ISM table 10 and TG table 28: the 4, 8 and 10 drive builds
XB, XA, Y = 434.0, 482.0, 42.8          # between the ears, across them, height
ZA_WITHOUT_BEZEL, ZB = 22.0, 751.48     # front face to the ears, ears to the rear wall
DEPTH = ZA_WITHOUT_BEZEL + ZB           # 773.48


# --- the envelope ------------------------------------------------------------

def test_the_chassis_is_the_ism_table_10_envelope():
    ch = DOC["chassis"]
    assert (ch["width"], ch["height"], ch["ru"]) == (XB, Y, 1)
    # the depth is the front face to the rear wall, derived as the R660's is
    assert ch["depth"] == pytest.approx(DEPTH, abs=0.05)


def test_every_front_is_the_482_6_rack_face_because_the_ears_carry_the_panels():
    """ISM tables 1 to 5 list the left and right control panels as front features;
    Xa is 482.0 across the ears, so a face that holds both is the 482.6 rack face
    (the library's rule, #865) and the panels sit in its outer 25 mm."""
    fronts = [n for n, v in VIEWS.items() if n.startswith("front")]
    assert sorted(fronts) == ["front", "front-e3s14", "front-e3s16", "front-lff4",
                              "front-nobp", "front-sff8sf"]
    for n in fronts:
        v = VIEWS[n]
        assert (v["size"]["w"], v["size"]["h"]) == (482.6, Y)
        assert 480.0 <= v["size"]["w"] <= 487.0
        assert abs(v["size"]["w"] - XA) < 1.0
        left = next(b for b in bays(n) if b["id"] == "panel-left")
        assert left["at"][0] + left["size"]["w"] <= 25.0, "the left control panel is in the left ear"
        button = next(p for p in placements(n) if p["id"] == "power-btn")
        assert button["at"][0] >= 457.0, "the power button is in the right control panel"


def test_the_other_faces_are_the_body_and_the_depth():
    assert VIEWS["rear"]["size"] == {"w": XB, "h": Y}
    assert VIEWS["top"]["size"] == {"w": XB, "h": DOC["chassis"]["depth"]}
    for n in ("left", "right"):
        assert VIEWS[n]["size"] == {"w": DOC["chassis"]["depth"], "h": Y}


def test_the_bezel_is_drawn_fitted_and_off_the_drives():
    """ISM table 10: 35.84 ear to front with the bezel, 22.0 without; ISM 'Removing
    the front bezel'. The bezel is `mounts`, drawn fitted over the drives."""
    bezel = contract("dell/bezel-1u-16g@1")
    assert bezel["behaviour"] == "mounts"
    assert bezel["size"]["d"] == pytest.approx(35.84 - 22.0, abs=0.01)


# --- the fronts: ISM figures 1 to 5, 20 and 21, table 74 ---------------------

FRONTS = {
    # view: (bays that hold drives, their group, how the group is numbered)
    "front": (10, "drives"),
    "front-sff8sf": (8, "drives"),
    "front-lff4": (4, "drives-lff"),
    "front-nobp": (0, None),
    "front-e3s16": (16, "drives-e3s"),
    "front-e3s14": (14, "drives-e3s"),
}


def drive_bays(view):
    group = FRONTS[view][1]
    return [b for b in bays(view) if b.get("group") == group] if group else []


@pytest.mark.parametrize("view,want", [(v, w[0]) for v, w in FRONTS.items()], ids=list(FRONTS))
def test_each_front_has_the_bays_the_ism_lists(view, want):
    got = drive_bays(view)
    assert len(got) == want
    assert sorted(b["rel-pos"] for b in got) == list(range(want)), "numbered from 0"
    for b in got:
        assert re.fullmatch(r"(drive|lff|e3s)-\d+", b["id"])
        assert "blank" in b["default"].split("/")[1], \
            "every bay defaults to a blank: Dell publishes no default drive count"


def test_the_lff_front_has_four_3_5_inch_columns_on_a_107_2_pitch():
    got = sorted(drive_bays("front-lff4"), key=lambda b: b["rel-pos"])
    assert [b["id"] for b in got] == ["lff-0", "lff-1", "lff-2", "lff-3"]
    xs = [b["at"][0] for b in got]
    assert [round(b - a, 1) for a, b in zip(xs, xs[1:])] == [107.2] * 3
    # the carrier is drawn wide and fits its bay exactly
    carrier = contract("common/drive-carrier-35@1")["size"]
    for b in got:
        assert (b["size"]["w"], b["size"]["h"]) == (carrier["w"], carrier["h"])
        assert "rotate" not in b
    # ISM figure 1 (callout 3): the VGA connector is in the top strip above the
    # fourth drive, not in the right control panel as on the 2.5 inch fronts
    vga = next(p for p in placements("front-lff4") if p["id"] == "vga")
    assert vga["at"][0] > got[3]["at"][0] and vga["at"][1] < got[3]["at"][1]
    assert "rotate" not in vga


@pytest.mark.parametrize("view,columns", [("front", 5), ("front-sff8sf", 4)])
def test_the_2_5_inch_bays_are_numbered_as_the_service_label_prints_them(view, columns):
    """ISM figures 20 (10 x 2.5) and 21 (8 x 2.5): 0 over 1, 2 over 3, ... column by
    column, the upper bay even."""
    got = {b["rel-pos"]: b for b in drive_bays(view)}
    assert sorted(got) == list(range(2 * columns))
    for n in range(columns):
        upper, lower = got[2 * n], got[2 * n + 1]
        assert upper["id"] == f"drive-{2 * n}" and lower["id"] == f"drive-{2 * n + 1}"
        assert upper["at"][0] == lower["at"][0], "one column"
        assert upper["at"][1] < lower["at"][1], "the even bay is the upper"
    xs = [got[2 * n]["at"][0] for n in range(columns)]
    assert xs == sorted(xs)


def test_the_8_bay_front_has_the_smart_flow_vent_where_figure_21_has_it():
    xs = [b["at"][0] for b in drive_bays("front-sff8sf") if b["rel-pos"] % 2 == 0]
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    assert max(gaps) > 150 and sorted(gaps)[:-1] == pytest.approx([82.85] * 2, abs=0.01), gaps


def test_the_e3s_fronts_are_four_rows_by_four_columns_less_the_14_drive_fillers():
    """ISM figures 4 and 5: the 16-drive front fills four columns of four around a
    centre vent; the 14-drive front's last column ends in a two-slot filler."""
    for view, n in (("front-e3s16", 16), ("front-e3s14", 14)):
        got = drive_bays(view)
        assert len(got) == n
        assert len({b["at"][0] for b in got}) == 4 and len({b["at"][1] for b in got}) == 4
        centre = next(p for p in placements(view) if p["id"] == "centre-vent")
        assert centre["ref"] == "dell/e3s-filler-1u@1"
    filler = next(b for b in bays("front-e3s14") if b["id"] == "e3s-filler-14")
    assert filler["accepts"] == ["dell/e3s-filler-2slot-1u@1"]
    assert not [b for b in bays("front-e3s16") if b["group"] == "fillers"]


def test_the_bezel_hides_exactly_the_drives_of_its_front():
    for view in FRONTS:
        bezel = next(p for p in placements(view) if p["id"] == "bezel")
        assert bezel["ref"] == "dell/bezel-1u-16g@1"
        want = [b["id"] for b in drive_bays(view)]
        assert bezel.get("hides", []) == want, view
        assert set(want) <= set(bezel["for"])
        assert not {"vga", "mark-vga", "centre-vent"} & set(bezel.get("hides", []))


def test_the_no_backplane_front_has_no_drive_bays_and_grilles_instead():
    """ISM table 10 and figure 20: the 0-drive build, drawn as fixed grilles."""
    assert drive_bays("front-nobp") == []
    holes = [d for d in VIEWS["front-nobp"]["panel"]["decor"] if d.get("size") == [4.05, 4.03]]
    assert len(holes) == 245


# --- the configurations: ISM tables 74 and 101, figures 70 and 80 to 83 -------

FRONT_PREFIX = {"sff10": "front", "sff8sf": "front-sff8sf", "lff4": "front-lff4",
                "nobp": "front-nobp", "e3s14": "front-e3s14", "e3s16": "front-e3s16"}
RISER_BUILDS = ["rc1-2a3a", "rc2-2p3p", "rc3-1p4p", "rc4-2q", "rc7-2a"]
REAR_STORAGE = {"sff10": ["rc5-3p-rear2", "rc6-2s3s"], "lff4": ["rc5-3p-rear2", "rc6-2s3s"]}


def expected_builds():
    names = {f"{f}-{rc}" for f in FRONT_PREFIX for rc in RISER_BUILDS}
    names |= {f"{f}-{rc}" for f, rcs in REAR_STORAGE.items() for rc in rcs}
    return names


def test_the_orderable_builds_are_the_fronts_times_the_ism_riser_configurations():
    orderable = {n for n, c in CONFIGS.items() if c["kind"] == "orderable"}
    assert orderable == expected_builds()
    assert len(orderable) == 34
    assert {n for n, c in CONFIGS.items() if c["kind"] != "orderable"} == {"sff10-rc1-2a3a-populated"}


def test_the_default_build_is_the_ten_bay_front_with_riser_configuration_1():
    defaults = [n for n, c in CONFIGS.items() if c.get("default")]
    assert defaults == ["sff10-rc1-2a3a"]
    assert "views" not in CONFIGS["sff10-rc1-2a3a"], "the default front is the view named `front`"


@pytest.mark.parametrize("config", sorted(expected_builds()))
def test_each_build_binds_its_own_front_and_names_itself_as_the_library_does(config):
    prefix = config.split("-")[0]
    assert re.fullmatch(r"(sff10|sff8sf|lff4|nobp|e3s14|e3s16)-rc\d+-[0-9a-z]+(-rear2)?", config), config
    assert front_of(config) == FRONT_PREFIX[prefix]
    assert front_of(config) in VIEWS


def test_rear_storage_is_paired_only_with_the_fronts_the_ism_pairs_it_with():
    """ISM figure 70 (4 x 3.5 inch with rear 2 x E3.S), figures 80 and 82 (10 x 2.5
    inch with rear 2 x 2.5 inch), 81 and 83 (rear 2 x E3.S), TG table 11 (4 x 3.5 inch
    with rear 2 x 2.5 inch): configurations 5 and 6 go with those two fronts only."""
    rear = {n for n in CONFIGS if "-rc5-" in n or "-rc6-" in n}
    assert rear == {"sff10-rc5-3p-rear2", "lff4-rc5-3p-rear2", "sff10-rc6-2s3s", "lff4-rc6-2s3s"}


# --- the rear: ISM tables 16, 100 and 101, figures 6 to 9 and 115 to 124 -----

def rear_bays(config):
    return {b["id"]: b for b in bays("rear") if "only-in" not in b or config in b["only-in"]}


def occupant(config, bay):
    return (CONFIGS[config].get("bays") or {}).get(bay["id"], bay["default"])


def slots_of(config):
    """{riser bay: {slot id: (processor, generation, height)}} of the config's rear."""
    out = {}
    for bid, b in rear_bays(config).items():
        if b["group"] != "risers":
            continue
        got = {}
        for sid, s in (contract(occupant(config, b)).get("bays") or {}).items():
            if sid.startswith("slot-"):
                sl = s["slot"]
                got[sid] = (sl["processor"], sl["generation"], sl["height"])
        out[bid] = got
    return out


RISER_SLOTS = {
    # config: {riser bay: {slot: (processor, PCIe generation, height)}}
    # ISM table 100 (heights and Gen5 marks), table 16 and TG table 18 (processors)
    "rc1-2a3a": {"riser-2": {"slot-1": (1, 4, "low"), "slot-2": (2, 4, "low")},
                 "riser-3": {"slot-3": (2, 4, "low")}},
    "rc2-2p3p": {"riser-2": {"slot-1": (1, 5, "low"), "slot-2": (2, 4, "low")},
                 "riser-3": {"slot-3": (2, 5, "low")}},
    "rc3-1p4p": {"riser-1": {"slot-1": (1, 5, "full")}, "riser-4": {"slot-2": (2, 5, "full")}},
    "rc4-2q": {"riser-2q": {"slot-1": (1, 5, "low"), "slot-2": (2, 5, "low")}},
    "rc5-3p-rear2": {"riser-3": {"slot-3": (2, 5, "low")}},
    "rc6-2s3s": {"riser-2": {"slot-1": (1, 5, "low")}, "riser-3": {"slot-3": (2, 5, "low")}},
    "rc7-2a": {"riser-2": {"slot-1": (1, 4, "low"), "slot-2": (2, 4, "low")}},
}


@pytest.mark.parametrize("config", sorted(expected_builds()))
def test_each_rear_has_its_risers_slots_numbered_as_dell_prints_them(config):
    rc = config.split("-", 1)[1]
    assert slots_of(config) == RISER_SLOTS[rc]


@pytest.mark.parametrize("rc,blank", [("rc4-2q", "riser-3-blank-r2q"), ("rc7-2a", "riser-3-blank")])
def test_the_configurations_without_riser_3_close_its_place_with_a_blank(rc, blank):
    config = f"sff10-{rc}"
    assert blank in rear_bays(config) and "riser-3" not in rear_bays(config)


def test_configuration_5_has_two_rear_2_5_inch_drives_and_6_two_e3s_in_riser_2s():
    rear = rear_bays("sff10-rc5-3p-rear2")
    assert sorted(b for b in rear if b.startswith("rear-drive-")) == ["rear-drive-0", "rear-drive-1"]
    assert "riser-2" not in rear, "the rear drive module is where riser 2 would be"
    r2s = contract(occupant("sff10-rc6-2s3s", rear_bays("sff10-rc6-2s3s")["riser-2"]))
    assert sorted(k for k in r2s["bays"] if k.startswith("e3s-")) == ["e3s-0", "e3s-1"]
    assert not [b for b in rear_bays("sff10-rc6-2s3s") if b.startswith("rear-drive-")]


def test_the_rear_storage_builds_say_where_the_drives_are():
    for n in ("sff10-rc5-3p-rear2", "lff4-rc5-3p-rear2"):
        assert {"rear-drive-0", "rear-drive-1"} <= set(rear_bays(n))
    for n in expected_builds() - {"sff10-rc5-3p-rear2", "lff4-rc5-3p-rear2"}:
        assert not [b for b in rear_bays(n) if b.startswith("rear-drive-")], n


def test_the_ism_riser_numbering_governs_the_left_riser_is_riser_2():
    """ISM tables 6 to 9 call the left riser 'riser 1'; its riser section calls it
    riser 2 (slots 1 and 2) and the right riser 3 (slot 3). The riser section
    governs, as on the R660."""
    r = {b["id"]: b for b in bays("rear")}
    assert r["riser-2"]["at"][0] < r["riser-3"]["at"][0]
    assert r["riser-2"]["rel-pos"] < r["riser-3"]["rel-pos"] < r["riser-4"]["rel-pos"]


# --- the supplies, OCP, LOM, rear I/O and boot module ------------------------

def test_the_supply_bays_accept_the_supplies_ism_table_13_lists():
    """800 W Platinum, 1100 W Titanium and 1400 W Platinum or Titanium are the AC
    supplies on the 60 mm C14 face; the R660's 700 W is not in the R6625's table, and
    the 1100 W DC, 277 V and 1800 W (C15) supplies are not modelled."""
    for bid in ("psu-1", "psu-2"):
        b = next(b for b in bays("rear") if b["id"] == bid)
        watts = sorted(contract(a)["attrs"]["power-output-w"] for a in b["accepts"])
        assert watts == [800, 1100, 1400]
        assert contract(b["default"])["attrs"]["inlet"] == "c14"
    left = next(b for b in bays("rear") if b["id"] == "psu-1")
    right = next(b for b in bays("rear") if b["id"] == "psu-2")
    assert left["at"][0] < 100 and right["at"][0] > 330, "supplies at opposite ends of the rear"
    assert DOC["chassis"]["power"] == "ac"
    assert DOC["groups"]["psus"]["attrs"]["redundancy"] == "1+1"


def test_the_ocp_bay_takes_the_cards_ism_table_21_lists_and_not_the_tg_100g_ones():
    """ISM table 21: OCP 1 GbE x 4, 10 GbE x 2, 10 GbE x 4, 25 GbE x 2, 25 GbE x 4.
    TG table 15 also lists 100 GbE cards; the ISM governs (a sources-disagree gap)."""
    ocp = next(b for b in bays("rear") if b["id"] == "ocp")
    names = {a.split("/")[1].split("@")[0] for a in ocp["accepts"]}
    assert names == {"ocp3-blank-16g", "ocp3-4x1g-rj45", "ocp3-2x10g-rj45", "ocp3-4x10g-rj45",
                     "ocp3-2x25g-sfp28", "ocp3-4x25g-sfp28"}
    assert any(g["what"] == "ocp-100g-listed-by-one-document" and g["reason"] == "sources-disagree"
               for g in DOC["gaps"])


def test_the_lom_the_rear_io_and_the_boot_module_are_the_ism_s_field_replaceable_parts():
    rear = {b["id"]: b for b in bays("rear")}
    assert rear["lom"]["accepts"][0] == "dell/lom-2x1g-16g@1" and rear["lom"]["default"] == "dell/lom-2x1g-16g@1"
    assert "dell/mic-card-16g@1" in rear["lom"]["accepts"]      # ISM figure 186, table 21
    assert rear["rio"]["default"] == "dell/rear-io-board-16g@1"
    assert rear["boss"]["default"] == "dell/boss-n1-blank-1u@1"  # ISM table 6: insert the blank when unused
    assert rear["ocp"]["default"] == "dell/ocp3-blank-16g@1"


# --- the top view: ISM figures 10, 11 and 101, tables 95 and 96 --------------

def test_the_top_view_has_24_dimm_sockets_named_as_the_memory_label_prints_them():
    """ISM: twelve channels per processor, 24 sockets; tables 95 and 96: A1-A12 on
    processor 1, B1-B12 on processor 2."""
    dimms = [b for b in bays("top") if b["group"] == "memory"]
    ids = {b["id"] for b in dimms}
    assert ids == {f"dimm-{p}{n}" for p in "ab" for n in range(1, 13)}
    assert all(b["accepts"] == ["common/dimm-plan@1"] for b in dimms)
    # seen from above, rear at the top: six sockets at the left (all processor 2's), twelve
    # between the heatsinks (six of each) and six at the right (all processor 1's)
    left = [b["id"] for b in dimms if b["at"][0] < 100]
    middle = [b["id"] for b in dimms if 100 < b["at"][0] < 330]
    right = [b["id"] for b in dimms if b["at"][0] > 330]
    assert (len(left), len(middle), len(right)) == (6, 12, 6)
    assert all(i.startswith("dimm-b") for i in left) and all(i.startswith("dimm-a") for i in right)
    assert sum(i.startswith("dimm-b") for i in middle) == 6
    # figure 101: the middle run reads B2 B6 B4 B10 B8 B12 then A11 A7 A9 A3 A5 A1
    run = [b["id"] for b in sorted((b for b in dimms if 100 < b["at"][0] < 330), key=lambda b: b["at"][0])]
    assert run == ["dimm-" + s.lower() for s in "B2 B6 B4 B10 B8 B12 A11 A7 A9 A3 A5 A1".split()]


def test_the_top_view_has_four_fan_modules_and_two_heatsinks_over_the_sockets():
    """ISM, cooling fan specifications: up to four sets of dual fan modules; two
    processors, one heatsink each (ISM tables 12 and 33)."""
    fans = [b for b in bays("top") if b["group"] == "fans"]
    assert [b["id"] for b in fans] == ["fan-1", "fan-2", "fan-3", "fan-4"]
    sinks = [p for p in placements("top") if p["group"] == "processors"]
    assert sorted(p["id"] for p in sinks) == ["heatsink-1", "heatsink-2"]
    # CPU 1 on the right as the front faces you, CPU 2 on the left
    xs = {p["id"]: p["at"][0] for p in sinks}
    assert xs["heatsink-2"] < 217 < xs["heatsink-1"]
    assert DOC["groups"]["fans"]["attrs"]["redundancy"] == "n+1"      # TG, thermal features


def test_the_top_view_carries_the_plan_projections_of_the_rear_and_front_parts():
    plans = {b["id"] for v in ("rear", "front") for b in bays(v) if b.get("plan")}
    assert {"psu-1", "psu-2", "boss", "ocp", "lom", "rio", "riser-2", "riser-3", "drive-0"} <= plans
    top = {p["id"] for p in placements("top")}
    assert {"system-board", "air-shroud", "fan-bracket", "system-cover", "backplane-cover"} <= top


# --- the parts -----------------------------------------------------------------

NEW = ["r6625-system-board", "r6625-heatsink", "r6625-air-shroud"]


@pytest.mark.parametrize("name", NEW)
def test_the_new_components_are_model_prefixed_and_say_where_their_figures_came_from(name):
    c = contract(f"dell/{name}@1")
    assert c["name"] == name
    text = yaml.safe_dump(c["provenance"])
    assert "ISM" in text or "Installation and Service Manual" in text
    assert c["size"]["w"] > 0 and c["size"]["h"] > 0


def test_the_heatsink_is_not_the_r660s_and_does_not_overlap_the_shroud():
    hs, r660 = contract("dell/r6625-heatsink@1"), contract("dell/heatsink-1u-16g@1")
    assert (hs["size"]["w"], hs["size"]["h"]) != (r660["size"]["w"], r660["size"]["h"])
    top = {p["id"]: p for p in placements("top")}
    sink = top["heatsink-1"]
    assert sink["at"][1] + hs["size"]["h"] <= top["air-shroud"]["at"][1] + 1e-6


# --- the DCIM device types: one per distinct chassis, 1U, full depth ----------

def bay_signature(config):
    """The exporter's own identity of a configuration (dcim_export.bay_signature): the
    ids of the bays it renders on the faces it binds. Two builds that differ only in
    what is seated - riser 2P for 2A - are one device type; an example is none."""
    front = front_of(config)
    ids = {b["id"] for b in bays(front)}
    ids |= set(rear_bays(config))
    ids |= {b["id"] for b in bays("top")}
    return tuple(sorted(ids))


def test_the_orderable_builds_make_26_distinct_chassis():
    """Six fronts by four rear layouts that differ in their bays (riser 2 and 3;
    riser 1 and 4; riser 2Q and its blank; riser 2 and a blank), and the rear drive
    module on two of them. Configuration 6 shares configuration 1's bays (the E3.S
    drives are riser 2S's own), as 2P does."""
    assert len({bay_signature(c) for c in expected_builds()}) == 26


@pytest.mark.parametrize("system", ["netbox", "nautobot"])
def test_the_dcim_export_has_one_device_type_per_distinct_configuration(system):
    d = EXPORTS / system / "device-types" / "Dell"
    got = sorted(d.glob("PowerEdge R6625 *.yaml"))
    names = {g.stem.split(" ", 2)[2] for g in got}
    assert len(got) == 26 and names <= expected_builds(), sorted(names - expected_builds())
    # every orderable build is represented by the type of its signature, and no
    # example (a picture, not a product) names a type
    assert {bay_signature(n) for n in names} == {bay_signature(c) for c in expected_builds()}
    assert not [n for n in names if CONFIGS[n]["kind"] != "orderable"]
    for g in got:
        t = yaml.safe_load(g.read_text())
        assert t["manufacturer"] == "Dell"
        assert t["model"] == "PowerEdge R6625 " + g.stem.split(" ", 2)[2]
        assert t["u_height"] == 1.0
        assert t["is_full_depth"] is True
