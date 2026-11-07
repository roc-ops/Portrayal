"""The NEMA 5-15R receptacle face, std/nema-5-15r@1.

`nema-5-15r` was a registered interface with a plug that mates it and no part
that presents it. These tests read the real library for what is true of the
part: it presents the key at a mate point, its neutral slot is a plain slot and
not the T of a 5-20R, its DCIM outlet type is a value both targets list, and a
5-15P is the plug it takes while a 5-20P is not.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import lint
from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
COMP = LIB / "components"
SVG = "{http://www.w3.org/2000/svg}"

REF = "std/nema-5-15r@1"
CORD_15, CORD_20 = "generic/nema-5-15p-cord@1", "generic/nema-5-20p-cord@1"
C14 = "generic/c14-plug@1"


def contract(ref=REF):
    name, major = ref.split("@")
    return yaml.safe_load((COMP / name / f"v{major}" / "contract.yaml").read_text())


def skin_ids(ref=REF):
    name, major = ref.split("@")
    root = ET.parse(COMP / name / f"v{major}" / "skins/default.svg").getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def standards():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def test_the_part_presents_the_registered_receptacle_key():
    c = contract()
    assert c["class"] == "inlet" and c["interface"] == "nema-5-15r"
    assert c["conforms"] == "nema-5-15r" and "mates" not in c
    assert c["attrs"]["outlet"] == "nema-5-15r" and c["attrs"]["media"] == "ac"
    assert c["attrs"]["rating-a"] == 15 and "input" not in c["attrs"]
    reg = render_mod._connector_registry()
    assert reg["nema-5-15r"].get("standard") == "nema-5-15r"
    assert "nema-5-20r" in reg, "a 5-15R and a 5-20R stay two interfaces"


def test_size_is_the_registry_entry_and_a_flat_face_has_no_pit():
    c = contract()
    entry = standards()["nema-5-15r"]
    assert (c["size"]["w"], c["size"]["h"]) == (entry["w"], entry["h"])
    assert "d" not in c["size"]
    assert {f["node"] for f in c["relief"]["features"] if f.get("pocket")} == \
        {"hole-earth", "slot-line", "slot-neutral"}


def test_the_neutral_slot_is_a_plain_slot_and_not_a_t():
    """The T is the 5-20 key; a 5-15R has two parallel slots and an earth hole."""
    ids = skin_ids()
    assert ids["slot-neutral"].tag == f"{SVG}rect"
    assert ids["slot-line"].tag == f"{SVG}rect"
    assert ids["hole-earth"].tag == f"{SVG}path"
    t = skin_ids("std/nema-5-20r@1")["slot-neutral"]
    assert t.tag == f"{SVG}path", "the 5-20R's neutral slot is the T"


def test_the_blades_stand_6_35_either_side_of_the_mate_on_the_blade_line():
    """The mate is on the earth axis at the line of the blades, as the 5-20R's
    is; a 5-15P's blades are 12.7 apart (Volex PS204), 6.35 each side of it."""
    ids = skin_ids()
    mx, my = contract()["connection-points"]["mate"]["at"]
    centre = {k: (float(ids[k].get("x")) + float(ids[k].get("width")) / 2,
                  float(ids[k].get("y")) + float(ids[k].get("height")) / 2)
              for k in ("slot-line", "slot-neutral")}
    assert centre["slot-line"][0] == pytest.approx(mx - 6.35, abs=0.05)
    assert centre["slot-neutral"][0] == pytest.approx(mx + 6.35, abs=0.05)
    assert centre["slot-line"][1] == pytest.approx(my, abs=0.05)
    assert centre["slot-neutral"][1] == pytest.approx(my, abs=0.05)
    earth = ids["hole-earth"].get("d").replace("M", "").split("H")
    left = float(earth[0].split()[0])
    right = float(earth[1].split()[0])
    assert (left + right) / 2 == pytest.approx(mx, abs=0.01)


def test_the_outlet_exports_as_the_type_both_targets_list():
    assert dx.PART_OUTLET["std/nema-5-15r"] == "nema-5-15r"
    assert "nema-5-15r" in dx.OUTLET_TYPES
    assert set(dx.PART_OUTLET.values()) <= dx.OUTLET_TYPES


def test_a_5_15p_is_offered_and_a_5_20p_is_not():
    cands = render_mod._pluggable_candidates([str(LIB)])
    offered = {r for r, _c in cands["nema-5-15r"]}
    assert CORD_15 in offered and CORD_20 not in offered and C14 not in offered
    # and the 5-20R still offers both of the NEMA plugs
    assert {CORD_15, CORD_20} <= {r for r, _c in cands["nema-5-20r"]}


def test_lint_seats_a_5_15p_in_it_and_refuses_the_others(capsys):
    def said(occ):
        found = []
        orig = lint.err
        lint.err = lambda path, code, msg, *a, **k: found.append((code, msg))
        try:
            lint._mate_check("x.yaml", "front/p", occ, REF, [str(LIB)])
        finally:
            lint.err = orig
        return found

    assert said(CORD_15) == []
    assert [c for c, _m in said(CORD_20)] == ["L12"]
    assert [c for c, _m in said(C14)] == ["L12"]
