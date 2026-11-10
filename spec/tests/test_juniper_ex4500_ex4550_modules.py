"""The expansion and uplink modules of the Juniper EX4550 and EX4500 switches.

Five module types: the EX4550's EX4550-EM-8XSFP, EX4550-EM-8XT, EX4550-EM-2QSFP and EX4550-VC-128G, and the
EX4500's 4-port SFP+ uplink module. Each guide draws the faces flat. Each test reads the YAML a contributor edits.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# component -> (model as printed or None, port id prefix, ports, port ref, lamp ref and count, weight as printed or None, size)
MODULES = {
    "ex4550-em-8xsfp": ("EX4550-EM-8XSFP", "port-", 8, "std/sfp-ganged@1", ("common/led-arrow-sm@1", 16), "0.74 lb (0.34 kg)", (86.5, 41.0)),
    "ex4550-em-8xt": ("EX4550-EM-8XT", "port-", 8, "common/rj45-ganged-eth-plain@1", ("common/led-arrow-sm@1", 8), "0.9 lb (0.41 kg)", (86.5, 41.0)),
    "ex4550-em-2qsfp": ("EX4550-EM-2QSFP", "port-", 2, "std/qsfp-ganged@1", ("common/led-dot@1", 5), "0.61 lb (0.28 kg)", (86.5, 41.0)),
    "ex4550-vc-128g": ("EX4550-VC-128G", "vcp-", 2, "juniper/ex4200-vcp-port@1", ("common/led-dot@1", 1), "0.66 lb (0.3 kg)", (86.5, 41.0)),
    "ex4500-uplink-sfp-plus": (None, "port-", 4, "std/sfp-ganged@1", ("common/led-dot@1", 9), None, (151.0, 40.8)),
}
EM = ["ex4550-em-8xsfp", "ex4550-em-8xt", "ex4550-em-2qsfp", "ex4550-vc-128g"]
# device -> (the cover each bay ships, the bays, the modules they take)
DEVICES = {
    "ex4550-32f": ("ex4550-em-cover", ["em-1", "em-2"], EM),
    "ex4550-32t": ("ex4550-em-cover", ["em-1", "em-2"], EM),
    "ex4500-40f": ("ex4500-uplink-cover", ["uplink-1", "uplink-2"], ["ex4500-uplink-sfp-plus"]),
}
EXAMPLES = {
    "ex4550-32f": {"em-8xsfp": {"em-1": "ex4550-em-8xsfp"}, "em-2qsfp": {"em-1": "ex4550-em-2qsfp"}, "vc-128g": {"em-2": "ex4550-vc-128g"}},
    "ex4550-32t": {"em-8xt": {"em-1": "ex4550-em-8xt"}},
    "ex4500-40f": {"uplink-sfp-plus": {"uplink-1": "ex4500-uplink-sfp-plus", "uplink-2": "ex4500-uplink-sfp-plus"}},
}


def contract(name):
    return yaml.safe_load((LIB / "components/juniper" / name / "v1/contract.yaml").read_text())


def device(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "device.yaml").read_text())


def layout(name):
    return yaml.safe_load((LIB / "devices/juniper" / name / "layout.yaml").read_text())


def bays(d):
    return {b["id"]: b for v in d["views"].values() for b in (v.get("components") or {}).get("bays", [])}


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_fills_the_slot_it_goes_in(comp):
    c = contract(comp)
    assert (c["kind"], c["behaviour"]) == ("module", "fills")
    assert c["class"] == ("fabric" if comp == "ex4550-vc-128g" else "line-card")
    assert (c["size"]["w"], c["size"]["h"]) == MODULES[comp][6]
    if MODULES[comp][0]:
        assert c["attrs"]["model"] == MODULES[comp][0]


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_has_the_ports_and_lamps_its_figure_draws(comp):
    _m, prefix, ports, port_ref, (lamp_ref, lamps), _w, _s = MODULES[comp]
    parts = contract(comp)["parts"]
    found = [p for p in parts if p["id"].startswith(prefix)]
    assert len(found) == ports
    assert {p["ref"] for p in found} == {port_ref}
    assert len([p for p in parts if p["ref"] == lamp_ref and p["id"].startswith("led-")]) == lamps


def test_the_eight_port_modules_have_two_rows_of_four():
    """Figures 11 and 12: even numbers on the upper row, odd on the lower, four columns."""
    for comp in ("ex4550-em-8xsfp", "ex4550-em-8xt"):
        ports = {p["id"]: p for p in contract(comp)["parts"] if p["id"].startswith("port-")}
        upper = {i for i, p in ports.items() if p["at"][1] < 15}
        assert upper == {f"port-{n}" for n in (0, 2, 4, 6)}
        assert len({p["at"][0] for p in ports.values()}) == 4


def test_the_virtual_chassis_ports_are_numbered_as_the_face_prints_them():
    """Figure 15: VCP-1 above VCP-0."""
    ports = {p["id"]: p["at"][1] for p in contract("ex4550-vc-128g")["parts"] if p["id"].startswith("vcp-")}
    assert ports["vcp-1"] < ports["vcp-0"]


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_states_what_the_guide_prints_and_no_invented_power(comp):
    c = contract(comp)
    weight = MODULES[comp][5]
    if weight:
        assert c["attrs"]["weight"] == weight
    else:
        assert c["attrs"]["weight-note"] == "not published"
    assert c["attrs"]["power-absent"] == "not-published"
    assert not any(k.startswith("power-draw") for k in c["attrs"])


@pytest.mark.parametrize("comp", MODULES)
def test_each_module_fits_inside_its_slot(comp):
    c = contract(comp)
    w, h = c["size"]["w"], c["size"]["h"]
    for p in c["parts"]:
        assert 0 <= p["at"][0] <= w and 0 <= p["at"][1] <= h


@pytest.mark.heavy
@pytest.mark.parametrize("comp", [m for m in MODULES if MODULES[m][0]])
def test_one_maker_part_number_is_one_component(comp):
    """A part number is never carried by a second component (no twin)."""
    holders = []
    for path in (LIB / "components").glob("*/*/v*/contract.yaml"):
        model = str((yaml.safe_load(path.read_text()).get("attrs") or {}).get("model", ""))
        if model == MODULES[comp][0]:
            holders.append(path.parent.parent.name)
    assert holders == [comp]


@pytest.mark.parametrize("dev", DEVICES)
def test_the_bays_take_the_modules_the_guide_lists_and_ship_the_cover(dev):
    cover, ids, modules = DEVICES[dev]
    found = bays(device(dev))
    for bay_id in ids:
        bay = found[bay_id]
        assert set(bay["accepts"]) == {f"juniper/{cover}@1"} | {f"juniper/{m}@1" for m in modules}
        assert bay["default"] == f"juniper/{cover}@1"
        assert all((bay["size"]["w"], bay["size"]["h"]) == MODULES[m][6] for m in modules)


@pytest.mark.parametrize("dev", EXAMPLES)
def test_example_configurations_seat_each_module_and_none_is_orderable(dev):
    """An example shows a module in the slot; it is an illustration, so it is never an order code."""
    cfgs = device(dev)["configurations"]
    seated = {k: {b: v for b, v in c["bays"].items()} for k, c in cfgs.items() if c.get("kind") == "example" and k in EXAMPLES[dev]}
    assert seated == {k: {b: f"juniper/{m}@1" for b, m in s.items()} for k, s in EXAMPLES[dev].items()}
    assert not any(c.get("part-numbers") for k, c in cfgs.items() if k in EXAMPLES[dev])


@pytest.mark.parametrize("dev", DEVICES)
def test_the_layout_names_the_modules_connector_as_a_gap_and_no_longer_lists_the_modules(dev):
    gaps = {g["what"] for g in layout(dev).get("gaps") or []}
    assert not gaps & {"expansion-modules", "uplink-modules"}
    assert "module-connector" in gaps
