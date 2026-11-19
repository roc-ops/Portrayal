"""The IRIG-B card's optical output and alarm relay are parts that present a registered key, each with a mate.

`oscilloquartz/irig-b@1` (the OSA 542x time-code expansion card) drew its optical output and its alarm/pulse relay
as elements of class `port`, which present no interface. The OSA 5422 data sheet (IRIG/TIMECODE line card) names the
connectors: an ST connector for the 820 nm multimode optical output, and a 3-pin WR-TBL Series 382 terminal block on a
2.50 mm pitch for the alarm/pulse relay. Each is now a placed part under the id the element had; the ST receptacle
presents `st` and a plug mates it, the three-position header presents `terminal-250-3` and a plug mates it. The isolated
IRIG input and the ten IRIG outputs are still elements of the card: no page held names their connectors.
"""
import json
import pathlib

import pytest
import yaml

import onebuild
from portrayal import dcim_export

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
CARD = "oscilloquartz/irig-b@1"
ST_RECEPTACLE, ST_PLUG = "common/st-receptacle@1", "generic/st-plug@1"
HEADER, HEADER_PLUG = "common/terminal-header-250-3@1", "generic/terminal-250-3-plug@1"
DEVICES = ("osa-5420-quartz", "osa-5420-quartz-hq-plus", "osa-5421-quartz-hq-plus-plus", "osa-5421-rubidium")


def contract(ref):
    ns, tail = ref.split("/")
    name, major = tail.split("@")
    return yaml.safe_load((LIBRARY / "components" / ns / name / f"v{major}" / "contract.yaml").read_text())


def registry():
    return yaml.safe_load((ROOT / "spec" / "schemas" / "connectors.yaml").read_text())["interfaces"]


def device(name):
    return yaml.safe_load((LIBRARY / "devices" / "oscilloquartz" / name / "device.yaml").read_text())


def mated_by():
    """Every key a contract of the library mates, as {key: [refs]}."""
    out = {}
    for path in (LIBRARY / "components").glob("*/*/v*/contract.yaml"):
        doc = yaml.safe_load(path.read_text()) or {}
        keys = doc.get("mates")
        for key in ([keys] if isinstance(keys, str) else keys or []):
            out.setdefault(key, []).append(f"{path.parts[-4]}/{path.parts[-3]}@{path.parts[-2][1:]}")
    return out


def test_the_two_keys_are_registered_and_say_what_they_are():
    keys = registry()
    for key in ("st", "terminal-250-3"):
        assert key in keys and len(str(keys[key].get("note", ""))) > 80, key
    assert "2.50" in keys["terminal-250-3"]["note"] and "ST" in keys["st"]["note"]


def test_each_receptacle_presents_its_key_and_a_plug_mates_it():
    mates = mated_by()
    for part, plug, key in ((ST_RECEPTACLE, ST_PLUG, "st"), (HEADER, HEADER_PLUG, "terminal-250-3")):
        doc, plug_doc = contract(part), contract(plug)
        assert doc["interface"] == key and doc["class"] == "port", part
        assert plug_doc["mates"] == key and plug_doc["class"] == "port" and "interface" not in plug_doc, plug
        assert mates[key] == [plug], key


def test_the_header_is_three_positions_on_a_2_50_pitch():
    attrs = contract(HEADER)["attrs"]
    assert attrs["positions"] == 3 and attrs["pitch-mm"] == 2.5
    assert contract(HEADER_PLUG)["attrs"]["pitch-mm"] == 2.5


def test_the_card_places_the_two_parts_at_the_ids_its_elements_had():
    doc = contract(CARD)
    placed = {p["id"]: p for p in doc["parts"]}
    assert placed["optical-out"]["ref"] == ST_RECEPTACLE and placed["alarm-pulse"]["ref"] == HEADER
    assert "optical-out" not in doc["elements"] and "alarm-pulse" not in doc["elements"]
    assert placed["optical-out"]["group"] in doc["groups"] and placed["alarm-pulse"]["group"] in doc["groups"]
    assert placed["optical-out"]["group"] != placed["alarm-pulse"]["group"]


def test_the_card_still_draws_the_two_connectors_no_page_names_as_elements():
    doc = contract(CARD)
    assert "irig-in" in doc["elements"] and "irig-out" in doc["elements"]


def test_the_two_receptacles_are_named_in_the_register_of_ports_no_dcim_types():
    for part in (ST_RECEPTACLE, HEADER):
        assert part.split("@")[0] in dcim_export.NOT_A_DCIM_PORT, part


@pytest.mark.heavy
def test_the_index_publishes_each_receptacle_as_a_slot_its_plug_seats_in():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    card = {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}[CARD]
    slots = {c["id"]: (c["interface"], c["kind"], c["accepts"]) for c in card["cages"]}
    assert slots["optical-out"] == ("st", "connector", [ST_PLUG])
    assert slots["alarm-pulse"] == ("terminal-250-3", "connector", [HEADER_PLUG])


def test_no_oscilloquartz_device_says_the_optical_connector_is_unnamed():
    for name in DEVICES:
        gaps = {g["what"]: g for g in device(name).get("gaps") or []}
        assert "optical-irig-connector" not in gaps, name
        text = " ".join(str(g.get("note", "")) for g in gaps.values())
        assert "optical output is a round barrel 7.4 across" not in text, name
