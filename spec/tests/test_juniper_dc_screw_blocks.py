"""The four-screw DC terminal block of seven Juniper DC supplies is a place a cable lands, and each supply states one DC input port.

The EX4600, QFX5100 and QFX5200 DC supplies (JPSU-650W-DC and JPSU-850W-DC, each an AFI and an AFO) and the MX204 DC supply used to
draw their terminal block as art, so they offered no place for a DC feed. Each block has four screws printed V-, V-, V+ and V+ from
the left, and the vendor's guide says the two V+ screws are joined inside the supply, as are the two V- screws, and that a supply is
fed from one source. Each supply now composes its four screws as parts, each a seat a ring lug lands on, and states one DC input
port of two poles (decided 2026-11-03): `batt` on the first V- screw and `rtn` on the first V+ screw, counted from the left. The
second screw of each pair is a seat outside the port, as an earth seat is:

  - `pole-batt` and `shunt-batt` are the V- screws, `pole-rtn` and `shunt-rtn` the V+ screws, each at the centre of the screw the
    supply's skin already draws;
  - the roles are the guide's words, "(input)" for V- and "(return)" for V+, not the printed signs; no port states a voltage, because
    the guides print ranges (or two nominals);
  - a current is stated only where the guides of every chassis that seats the supply print one figure (the 850 W pair, 10 A; the MX204
    supply, 20 A), and a wire size only where they agree (14 to 16 AWG);
  - the supplies' elements, ids, descriptions and skins are unchanged.

These run against the real library, a components index built by the indexer the build runs, the device locks and the records file.
They read no library/dist and render nothing.
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
LUG = "generic/ring-lug@1"
IDS = ["pole-batt", "shunt-batt", "pole-rtn", "shunt-rtn"]
POLES = [("batt", "pole-batt"), ("rtn", "pole-rtn")]
HALF = 1.7

# supply -> the screws' centres as the skin draws them, the lift of each part (None: none), the port's figures, the version, the
# regular expression that reads the four centres out of the skin, and the ids of its elements
EX = dict(centres=[(14.8, 12.1), (23.1, 12.1), (31.6, 12.1), (39.8, 12.1)], lift=1.2, rating=None, version="1.1.0",
          skin=r'<g id="term-(?:neg|pos)-[ab]">\s*<circle cx="([\d.]+)" cy="([\d.]+)" r="3\.5"',
          elements=["esd-point", "latch", "led-fault", "led-in", "led-out", "lever", "term-neg-a", "term-neg-b", "term-pos-a",
                    "term-pos-b"])
QFX5100 = dict(centres=[(14.8, 11.7), (23.2, 11.7), (31.5, 11.7), (39.8, 11.7)], lift=None, rating=None, version="1.1.0",
               skin=r'<circle cx="([\d.]+)" cy="(11\.7)" r="3\.2"/>',
               elements=["latch", "led-fault", "led-in", "led-out", "lever", "terminal-block"])
QFX5200 = dict(centres=[(15.2, 10.6), (23.6, 10.6), (32.0, 10.6), (40.4, 10.6)], lift=2.2, rating=10, version="1.1.0",
               skin=r'<g id="stud-\d"><polygon [^>]*/><circle cx="([\d.]+)" cy="([\d.]+)" r="1\.7"',
               elements=["latch", "led-fault", "led-in", "led-out", "lever", "terminals"])
MX204 = dict(centres=[(8.0, 11.6), (19.0, 11.6), (30.0, 11.6), (41.0, 11.6)], lift=2.2, rating=20, version="1.3.0",
             skin=r'<g id="stud-\d"><polygon [^>]*/><circle cx="([\d.]+)" cy="([\d.]+)" r="2\.1"',
             elements=["latch", "led-fault", "led-in", "led-out", "terminals"])
SUPPLIES = {
    "juniper/ex4600-jpsu-650-dc-afi@1": dict(EX, awg=[14, 16]),
    "juniper/ex4600-jpsu-650-dc-afo@1": dict(EX, awg=None),
    "juniper/qfx5100-jpsu-650w-dc-afi@1": dict(QFX5100, awg=[14, 16]),
    "juniper/qfx5100-jpsu-650w-dc-afo@1": dict(QFX5100, awg=[14, 16]),
    "juniper/qfx5200-jpsu-850w-dc-afi@1": dict(QFX5200, awg=[14, 16]),
    "juniper/qfx5200-jpsu-850w-dc-afo@1": dict(QFX5200, awg=[14, 16]),
    "juniper/mx204-psu-dc@1": dict(MX204, awg=[14, 16]),
}
# the devices that seat them: slug -> version on the change
DEVICES = {
    "ex4550-32f": "0.3.0", "ex4550-32t": "0.3.0", "ex4600-40f": "0.2.0", "ex4650-48y": "0.2.0", "ex9251": "0.2.0", "mx204": "4.1.0",
    "qfx3500-48s4q": "0.2.0", "qfx3600-16q": "0.2.0", "qfx5100-24q": "0.2.0", "qfx5100-48s": "0.2.0", "qfx5100-48t": "0.2.0",
    "qfx5100-96s": "0.2.0", "qfx5110-32q": "0.2.0", "qfx5110-48s": "0.2.0", "qfx5120-48t": "0.2.0", "qfx5200-32c": "0.2.0",
}


def folder(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((folder(ref) / "contract.yaml").read_text())


def words(text):
    return " ".join(str(text).split())


def at_of(centre):
    return [round(centre[0] - HALF, 2), round(centre[1] - HALF, 2)]


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@pytest.mark.parametrize("ref", SUPPLIES)
def test_each_supply_composes_four_terminal_screws_and_nothing_else(ref):
    want = SUPPLIES[ref]
    parts = contract(ref)["parts"]
    expected = [{"ref": SCREW, "id": i, "at": at_of(c), **({"lift": want["lift"]} if want["lift"] else {})}
                for i, c in zip(IDS, want["centres"])]
    assert parts == expected


def test_the_screw_part_presents_terminal_stud_and_the_ring_lug_mates_it():
    assert contract(SCREW)["interface"] == "terminal-stud"
    assert contract(LUG)["mates"] == "terminal-stud"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_four_seats_stand_at_the_centres_of_the_four_screws_the_skin_draws(ref):
    want = SUPPLIES[ref]
    skin = (folder(ref) / "skins/default.svg").read_text()
    drawn = [(float(x), float(y)) for x, y in re.findall(want["skin"], skin)]
    assert drawn == want["centres"]
    for part, centre in zip(contract(ref)["parts"], drawn):
        assert [round(part["at"][0] + HALF, 2), round(part["at"][1] + HALF, 2)] == list(centre), part["id"]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_lift_is_the_one_the_contract_already_gives_the_screws_or_studs_it_stands_on(ref):
    d = contract(ref)
    want = SUPPLIES[ref]["lift"]
    relief = {f["node"]: f for f in d["relief"]["features"]}
    if want is None:
        assert list(relief) == ["latch"]
        assert all("lift" not in p for p in d["parts"])
    elif ref.startswith("juniper/ex4600"):
        assert [relief[n]["cyl"] for n in ("term-neg-a", "term-neg-b", "term-pos-a", "term-pos-b")] == [want] * 4
    else:
        assert [relief[f"stud-{i}"]["lift"] for i in range(4)] == [want] * 4
    assert all(p.get("lift") == want for p in d["parts"])


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_dc_port_is_one_input_of_two_poles_and_the_second_screws_are_in_none(ref):
    want = SUPPLIES[ref]
    ports = contract(ref)["dc"]["ports"]
    assert [p["id"] for p in ports] == ["input"]
    port = ports[0]
    assert port["direction"] == "input"
    assert [(q["role"], q["slot"]) for q in port["poles"]] == POLES
    assert not {"shunt-batt", "shunt-rtn"} & {q["slot"] for q in port["poles"]}
    assert port.get("awg") == want["awg"]
    assert port.get("rating-a") == want["rating"]
    assert "voltage" not in port and "side" not in port


@pytest.mark.parametrize("ref", SUPPLIES)
def test_every_fact_the_port_states_names_a_provenance_entry_that_says_where_it_came_from(ref):
    d = contract(ref)
    want = {"poles": "poles"}
    if SUPPLIES[ref]["rating"] is not None:
        want["rating-a"] = "rating"
    if SUPPLIES[ref]["awg"] is not None:
        want["awg"] = "awg"
    source = d["dc"]["ports"][0]["source"]
    assert source == want
    for key in ("seats", "shunts", "poles", "voltage", "rating", "awg"):
        assert len(words(d["provenance"][key])) >= 40, key
    poles = words(d["provenance"]["poles"])
    assert "PDF page" in poles and "shunted internally together" in poles and "`batt` on the left V-" in poles
    assert ("RTN (return) terminal" if ref.startswith("juniper/mx204") else "V+ (return) DC power input terminal") in poles


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_choice_of_the_screw_that_carries_the_pole_is_declared_a_choice(ref):
    text = words(contract(ref)["provenance"]["shunts"])
    assert text.startswith("THE SECOND SCREW OF EACH PAIR IS A SEAT OUTSIDE THE PORT")
    assert "CHOICE AND NOT A READING" in text and "decided 2026-11-03" in text and "four poles would be a major" in text


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_missing_voltage_is_said_and_so_is_a_missing_current_or_wire_size(ref):
    d = contract(ref)
    assert words(d["provenance"]["voltage"]).startswith("NOT STATED") and "the port states none" in d["provenance"]["voltage"].lower()
    if SUPPLIES[ref]["rating"] is None:
        assert words(d["provenance"]["rating"]).startswith("NOT STATED") and "the port states none" in words(d["provenance"]["rating"])
    else:
        assert f"`rating-a` {SUPPLIES[ref]['rating']}" in words(d["provenance"]["rating"])
    if SUPPLIES[ref]["awg"] is None:
        assert words(d["provenance"]["awg"]).startswith("NOT STATED") and "JPSU-650W-DC-AFO" in d["provenance"]["awg"]
        assert "minimum 12 AWG" in words(d["provenance"]["awg"])
    else:
        assert "states both, 14 and 16" in words(d["provenance"]["awg"])


def test_the_two_components_of_one_maker_part_state_the_same_port_but_for_the_wire_the_ex9251_guide_disputes():
    for a, b in (("juniper/ex4600-jpsu-650-dc-afi@1", "juniper/qfx5100-jpsu-650w-dc-afi@1"),
                 ("juniper/ex4600-jpsu-650-dc-afo@1", "juniper/qfx5100-jpsu-650w-dc-afo@1")):
        pa, pb = contract(a)["dc"]["ports"][0], contract(b)["dc"]["ports"][0]
        assert pa["poles"] == pb["poles"] and pa.get("rating-a") == pb.get("rating-a")
        assert [p["id"] for p in contract(a)["parts"]] == [p["id"] for p in contract(b)["parts"]]
    assert contract("juniper/ex4600-jpsu-650-dc-afi@1")["dc"]["ports"][0]["awg"] == [14, 16]
    assert "awg" not in contract("juniper/ex4600-jpsu-650-dc-afo@1")["dc"]["ports"][0]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_version_the_elements_and_the_description_stand_as_they_were(ref):
    d = contract(ref)
    assert d["version"] == SUPPLIES[ref]["version"]
    assert d["attrs"]["inlet"] == "dc-terminal"
    assert sorted(d["elements"]) == SUPPLIES[ref]["elements"]
    assert "skins" not in d or d["skins"] == ["default"]


@pytest.mark.heavy
@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_build_publishes_four_seats_that_accept_the_ring_lug_and_one_dc_port(index, ref):
    entry = index[ref]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"]) for c in entry["cages"]] == [
        (i, "connector", "terminal-stud", [LUG]) for i in IDS]
    assert [(p["id"], p["direction"]) for p in entry["dc-ports"]] == [("input", "input")]
    assert [(q["role"], q["slot"]) for q in entry["dc-ports"][0]["poles"]] == POLES


@pytest.mark.parametrize("slug", DEVICES)
def test_each_device_that_seats_a_supply_takes_one_minor(slug):
    folder_ = LIB / "devices/juniper" / slug
    lock = json.loads((folder_ / "device.lock.json").read_text())
    for fn in ("layout.yaml", "device.yaml"):
        if (folder_ / fn).exists():
            assert re.search(rf"^version: {re.escape(DEVICES[slug])}$", (folder_ / fn).read_text(), re.M), fn
    assert lock["version"] == DEVICES[slug]
    refs = lock["composed-refs"]
    assert refs[SCREW].startswith("1.0.1+")
    assert any(r in refs for r in SUPPLIES)


@pytest.mark.parametrize("slug", DEVICES)
def test_the_lock_holds_one_input_port_for_each_supply_bay_a_dc_configuration_seats(slug):
    lock = json.loads((LIB / "devices/juniper" / slug / "device.lock.json").read_text())
    ports = lock["dc-ports"]
    assert ports and all(path.endswith("/module/input") for path in ports)
    for path, refs in ports.items():
        for ref, fact in refs.items():
            assert ref in SUPPLIES and fact["voltage"] is None and fact["rating-a"] == SUPPLIES[ref]["rating"]


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_findings_this_change_closes_have_no_row_left(ref):
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == ref and r["code"] == "C19"] == []
