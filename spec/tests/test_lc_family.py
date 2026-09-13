"""The LC family: one bore part and the three faces that compose it (#126).

std/lc-bore drew a 4.7 SQUARE until #126. A real LC opening is keyed - the
square is only its first tier, and an LC plug's latch rides in three more.

Where the figures come from, because they are not all the same strength:

  * 4.7 +/-0.05 square and the 6.25 +/-0.05 pitch are DIMENSIONED, twice over -
    section A-A of the ProLabs PAN-QSFP28-100GBASE-CWDM4-C datasheet and the
    LINK-PP LS-SM311G-10C product drawing, which is the first transceiver-
    specific source the library has held for either.
  * The three latch tier WIDTHS are dimensioned on the plug that enters the
    opening - SENKO DS-LC-000004 Rev A gives 3.3 / 4.3 / 2.3 with tolerances -
    plus the clearance traced off SENKO DS-LC-000010 Rev A.
  * The three latch tier HEIGHTS are CONVENTIONAL. Five documents draw this
    receptacle and none dimensions its slot; they defer to IEC 61754-20, which
    is paywalled. These tests exist to keep that distinction visible.

The drawings are under working/intake/fiber-connectors/lc/ and are not
committed; the numbers are.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))

STANDARDS = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]

BODY = (4.7, 4.7)
NECK = (3.46, 0.42)
SHOULDER = (4.7, 0.49)
TONGUE = (2.64, 0.69)
APERTURE = (4.7, 6.3)


def contract(ref):
    nsname, major = ref.rsplit("@", 1)
    return yaml.safe_load((LIB / "components" / nsname / f"v{major}" / "contract.yaml").read_text())


def skin(ref, name="default"):
    nsname, major = ref.rsplit("@", 1)
    return (LIB / "components" / nsname / f"v{major}" / "skins" / f"{name}.svg").read_text()


def test_the_registry_aperture_is_the_keyed_opening_not_the_square():
    r = STANDARDS["lc-duplex-receptacle"]
    assert (r["w"], r["h"]) == APERTURE
    # The pair is only as strong as its weaker half, and the halves differ: the
    # 4.7 is dimensioned and the 6.3 is not. Recording `drawing` here would let
    # a consumer read a fitted height as a measured one.
    assert r["confidence"] == "estimated"
    assert r["pitch"] == 6.25 and r["pitch-confidence"] == "verified"


def test_the_registry_carries_the_four_tiers():
    tiers = STANDARDS["lc-duplex-receptacle"]["tiers"]
    assert [t["name"] for t in tiers] == ["body", "neck", "shoulder", "tongue"]
    assert (tiers[0]["w"], tiers[0]["h"]) == BODY
    assert (tiers[1]["w"], tiers[1]["h"]) == NECK
    assert (tiers[2]["w"], tiers[2]["h"]) == SHOULDER
    assert (tiers[3]["w"], tiers[3]["h"]) == TONGUE
    # The body is the dimensioned tier and says nothing; the three latch tiers
    # are the library's convention and each says so on its own row. Same shape
    # of record std/rj45@2 uses for its own undimensioned slot.
    assert "confidence" not in tiers[0]
    assert all(t["confidence"] == "conventional" for t in tiers[1:])


def test_the_tiers_sum_to_the_aperture():
    tiers = STANDARDS["lc-duplex-receptacle"]["tiers"]
    assert round(sum(t["h"] for t in tiers), 6) == APERTURE[1]
    assert max(t["w"] for t in tiers) == APERTURE[0]


def test_both_sources_for_the_square_are_named():
    r = STANDARDS["lc-duplex-receptacle"]
    # The single-source risk this entry carried is retired, and the entry has to
    # keep saying so - a reader who sees only ProLabs cannot tell that the 4.7
    # was independently confirmed on a transceiver.
    assert "ProLabs" in r["registry"]
    assert "LINK-PP" in r["registry"]
    assert "61754-20" in r["notes"]


def test_the_bore_is_one_keyed_part_at_one_version():
    versions = sorted(p.name for p in (LIB / "components/std/lc-bore").iterdir() if p.is_dir())
    # #126's first half: two majors drawing the same square. There is one.
    assert versions == ["v3"]
    c = contract("std/lc-bore@3")
    assert c["version"] == "3.0.0"
    assert (c["size"]["w"], c["size"]["h"]) == APERTURE
    assert c["conforms"] == "lc-duplex-receptacle"
    assert c["elements"]["bore"]["size"] == list(APERTURE)


def test_the_skin_draws_the_tiers_and_not_a_rect():
    s = skin("std/lc-bore@3")
    # A <rect id="bore"> is the defect #126 opened. The opening is a path.
    assert '<path id="bore"' in s
    assert '<rect id="bore"' not in s
    for node in ("key-neck", "key-shoulder", "key-tongue", "ferrule", "sleeve"):
        assert f'id="{node}"' in s


def test_the_keyway_scoop_steps_deeper_going_out_from_the_bore():
    tops = {f["node"]: f["top"] for f in contract("std/lc-bore@3")["relief"]["features"]
            if f["node"].startswith("key-")}
    # The slot rounds away toward its outer end so a finger can reach the latch.
    # This vocabulary has no chamfers (spec/DEPTH-AND-3D.md s7), so three steps
    # approximate the curve - and it is the ORDER that is being claimed here,
    # not the values, which are estimated and say so.
    assert tops["key-neck"] > tops["key-shoulder"] > tops["key-tongue"]


def test_every_invented_relief_magnitude_says_it_is_invented():
    for f in contract("std/lc-bore@3")["relief"]["features"]:
        assert f["confidence"] == "estimated"
        assert f["source"].strip()


def test_the_three_faces_compose_the_bore_tongue_up():
    # Every receptacle in the corpus is drawn latch-up; the part draws it down,
    # so each placement turns it. A placement that forgets is upside down.
    for ref, ids in (("common/lc-duplex-adapter@3", ("tx", "rx")),
                     ("common/sfp-lc-duplex@1", ("lc-a", "lc-b")),
                     ("common/qsfp-transceiver@1", ("tx", "rx"))):
        parts = {p["id"]: p for p in contract(ref)["parts"] if p["ref"].startswith("std/lc-bore@")}
        assert set(parts) == set(ids), ref
        for p in parts.values():
            assert p["ref"] == "std/lc-bore@3", ref
            assert p["rotate"] == 180, ref


def test_the_adapter_bore_centres_sit_on_the_verified_pitch():
    # Three majors of lc-bore passed under this part with its centres unmoved
    # at (3.3, 5.5) and (9.9, 5.5) - the Smartoptics stencil's 6.6 pitch. That
    # was corrected to the standard's verified 6.25 (task 1, connector-components
    # plan): centres now at (3.175, 5.5) and (9.425, 5.5). The dust caps moved
    # with them, so they still plug the bore SQUARE, which still starts at y 3.15.
    c = contract("common/lc-duplex-adapter@3")
    parts = {p["id"]: p for p in c["parts"]}
    for pid, x in (("tx", 0.825), ("rx", 7.075)):
        assert parts[pid]["at"] == [x, 1.55]
        # at.y + tongue+shoulder+neck = the square's top edge, rotated
        assert round(parts[pid]["at"][1] + 1.60, 6) == 3.15
    assert c["elements"]["cap-tx"]["at"] == [0.825, 3.15]
    assert c["elements"]["cap-rx"]["at"] == [7.075, 3.15]


def test_the_transceiver_optical_axis_is_below_the_face_centreline():
    # It sat at 4.25 - half of 8.5 - which no source gives and which only ever
    # suited a square bore. A 6.3 opening at 4.25 collides with the SFP's bail
    # and will not fit inside the QSFP's receptacle housing at all.
    sfp = contract("common/sfp-lc-duplex@1")
    assert sfp["size"]["h"] == 8.5
    assert sfp["connection-points"]["optical"]["at"][1] == 5.7
    # mate aligns the module in its cage and stays on the centreline.
    assert sfp["connection-points"]["mate"]["at"][1] == 4.25

    qsfp = contract("common/qsfp-transceiver@1")
    assert qsfp["size"]["h"] == 8.5
    assert qsfp["connection-points"]["optical-tx"]["at"][1] == 4.9
    assert qsfp["connection-points"]["optical-rx"]["at"][1] == 4.9
    assert qsfp["connection-points"]["mate"]["at"][1] == 4.25


def test_the_transceiver_apertures_clear_the_art_around_them():
    sfp = contract("common/sfp-lc-duplex@1")
    top = {p["id"]: p["at"][1] for p in sfp["parts"] if p["ref"].startswith("std/lc-bore@")}
    # The bail lies across 0.55..1.60. An aperture starting above 1.60 cuts it.
    assert all(y >= 1.60 for y in top.values()), top

    qsfp = contract("common/qsfp-transceiver@1")
    ap_top = min(p["at"][1] for p in qsfp["parts"] if p["ref"].startswith("std/lc-bore@"))
    housing = skin("common/qsfp-transceiver@1", "lc")
    # The housing has to contain the opening it frames - it was 5.30 tall
    # against a 6.3 opening, which is impossible at any position.
    assert 'id="opening"' in housing and 'height="6.90"' in housing
    assert ap_top >= 0.65 and ap_top + APERTURE[1] <= 7.55


def ferrule_centres(ref):
    """Where each composed bore's ferrule actually lands on the parent face.

    The ferrule sits at (2.35, 2.35) in the bore's own frame; rotate: 180 turns
    the part about its own centre, which puts it at (2.35, 6.3 - 2.35).
    """
    out = []
    for p in contract(ref)["parts"]:
        if not p["ref"].startswith("std/lc-bore@"):
            continue
        x, y = p["at"]
        assert p.get("rotate") == 180, ref
        out.append((round(x + 2.35, 6), round(y + APERTURE[1] - 2.35, 6)))
    return sorted(out)


def test_the_declared_optical_point_is_where_the_ferrules_actually_are():
    """The invariant that catches an axis moving without its record moving.

    #126 moved the transceiver apertures and their optical points together, but
    a prose passage describing the OLD centres survived the move in
    sfp-lc-duplex and had to be caught in review. Coordinates can be checked
    even when prose cannot, so check them: whatever the placements resolve to
    is what `optical` has to say, on all three faces.
    """
    for ref, keys in (("common/lc-duplex-adapter@3", ["optical"]),
                      ("common/sfp-lc-duplex@1", ["optical"]),
                      ("common/qsfp-transceiver@1", ["optical-tx", "optical-rx"])):
        centres = ferrule_centres(ref)
        assert len(centres) == 2, ref
        # both bores share one axis - they are a duplex pair, not a stack
        assert centres[0][1] == centres[1][1], ref
        cps = contract(ref)["connection-points"]
        if len(keys) == 2:
            assert [tuple(cps[k]["at"]) for k in keys] == centres, ref
        else:
            # one point for the pair: the midpoint of the two ferrules
            mid = (round(sum(c[0] for c in centres) / 2, 6), centres[0][1])
            assert tuple(cps[keys[0]]["at"]) == mid, ref


def test_mate_stays_on_the_centreline_even_though_optical_does_not():
    # mate aligns the module in its cage and is not the optical axis. #126
    # separated the two on both transceivers; nothing may quietly re-merge them.
    for ref in ("common/sfp-lc-duplex@1", "common/qsfp-transceiver@1"):
        c = contract(ref)
        assert c["connection-points"]["mate"]["at"][1] == c["size"]["h"] / 2, ref


def test_the_qsfp_silkscreen_is_not_the_colour_of_the_face_it_sits_on():
    # T and R were #8d949c on a #8d949c face and had never rendered at all.
    lc = skin("common/qsfp-transceiver@1", "lc")
    assert 'fill="#8d949c" text-anchor="middle"' not in lc
    assert 'id="silkscreen"' in lc
