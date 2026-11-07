"""The SFP-DD cages: `std/sfp-dd@1` and `std/sfp-dd-ganged@1`.

Written before either cage, and each assertion below was seen failing against
a tree with neither. The figures come from two cage makers' own documents, read
as data, and not from the SFP-DD MSA, whose sites are no longer reliable:

  TE Connectivity customer drawing C-2359845 rev A (2020-06-18), "Cage Assembly,
  SFPDD 1x1 Standard, w/ General HS", sheets 1 and 3;
  TE application specification 114-60027 rev A (2020-06-18), Figure 4 and 3.2 A;
  Molex product customer drawing 2048233001 rev A (2022-12-10), "SFP-DD 1x1 STD
  1 Rear Leg" (sales drawing for part 204823-4101), sheets 1 and 6;
  Molex application specification 2048230001 rev A (2020-01-02).

Where the two agree the test pins the figure. Where they differ the test pins
the one the contract uses and says which maker it is.

The lint tests use a throwaway device, never a library one: the first device
to place these cages is a later change.
"""
import json
import pathlib
import re

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import lint as L

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMAS = ROOT / "spec/schemas"
STD = LIB / "components/std"

L.STANDARDS.update(L.load_yaml(SCHEMAS / "standards.yaml")["standards"])

SINGLE = STD / "sfp-dd/v1/contract.yaml"
GANGED = STD / "sfp-dd-ganged/v1/contract.yaml"


def _contract(path):
    return yaml.safe_load(path.read_text())


def _provenance(doc):
    return json.dumps(doc.get("provenance") or {}, sort_keys=True)


# --- the dimensions, against the makers' drawings ----------------------------

def test_the_single_cage_is_the_bezel_cutout_both_makers_dimension():
    """TE sheet 3 and Molex sheet 6 both give the bezel cutout of a 1x1 cage as
    15.45 +/-0.10 by 10.40 +/-0.10, R0.30 max. TE's depth is the bezel to the
    centreline of the connector guide pins, 38.90 +/-0.30 (sheet 3); Molex's
    held sheets give no bezel-to-connector figure."""
    c = _contract(SINGLE)
    assert c["size"] == {"w": 15.45, "h": 10.4, "d": 38.9}
    assert c["elements"]["opening"]["size"] == [15.45, 10.4]
    assert c["conforms"] == "sfp-dd" and c["interface"] == "sfp-dd"
    assert c["attrs"] == {"media": "sfp-dd"}


def test_the_cage_interior_is_the_port_opening_both_makers_dimension():
    """TE sheet 1, "port opening" 14.00 +/-0.10 by 8.95 +/-0.10; Molex sheet 1,
    14.00 +/-0.10 by 8.95 +/-0.15, "inside to inside". The tolerance on the
    height differs; the figure does not."""
    for path in (SINGLE, GANGED):
        c = _contract(path)
        assert c["relief"]["size"] == {"w": 14.0, "h": 8.95}, path
        assert c["relief"]["cavity"] == "cavity", path


def test_the_ganged_port_is_its_share_of_one_continuous_slot():
    """TE 114-60027 3.2 A: port-to-port centreline spacing is 14.25. Figure 4's
    cutouts are N x 14.25 + 1.2 wide (1x1 15.45, 1x4 58.20, 1x6 86.70, 1x8
    115.20) by 10.4, so a port's share is 14.25 and neighbours abut."""
    c = _contract(GANGED)
    assert c["size"] == {"w": 14.25, "h": 10.4, "d": 38.9}
    assert c["elements"]["opening"]["size"] == [14.25, 10.4]
    assert c["conforms"] == "sfp-dd-ganged" and c["interface"] == "sfp-dd"
    assert c["attrs"] == {"media": "sfp-dd"}
    for n, cutout in ((1, 15.45), (4, 58.20), (6, 86.70), (8, 115.20)):
        assert n * c["size"]["w"] + 1.2 == pytest.approx(cutout)


def test_the_mate_point_is_the_centre_of_the_opening():
    single, ganged = _contract(SINGLE), _contract(GANGED)
    assert single["connection-points"]["mate"] == {"at": [7.725, 5.2], "direction": "front"}
    assert ganged["connection-points"]["mate"] == {"at": [7.125, 5.2], "direction": "front"}


def test_every_dimension_names_its_maker_drawing():
    """Each of size, depth and the interior says which drawing and sheet it is
    read from, for both makers where both state it."""
    for path in (SINGLE, GANGED):
        prov = _contract(path)["provenance"]
        for key in ("size", "depth", "relief.size"):
            assert key in prov, (path, key)
        for key in ("size", "relief.size"):
            text = prov[key]
            assert "2359845" in text and "rev A" in text, (path, key)
            assert "2048233001" in text, (path, key)
        assert "2359845" in prov["depth"] and "38.90" in prov["depth"]


def test_the_single_cages_pitch_and_the_ganged_ones_row_say_where_they_come_from():
    single = _contract(SINGLE)["provenance"]
    assert "16.25" in single["pitch"] and "114-60027" in single["pitch"]
    assert "Molex" in single["pitch"] and "1.30" in single["pitch"]
    ganged = _contract(GANGED)["provenance"]
    assert "14.25" in ganged["size"] and "114-60027" in ganged["size"]


def test_a_figure_read_off_a_picture_is_estimated_and_says_how():
    """The latch side is read off the front view and the Molex wording differs
    from TE's; the collar is the library's one shared estimate."""
    for path in (SINGLE, GANGED):
        prov = _contract(path)["provenance"]
        assert prov["latch"].startswith("estimated"), path
        assert "front view" in prov["latch"], path
    collar = next(f for f in _contract(SINGLE)["relief"]["features"]
                  if f["node"] == "collar")
    assert collar["confidence"] == "estimated" and collar["out"] == 1.0
    assert "relief" not in _contract(GANGED) or not any(
        f.get("node") == "collar" for f in _contract(GANGED)["relief"].get("features", []))


def test_the_skins_are_drawn_at_the_contracts_size():
    for path, w in ((SINGLE, 15.45), (GANGED, 14.25)):
        svg = (path.parent / "skins/default.svg").read_text()
        assert f'viewBox="0 0 {w:g} 10.4"' in svg, path
        assert f'width="{w:g}mm" height="10.4mm"' in svg, path
        for node in ("opening", "cavity"):
            assert f'id="{node}"' in svg, (path, node)
    assert 'id="collar"' in (SINGLE.parent / "skins/default.svg").read_text()


# --- the registry ------------------------------------------------------------

def _std():
    return yaml.safe_load((SCHEMAS / "standards.yaml").read_text())["standards"]


def test_standards_has_the_single_cage():
    e = _std()["sfp-dd"]
    assert (e["w"], e["h"], e["radius"], e["depth"]) == (15.45, 10.4, 0.3, 38.9)
    assert e["confidence"] == "drawing" and e["depth-confidence"] == "drawing"
    assert e["cavity"] == {"w": 14.0, "h": 8.95}
    assert e["pitch"] == 16.25 and e["pitch-kind"] == "floor"
    for cited in ("2359845", "114-60027", "2048233001", "2048230001"):
        assert cited in e["registry"], cited


def test_standards_has_the_ganged_cage():
    e = _std()["sfp-dd-ganged"]
    assert (e["w"], e["h"], e["depth"]) == (14.25, 10.4, 38.9)
    assert e["confidence"] == "drawing"
    assert "row-pitch" not in e, "neither maker states a belly-to-belly row pitch"
    assert "114-60027" in e["registry"]


def test_the_media_name_speeds_and_lanes_say_what_only_the_msa_settles():
    """The makers' documents name the module (SFP-DD), its connector (40
    positions, 0.8 mm pitch) and what mates with the cage (SFP-DD MSA
    compliant transceivers). Neither states a rate, a lane count or that an SFP
    module works in the cage, so those carry `unconfirmed`."""
    e = _std()["sfp-dd"]
    assert e["media"] == "sfp-dd"
    assert e["connector-positions"] == 40 and e["connector-pitch"] == 0.8
    assert e["lanes"] == 2 and e["lanes-confidence"] == "unconfirmed"
    assert e["speeds"] == {"per-lane": ["25g", "50g"], "aggregate": ["50g", "100g"]}
    assert e["speeds-confidence"] == "unconfirmed"
    assert e["backwards-compatible-with"] == "sfp"
    assert e["backwards-confidence"] == "unconfirmed"
    assert e["export-media"] == "100gbase-x-sfpdd"
    assert "MSA" in e["backwards-note"] and "14.00" in e["backwards-note"]
    assert _std()["sfp-dd-ganged"]["media"] == "sfp-dd"


def test_the_registry_no_longer_says_there_is_no_cage():
    fam = yaml.safe_load((SCHEMAS / "pluggables.yaml").read_text())["families"]["sfp-dd"]
    assert "NO CAGE IN THE LIBRARY YET" not in fam["source"]
    assert "std/sfp-dd" in fam["source"]
    assert fam["interface"] == "sfp-dd" and fam["also-accepts"] == ["sfp"]


def test_l103_no_longer_warns_for_any_family():
    with L.collecting() as found:
        L.lint_pluggable_family_interfaces(LIB)
    assert [w for w in found.warnings if "[L103]" in w] == []


# --- the registry is enforced against a contract ------------------------------

class _NoSchema:
    def iter_errors(self, _data):
        return iter(())


def _lint_contract(tmp_path, doc):
    p = tmp_path / "contract.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    with L.collecting() as found:
        L.lint_component(p, _NoSchema())
    return [e for e in found.errors if "[L9]" in e]


def test_a_cage_that_departs_from_the_registry_is_an_l9_error(tmp_path):
    """Non-vacuity: the clean contracts above are only meaningful if a wrong
    one is refused."""
    doc = _contract(SINGLE)
    assert _lint_contract(tmp_path, doc) == []
    doc["size"] = dict(doc["size"], w=14.5)
    assert any("15.45" in e for e in _lint_contract(tmp_path, doc))
    doc = _contract(GANGED)
    assert _lint_contract(tmp_path, doc) == []
    doc["size"] = dict(doc["size"], d=41.0)
    assert any("38.9" in e for e in _lint_contract(tmp_path, doc))


def test_two_single_cages_closer_than_the_floor_are_an_l81_finding():
    parts = [{"ref": "std/sfp-dd@1", "id": i, "at": [x, 0.0]}
             for i, x in (("a", 0.0), ("b", 15.5))]
    doc = {"kind": "component", "size": {"w": 40.0, "h": 12.0}, "parts": parts}
    with L.collecting() as found:
        L.lint_component_composed_pitch("t/contract.yaml", doc, [str(LIB)])
    hits = [e for e in found.errors if "[L81]" in e]
    assert len(hits) == 1 and "16.25" in hits[0] and "floor" in hits[0], hits
    parts[1]["at"] = [16.25, 0.0]
    with L.collecting() as found:
        L.lint_component_composed_pitch("t/contract.yaml", doc, [str(LIB)])
    assert [e for e in found.errors if "[L81]" in e] == []


# --- a minimal face that uses each cage, linted --------------------------------

def _face():
    """A 1RU face: one single cage, a four-port ganged row and the belly-to-belly
    row below it, 14.25 apart with the lower row turned over."""
    placements = [{"id": "single-1", "ref": "std/sfp-dd@1", "group": "dd",
                   "at": [20.0, 10.0]}]
    for i in range(4):
        placements.append({"id": f"gang-{i + 1}", "ref": "std/sfp-dd-ganged@1",
                           "group": "dd", "at": [100.0 + 14.25 * i, 10.0]})
        placements.append({"id": f"gang-{i + 5}", "ref": "std/sfp-dd-ganged@1",
                           "group": "dd", "rotate": 180,
                           "at": [100.0 + 14.25 * i, 22.95]})
    return {"format": 1, "kind": "device", "name": "sfp-dd-fixture",
            "version": "1.0.0", "manufacturer": "Acme", "model": "SDD-1",
            "maturity": "draft", "profile": "networking",
            "chassis": {"width": 440.0, "height": 44.0, "depth": 300.0},
            "groups": {"dd": {"term": "Port", "role": "traffic",
                              "attrs": {"media": "sfp-dd", "speed": "100g"}}},
            "views": {"front": {"size": {"w": 440.0, "h": 44.0},
                                "components": {"placements": placements}}}}


def _lint_face(tmp_path, doc):
    p = tmp_path / "device.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    validator = L.load_schema(SCHEMAS, "device.schema.json")
    with L.collecting() as found:
        L.lint_device(p, validator, [str(LIB)])
    return found


def test_a_face_of_each_cage_lints_clean(tmp_path):
    found = _lint_face(tmp_path, _face())
    assert found.errors == [], found.errors
    codes = {"L9", "L22", "L26", "L81", "L103", "L104", "L108"}
    mine = [w for w in found.warnings
            if any(f"[{c}]" in w for c in codes)]
    assert mine == [], mine


def test_a_face_that_declares_sfp_dd_media_over_an_sfp_cage_is_l104(tmp_path):
    """Non-vacuity for the aperture check: the same face on `std/sfp-ganged@1`
    presents the `sfp` family, so L104 fires; on the SFP-DD cages it does not."""
    doc = _face()
    doc["views"]["front"]["components"]["placements"] = [
        {"id": "p", "ref": "std/sfp-ganged@1", "group": "dd", "at": [20.0, 10.0]}]
    found = _lint_face(tmp_path, doc)
    assert [w for w in found.warnings if "[L104]" in w], found.warnings


# --- what the cages offer ------------------------------------------------------

@pytest.mark.heavy
def test_an_sfp_dd_cage_offers_the_sfp_generics_and_no_part_names_it(tmp_path):
    """No generic optic is added: no part states `mates: sfp-dd`, and the
    family's `also-accepts: [sfp]` is what seats the SFP generics. If an
    SFP-DD optic is ever drawn this list gains it, and this test says so."""
    import sys
    import warmrender
    dev = tmp_path / "device.yaml"
    dev.write_text(yaml.safe_dump(_face(), sort_keys=False))
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"),
                        str(dev), "--library", str(LIB), "--out", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    idx = json.loads((tmp_path / "sfp-dd-fixture.configs.json").read_text())
    by_id = {c["id"]: c for c in idx["cages"]["front"]}
    assert set(by_id) >= {"single-1", "gang-1", "gang-8"}
    offered = {tuple(c["accepts"]) for c in by_id.values()}
    assert len(offered) == 1, offered
    assert list(offered.pop()) == ["generic/sfp-cable@1", "generic/sfp-lc-simplex@2",
                                    "generic/sfp-lc@1", "generic/sfp-rj45@1",
                                    "generic/sfp-sc-key-up@1", "generic/sfp-sc@1",
                                    "molex/sfp-plus-passive-dac@1",
                                    "wetatronics/conx-sfp@1"]
    for c in by_id.values():
        assert c["interface"] == "sfp-dd" and c["media"] == "sfp-dd"
    import libdata
    assert not [ref for ref, _path, doc in libdata.components()
                if doc.get("mates") == "sfp-dd"]


# --- the export ----------------------------------------------------------------

def test_the_export_types_each_cage_a_name_both_dcim_targets_have():
    """`100gbase-x-sfpdd` is TYPE_100GE_SFP_DD in netbox-community/netbox
    (netbox/dcim/choices.py at 758af333) and in nautobot/nautobot
    (nautobot/dcim/choices.py at 45d26083). Neither has a 50G SFP-DD type, so a
    port stating 50g is untyped here rather than exported as an SFP56."""
    assert dx.PART_IFACE["std/sfp-dd"] == "100gbase-x-sfpdd"
    assert dx.PART_IFACE["std/sfp-dd-ganged"] == "100gbase-x-sfpdd"
    assert dx.iface_type({"ref": "std/sfp-dd@1"}, {"media": "sfp-dd", "speed": "100g"}) \
        == "100gbase-x-sfpdd"
    assert dx.iface_type({"ref": "std/sfp-dd-ganged@1"},
                         {"media": "sfp-dd", "speed": "100g"}) == "100gbase-x-sfpdd"
    assert dx.iface_type({"ref": "std/sfp-dd-ganged@1"},
                         {"media": "sfp-dd", "speed": "50g"}) is None
    assert dx.iface_type({"ref": "std/sfp-dd-ganged@1"}, {"media": "sfp-dd"}) is None


def test_a_qsfp_dd_cage_is_still_a_qsfp_dd_cage_to_the_export():
    assert dx.iface_type({"ref": "std/qsfp-dd@1"},
                         {"media": "qsfp-dd", "speed": "400g"}) == "400gbase-x-qsfpdd"
