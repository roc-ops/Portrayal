"""The alarm connector and the BITS header of the Nokia general facilities cards are parts that present a registered key.

`nokia/ngfc-h@1` (the NFXS-E BB shelf) and `nokia/ngfc-g@1` (the NFXS-F BB shelf) drew their 50-pin micro D-sub alarm connector
and their six-pin wire-wrap BITS header as elements of class `port`, which present no interface. Each is now a placed part that
presents its key: the receptacle presents `micro-dsub-50` and a cable plug mates it; the header presents `wire-wrap-6`, whose
registry entry says why no plug seats on it. The ids `alarm-io` and `bits` are the ones the elements had.
"""
import pathlib

import yaml

from portrayal import dcim_export

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
RECEPTACLE = "common/micro-dsub-50-receptacle@1"
PLUG = "common/micro-dsub-50-plug@1"
HEADER = "common/wire-wrap-header-6@1"
CARDS = ("nokia/ngfc-h@1", "nokia/ngfc-g@1")


def contract(ref):
    ns, tail = ref.split("/")
    name, major = tail.split("@")
    return yaml.safe_load((LIBRARY / "components" / ns / name / f"v{major}" / "contract.yaml").read_text())


def mated_by():
    """Every key a contract of the library mates, as {key: [refs]}."""
    out = {}
    for path in (LIBRARY / "components").glob("*/*/v*/contract.yaml"):
        doc = yaml.safe_load(path.read_text()) or {}
        keys = doc.get("mates")
        for key in ([keys] if isinstance(keys, str) else keys or []):
            out.setdefault(key, []).append(f"{path.parts[-4]}/{path.parts[-3]}@{path.parts[-2][1:]}")
    return out


def test_the_receptacle_presents_the_alarm_key_and_a_cable_plug_mates_it():
    assert contract(RECEPTACLE)["interface"] == "micro-dsub-50" and contract(RECEPTACLE)["class"] == "port"
    plug = contract(PLUG)
    assert plug["mates"] == "micro-dsub-50" and plug["class"] == "port" and "interface" not in plug


def test_the_header_presents_the_bits_key_and_no_part_mates_it():
    assert contract(HEADER)["interface"] == "wire-wrap-6" and contract(HEADER)["class"] == "port"
    assert "wire-wrap-6" not in mated_by(), "the registry says no plug seats on this header"


def test_each_card_places_the_two_parts_at_the_ids_its_elements_had():
    for ref in CARDS:
        doc = contract(ref)
        placed = {p["id"]: p for p in doc["parts"]}
        assert placed["alarm-io"]["ref"] == RECEPTACLE and placed["bits"]["ref"] == HEADER, ref
        assert "alarm-io" not in doc["elements"] and "bits" not in doc["elements"], ref
        assert placed["alarm-io"]["group"] == "alarm" and placed["bits"]["group"] == "bits", ref
        assert {"alarm", "bits"} <= set(doc["groups"]), ref


def test_the_cards_do_not_say_that_no_part_exists_for_either_connector():
    for ref in CARDS:
        text = " ".join(str(contract(ref)["groups"]["craft"]["description"]).split())
        assert "no library part exists" not in text and "cannot join a group" not in text, ref


def test_the_two_parts_the_cards_place_are_named_in_the_register_of_ports_no_dcim_types():
    for part in (RECEPTACLE, HEADER):
        assert part.split("@")[0] in dcim_export.NOT_A_DCIM_PORT, part


def test_the_records_file_holds_no_port_row_for_the_two_shelves():
    rows = yaml.safe_load((LIBRARY / "conformance-exceptions.yaml").read_text())["rows"]
    left = [r for r in rows if r["code"] == "C22" and r["part"] in ("nfxs-e-bb", "nfxs-f-bb")]
    assert not left, "the alarm connector and the BITS header are no longer reported as ports with no interface"
