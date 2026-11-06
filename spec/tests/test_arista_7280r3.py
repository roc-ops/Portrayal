"""The rest of the Arista 7280R3 line: seven 1RU and 2RU fixed switch routers (#1204, slice 1).

One device a front panel, `arista/<model>`: the 7280PR3-24, 7280DR3-24, 7280CR3-32P4, 7280CR3-36S,
7280SR3-48YC8, 7280SR3-40YC6 and 7280CR3-96. The K, K-A and E-M builds share their base model's front
figure (guide Appendix C), size (Table 1) and supplies (Table 4), so they are `kind: orderable`
configurations of it with their own part numbers, each in its front-to-rear (-F) and rear-to-front (-R)
builds where the data sheet lists both. The 7280TR3-40C6 has no front figure in the guide and is in
`test_arista_7280r3_rest.py`.
The expected figures are Arista's: the 7280R3 Series Quick Start Guide (DOC-07041-01, Table 1 for the
envelope, Tables 3 and 4 for the supplies, Appendix C and D for the faces) and the 7280R3 Series Data Sheet
(03-0045-59, 11 August 2025: the model comparison tables and the ordering information). The 7280CR3-32D4 is
the sibling already on main and has its own module, `test_arista_7280cr3_32d4.py`.
Each test reads the YAML a contributor edits, or the generated export a DCIM user imports.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

P15 = ("arista/7280r3-pwr-1500-ac@1", None, "arista/7280r3-pwr-1500-dc@1", None)
P10 = ("arista/7280cr3-pwr-1000-ac@1", "arista/7280cr3-pwr-1000-ac-rev@1",
       "arista/7280cr3-pwr-1000-dc@1", "arista/7280cr3-pwr-1000-dc-rev@1")
P05 = ("arista/7280r3-pwr-500-ac@1", "arista/7280r3-pwr-500-ac-rev@1",
       "arista/7280r3-pwr-500-dc@1", "arista/7280r3-pwr-500-dc-rev@1")
P24 = ("arista/7280dr3a-pwr-2400-ac@1", None, "arista/7280dr3a-pwr-2400-dc@1", None)
F11H = ("arista/7280cr3-fan@1", "arista/7280cr3-fan-rev@1")
F11H_ONLY = ("arista/7280cr3-fan@1", None)
F11M = ("arista/7280r3-fan-m@1", "arista/7280r3-fan-m-rev@1")
F36 = ("arista/7280r3-fan-m@1", "arista/7280cr3-fan-rev@1")   # the 36S: M forward, H reverse
F12H = ("arista/7280dr3a-fan@1", None)

QSFP, QSFPDD, OSFP, SFP = "std/qsfp-ganged@1", "std/qsfp-dd@1", "std/osfp@1", "std/sfp-ganged@1"

# device -> what the guide and the data sheet say of it
D = {
    "7280pr3-24": dict(
        model="7280PR3-24", family="7280R3", depth=582.0, ru=1, weight="12.7 kg", power=(650, 1100),
        cages=[(OSFP, 1, 24, "osfp-400g", True)], lamps=0, mgmt="rear", psu=P15, fan=F11H_ONLY, nfans=3,
        orderable={"f": ("DCS-7280PR3-24-F", "front-to-back"), "k-f": ("DCS-7280PR3K-24-F", "front-to-back")},
        example=["dc-f"], u=1.0),
    "7280dr3-24": dict(
        model="7280DR3-24", family="7280R3", depth=574.0, ru=1, weight="13.1 kg", power=(560, 1110),
        cages=[(QSFPDD, 1, 24, "qsfpdd-400g", True)], lamps=0, mgmt="rear", psu=P15, fan=F11H_ONLY, nfans=3,
        orderable={"f": ("DCS-7280DR3-24-F", "front-to-back"), "k-f": ("DCS-7280DR3K-24-F", "front-to-back")},
        example=["dc-f"], u=1.0),
    "7280cr3-32p4": dict(
        model="7280CR3-32P4", family="7280CR3", depth=558.3, ru=1, weight="12.3 kg", power=(535, 851),
        cages=[(QSFP, 1, 32, "qsfp28", True), (OSFP, 33, 36, "osfp-400g", True)], lamps=128, mgmt="rear",
        psu=P10, fan=F11H, nfans=3,
        orderable={"f": ("DCS-7280CR3-32P4-F", "front-to-back"), "r": ("DCS-7280CR3-32P4-R", "back-to-front"),
                   "k-f": ("DCS-7280CR3K-32P4-F", "front-to-back"), "k-r": ("DCS-7280CR3K-32P4-R", "back-to-front"),
                   "k-a-f": ("DCS-7280CR3K-32P4A-F", "front-to-back"),
                   "k-a-r": ("DCS-7280CR3K-32P4A-R", "back-to-front")},
        example=["dc-f", "dc-r"], u=1.0),
    "7280cr3-36s": dict(
        model="7280CR3-36S", family="7280CR3", depth=471.7, ru=1, weight="10.5 kg", power=(254, 423),
        cages=[(QSFP, 1, 34, "qsfp28", True), (QSFPDD, 35, 36, "qsfpdd-400g", True)], lamps=0, mgmt="front",
        psu=P10, fan=F36, nfans=2,
        orderable={"f": ("DCS-7280CR3-36S-F", "front-to-back"), "r": ("DCS-7280CR3-36S-R", "back-to-front"),
                   "k-f": ("DCS-7280CR3K-36S-F", "front-to-back"),
                   "k-a-f": ("DCS-7280CR3K-36A-F", "front-to-back"),
                   "k-a-r": ("DCS-7280CR3K-36A-R", "back-to-front")},
        example=["dc-f", "dc-r"], u=1.0),
    "7280sr3-48yc8": dict(
        model="7280SR3-48YC8", family="7280SR3", depth=467.0, ru=1, weight="9.2 kg", power=(155, 325),
        cages=[(SFP, 1, 48, "sfp28", True), (QSFP, 49, 56, "qsfp28", True)], lamps=80, mgmt="rear",
        psu=P05, fan=F11M, nfans=2,
        orderable={"f": ("DCS-7280SR3-48YC8-F", "front-to-back"), "r": ("DCS-7280SR3-48YC8-R", "back-to-front"),
                   "k-f": ("DCS-7280SR3K-48YC8-F", "front-to-back"),
                   "k-r": ("DCS-7280SR3K-48YC8-R", "back-to-front"),
                   "k-a-f": ("DCS-7280SR3K-48YC8A-F", "front-to-back"),
                   "k-a-r": ("DCS-7280SR3K-48YC8A-R", "back-to-front")},
        example=["dc-f", "dc-r"], u=1.0),
    "7280sr3-40yc6": dict(
        model="7280SR3-40YC6", family="7280SR3", depth=469.0, ru=1, weight="9.57 kg", power=(130, 214),
        cages=[(SFP, 1, 40, "sfp28", True), (QSFP, 41, 46, "qsfp28", True)], lamps=40, mgmt="rear",
        psu=P05, fan=F11M, nfans=2,
        orderable={"f": ("DCS-7280SR3-40YC6-F", "front-to-back"), "r": ("DCS-7280SR3-40YC6-R", "back-to-front"),
                   "m-f": ("DCS-7280SR3E-40YC6-M-F", "front-to-back"),
                   "m-r": ("DCS-7280SR3E-40YC6-M-R", "back-to-front")},
        example=["dc-f", "dc-r"], u=1.0),
    "7280cr3-96": dict(
        model="7280CR3-96", family="7280CR3", depth=761.0, ru=2, weight="23.6 kg", power=(1003, 1803),
        cages=[(QSFP, 1, 80, "qsfp28", True), (QSFP, 81, 96, "qsfp28", False)], lamps=0, mgmt="front",
        psu=P24, fan=F12H, nfans=4,
        orderable={"f": ("DCS-7280CR3-96-F", "front-to-back"), "k-f": ("DCS-7280CR3K-96-F", "front-to-back")},
        example=["dc-f"], u=2.0),
}
HEIGHT = {"7280sr3-48yc8": 43.5, "7280cr3-96": 87.9}
GROUP_ATTRS = {"osfp-400g": {"media": "osfp", "speed": "400g"}, "qsfpdd-400g": {"media": "qsfp-dd", "speed": "400g"},
               "qsfp28": {"media": "qsfp28", "speed": "100g"}, "sfp28": {"media": "sfp28", "speed": "25g"}}
IFACE = {"osfp-400g": "400gbase-x-osfp", "qsfpdd-400g": "400gbase-x-qsfpdd", "qsfp28": "100gbase-x-qsfp28",
         "sfp28": "25gbase-x-sfp28"}
NEW_COMPONENTS = {
    "7280r3-pwr-500-ac": ("PWR-511-AC-RED", "psu", "front-to-back", "ac", 500),
    "7280r3-pwr-500-ac-rev": ("PWR-511-AC-BLUE", "psu", "back-to-front", "ac", 500),
    "7280r3-pwr-500-dc": ("PWR-511-DC-RED", "psu", "front-to-back", "dc", 500),
    "7280r3-pwr-500-dc-rev": ("PWR-511-DC-BLUE", "psu", "back-to-front", "dc", 500),
    "7280r3-pwr-1500-ac": ("PWR-1511-AC-RED", "psu", "front-to-back", "ac", 1500),
    "7280r3-pwr-1500-dc": ("PWR-1511-DC-RED", "psu", "front-to-back", "dc", 1500),
    "7280r3-fan-m": ("FAN-7011M-F", "fan", "front-to-back", None, None),
    "7280r3-fan-m-rev": ("FAN-7011M-R", "fan", "back-to-front", None, None),
}
DEVICES = sorted(D)


def load(dev):
    return yaml.safe_load((LIB / "devices/arista" / dev / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components/arista" / name / "v1/contract.yaml").read_text())


def placements(d, view):
    return (d["views"][view].get("components") or {}).get("placements") or []


def bays(d, view):
    return {b["id"]: b for b in (d["views"][view].get("components") or {}).get("bays") or []}


def cage_map(d, ref, lo, hi):
    return {int(p["id"].split("-")[1]): p for p in placements(d, "front")
            if p["ref"] == ref and p["id"].startswith("port-") and lo <= int(p["id"].split("-")[1]) <= hi}


# ---------------------------------------------------------------- the envelope


@pytest.mark.parametrize("dev", DEVICES)
def test_the_envelope_is_the_guides_table_1_and_the_data_sheets_body(dev):
    """Table 1 gives the size over the ears (48.3 cm); the data sheet gives the body between them,
    43.99 cm, which is what is modelled."""
    x, c = D[dev], load(dev)["chassis"]
    assert c["ru"] == x["ru"]
    assert c["width"] == pytest.approx(440.0, abs=0.5)
    assert c["height"] == pytest.approx(HEIGHT.get(dev, 43.7), abs=0.3)
    assert c["depth"] == pytest.approx(x["depth"], abs=0.5)
    assert (483.0 - c["width"]) / 2 == pytest.approx(21.5, abs=0.5)
    assert load(dev)["attrs"]["physical"]["weight"].startswith(x["weight"])


@pytest.mark.parametrize("dev", DEVICES)
def test_every_face_is_sized_from_the_envelope(dev):
    d = load(dev)
    c, v = d["chassis"], d["views"]
    assert set(v) == {"front", "rear", "top", "bottom", "left", "right"}
    for n in ("front", "rear"):
        assert v[n]["size"] == {"w": c["width"], "h": c["height"]}, n
    for n in ("top", "bottom"):
        assert v[n]["size"] == {"w": c["width"], "h": c["depth"]}, n
    for n in ("left", "right"):
        assert v[n]["size"] == {"w": c["depth"], "h": c["height"]}, n


@pytest.mark.parametrize("dev", DEVICES)
def test_the_maker_and_the_names_are_as_printed(dev):
    d = load(dev)
    assert d["manufacturer"] == "Arista"
    assert d["model"] == D[dev]["model"]
    assert d["portfolio"] == {"line": "7000 Series", "family": D[dev]["family"]}
    assert d["maturity"] == "modelled"
    assert {"name": f"DCS-{D[dev]['model']}", "kind": "marketing"} in d["aliases"]
    assert d["manufacturer"] == "Arista" and d["chassis"]["airflow"] == "front-to-back"


@pytest.mark.parametrize("dev", DEVICES)
def test_the_device_has_a_layout_source_in_step_with_it(dev):
    assert (LIB / "devices/arista" / dev / "layout.yaml").is_file()


def test_no_variant_is_a_device_of_its_own():
    """A K, K-A or E-M build with its base model's face is a configuration of it (the same hardware
    under another part number). The 7280TR3-40C6 has a face of its own and is in
    `test_arista_7280r3_rest.py`."""
    names = {p.name for p in (LIB / "devices/arista").iterdir()}
    for n in ("7280pr3k-24", "7280dr3k-24", "7280cr3k-32p4", "7280cr3k-36s", "7280sr3k-48yc8",
              "7280sr3e-40yc6-m", "7280cr3k-96"):
        assert n not in names, n
    assert set(D) <= names


# ------------------------------------------------------------------ the front


@pytest.mark.parametrize("dev", DEVICES)
def test_the_front_has_every_port_with_its_cage_and_numbering(dev):
    d = load(dev)
    total = 0
    for ref, lo, hi, group, stacked in D[dev]["cages"]:
        cages = cage_map(d, ref, lo, hi)
        assert sorted(cages) == list(range(lo, hi + 1)), (dev, group)
        total += len(cages)
        for n, p in cages.items():
            assert p["rel-pos"] == n and p["group"] == group, (dev, n)
        if stacked:
            for n, p in cages.items():
                if n % 2 == 1 and n + 1 in cages and ref != OSFP:
                    q = cages[n + 1]
                    assert p["at"][1] < q["at"][1] and p["at"][0] == q["at"][0], (dev, n)
                    # the library's belly-to-belly convention: upper upright, lower turned 180
                    assert p.get("rotate", 0) == 0 and q.get("rotate") == 180, (dev, n)
                if n % 2 == 1 and n + 1 in cages and ref == OSFP:
                    assert p.get("rotate", 0) == cages[n + 1].get("rotate", 0)
        else:
            xs = [cages[n]["at"][0] for n in range(lo, hi + 1)]
            assert xs == sorted(xs) and len(set(cages[n]["at"][1] for n in cages)) == 1, (dev, group)
        assert d["groups"][group]["attrs"] == GROUP_ATTRS[group], (dev, group)
    assert total == sum(hi - lo + 1 for _, lo, hi, _, _ in D[dev]["cages"])


@pytest.mark.parametrize("dev", DEVICES)
def test_a_column_pitch_is_the_registrys_and_the_cages_abut_or_gutter(dev):
    """qsfp-ganged 19.0 mm, sfp-ganged 14.25 mm (its cages abut) inside a block; a wider gutter between."""
    d = load(dev)
    for ref, lo, hi, group, stacked in D[dev]["cages"]:
        want = {QSFP: 19.0, SFP: 14.25}.get(ref)
        if want is None:
            continue
        cages = cage_map(d, ref, lo, hi)
        xs = sorted({p["at"][0] for p in cages.values()})
        steps = [round(b - a, 2) for a, b in zip(xs, xs[1:])]
        assert steps and all(s >= want - 0.02 for s in steps), (dev, ref)
        if (dev, ref) != ("7280sr3-40yc6", QSFP):
            # the 40YC6's three QSFP columns are drawn in wider bezels on a 25.4 mm pitch (figure C-7)
            assert min(steps) == pytest.approx(want, abs=0.02), (dev, ref)
        else:
            assert steps == [25.4, 25.4]


@pytest.mark.parametrize("dev", DEVICES)
def test_every_cage_has_its_numeral(dev):
    d = load(dev)
    n_ports = sum(hi - lo + 1 for _, lo, hi, _, _ in D[dev]["cages"])
    printed = {s["for"]: s["text"] for s in d["views"]["front"]["silkscreen"]
               if str(s.get("for", "")).startswith("port-") and s.get("text")}
    assert printed == {f"port-{n}": str(n) for n in range(1, n_ports + 1)}


@pytest.mark.parametrize("dev", DEVICES)
def test_port_lamps_are_those_the_guides_figure_draws(dev):
    d = load(dev)
    lamps = [p for p in placements(d, "front") if p["id"].startswith("led-port-")]
    assert len(lamps) == D[dev]["lamps"]
    if lamps:
        assert all(p["group"] == "port-leds" and p["for"].startswith("port-") for p in lamps)
        assert len({p["rel-pos"] for p in lamps}) == len(lamps)
    else:
        assert "port-leds" not in d["groups"]
        assert [g for g in d["gaps"] if g["what"] in ("port-lamps",)], dev


@pytest.mark.parametrize("dev", DEVICES)
def test_the_front_carries_four_status_lamps_beyond_every_cage(dev):
    d = load(dev)
    ps = {p["id"]: p for p in placements(d, "front")}
    ids = ("led-system", "led-fan", "led-ps1", "led-ps2")
    for i in ids:
        assert i in ps and ps[i]["group"] == "status-leds", i
    assert [ps[i]["rel-pos"] for i in ids] == [1, 2, 3, 4]
    size = {QSFP: (19.0, 10.0), QSFPDD: (19.0, 10.0), OSFP: (23.1, 13.5), SFP: (14.25, 10.4)}
    for p in placements(d, "front"):
        if p["ref"] in size:
            w, h = size[p["ref"]]
            for i in ids:
                x, y = ps[i]["at"]
                assert not (p["at"][0] <= x <= p["at"][0] + w and p["at"][1] <= y <= p["at"][1] + h), (dev, i)


@pytest.mark.parametrize("dev", DEVICES)
def test_the_management_ports_are_where_the_guides_figures_put_them(dev):
    """Figures C-5 and C-8 draw the console, USB and Ethernet management ports on the front; the other
    five faces have them at the rear (figure D-1 and D-2 callout 3 'Management ports')."""
    d = load(dev)
    face = D[dev]["mgmt"]
    other = "rear" if face == "front" else "front"
    ps = {p["id"]: p for p in placements(d, face)}
    assert {"console", "usb", "mgmt"} <= set(ps)
    assert ps["mgmt"]["ref"] == "common/rj45-eth@1" and ps["console"]["ref"] == "std/rj45@2"
    assert ps["usb"]["ref"] == "std/usb-a@1"
    assert not {"console", "usb", "mgmt"} & {p["id"] for p in placements(d, other)}
    assert d["groups"]["mgmt"]["role"] == "management"


@pytest.mark.parametrize("dev", DEVICES)
def test_the_front_prints_the_model_and_reserves_the_logo_zone(dev):
    d = load(dev)
    front = d["views"]["front"]
    assert D[dev]["model"] in {s.get("text") for s in front["silkscreen"]}
    zones = [r for r in front.get("regions") or [] if r["id"] == "logo-zone"]
    assert len(zones) == 1 and "not drawn" in zones[0]["label"]
    for name, v in d["views"].items():
        drawn = list(v.get("silkscreen") or []) + list((v.get("panel") or {}).get("decor") or [])
        assert "ARISTA" not in {str(i.get("text", "")).upper() for i in drawn}, name


# ------------------------------------------------------------------- the rear


@pytest.mark.parametrize("dev", DEVICES)
def test_each_bay_takes_the_modules_the_guide_lists(dev):
    d, x = load(dev), D[dev]
    b = bays(d, "rear")
    nfan = x["nfans"]
    assert sorted(b) == sorted([f"fan-{i}" for i in range(1, nfan + 1)] + ["psu-1", "psu-2"])
    fwd, rev = x["fan"]
    for i in range(1, nfan + 1):
        assert sorted(b[f"fan-{i}"]["accepts"]) == sorted(m for m in (fwd, rev) if m), (dev, i)
        assert b[f"fan-{i}"]["default"] == fwd
    ac, ac_r, dc, dc_r = x["psu"]
    for i in (1, 2):
        assert sorted(b[f"psu-{i}"]["accepts"]) == sorted(m for m in x["psu"] if m), (dev, i)
        assert b[f"psu-{i}"]["default"] == ac
    # the fans sit on an even pitch between the supplies
    xs = [b[f"fan-{i}"]["at"][0] for i in range(1, nfan + 1)]
    gaps = [round(q - p, 1) for p, q in zip(xs, xs[1:])]
    if x["ru"] == 1 and nfan == 3:
        assert gaps[0] == pytest.approx(gaps[1], abs=0.2)
    for ref in [m for m in (fwd, rev) + x["psu"] if m]:
        ns, name = ref.split("@")[0].split("/")
        assert (LIB / "components" / ns / name / "v1/contract.yaml").is_file(), ref


def test_the_96_rear_has_the_two_supplies_stacked_at_the_right_and_a_grounding_strip():
    d = load("7280cr3-96")
    b = bays(d, "rear")
    assert b["psu-1"]["at"][0] == b["psu-2"]["at"][0] > max(b[f"fan-{i}"]["at"][0] for i in (1, 2, 3, 4))
    assert b["psu-1"]["at"][1] < b["psu-2"]["at"][1]
    assert {p["id"] for p in placements(d, "rear")} == {"ground-1", "ground-2"}


def test_the_36s_rear_has_no_management_block_because_the_front_carries_it():
    d = load("7280cr3-36s")
    assert placements(d, "rear") == []
    assert not (d["views"]["rear"].get("panel") or {}).get("cutouts")


def test_the_new_modules_carry_the_data_sheets_part_numbers_airflow_and_ratings():
    for name, (pn, cls, airflow, inp, watts) in NEW_COMPONENTS.items():
        c = contract(name)
        assert list(c["part-numbers"]) == [pn] and c["class"] == cls, name
        assert c["attrs"]["airflow"] == airflow, name
        assert "size" in (c.get("provenance") or {}), name
        if cls == "psu":
            assert c["attrs"]["power-output-w"] == watts and c["attrs"]["input"] == inp, name
            assert c["size"] == {"w": 73.5, "h": 40.0}, name
        # the handle: red for an air-exit module, blue for an air-inlet one (guide section 2.1)
        finish = c["fields"]["handle-finish"]["default"].lower()
        r, g, b = (int(finish[i:i + 2], 16) for i in (1, 3, 5))
        assert (r > b) == (airflow == "front-to-back"), name


def test_the_new_components_are_family_prefixed_and_none_copies_an_existing_part_number():
    root = LIB / "components/arista"
    mine = sorted(p.name for p in root.iterdir() if p.name.startswith("7280r3-"))
    assert mine == sorted(NEW_COMPONENTS)
    seen = {}
    for p in root.iterdir():
        for pn in (contract(p.name).get("part-numbers") or {}):
            seen.setdefault(pn, []).append(p.name)
    assert not {pn: n for pn, n in seen.items() if len(n) > 1}, "a part number is modelled twice"


# ------------------------------------------------------------ configurations


@pytest.mark.parametrize("dev", DEVICES)
def test_the_orderable_configurations_are_the_datasheets_part_numbers(dev):
    cf = load(dev)["configurations"]
    x = D[dev]
    assert {n for n, c in cf.items() if c["kind"] == "orderable"} == set(x["orderable"])
    for name, (pn, _) in x["orderable"].items():
        assert list(cf[name]["part-numbers"]) == [pn], name
    for n in x["example"]:
        assert cf[n]["kind"] == "example" and "part-numbers" not in cf[n], n
    assert [n for n, c in cf.items() if c.get("default")] == ["base"]
    assert cf["base"]["kind"] == "base"


@pytest.mark.parametrize("dev", DEVICES)
def test_each_configuration_seats_matching_supplies_and_fans_for_its_airflow(dev):
    d, x = load(dev), D[dev]
    cf = d["configurations"]
    ac, ac_r, dc, dc_r = x["psu"]
    fwd, rev = x["fan"]
    for name, c in cf.items():
        seat = c.get("bays") or {}
        rtf = c.get("airflow") == "back-to-front"
        is_dc = c.get("power") == "dc"
        psu = {(False, False): ac, (True, False): ac_r, (False, True): dc, (True, True): dc_r}[(rtf, is_dc)]
        assert psu, (dev, name)
        if not rtf and not is_dc:
            assert not seat, (dev, name)   # the default seating is the AC, front-to-rear one
            continue
        assert seat["psu-1"] == seat["psu-2"] == psu, (dev, name)
        if rtf:
            assert {seat[f"fan-{i}"] for i in range(1, x["nfans"] + 1)} == {rev}, (dev, name)
        else:
            assert not [k for k in seat if k.startswith("fan-")], (dev, name)
    for name, (pn, airflow) in x["orderable"].items():
        assert cf[name].get("airflow", "front-to-back") == airflow, name


@pytest.mark.parametrize("dev", DEVICES)
def test_the_device_carries_the_base_models_power_figure(dev):
    p = load(dev)["attrs"]["power"]
    assert (p["power-typical-w"], p["power-max-w"]) == D[dev]["power"]


def test_the_a_builds_state_their_own_power_figure_in_their_attrs():
    """Guide Table 4: the 36A draws 262 / 437 W and the 48YC8A 162 / 338 W, against the base figures;
    each A build states its own in `attrs`, and the device keeps the base model's (the test above)."""
    for dev, own in (("7280cr3-36s", (262, 437)), ("7280sr3-48yc8", (162, 338))):
        cf = load(dev)["configurations"]
        for n in ("k-a-f", "k-a-r"):
            p = cf[n]["attrs"]["power"]
            assert (p["power-typical-w"], p["power-max-w"]) == own, (dev, n)


def test_the_e_m_build_has_the_40yc6_face_and_its_own_part_numbers():
    cf = load("7280sr3-40yc6")["configurations"]
    assert list(cf["m-f"]["part-numbers"]) == ["DCS-7280SR3E-40YC6-M-F"]
    assert list(cf["m-r"]["part-numbers"]) == ["DCS-7280SR3E-40YC6-M-R"]


# ------------------------------------------------------------------ the DCIM


def _exported(target, dev):
    folder = LIB / "exports" / target / "device-types" / "Arista"
    return folder, D[dev]["orderable"]


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
@pytest.mark.parametrize("dev", DEVICES)
def test_the_dcim_types_export_one_per_orderable_configuration_with_the_guides_height(dev, target):
    folder, orderable = _exported(target, dev)
    for pn, _ in orderable.values():
        doc = yaml.safe_load((folder / f"{pn}.yaml").read_text())
        assert doc["manufacturer"] == "Arista" and doc["model"] == pn
        assert doc["u_height"] == D[dev]["u"], pn


def test_no_example_configuration_is_exported_as_a_device_type():
    """The DC builds are worked examples with no part number a DCIM could hold."""
    pns = {pn for dd in D.values() for pn, _ in dd["orderable"].values()}
    for target in ("netbox", "nautobot"):
        folder = LIB / "exports" / target / "device-types" / "Arista"
        for p in folder.glob("DCS-7280*.yaml"):
            if p.stem.startswith(("DCS-7280PR3", "DCS-7280DR3-", "DCS-7280DR3K-", "DCS-7280CR3-32P4",
                                  "DCS-7280CR3K-32P4", "DCS-7280CR3-36S", "DCS-7280CR3K-36",
                                  "DCS-7280SR3", "DCS-7280CR3-96", "DCS-7280CR3K-96")):
                assert p.stem in pns, p.name


@pytest.mark.parametrize("dev", DEVICES)
def test_the_exported_type_lists_every_port_once(dev):
    pn = next(iter(D[dev]["orderable"].values()))[0]
    doc = yaml.safe_load((LIB / "exports/netbox/device-types/Arista" / f"{pn}.yaml").read_text())
    types = {i["name"]: i["type"] for i in doc["interfaces"]}
    total = sum(hi - lo + 1 for _, lo, hi, _, _ in D[dev]["cages"])
    assert {f"port-{n}" for n in range(1, total + 1)} <= set(types)
    assert f"port-{total + 1}" not in types and "port-0" not in types
    for ref, lo, hi, group, _ in D[dev]["cages"]:
        assert {types[f"port-{n}"] for n in range(lo, hi + 1)} == {IFACE[group]}, (dev, group)


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_new_modules_export_as_module_types(target):
    for name, (pn, *_rest) in NEW_COMPONENTS.items():
        path = LIB / "exports" / target / "module-types/Arista" / f"{pn}.yaml"
        mod = yaml.safe_load(path.read_text())
        assert mod["manufacturer"] == "Arista" and mod["part_number"] == pn
