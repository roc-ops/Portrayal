"""Four Juniper EX DC supplies offer a power end: their terminals are seats a ring lug lands on, and each states its DC ports.

Each supply drew its terminal block as art inside its skin, so it offered no place for a DC feed. Each now composes the screws of
that block as parts and states the DC port or ports the vendor's hardware guide describes:

  - juniper/ex4300-jpsu-550-dc-afi@1 and juniper/ex4300-jpsu-550-dc-afo@1 (the EX4300 550 W supplies, one block of five screws
    printed + - earth - +): four terminal screws and one earth screw, and one port per feed, `feed-a` on the left pair and
    `feed-b` on the right pair, the poles `pos` and `neg` the supply prints (V+ and V-); the earth screw between them is common
    to both feeds and is a ground seat outside both ports;
  - juniper/ex4500-psu-dc-fb@1 (a pair of terminals, -48V and RTN): one input port, the poles `batt` and `rtn`;
  - juniper/ex9253-jnp-pwr1100-dc@1 (two studs with nuts, RTN and -48V): one input port, the poles `rtn` and `batt`.

The four devices that seat them take a minor each (the EX4300-32F, the EX4300-48T, the EX4500-40F and the EX9253) and the four
records of the issue that the change closes are gone. These run against the real library, a components index built by the indexer the build runs, and the records file. They read no
library/dist and render nothing.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SCREW = "common/terminal-screw-34@1"
EARTH = "common/ground-screw@1"
LUG = "generic/ring-lug@1"

AFI, AFO = "juniper/ex4300-jpsu-550-dc-afi@1", "juniper/ex4300-jpsu-550-dc-afo@1"
EX4500 = "juniper/ex4500-psu-dc-fb@1"
EX9253 = "juniper/ex9253-jnp-pwr1100-dc@1"

# the seats as (id, part, at): the centre of each terminal the skin already draws, less half the part's own width
EX4300_SEATS = [("pole-a-pos", SCREW, [30.2, 24.7]), ("pole-a-neg", SCREW, [38.6, 24.7]), ("earth", EARTH, [46.0, 23.6]),
                ("pole-b-neg", SCREW, [55.5, 24.7]), ("pole-b-pos", SCREW, [63.9, 24.7])]
EX4300_PORTS = [("feed-a", [("pos", "pole-a-pos"), ("neg", "pole-a-neg")]), ("feed-b", [("neg", "pole-b-neg"), ("pos", "pole-b-pos")])]
EX4500_SEATS = [("pole-batt", SCREW, [6.7, 10.9]), ("pole-rtn", SCREW, [6.7, 25.7])]
EX9253_SEATS = [("pole-rtn", SCREW, [24.2, 10.2]), ("pole-batt", SCREW, [24.2, 25.4])]

# ref -> (version, seats, ports as (id, poles), elements the supply already had)
SUPPLIES = {
    AFI: ("1.1.0", EX4300_SEATS, EX4300_PORTS, ["latch", "led-in-ok", "led-out-ok", "terminal-block"]),
    AFO: ("1.1.0", EX4300_SEATS, EX4300_PORTS, ["latch", "led-in-ok", "led-out-ok", "terminal-block"]),
    EX4500: ("1.1.0", EX4500_SEATS, [("input", [("batt", "pole-batt"), ("rtn", "pole-rtn")])],
             ["led-status", "lever", "term-neg", "term-pos"]),
    EX9253: ("1.1.0", EX9253_SEATS, [("input", [("rtn", "pole-rtn"), ("batt", "pole-batt")])],
             ["handle", "led-status", "tab", "term-a", "term-b"]),
}
# the figures each port states: (voltage, rating-a, awg). None says the contract states none, on purpose.
FIGURES = {
    AFI: ({"nominal": -48, "range": [-40.8, -60]}, None, [14, 16]),
    AFO: ({"nominal": -48, "range": [-40.8, -60]}, None, [14, 16]),
    EX4500: ({"nominal": -48, "range": [-42, -60]}, 30, None),
    EX9253: (None, 32, None),
}
# the skin's own terminals, as the regex that reads their centres in order
CENTRES = {
    AFI: r'<circle class="terminal" id="terminal-\d" cx="([\d.]+)" cy="([\d.]+)" r="2\.2"/>',
    AFO: r'<circle class="terminal" id="terminal-\d" cx="([\d.]+)" cy="([\d.]+)" r="2\.2"/>',
    EX4500: r'<g id="term-(?:neg|pos)">\s*<circle cx="([\d.]+)" cy="([\d.]+)" r="2\.4"',
    EX9253: r'<g id="term-[ab]">\s*<circle cx="([\d.]+)" cy="([\d.]+)" r="4\.3"',
}
# the devices that seat them and the version each is at (a minor, then patches)
DEVICES = {"ex4300-32f": "0.3.0", "ex4300-48t": "0.3.0", "ex4500-40f": "0.4.0", "ex9253": "0.2.0"}
SEATED_BY = {"ex4300-32f": [AFO, AFI], "ex4300-48t": [AFO, AFI], "ex4500-40f": [EX4500], "ex9253": [EX9253]}


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_composes_the_screws_of_its_block_and_nothing_else(ref):
    _, seats, _, _ = SUPPLIES[ref]
    assert contract(ref)["parts"] == [dict(ref=r, id=i, at=at) for i, r, at in seats]


def test_both_screw_parts_present_terminal_stud_and_the_ring_lug_mates_them():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(EARTH)["interface"] == "terminal-stud" and contract(EARTH)["class"] == "ground"
    assert contract(LUG)["mates"] == "terminal-stud"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_seats_stand_at_the_centres_of_the_terminals_the_skin_already_draws(ref):
    _, seats, _, _ = SUPPLIES[ref]
    skin = (path_of(ref) / "skins/default.svg").read_text()
    centres = [[float(x), float(y)] for x, y in re.findall(CENTRES[ref], skin)]
    assert len(centres) == len(seats)
    for (ident, part, at), centre in zip(seats, centres):
        half = contract(part)["size"]["w"] / 2
        assert [round(at[0] + half, 2), round(at[1] + half, 2)] == centre, ident


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_elements_the_version_and_the_description_are_what_the_change_leaves(ref):
    version, _, _, elements = SUPPLIES[ref]
    d = contract(ref)
    assert d["version"] == version
    assert sorted(d["elements"]) == elements
    assert d["attrs"]["inlet"] == "dc-terminal"
    assert d["description"].startswith("Juniper JPSU-550-DC-AF" if ref in (AFI, AFO) else
                                       "The DC power supply of the Juniper EX4500" if ref == EX4500 else "Juniper JNP-PWR1100-DC")


@pytest.mark.parametrize("ref", SUPPLIES)
def test_each_supply_states_its_ports_with_the_roles_it_prints(ref):
    _, _, ports, _ = SUPPLIES[ref]
    got = contract(ref)["dc"]["ports"]
    assert [p["id"] for p in got] == [i for i, _ in ports]
    for port, (_, poles) in zip(got, ports):
        assert port["direction"] == "input"
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles
        assert "side" not in port, "no guide of these supplies names a feed A or B"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_each_port_states_only_the_figures_a_held_table_prints(ref):
    voltage, rating, awg = FIGURES[ref]
    for port in contract(ref)["dc"]["ports"]:
        assert port.get("voltage") == voltage
        assert port.get("rating-a") == rating
        assert port.get("awg") == awg


@pytest.mark.parametrize("ref", [AFI, AFO])
def test_the_shared_earth_screw_of_the_ex4300_block_is_a_ground_seat_outside_both_ports(ref):
    d = contract(ref)
    slots = [q["slot"] for p in d["dc"]["ports"] for q in p["poles"]]
    assert "earth" not in slots and len(slots) == len(set(slots)) == 4
    assert [q["ref"] for q in d["parts"] if q["id"] == "earth"] == [EARTH]
    assert words(d["provenance"]["earth"]).startswith("A DECLARED STAND-IN")


@pytest.mark.parametrize("ref", SUPPLIES)
def test_every_fact_the_ports_state_names_a_provenance_entry_that_says_where_it_came_from(ref):
    d = contract(ref)
    voltage, rating, awg = FIGURES[ref]
    want = {"poles": "poles"}
    if voltage:
        want["voltage"] = "voltage"
    if rating:
        want["rating-a"] = "rating"
    if awg:
        want["awg"] = "awg"
    for port in d["dc"]["ports"]:
        assert port["source"] == want
    for key in set(want.values()) | {"seats", "voltage", "rating", "awg"}:
        assert len(words(d["provenance"][key])) >= 40, key
    for key in ("voltage", "rating", "awg"):
        text = words(d["provenance"][key])
        if key == "voltage" and voltage or key == "rating" and rating or key == "awg" and awg:
            assert not text.startswith("NOT STATED"), key
        else:
            assert text.startswith("NOT STATED"), key


def test_the_roles_are_the_legend_the_supply_prints():
    assert "V+" in words(contract(AFO)["provenance"]["poles"]) and "V-" in words(contract(AFO)["provenance"]["poles"])
    assert "RTN" in words(contract(EX9253)["provenance"]["poles"]) and "-48V" in words(contract(EX9253)["provenance"]["poles"])
    assert "RTN" in words(contract(EX4500)["provenance"]["poles"]) and "-48V" in words(contract(EX4500)["provenance"]["poles"])


@pytest.mark.heavy
@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_build_publishes_the_seats_that_accept_the_ring_lug_and_the_ports(index, ref):
    _, seats, ports, _ = SUPPLIES[ref]
    entry = index[ref]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i, _, _ in seats]
    assert [(p["id"], p["direction"]) for p in entry["dc-ports"]] == [(i, "input") for i, _ in ports]
    for port, (_, poles) in zip(entry["dc-ports"], ports):
        assert [(q["role"], q["slot"]) for q in port["poles"]] == poles


@pytest.mark.parametrize("device", DEVICES)
def test_each_device_that_seats_a_supply_takes_one_minor(device):
    folder = LIB / "devices/juniper" / device
    lock = json.loads((folder / "device.lock.json").read_text())
    for fn in ("layout.yaml", "device.yaml"):
        assert re.search(rf"^version: {re.escape(DEVICES[device])}$", (folder / fn).read_text(), re.M), fn
    assert lock["version"] == DEVICES[device]
    for ref in SEATED_BY[device]:
        assert lock["composed-refs"][ref].startswith("1.1.0+")
        assert lock["composed-refs"][SCREW].startswith("1.0.1+")
    assert lock["dc-ports"], device


def test_the_lock_of_the_ex4300_32f_holds_the_two_feeds_of_the_dc_supply_it_seats():
    lock = json.loads((LIB / "devices/juniper/ex4300-32f/device.lock.json").read_text())
    ports = {path: refs for path, refs in lock["dc-ports"].items()}
    assert sorted(ports) == ["psu-0/module/feed-a", "psu-0/module/feed-b"]
    for path, refs in ports.items():
        assert AFO in refs and refs[AFO]["voltage"] == {"nominal": -48, "range": [-40.8, -60]}


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    closed = [r for r in rows if r["part"] in SUPPLIES and r["code"] == "C19"]
    assert closed == []
