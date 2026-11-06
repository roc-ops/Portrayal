"""The two FHD-FAPM6 panels that come loaded: six Cat6 RJ45 keystones, or six blanks.

The FAPM6 itself ships with empty clips, so nothing can be cabled to it. These
two are whole panels, declared the way fs/fhd-fap18lcd-os2 is: fixed composed
parts at the clip positions, no cage and no nesting.

- each panel has the FAPM6's face and size, and its six parts sit in the six
  openings the FAPM6 punches;
- the RJ45 panel's parts are `p1` to `p6`, `std/rj45@2`, a port a cable lands
  on, and it declares a rear face, `bN` behind `pN`, each a punch-down (IDC)
  termination a cable ends on, and no optical block;
- the blank panel composes a blanking insert in each opening and no part of
  class `port`;
- every enclosure that accepts the FAPM6 accepts both.

Read from the contracts, so it cannot skip.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
COMP = LIB / "components"

FAPM6_ENCLOSURES = ["fhd-1ube", "fhd-1ufce", "fhd-1ufmt-n", "fhd-1ufmt-s", "fhd-1ume", "fhd-2ufce", "fhd-4ufce"]
NEW = ["fs/fhd-fapm6-rj45@1", "fs/fhd-fapm6-blank@1"]


def _load(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return yaml.safe_load((COMP / ns / name / f"v{major}" / "contract.yaml").read_text())


def _opening(part):
    """top-left of the opening a FAPM6 clip sits in"""
    return part["at"]


def test_both_panels_wear_the_fapm6_face_and_size():
    base = _load("fs/fhd-fapm6@1")
    for ref in NEW:
        doc = _load(ref)
        assert doc["kind"] == "module" and doc["class"] == "adapter-panel", ref
        assert doc["size"] == base["size"], ref
        assert doc["body"] == base["body"], ref
        assert (COMP / ref.split("/")[0] / doc["name"] / "v1" / "skins" / "default.svg").exists(), ref


def test_the_rj45_panel_has_six_ports_p1_to_p6_in_the_six_openings():
    doc, base = _load("fs/fhd-fapm6-rj45@1"), _load("fs/fhd-fapm6@1")
    assert [p["id"] for p in doc["parts"]] == [f"p{n}" for n in range(1, 7)]
    jack = _load("std/rj45@2")
    assert jack["class"] == "port" and jack["interface"] == "rj45"
    clips = base["parts"]
    clip = _load(clips[0]["ref"])["size"]
    for p, c in zip(doc["parts"], clips):
        assert p["ref"] == "std/rj45@2", p
        # the housing lies wholly inside the opening its clip would fill
        x, y = p["at"]
        cx, cy = _opening(c)
        assert cx <= x and x + jack["size"]["w"] <= cx + clip["w"] + 1e-6, p
        assert cy <= y and y + jack["size"]["h"] <= cy + clip["h"] + 1e-6, p


def test_the_rj45_panel_numbers_its_ports_as_fs_prints_them():
    """FS numbers COLUMN BY COLUMN, the lower of a pair first (the FAPM6's own
    face-legends): 1 and 2 are the left pair, 5 and 6 the right."""
    doc, base = _load("fs/fhd-fapm6-rj45@1"), _load("fs/fhd-fapm6@1")
    offsets = [p["at"][0] - c["at"][0] for p, c in zip(doc["parts"], base["parts"])]
    assert offsets == pytest.approx([offsets[0]] * 6), "one offset from every clip position"
    low, up = doc["parts"][0]["at"], doc["parts"][1]["at"]
    assert low[0] == up[0] and low[1] > up[1], "p1 is below p2 in the left column"
    xs = [p["at"][0] for p in doc["parts"]]
    assert xs == sorted(xs) and len(set(xs)) == 3


def test_the_rj45_panel_has_a_punch_down_rear_for_each_jack():
    doc = _load("fs/fhd-fapm6-rj45@1")
    assert "optical" not in doc and "cages" not in doc and "bays" not in doc
    assert doc["faces"] == {"rear": {"ref": "fs/fhd-fapm6-rj45-rear@1"}}
    rear = _load("fs/fhd-fapm6-rj45-rear@1")
    assert [p["id"] for p in rear["parts"]] == [f"b{n}" for n in range(1, 7)], "bN behind pN"
    for p in rear["parts"]:
        assert p["ref"] == "common/idc-termination@1", p
    term = _load("common/idc-termination@1")
    assert term["class"] == "port" and term["attrs"]["media"] == "idc"
    text = " ".join(str(v) for v in (doc["description"], *doc["provenance"].values())).lower()
    assert "punch-down" in text and "idc" in text, "the part must say the rear is an IDC termination"
    assert "estimated" in text, "the match of #72818 to the punch-down jack is declared"


def test_the_blank_panel_closes_every_opening_and_offers_no_port():
    doc, base = _load("fs/fhd-fapm6-blank@1"), _load("fs/fhd-fapm6@1")
    assert len(doc["parts"]) == 6
    assert [p["at"] for p in doc["parts"]] == [c["at"] for c in base["parts"]]
    for p in doc["parts"]:
        assert _load(p["ref"])["class"] != "port", p
    assert "faces" not in doc and "optical" not in doc and "cages" not in doc and "bays" not in doc


@pytest.mark.parametrize("name", FAPM6_ENCLOSURES)
def test_every_fapm6_enclosure_accepts_both_panels(name):
    text = (LIB / "devices" / "fs" / name / "device.yaml").read_text()
    lists = text.count("- fs/fhd-fapm6@1")
    assert lists >= 4, name
    for ref in NEW:
        assert text.count(f"- {ref}") == lists, f"{name}: {ref} is in {text.count(f'- {ref}')} of {lists} accepts lists"
