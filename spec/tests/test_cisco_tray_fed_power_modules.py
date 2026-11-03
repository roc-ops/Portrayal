"""The five Cisco ASR 9000 power modules that are fed through a power tray say where their cables land.

The cables of these modules do not land on the module. The DC source and return cables land on lugs over the terminal studs of the
power tray, and the AC power cord plugs into a receptacle at the rear of the AC power tray (Cisco ASR 9000 Series Aggregation Services
Router Hardware Installation Guide, printed pages 42 to 47 and 195 to 199). The trays are not drawn by any of the seven chassis that
seat the modules, so each module carries an `unmated` sentence (spec/schemas/component.schema.json) that says it is drawn from the
front of its tray, that the cables land on the tray, which is not drawn, and that it has no inlet, terminal or lug. None presents an
interface, a slot or a mate.

These run against the real library and the records file. They read no library/dist and render nothing.
"""
import json
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
GUIDE = "Cisco ASR 9000 Series Aggregation Services Router Hardware Installation Guide"

# ref -> the words its sentence has to carry: what the module is, where it is drawn from, where the cables land, that the tray is not
# drawn, and the printed pages of the guide the sentence rests on
PARTS = {
    "cisco/a9k-pwr-2kw-dc@1": ("version 1 DC power module", "front of its power tray", "terminal studs of the power tray",
                               "which is not drawn", "printed pages 42 and 45"),
    "cisco/a9k-pwr-3kw-ac@1": ("version 1 AC power module", "front of its power tray", "rear of the power tray",
                               "which is not drawn", "printed pages 195 and 196"),
    "cisco/a9k-power-module-v2@1": ("version 2 power module", "front of its power tray", "rear of the AC power tray",
                                    "terminal studs of the DC power tray", "neither tray is drawn", "printed pages 42, 46, 195 and 196"),
    "cisco/pwr-4p4kw-dc-v3@1": ("version 3 DC power module", "front of its power tray", "terminal studs of the power tray",
                                "which is not drawn", "printed pages 42 and 47"),
    "cisco/pwr-6kw-ac-v3@1": ("version 3 AC power module", "front of its power tray", "rear of the power tray",
                              "which is not drawn", "printed pages 195 and 196"),
}
OFFERS = ("interface", "presents", "cages", "mates")        # the keys of a part that takes a cable or a plug

# chassis -> the modules it seats (as a default, a choice or a configuration's occupant)
CHASSIS = {
    "cisco/asr-9006": ("cisco/a9k-pwr-3kw-ac@1", "cisco/a9k-pwr-2kw-dc@1"),
    "cisco/asr-9010": ("cisco/a9k-pwr-3kw-ac@1", "cisco/a9k-pwr-2kw-dc@1"),
    "cisco/asr-9904": ("cisco/a9k-power-module-v2@1",),
    "cisco/asr-9912": ("cisco/a9k-power-module-v2@1",),
    "cisco/asr-9922": ("cisco/a9k-power-module-v2@1",),
    "cisco/asr-9906": ("cisco/pwr-6kw-ac-v3@1", "cisco/pwr-4p4kw-dc-v3@1"),
    "cisco/asr-9910": ("cisco/pwr-6kw-ac-v3@1", "cisco/pwr-4p4kw-dc-v3@1"),
}
# the three power tray parts of the library; no chassis places one, which is what the sentences say
TRAYS = ("cisco/a9k-power-tray@1", "cisco/a9k-ac-pem-v3@1", "cisco/a9k-dc-pem-v3@1")


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def scalars(node):
    """Every string a parsed YAML document holds as a value or as a list item, whole (a long note is one string and never equals a ref)."""
    if isinstance(node, str):
        yield node.strip()
    elif isinstance(node, dict):
        for value in node.values():
            yield from scalars(value)
    elif isinstance(node, list):
        for item in node:
            yield from scalars(item)


def seated_refs(slug):
    return set(scalars(yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())))


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@pytest.mark.parametrize("ref", PARTS)
def test_the_module_says_where_its_cables_land(ref):
    sentence = contract(ref).get("unmated")
    assert isinstance(sentence, str) and len(sentence) >= 40, f"{ref}: no `unmated` sentence of at least 40 characters"
    assert ":" not in sentence, f"{ref}: the sentence carries a colon"
    missing = [word for word in (*PARTS[ref], GUIDE, "no inlet, terminal or lug") if word not in sentence]
    assert not missing, f"{ref}: its sentence does not say {missing}: {sentence!r}"


@pytest.mark.parametrize("ref", PARTS)
def test_the_module_offers_no_interface_slot_or_mate(ref, index):
    offered = [key for key in OFFERS if key in contract(ref)]
    assert not offered, f"{ref} states {offered}, so it is a connector and cannot say that nothing plugs into it"
    assert not index[ref].get("cages"), f"{ref} publishes slots: {index[ref].get('cages')}"


@pytest.mark.parametrize("ref", PARTS)
def test_the_module_keeps_its_drawing(ref):
    doc = contract(ref)
    assert doc["kind"] == "module" and doc["class"] == "psu", f"{ref}: no longer a power supply module"
    assert {"input", "output", "fault"} <= set(doc["elements"]), f"{ref}: a status lamp is gone"
    assert "parts" not in doc and "dc" not in doc, f"{ref} composes parts or states a DC port, which a sentence-only change does not"


@pytest.mark.parametrize("slug", CHASSIS)
def test_each_chassis_still_seats_its_modules(slug):
    held = seated_refs(slug)
    assert not [ref for ref in CHASSIS[slug] if ref not in held], f"{slug} no longer seats {CHASSIS[slug]}"


@pytest.mark.parametrize("slug", CHASSIS)
def test_no_chassis_places_a_power_tray(slug):
    placed = [ref for ref in TRAYS if ref in seated_refs(slug)]
    assert not placed, (f"{slug} places {placed}: the sentences of the five modules say the tray is not drawn and the cables land on it, "
                        "so they are to be reworded in the same change")


def test_the_records_file_holds_no_row_for_these_parts():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert not [r["part"] for r in rows if r["part"] in PARTS], "a part with a sentence needs no row"
