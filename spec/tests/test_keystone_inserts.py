"""Keystone inserts for the FHD-FAPM6, seated one opening at a time.

The panel's six openings each take a blanking insert or a Cat6 RJ45 keystone
jack, chosen per opening, and a cable lands on any jack's port. What this holds
true of the library:

- `keystone` is a registered connector interface, and the newest keystone clip
  presents it at its `mate` point, empty as FS ships it;
- the FHD-FAPM6 composes that clip in each of its six openings, and the build
  publishes six slots of interface `keystone` that take every part that mates
  the interface and hold none;
- every part that mates `keystone` is an occupant that fills the opening, is
  centred where the clip's `mate` point stands, and is honest about what it
  estimates: the blank composes nothing, the jack composes one RJ45 port;
- the jack publishes that port as a slot a plug lands on, in its own frame;
- the seven enclosures that take the panel lock a clip that presents the interface.

Read from the contracts, the components index the build's indexer writes and
the locks; nothing here needs a build. The kit's side (a cable end four levels
down) is test_keystone_jack_chain_js.py.
"""
import json
import pathlib

import pytest
import yaml

import onebuild

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
COMP = LIB / "components"
ENCLOSURES = ["fhd-1ube", "fhd-1ufce", "fhd-1ufmt-n", "fhd-1ufmt-s", "fhd-1ume", "fhd-2ufce", "fhd-4ufce"]
OPENINGS = [f"clip{n}" for n in range(1, 7)]


def _ref(c):
    return f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}"


def _contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((COMP / ns / name / f"v{major}" / "contract.yaml").read_text())


def _index():
    d = onebuild.components_index()
    return {_ref(c): c for c in json.loads((d / "components.json").read_text())["components"]}


def _newest(ns, name):
    return max(int(p.name[1:]) for p in (COMP / ns / name).iterdir() if p.name.startswith("v"))


def _inserts():
    """every contract that mates the keystone interface: {ref: contract}"""
    out = {}
    for path in COMP.glob("*/*/v*/contract.yaml"):
        doc = yaml.safe_load(path.read_text())
        mates = doc.get("mates")
        if "keystone" in ([mates] if isinstance(mates, str) else mates or []):
            out[f"{path.parts[-4]}/{path.parts[-3]}@{path.parts[-2][1:]}"] = doc
    assert out, "no part mates keystone, so there is nothing to seat in an opening"
    return out


def test_keystone_is_a_registered_connector_interface():
    reg = yaml.safe_load((ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"]
    assert "keystone" in reg
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]
    assert reg["keystone"]["standard"] in std


def test_the_newest_clip_presents_keystone_at_its_mate_point_and_ships_empty():
    clip = _contract(f"common/keystone-clip@{_newest('common', 'keystone-clip')}")
    assert clip["interface"] == "keystone"
    assert "default" not in clip
    assert clip["connection-points"]["mate"]["at"] == [clip["size"]["w"] / 2, clip["size"]["h"] / 2]
    assert clip["conforms"] == "keystone-opening"


def test_the_fapm6_composes_the_newest_clip_in_each_of_its_six_openings():
    fapm6 = _contract("fs/fhd-fapm6@1")
    newest = f"common/keystone-clip@{_newest('common', 'keystone-clip')}"
    assert [p["id"] for p in fapm6["parts"]] == OPENINGS
    assert {p["ref"] for p in fapm6["parts"]} == {newest}
    assert (COMP / "common/keystone-clip" / f"v{_newest('common', 'keystone-clip')}" / "skins/default.svg").exists()


def test_every_keystone_clip_a_part_composes_presents_the_interface():
    """a clip composed without an interface publishes no slot, so nothing seats in its opening"""
    bare = []
    for path in COMP.glob("*/*/v*/contract.yaml"):
        for part in yaml.safe_load(path.read_text()).get("parts") or []:
            if str(part.get("ref", "")).startswith("common/keystone-clip@") and not _contract(part["ref"]).get("interface"):
                bare.append((str(path.relative_to(COMP)), part["ref"]))
    assert bare == []


@pytest.mark.heavy
def test_the_fapm6_publishes_six_empty_keystone_slots_that_take_every_insert():
    fapm6, inserts = _index()["fs/fhd-fapm6@1"], _inserts()
    assert set(inserts) >= {"common/keystone-blank@2", "fs/keystone-rj45-cat6@1"}
    assert [g["id"] for g in fapm6["cages"]] == OPENINGS
    for g in fapm6["cages"]:
        assert g["interface"] == "keystone" and g["kind"] == "connector", g
        assert g["default"] is None, g
        assert sorted(g["accepts"]) == sorted(inserts), g


def test_every_insert_fills_the_opening_and_lands_centred_in_the_clip():
    clip = _contract(f"common/keystone-clip@{_newest('common', 'keystone-clip')}")
    for ref, doc in _inserts().items():
        assert doc["behaviour"] == "occupies", ref
        assert doc["size"] == clip["size"], ref
        assert doc["conforms"] == "keystone-opening", ref
        assert doc["connection-points"]["mate"]["at"] == clip["connection-points"]["mate"]["at"], ref
        assert (COMP / ref.split("/")[0] / doc["name"] / f"v{ref.split('@')[1]}" / "skins/default.svg").exists(), ref


def test_every_insert_says_what_it_estimates():
    for ref, doc in _inserts().items():
        text = " ".join(str(v) for v in (doc.get("provenance") or {}).values())
        assert "ESTIMATED" in text, f"{ref} states no estimate, and no held document draws it face-on"


@pytest.mark.heavy
def test_the_blank_composes_nothing_and_offers_no_port():
    doc = _contract("common/keystone-blank@2")
    assert not doc.get("parts") and "interface" not in doc
    assert _index()["common/keystone-blank@2"].get("cages") is None


@pytest.mark.heavy
def test_the_jack_composes_one_rj45_port_a_plug_lands_on():
    doc = _contract("fs/keystone-rj45-cat6@1")
    assert [p["id"] for p in doc["parts"]] == ["rj45"]
    housing = _contract(doc["parts"][0]["ref"])
    assert housing["class"] == "port" and housing["interface"] == "rj45"
    # the housing lies wholly inside the opening it is seated in
    x, y = doc["parts"][0]["at"]
    assert x >= 0 and y >= 0
    assert x + housing["size"]["w"] <= doc["size"]["w"] + 1e-6 and y + housing["size"]["h"] <= doc["size"]["h"] + 1e-6
    cages = _index()["fs/keystone-rj45-cat6@1"]["cages"]
    assert [(g["id"], g["interface"], g["kind"]) for g in cages] == [("rj45", "rj45", "connector")]
    assert cages[0]["accepts"] == ["generic/rj45-plug@1"]


@pytest.mark.parametrize("name", ENCLOSURES)
def test_every_enclosure_that_takes_the_fapm6_locks_a_clip_that_presents_the_interface(name):
    lock = json.loads((LIB / "devices/fs" / name / "device.lock.json").read_text())
    clips = [r for r in lock["composed-refs"] if r.startswith("common/keystone-clip@")]
    assert clips, name
    for ref in clips:
        assert _contract(ref).get("interface") == "keystone", f"{name} locks {ref}"
