"""Two fixed power cords and a supply whose inlet is elsewhere say why nothing lands on them, and three decor entries that frame an
inlet are named for what they are.

A fixed cord ends in a plug of its own, so nothing plugs into the cord. The Casa C40G AC supply is drawn from the front, and its
AC inlet is at the other end of the module, which the chassis draws as the rear AC input panel. Each of the three parts carries an
`unmated` sentence (spec/schemas/component.schema.json), and none presents an interface, a slot or a mate. Three decor entries named
`inlet-flange` and `terminal-block` were read by lint L197 as connectors drawn as art; two of them frame a C20 inlet that the device
already places, and the third is the wiring strip of a fan panel's back: each is renamed for what it is.

These run against the real library and the records file. They read no library/dist and render nothing.
"""
import json
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# ref -> the words its sentence has to carry, so the sentence says what the part is and why nothing lands on it
PARTS = {
    "eaton/tripplite-cord-l5-20p@1": ("fixed", "NEMA L5-20P", "cord's own end"),
    "fs/fan-cord-5-15p@1": ("fixed", "plug of its own", "cord's own end"),
    "casa/c40g-psu-ac@1": ("other end", "AC input panel", "no inlet, terminal or lug"),
}
OFFERS = ("interface", "presents", "cages", "mates")        # the keys of a part that takes a cable or a plug

# device -> (decor id and kind it had, the one it has now)
DECOR = {
    "eaton/pdu12iec": ("inlet-flange", "inlet-moulding"),
    "eaton/pdumv20hvnetlx": ("inlet-flange", "inlet-moulding"),
    "fs/fanp3u3f": ("terminal-block", "wiring-strip"),
}


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def device(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


def decor(slug):
    return [(vname, d) for vname, v in (device(slug).get("views") or {}).items() for d in ((v.get("panel") or {}).get("decor") or [])]


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@pytest.mark.parametrize("ref", PARTS)
def test_the_part_says_why_nothing_lands_on_it(ref):
    sentence = contract(ref).get("unmated")
    assert isinstance(sentence, str) and len(sentence) >= 40, f"{ref}: no `unmated` sentence of at least 40 characters"
    missing = [word for word in PARTS[ref] if word not in sentence]
    assert not missing, f"{ref}: its sentence does not say {missing}: {sentence!r}"


@pytest.mark.heavy
@pytest.mark.parametrize("ref", PARTS)
def test_the_part_offers_no_interface_slot_or_mate(ref, index):
    offered = [key for key in OFFERS if key in contract(ref)]
    assert not offered, f"{ref} states {offered}, so it is a connector and cannot say that nothing plugs into it"
    assert not index[ref].get("cages"), f"{ref} publishes slots: {index[ref].get('cages')}"


def test_the_fixed_cords_still_state_the_plug_the_exports_read():
    assert contract("eaton/tripplite-cord-l5-20p@1")["attrs"]["plug"] == "nema-l5-20p"
    assert contract("fs/fan-cord-5-15p@1")["attrs"]["plug"] == "nema-5-15p"


def test_the_records_file_holds_no_row_for_these_parts():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert not [r["part"] for r in rows if r["part"] in PARTS], "a part with a sentence needs no row"


@pytest.mark.parametrize("slug", DECOR)
def test_the_decor_is_named_for_what_it_is_and_no_connector_name_is_left(slug):
    old, new = DECOR[slug]
    entries = decor(slug)
    assert [(d["id"], d["kind"]) for _, d in entries if d["id"] in (old, new)] == [(new, new)], f"{slug}: the decor {old!r} is not named {new!r}"
    names = yaml.safe_load((ROOT / "spec" / "schemas" / "connector-decor-names.yaml").read_text())["names"]
    assert not [(v, d["id"], d["kind"]) for v, d in entries if d.get("kind") in names], f"{slug}: a decor kind that lint L197 reads as a connector"


@pytest.mark.parametrize("slug", ["eaton/pdu12iec", "eaton/pdumv20hvnetlx"])
def test_the_moulding_frames_the_one_c20_inlet_the_device_already_places(slug):
    placed = [p for v in device(slug)["views"].values() for p in ((v.get("components") or {}).get("placements") or [])]
    assert [(p["id"], p["ref"]) for p in placed if p["ref"] == "std/c20-inlet@1"] == [("input", "std/c20-inlet@1")]
