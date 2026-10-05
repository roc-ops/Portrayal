"""The RJ45 family: two bare jacks, two lamped ones (docs/rj45-family-design.md).

Every figure here is from TE customer drawing 1734264 rev A2 unless a test says
otherwise. The drawings are under working/intake/standards/rj45/ and are not
committed; the numbers are.
"""
import pathlib
import re
import shutil
import subprocess
import sys
import textwrap

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
from portrayal import lint
from portrayal import dcim_export as dx
from portrayal import libwalk

STANDARDS = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]

# sweep_rj45.py's own job is done - task 15 deletes the seven parts it converts
# FROM, once every device that had one is swept. Its regression tests still
# prove the conversion was right, so they run it against this private library
# instead of the real one: a symlink of everything the real library still
# holds, plus the seven retired contracts as they were the day they were
# retired, frozen under spec/tests/fixtures/rj45_retired/ rather than restored
# from git history (which will not hold HEAD's copy forever).
RETIRED_FIXTURES = ROOT / "spec/tests/fixtures/rj45_retired"


@pytest.fixture(scope="session")
def sweep_lib(tmp_path_factory):
    """A private library sweep_rj45.py's regression tests run against: a
    symlink of everything the real library still holds, plus the seven
    retired contracts as they were the day they were retired. Built once per
    test session under pytest's own tmp_path_factory, which pytest cleans up
    itself (keeping the last few sessions' bases for post-mortem)."""
    tmp = tmp_path_factory.mktemp("rj45-sweep-lib")
    comp = tmp / "components"
    # Symlink each VERSION directory, not each name directory: std/rj45-ganged
    # and std/rj45 both still exist (their v2 is current), so their own name
    # directory must be real here too, or restoring v1 below would create it
    # inside the symlink's target - the real library - instead of this copy.
    for version_dir in (LIB / "components").glob("*/*/v*"):
        if not version_dir.is_dir():
            continue
        ns, name = version_dir.parent.parent.name, version_dir.parent.name
        (comp / ns / name).mkdir(parents=True, exist_ok=True)
        (comp / ns / name / version_dir.name).symlink_to(version_dir)
    for contract in RETIRED_FIXTURES.glob("*/*/*/contract.yaml"):
        ns, name, version = contract.parts[-4:-1]
        dest = comp / ns / name / version
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(contract, dest / "contract.yaml")
    return tmp

BODY = (11.91, 6.83)
SHOULDER = (6.30, 1.69)
SLOT_W = 4.06


def test_the_rj45_registry_entry_is_the_housing_from_te_1734264():
    r = STANDARDS["rj45"]
    assert (r["w"], r["h"], r["depth"]) == (15.8, 13.2, 18.6)
    assert r["confidence"] == "drawing"
    assert r["depth-confidence"] == "drawing"
    assert "1734264" in r["registry"]
    assert r["cavity"] == {"w": 11.91, "h": 11.2}


def test_the_registry_carries_the_three_tiers():
    for key in ("rj45", "rj45-ganged"):
        tiers = STANDARDS[key]["tiers"]
        assert [t["name"] for t in tiers] == ["body", "shoulder", "slot"]
        assert (tiers[0]["w"], tiers[0]["h"]) == BODY
        assert (tiers[1]["w"], tiers[1]["h"]) == SHOULDER
        # M2: the slot DOES carry a height, and the point of it carrying one is
        # that it also carries its own confidence - the 2.6 is conventional, not
        # dimensioned on TE 1734264 or the Amphenol views, and a consumer reading
        # the registry could not tell which tier figure was soft while the flag
        # lived only in the design note's prose.
        assert tiers[2]["w"] == SLOT_W
        assert tiers[2]["h"] == 2.6
        assert tiers[2]["confidence"] == "conventional"
        assert "confidence" not in tiers[0] and "confidence" not in tiers[1]


def test_the_ganged_cell_keeps_its_measured_face_and_gains_the_tiers():
    g = STANDARDS["rj45-ganged"]
    assert (g["w"], g["h"]) == (12.7, 11.0)
    assert g["confidence"] == "measured"
    assert g["cavity"] == {"w": 11.91, "h": 10.5}
    assert g["depth"] == 18.6
    assert g["depth-confidence"] == "drawing"


def contract(ref):
    nsname, major = ref.rsplit("@", 1)
    return yaml.safe_load((LIB / "components" / nsname / f"v{major}" / "contract.yaml").read_text())


def skin(ref, name="default"):
    nsname, major = ref.rsplit("@", 1)
    return (LIB / "components" / nsname / f"v{major}" / "skins" / f"{name}.svg").read_text()


def cavity_path(ref):
    m = re.search(r'id="cavity"[^>]*\bd="([^"]+)"', skin(ref), re.S)
    assert m, "no cavity path"
    return m.group(1)


def tier_widths(d):
    """The horizontal runs of an evenodd cavity path, largest first. A three-tier
    opening drawn as one outline has runs of the body, shoulder and slot widths."""
    runs = {abs(float(x)) for x in re.findall(r"h\s*(-?[\d.]+)", d)}
    return sorted(runs, reverse=True)


def test_std_rj45_v2_is_the_housing():
    c = contract("std/rj45@2")
    assert c["version"].startswith("2.")
    assert c["size"] == {"w": 15.8, "h": 13.2, "d": 18.6}
    assert c["conforms"] == "rj45" and c["interface"] == "rj45"
    assert c["elements"]["opening"]["class"] == "cutout"
    assert c["relief"]["cavity"] == "cavity"
    assert c["relief"]["size"] == {"w": 11.91, "h": 11.2}
    assert c["connection-points"]["mate"] == {"at": [7.9, 6.6], "direction": "front"}
    assert "1734264" in yaml.safe_dump(c["provenance"])


def test_std_rj45_v2_cavity_has_three_tiers():
    """Body 11.91; shoulder 6.30 drawn as two 2.805 steps in from the body;
    slot 4.06 reached by two 1.12 steps in from the shoulder (TE 1734264)."""
    widths = tier_widths(cavity_path("std/rj45@2"))
    assert 11.91 in widths and 4.06 in widths, widths
    assert 2.805 in widths and 1.12 in widths, widths
    assert round(11.91 - 2 * 2.805, 2) == 6.3
    assert round(6.3 - 2 * 1.12, 2) == 4.06


def test_std_rj45_v2_lints_clean(tmp_path):
    p = LIB / "components/std/rj45/v2/contract.yaml"
    import jsonschema, json
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    if not lint.STANDARDS:
        lint.STANDARDS.update(STANDARDS)
    with lint.collecting() as found:
        data = lint.lint_component(p, jsonschema.Draft202012Validator(schema))
        lint._skin_checks(p, data)    # L3 (every element id in the skin) and L4 (viewBox = size)
    assert not [e for e in found.errors
                if "[L9]" in e or "[L1]" in e or "[L3]" in e or "[L4]" in e], found.errors


def test_std_rj45_ganged_v2_is_the_cell():
    c = contract("std/rj45-ganged@2")
    assert c["size"] == {"w": 12.7, "h": 11.0, "d": 18.6}
    assert c["conforms"] == "rj45-ganged" and c["interface"] == "rj45"
    assert c["relief"]["size"] == {"w": 11.91, "h": 10.5}
    assert c["connection-points"]["mate"] == {"at": [6.35, 5.1], "direction": "front"}
    widths = tier_widths(cavity_path("std/rj45-ganged@2"))
    assert 11.91 in widths and 4.06 in widths and 2.805 in widths and 1.12 in widths, widths


def test_common_rj45_eth_composes_the_housing_and_adds_two_lamps():
    c = contract("common/rj45-eth@1")
    assert c["size"] == {"w": 15.8, "h": 13.2, "d": 18.6}
    assert c["parts"] == [{"ref": "std/rj45@2", "id": "jack", "at": [0.0, 0.0], "behind": True}]
    assert c["elements"]["led-a"]["at"] == [1.2, 11.83] and c["elements"]["led-a"]["size"] == [2.0, 1.1]
    assert c["elements"]["led-b"]["at"] == [12.6, 11.83]
    for el in ("led-a", "led-b"):
        assert c["elements"][el]["class"] == "led"
    # link on one window, activity on the other: names only, no colours asserted
    assert c["elements"]["led-a"]["states"] == ["off", "link"]
    assert c["elements"]["led-b"]["states"] == ["off", "activity"]
    assert c["connection-points"]["net"] == {"at": [7.9, 6.6], "direction": "front"}
    assert "conforms" not in c, "the wrapper composes the standard; it does not restate it"


def test_common_rj45_eth_pinside_carries_its_lamps_in_the_side_walls_at_the_pin_end():
    c = contract("common/rj45-eth-pinside@1")
    assert c["size"] == {"w": 15.8, "h": 13.2, "d": 18.6}
    assert c["parts"] == [{"ref": "std/rj45@2", "id": "jack", "at": [0.0, 0.0], "behind": True}]
    assert c["elements"]["led-a"]["at"] == [0.1, 1.6] and c["elements"]["led-b"]["at"] == [13.95, 1.6]
    for el in ("led-a", "led-b"):
        w, h = c["elements"][el]["size"]
        assert c["elements"][el]["class"] == "led" and h > w, "the window is taller than wide"
        x, y = c["elements"][el]["at"]
        # in a side wall (the opening spans x 1.945..13.855) and in the pin half
        assert x + w <= 1.945 or x >= 13.855, el
        assert y + h < c["size"]["h"] / 2, el
    assert c["elements"]["led-a"]["states"] == ["off", "link"]
    assert c["elements"]["led-b"]["states"] == ["off", "activity"]
    assert "conforms" not in c


def test_l76_takes_the_pinside_jack_as_lamped():
    """Without its entry in the lamped set the census follows `parts` to
    std/rj45@2 and calls an Ethernet port on it bare."""
    assert lint.rj45_class("common/rj45-eth-pinside@1", [str(LIB)]) == "lamped"
    eth = {"id": "port-1", "ref": "common/rj45-eth-pinside@1", "at": [0, 0], "attrs": {"role": "port"}}
    assert l76c("flom-x", [eth]) == []
    ws = l76c("flom-x", [{**eth, "id": "console", "attrs": {"role": "console"}}])
    assert len(ws) == 1 and "1 console/timing jack(s) on a lamped part" in ws[0]


def test_the_pinside_jack_exports_as_ethernet_at_the_cards_speed():
    assert dx.iface_type({"ref": "common/rj45-eth-pinside@1", "id": "port-1"}, {}, "traffic") == "1000base-t"
    card = contract("hpe/flom-817745-b21@1")
    assert [p["ref"] for p in card["parts"]] == ["common/rj45-eth-pinside@1"] * 2
    doc = dx.build_module(card, "HPE")
    assert [(i["name"], i["type"]) for i in doc["interfaces"]] == [("port-1", "10gbase-t"), ("port-2", "10gbase-t")]


def test_common_rj45_eth_skin_punches_the_opening_through_its_own_face():
    s = skin("common/rj45-eth@1")
    assert 'id="led-a"' in s and 'id="led-b"' in s
    assert "var(--led-color" in s
    # the face is drawn evenodd with the opening as a hole, so the composed jack
    # behind it shows through (see common/rj45-port@4's skin comment)
    assert 'fill-rule="evenodd"' in s


def test_common_rj45_ganged_eth_composes_the_cell_and_adds_two_lamps():
    c = contract("common/rj45-ganged-eth@1")
    assert c["size"] == {"w": 12.7, "h": 11.0, "d": 18.6}
    assert c["parts"] == [{"ref": "std/rj45-ganged@2", "id": "jack", "at": [0.0, 0.0], "behind": True}]
    assert c["elements"]["led-a"]["at"] == [1.2, 9.63]
    assert c["elements"]["led-b"]["at"] == [9.5, 9.63]
    assert c["elements"]["led-a"]["states"] == ["off", "link"]
    assert c["elements"]["led-b"]["states"] == ["off", "activity"]
    assert c["connection-points"]["net"] == {"at": [6.35, 5.1], "direction": "front"}
    s = skin("common/rj45-ganged-eth@1")
    assert 'fill-rule="evenodd"' in s and 'id="led-b"' in s


def test_the_dell_carrier_attaches_ism_meanings_to_the_new_lamps():
    c = contract("dell/rj45-port-14g@1")
    assert c["version"] == "1.3.0"
    # 1.3.0 (#610): the carrier presents the jack itself - it wraps a wrapper,
    # so the slot code could not reach std/rj45@2 through it - at the housing's
    # own centre, which the 180 turn leaves in place.
    assert c["interface"] == "rj45"
    assert c["connection-points"]["mate"] == {"at": [7.9, 6.6], "direction": "front"}
    part = c["parts"][0]
    assert part["ref"] == "common/rj45-eth@1"
    assert set(part["states"]) == {"led-a", "led-b"}, "the carrier names the new part's lamps"
    # common/rj45-eth@1's led-a is its LOCAL left window; the carrier's rotate:
    # 180 (added to restore keyway-up) lands it on screen-right, so the LINK
    # vocabulary - measured on the keyway's screen-left - lives on led-b now.
    names = [s if isinstance(s, str) else s["name"] for s in part["states"]["led-b"]]
    assert "off" in names and len(names) >= 3, "ISM table 11's LINK vocabulary survives"


def test_the_dell_carrier_turns_the_housing_keyway_up():
    c = contract("dell/rj45-port-14g@1")
    part = c["parts"][0]
    assert part["ref"] == "common/rj45-eth@1"
    assert part.get("rotate") == 180, (
        "common/rj45-eth@1 draws keyway-down unrotated; the Dell jacks are "
        "keyway-up in ISM figure 8, so the composed part must turn 180"
    )


def test_the_base_stylesheet_renders_the_link_state():
    """`link` is a bare token in common/rj45-eth@1 and common/rj45-ganged-eth@1,
    so it takes its presentation from the renderer's base stylesheet, as `up`
    and `activity` already do. Without a rule the lamp declares a state nothing
    paints, which test_state_css catches on a build - this catches it on the
    source."""
    from portrayal import render
    assert ".state-link" in render.STATE_CSS
    assert ".state-up" in render.STATE_CSS


def _dev(placements, groups=None):
    return {"kind": "device", "name": "d", "version": "1.0.0",
            "chassis": {"width": 100, "height": 40, "depth": 30},
            "groups": groups or {"mgmt": {"term": "Port"}, "console": {"term": "Port"}},
            "views": {"front": {"size": {"w": 100, "h": 40},
                                "components": {"placements": placements}}}}


def l76(data):
    with lint.collecting() as _found:
        lint.lint_device_rj45_lamps(pathlib.Path("d/device.yaml"), data, [str(LIB)])
    return [w for w in _found.warnings if "[L76]" in w]


def test_l76_is_quiet_when_roles_and_parts_agree():
    ws = l76(_dev([
        {"id": "mgmt-eth", "ref": "common/rj45-eth@1", "at": [0, 0], "group": "mgmt", "attrs": {"role": "mgmt"}},
        {"id": "console", "ref": "std/rj45@2", "at": [20, 0], "group": "console", "attrs": {"role": "console"}},
        {"id": "tod-in", "ref": "std/rj45-ganged@2", "at": [40, 0], "group": "mgmt"},
    ]))
    assert ws == []


def test_l76_counts_an_ethernet_jack_with_no_lamps():
    ws = l76(_dev([{"id": "port-1", "ref": "std/rj45-ganged@2", "at": [0, 0], "group": "mgmt", "attrs": {"role": "port"}}]))
    assert len(ws) == 1 and "1 Ethernet jack(s) on a part with no lamps" in ws[0]


def test_l76_counts_a_console_with_lamps_and_a_retired_part():
    ws = l76(_dev([
        {"id": "console", "ref": "common/rj45-eth@1", "at": [0, 0], "group": "console"},
        {"id": "port-2", "ref": "std/rj45-ganged@1", "at": [20, 0], "group": "mgmt", "attrs": {"role": "port"}},
    ]))
    assert len(ws) == 1
    assert "1 console/timing jack(s) on a lamped part" in ws[0]
    assert "1 on a retired RJ45 part" in ws[0]


# Defect found piloting the sweep on real devices: edgecore/as5912-54x draws
# mgmt-eth's two lamps as separate placements BESIDE the bare jack, not
# composed inside it. L76 must not count that as "on a part with no lamps" -
# the jack has lamps, they just aren't the ones the ref itself would draw.
def test_l76_does_not_count_an_ethernet_jack_whose_lamp_is_drawn_beside_it():
    ws = l76(_dev([
        {"id": "mgmt-eth", "ref": "std/rj45@2", "at": [0, 0], "group": "mgmt", "attrs": {"role": "mgmt"}},
        {"id": "led-mgmt-lnk", "ref": "common/led-dot@1", "at": [50, 50], "group": "mgmt",
         "for": "mgmt-eth", "attrs": {"function": "link"}},
    ]))
    assert ws == []


def test_l76_still_counts_an_ethernet_jack_with_truly_no_lamps():
    ws = l76(_dev([{"id": "mgmt-eth", "ref": "std/rj45@2", "at": [0, 0], "group": "mgmt", "attrs": {"role": "mgmt"}}]))
    assert len(ws) == 1 and "1 Ethernet jack(s) on a part with no lamps" in ws[0]


def _wants(id_, role=None, group="mgmt"):
    q = {"id": id_, "group": group, "attrs": ({"role": role} if role else {})}
    return lint.rj45_wants_lamps(q, {"mgmt": {"attrs": {}}})


@pytest.mark.parametrize("id_", ["con", "tod", "clk-a", "gm-ptp", "bits-0", "console-1"])
def test_rj45_wants_lamps_is_false_for_bare_ids(id_):
    assert _wants(id_) is False


def test_rj45_wants_lamps_is_false_for_console_role():
    assert _wants("port-9", role="console") is False


@pytest.mark.parametrize("id_", ["mgmt-eth", "port-1", "ethernet", "mgmt0"])
def test_rj45_wants_lamps_is_true_for_ethernet_ids(id_):
    assert _wants(id_) is True


# second-tod-x contains the bare token "tod" flanked by hyphens (-tod-), so it
# IS bare by the rule - it is not exempted just because "tod" isn't the whole id.
def test_rj45_wants_lamps_is_false_for_an_id_containing_the_bare_token():
    assert _wants("second-tod-x") is False


# contact-1 and oob contain no bare token (contact is not "con" bounded by a
# separator; oob is not "aux"/"con"/etc at all), and eth-lan is plainly Ethernet.
@pytest.mark.parametrize("id_", ["contact-1", "oob", "eth-lan"])
def test_rj45_wants_lamps_is_true_when_no_token_matches(id_):
    assert _wants(id_) is True


# The tokens added after #125's final review found 48 RJ48c T1/E1 ports swept
# onto the lamped part (review C1) and 24 Cisco timing jacks the census would
# have mis-flagged (review I5). Each is boundary-anchored like the rest.
@pytest.mark.parametrize("id_", ["ieee-1588", "ics-0", "port-t1", "e1-3",
                                 "ds1-0", "rj48-a", "che1-2"])
def test_rj45_wants_lamps_is_false_for_the_non_ethernet_tokens(id_):
    assert _wants(id_) is False


# ...and they are anchored, so they do not fire inside an unrelated word.
@pytest.mark.parametrize("id_", ["ice-0", "note1", "atm1"])
def test_the_new_tokens_do_not_fire_unanchored(id_):
    assert _wants(id_) is True


# media: is where half the corpus says what a jack is. casa/smm-sw-bdm-a's
# psu-monitor carries `media: rj45-telemetry` and no bare token anywhere else.
@pytest.mark.parametrize("media,want", [("rj45-telemetry", False),
                                        ("rj45-serial", False),
                                        ("rj45", True)])
def test_rj45_wants_lamps_reads_media(media, want):
    q = {"id": "psu-monitor", "group": "mgmt", "attrs": {"media": media}}
    assert lint.rj45_wants_lamps(q, {"mgmt": {"attrs": {}}}) is want


# On a component's parts:, the contract's own name is part of the text: a
# channelized T1/E1 card numbers its RJ48c jacks port-* like any other card.
def test_rj45_wants_lamps_reads_the_contract_name_for_a_component_part():
    q = {"id": "port-0-0", "attrs": {"media": "rj45"}}
    assert lint.rj45_wants_lamps(q, {}) is True
    assert lint.rj45_wants_lamps(q, {}, "mic-3d-16che1-t1-ce") is False
    assert lint.rj45_wants_lamps(q, {}, "spa-8xcht1-e1") is False
    assert lint.rj45_wants_lamps(q, {}, "mpc7e-10g") is True


def l76c(name, parts):
    with lint.collecting() as _found:
        lint.lint_component_rj45_lamps(
            pathlib.Path("library/components/x/y/v1/contract.yaml"),
            {"name": name, "parts": parts}, [str(LIB)])
    return [w for w in _found.warnings if "[L76]" in w]


# I5: 368 of the library's 762 RJ45 placements sit in component contracts, and
# the census that could not see them is how C1 got in.
def test_l76_counts_a_component_parts_entry():
    ws = l76c("mpc7e-10g", [{"id": "port-1", "ref": "std/rj45-ganged@2", "at": [0, 0],
                             "attrs": {"role": "port"}}])
    assert len(ws) == 1 and "1 Ethernet jack(s) on a part with no lamps" in ws[0]
    assert "mpc7e-10g" in ws[0]


def test_l76_is_quiet_on_a_t1_cards_bare_ports():
    assert l76c("mic-3d-16che1-t1-ce",
                [{"id": "port-0-0", "ref": "std/rj45-ganged@2", "at": [0, 0],
                  "attrs": {"media": "rj45"}}]) == []


def test_l76_counts_a_t1_cards_lamped_ports():
    ws = l76c("mic-3d-16che1-t1-ce",
              [{"id": "port-0-0", "ref": "common/rj45-ganged-eth@1", "at": [0, 0],
                "attrs": {"media": "rj45"}}])
    assert len(ws) == 1 and "1 console/timing jack(s) on a lamped part" in ws[0]


# The Dell carrier draws nothing and composes common/rj45-eth@1; a card placing
# it is placing a lamped jack, not a retired part.
def test_l76_follows_a_carrier_to_the_family_member_it_composes():
    assert l76c("ndc-4x-rj45-14g",
                [{"id": "port-1", "ref": "dell/rj45-port-14g@1", "at": [0, 0]}]) == []


# The family's own members compose each other by definition.
def test_l76_does_not_census_the_family_itself():
    with lint.collecting() as _found:
        lint.lint_component_rj45_lamps(
            LIB / "components/common/rj45-eth/v1/contract.yaml",
            yaml.safe_load((LIB / "components/common/rj45-eth/v1/contract.yaml").read_text()),
            [str(LIB)])
    assert [w for w in _found.warnings if "[L76]" in w] == []


# C1: these four cards are RJ48c carrying DS1, not Ethernet. They must stay bare.
@pytest.mark.parametrize("rel", [
    "components/cisco/spa-8xcht1-e1/v1/contract.yaml",
    "components/cisco/spa-8xcht1-e1-v2/v1/contract.yaml",
    "components/juniper/mic-3d-16che1-t1-ce/v1/contract.yaml",
    "components/juniper/mic-3d-16che1-t1-ce-v/v1/contract.yaml",
])
def test_the_t1_e1_cards_ports_are_bare_jacks(rel):
    d = yaml.safe_load((LIB / rel).read_text())
    jacks = [p for p in d["parts"] if "rj45" in str(p.get("ref"))]
    assert jacks
    assert {str(p["ref"]) for p in jacks} == {"std/rj45-ganged@2"}
    assert "port-jacks-are-bare" in d["provenance"]


SWEEP = ROOT / "spec/tools/sweeps/sweep_rj45.py"

FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d
version: 1.2.3
manufacturer: Acme
model: D
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
  mgmt-leds: {term: LED}
  console: {term: Port}
views:
  front:
    size: {w: 100, h: 40}
    panel:
      cutouts:
        - {id: mgmt-eth, at: [10.0, 10.0], size: [16, 14]}
        - {id: console, at: [40.0, 10.0], size: [16, 14]}
    silkscreen:
      - {at: [12, 30], text: MGMT, for: mgmt-eth}
      - {at: [12, 32], text: L, for: led-mgmt-l}
    components:
      placements:
        - {id: mgmt-eth, ref: std/rj45@1, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
        - {id: led-mgmt-l, ref: common/led-dot@1, at: [11.2, 21.73], group: mgmt-leds, rel-pos: 1, for: mgmt-eth,
           states: ['off', {name: link-1g, color: '#22c55e'}]}
        - {id: led-mgmt-r, ref: common/led-dot@1, at: [22.8, 21.73], group: mgmt-leds, rel-pos: 2, for: mgmt-eth, attrs: {function: activity}}
        - {id: console, ref: std/rj45@1, at: [40.0, 10.0], group: console, rel-pos: 2}
""")


def sweep(tmp_path, sweep_lib, *args):
    d = tmp_path / "devices/acme/d"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(FIXTURE)
    # the tool resolves component classes through --library; give it the real library
    # for components and the tmp tree for devices
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), *args],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout, (d / "device.yaml").read_text()


CON_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d
version: 1.2.3
manufacturer: Acme
model: D
chassis: {width: 100, height: 40, depth: 30}
groups:
  sio: {term: Port}
views:
  front:
    size: {w: 100, h: 40}
    panel:
      cutouts:
        - {id: con, at: [10.0, 10.0], size: [16, 14]}
    components:
      placements:
        - {id: con, ref: std/rj45@1, at: [10.0, 10.0], group: sio, rel-pos: 1}
""")


def test_the_sweep_maps_a_con_id_to_the_bare_ref(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(CON_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "con" in r.stdout
    assert "bare" in r.stdout, "an id like `con` must map bare (std/rj45@2), not lamped"


def test_the_sweep_reports_and_changes_nothing_without_apply(tmp_path, sweep_lib):
    out, text = sweep(tmp_path, sweep_lib)
    assert "mgmt-eth" in out and "console" in out
    assert text == FIXTURE


def test_the_sweep_moves_by_role_and_holds_the_centre(tmp_path, sweep_lib):
    _, text = sweep(tmp_path, sweep_lib, "--apply")
    d = yaml.safe_load(text)
    pl = {p["id"]: p for p in d["views"]["front"]["components"]["placements"]}
    assert pl["mgmt-eth"]["ref"] == "common/rj45-eth@1"
    assert pl["mgmt-eth"]["at"] == [10.1, 10.4]          # (16-15.8)/2, (14-13.2)/2
    assert pl["console"]["ref"] == "std/rj45@2"
    assert pl["console"]["at"] == [40.1, 10.4]


def test_the_sweep_lifts_the_lamps_into_the_jack(tmp_path, sweep_lib):
    _, text = sweep(tmp_path, sweep_lib, "--apply")
    d = yaml.safe_load(text)
    pl = {p["id"]: p for p in d["views"]["front"]["components"]["placements"]}
    assert "led-mgmt-l" not in pl and "led-mgmt-r" not in pl
    assert pl["mgmt-eth"]["states"]["led-a"] == ["off", {"name": "link-1g", "color": "#22c55e"}]
    assert pl["mgmt-eth"]["states"]["led-b"] == ["off", {"name": "activity"}]
    legends = [s["for"] for s in d["views"]["front"]["silkscreen"]]
    assert legends == ["mgmt-eth", "mgmt-eth"]


def test_the_sweep_resizes_the_cutouts_and_bumps_major(tmp_path, sweep_lib):
    _, text = sweep(tmp_path, sweep_lib, "--apply")
    d = yaml.safe_load(text)
    cuts = {c["id"]: c for c in d["views"]["front"]["panel"]["cutouts"]}
    assert cuts["mgmt-eth"]["size"] == [15.8, 13.2] and cuts["mgmt-eth"]["at"] == [10.1, 10.4]
    assert d["version"] == "2.0.0", "two ids were removed"
    # and the prose survived: textual edit, not a dump
    assert "text: MGMT" in text


def test_the_sweep_is_minor_when_no_id_is_removed(tmp_path, sweep_lib):
    # strip both lamp placements (led-mgmt-l's spans two lines) and the
    # silkscreen entry that names one of them, leaving valid YAML with no
    # lamp id anywhere for the sweep to remove
    lone = re.sub(r"      - \{at: \[12, 32\].*?for: led-mgmt-l\}\n", "", FIXTURE)
    lone = re.sub(r"        - \{id: led-mgmt-l.*?\n.*?\n", "", lone)
    lone = re.sub(r"        - \{id: led-mgmt-r.*?\n", "", lone)
    d = tmp_path / "devices/acme/d"; d.mkdir(parents=True); (d / "device.yaml").write_text(lone)
    subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"], check=True)
    assert yaml.safe_load((d / "device.yaml").read_text())["version"] == "1.3.0"


# --- Fix round 1: six review findings ------------------------------------

# Finding 1 (critical): the cutout's `at` must shift by half the difference
# between the CUTOUT's own old size and the new part's size, not by half the
# difference between the old and new PART sizes. celestica/es1010 port-1 is
# the real case: cutout size [12.7, 11] already matches the new part
# (common/rj45-ganged-eth@1, 12.7 x 11) even though the old part
# (common/rj45-hd@1, 14 x 12) does not - so the cutout must not move at all.
CUTOUT_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d2
version: 1.0.0
manufacturer: Acme
model: D2
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
views:
  front:
    size: {w: 100, h: 40}
    panel:
      cutouts:
        - {id: port-1, at: [2.11, 16.1], size: [12.7, 11]}
    components:
      placements:
        - {id: port-1, ref: common/rj45-hd@1, at: [2.11, 16.1], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
""")


def test_the_sweep_holds_the_cutouts_own_centre_not_the_parts(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d2"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(CUTOUT_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "cutouts held 1" in r.stdout, "this cutout was never derived from the old part - it is informative"
    data = yaml.safe_load((d / "device.yaml").read_text())
    cut = data["views"]["front"]["panel"]["cutouts"][0]
    assert cut["at"] == [2.11, 16.1], "cutout size already matches the new part: its centre must not move"
    assert cut["size"] == [12.7, 11.0]


# Finding 2 (critical): these contracts are retired wrappers deleted in a
# later task; sweeping their internal `jack:` part now would move it out from
# under the very file that's about to disappear. Skip by path, report nothing.
def test_the_sweep_skips_retired_rj45_wrapper_contracts(tmp_path, sweep_lib):
    lib = tmp_path / "lib"
    for rel in ("components/common/rj45-hd-plain", "components/std/rj45-ganged"):
        shutil.copytree(sweep_lib / rel, lib / rel)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(lib), "--components"],
                        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rj45-hd-plain" not in r.stdout


# Finding 3 (important): span() and cutout_span() must be scoped to the
# current view's line range. Two views carrying the same placement id (as 68
# non-RJ45 ids do today in variant views) must each be found and moved once.
SCOPING_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d3
version: 1.0.0
manufacturer: Acme
model: D3
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
views:
  front:
    size: {w: 100, h: 40}
    components:
      placements:
        - {id: mgmt-eth, ref: std/rj45@1, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
  front-lff-12:
    face: front
    size: {w: 100, h: 40}
    components:
      placements:
        - {id: mgmt-eth, ref: std/rj45@1, at: [50.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
""")


def test_the_sweep_scopes_ids_to_their_own_view(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d3"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(SCOPING_FIXTURE)
    subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"], check=True)
    data = yaml.safe_load((d / "device.yaml").read_text())
    front = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    variant = {p["id"]: p for p in data["views"]["front-lff-12"]["components"]["placements"]}
    assert front["mgmt-eth"]["ref"] == "common/rj45-eth@1"
    assert front["mgmt-eth"]["at"] == [10.1, 10.4]
    assert variant["mgmt-eth"]["ref"] == "common/rj45-eth@1"
    assert variant["mgmt-eth"]["at"] == [50.1, 10.4]


# Finding 4 (important): sweep_component must report an unresolved part
# instead of silently skipping it, matching sweep_device's own behaviour.
# The part's id line is written with two spaces after the colon so span()'s
# regex (which requires exactly one) cannot find it - a real-shaped miss,
# not a contrived one.
UNRESOLVED_CONTRACT = textwrap.dedent("""\
format: 1
kind: component
name: test-card
version: 1.0.0
class: card
profile: networking
size: {w: 50.0, h: 30.0, d: 10.0}
parts:
  - {id:  bad-jack, ref: std/rj45@1, at: [1.0, 1.0]}
""")


def test_the_sweep_reports_unresolved_parts_instead_of_silently_skipping(tmp_path):
    lib = tmp_path / "lib"
    contract_dir = lib / "components/acme/test-card/v1"
    contract_dir.mkdir(parents=True)
    (contract_dir / "contract.yaml").write_text(UNRESOLVED_CONTRACT)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(lib), "--components"],
                        capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no parts line" in r.stdout


# Finding 5 (important): legend re-pointing must (a) dedup a `for: [...]`
# list after two lifted ids collapse onto the same jack, and (b) not treat
# `-` as a word boundary, or `led-mgmt-l` matches inside `led-mgmt-l-2`.
LEGEND_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d4
version: 1.0.0
manufacturer: Acme
model: D4
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
  mgmt-leds: {term: LED}
views:
  front:
    size: {w: 100, h: 40}
    silkscreen:
      - {at: [12, 30], text: MGMT, for: [led-mgmt-l, led-mgmt-r]}
      - {at: [12, 34], text: L2, for: led-mgmt-l-2}
    components:
      placements:
        - {id: mgmt-eth, ref: std/rj45@1, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
        - {id: led-mgmt-l, ref: common/led-dot@1, at: [11.2, 21.73], group: mgmt-leds, rel-pos: 1, for: mgmt-eth, attrs: {function: link-1g}}
        - {id: led-mgmt-r, ref: common/led-dot@1, at: [22.8, 21.73], group: mgmt-leds, rel-pos: 2, for: mgmt-eth, attrs: {function: activity}}
        - {id: led-mgmt-l-2, ref: common/led-dot@1, at: [70.0, 21.73], group: mgmt-leds, rel-pos: 3, attrs: {function: link-1g}}
""")


def test_the_sweep_dedupes_and_respects_legend_boundaries(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d4"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(LEGEND_FIXTURE)
    subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"], check=True)
    data = yaml.safe_load((d / "device.yaml").read_text())
    legends = data["views"]["front"]["silkscreen"]
    assert legends[0]["for"] == ["mgmt-eth"], "two lifted ids collapsed onto the same jack must dedup"
    assert legends[1]["for"] == "led-mgmt-l-2", "a lamp that is NOT lifted must be untouched"


# Finding 6 (important, controller ruling): led-a is the component's LOCAL
# left window. A jack with rotate: 180 presents it on screen-right, so the
# lifted lamp with the LOWER x maps to led-b (not led-a) when rotated 180.
ROTATED_FIXTURE = FIXTURE.replace(
    "{id: mgmt-eth, ref: std/rj45@1, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}",
    "{id: mgmt-eth, ref: std/rj45@1, at: [10.0, 10.0], group: mgmt, rel-pos: 1, rotate: 180, attrs: {role: mgmt}}",
)
assert ROTATED_FIXTURE != FIXTURE, "fixture edit must actually take"


def test_the_sweep_flips_handedness_for_a_rotated_jack(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(ROTATED_FIXTURE)
    subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"], check=True)
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    # led-mgmt-l (lower x, 11.2) is the LEFT lamp; rotated 180 it presents on
    # screen-right, so its states land on led-b, not led-a.
    assert pl["mgmt-eth"]["states"]["led-b"] == ["off", {"name": "link-1g", "color": "#22c55e"}]
    assert pl["mgmt-eth"]["states"]["led-a"] == ["off", {"name": "activity"}]


# --- Fix round 2: a jack whose lamps sit beside it, not inside it ---------

# Defect found piloting the sweep on real devices: edgecore/as5912-54x
# mgmt-eth is common/rj45-bezel@2 (no lamps) and its two management lamps are
# drawn as separate placements BESIDE the jack, outside its footprint.
# Deciding by role alone (mgmt -> Ethernet -> wants lamps) moved the jack onto
# the LAMPED common/rj45-eth@1, which would draw four lamps where the
# hardware has two. Controller ruling: a jack with a `for:` lamp OUTSIDE its
# old footprint takes the BARE target regardless of role, and nothing is
# lifted from it.
EXTERNAL_LAMPS_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d6
version: 1.0.0
manufacturer: Acme
model: D6
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
  mgmt-leds: {term: LED}
views:
  front:
    size: {w: 100, h: 40}
    components:
      placements:
        - {id: mgmt-eth, ref: common/rj45-bezel@2, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
        - {id: led-mgmt-lnk, ref: common/led-dot@1, at: [11.0, 30.0], group: mgmt-leds, rel-pos: 1, for: mgmt-eth, attrs: {function: link}}
        - {id: led-mgmt-act, ref: common/led-dot@1, at: [15.0, 30.0], group: mgmt-leds, rel-pos: 2, for: mgmt-eth, attrs: {function: activity}}
""")


def test_the_sweep_leaves_a_jack_bare_when_its_lamps_are_external(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d6"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(EXTERNAL_LAMPS_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "external-lamps 1" in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt-eth"]["ref"] == "std/rj45@2", "role wanted lamps, but the lamps sit outside the footprint"
    assert "led-mgmt-lnk" in pl and "led-mgmt-act" in pl, "lamps beside the jack must not be lifted"
    assert "states" not in pl["mgmt-eth"]


def test_a_swept_device_renders_lamps_inside_its_management_jack(tmp_path):
    """After the Edgecore sweep the AS7726-32X's mgmt-eth is common/rj45-eth@1 and
    its two lamps are elements of that placement, not neighbours of it."""
    dev = LIB / "devices/edgecore/as7726-32x/device.yaml"
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    svg = next(tmp_path.glob("as7726-32x.*.front.svg")).read_text()
    assert 'data-path="mgmt-eth/led-a"' in svg and 'data-path="mgmt-eth/led-b"' in svg
    assert 'data-path="led-mgmt-eth-l"' not in svg
    assert 'data-path="mgmt-eth/jack/opening"' in svg, "the housing's three-tier cavity is in the drawing"
# --- Fix round 3: pilot lessons (derived cutouts, dropped skins, orphan groups) ---

# Ruling A: most RJ45 cutouts were DERIVED from the old part (`at` = jack `at`
# + the old part's own aperture offset, `size` = the old aperture's size).
# common/rj45-bezel@2 composes std/rj45@1 (16 x 14, offset (0, 0)) at [0.5, 0.5],
# so its derived aperture is 16 x 14 at the jack's own `at` + (0.5, 0.5). The new
# lamped target, common/rj45-eth@1, composes std/rj45@2 (15.8 x 13.2, offset
# (0, 0)) at (0, 0) - an aperture offset of zero, unlike the old bezel. A
# held-centre cutout would land 0.05-0.1mm off that new derived aperture and
# trip L63; the ruling instead RE-DERIVES a matching cutout from the new part.
DERIVED_CUTOUT_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d7
version: 1.0.0
manufacturer: Acme
model: D7
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
views:
  front:
    size: {w: 100, h: 40}
    panel:
      cutouts:
        - {id: mgmt-eth, at: [10.5, 10.5], size: [16, 14]}
    components:
      placements:
        - {id: mgmt-eth, ref: common/rj45-bezel@2, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
""")


def test_the_sweep_rederives_a_derived_cutout(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d7"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(DERIVED_CUTOUT_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "cutouts re-derived 1" in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt-eth"]["ref"] == "common/rj45-eth@1"
    assert pl["mgmt-eth"]["at"] == [10.6, 10.85]
    cut = data["views"]["front"]["panel"]["cutouts"][0]
    assert cut["at"] == [10.6, 10.85], "re-derived from the new part's own (0, 0) offset"
    assert cut["size"] == [15.8, 13.2]


# test_the_sweep_holds_the_cutouts_own_centre_not_the_parts (above, the es1010
# case) is the INFORMATIVE half of ruling A: its cutout never matched the old
# derived aperture (the old part's aperture offset is (0.65, 0.5), the cutout
# sits at the jack's own `at` with no offset applied), so it still holds its
# own centre and the report says "cutouts held 1" - already asserted there.


# Ruling B: a placement's `skin:` the new part does not declare is dropped.
# All four new parts declare skins: [default]; common/rj45-bezel@2 (console
# here, a bare target either way) declares skins: [default, dark] - `dark`
# has nowhere to go.
SKIN_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d8
version: 1.0.0
manufacturer: Acme
model: D8
chassis: {width: 100, height: 40, depth: 30}
groups:
  console: {term: Port}
views:
  front:
    size: {w: 100, h: 40}
    components:
      placements:
        - {id: console, ref: common/rj45-bezel@2, at: [10.0, 10.0], group: console, rel-pos: 1, skin: dark}
""")


def test_the_sweep_drops_a_skin_the_new_part_lacks(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d8"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(SKIN_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "skin dropped 1" in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["console"]["ref"] == "std/rj45@2"
    assert "skin" not in pl["console"], "std/rj45@2 declares skins: [default] only - dark has nowhere to go"


# Ruling C: after lifting, a group with no remaining member anywhere is
# reported (not removed - a group removal is its own major bump under
# devicelock's rules, a human's call). The brief's own FIXTURE is the case:
# mgmt-leds holds only led-mgmt-l/led-mgmt-r, both lifted into mgmt-eth.
def test_the_sweep_reports_an_emptied_group(tmp_path, sweep_lib):
    out, _ = sweep(tmp_path, sweep_lib, "--apply")
    assert ("! group mgmt-leds has no members after lifting - remove it by hand "
            "(a group removal is a major bump)") in out


# A fixture where mgmt-leds keeps another member (not lifted, since it is not
# `for:` the jack) must not be reported.
KEPT_GROUP_FIXTURE = FIXTURE.replace(
    "        - {id: console, ref: std/rj45@1, at: [40.0, 10.0], group: console, rel-pos: 2}\n",
    "        - {id: console, ref: std/rj45@1, at: [40.0, 10.0], group: console, rel-pos: 2}\n"
    "        - {id: led-other, ref: common/led-dot@1, at: [90.0, 30.0], group: mgmt-leds, rel-pos: 3, attrs: {function: fan}}\n",
)
assert KEPT_GROUP_FIXTURE != FIXTURE, "fixture edit must actually take"


def test_the_sweep_does_not_report_a_group_that_keeps_a_member(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(KEPT_GROUP_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "mgmt-leds has no members" not in r.stdout


# --- Controller ruling (ufispace s9* batch): a lamp on the jack's edge -----
#
# Five s9* devices drew a management lamp within a millimetre of the jack's
# footprint edge - not clearly inside, not clearly beside it. Ruling: within
# LAMP_EDGE_TOL (1.0mm) of the footprint counts as INSIDE (lifted); beyond it
# is still OUTSIDE (external, jack stays bare). mgmt-eth here is std/rj45@1 at
# [10.0, 10.0], so its old footprint is x:[10, 26], y:[10, 24] (16 x 14, see
# `size(std/rj45@1)`); a single `for:` lamp keeps this test clear of the
# separate "lamps both inside and outside" unresolved case.
EDGE_TOL_INSIDE_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d9
version: 1.0.0
manufacturer: Acme
model: D9
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
  mgmt-leds: {term: LED}
views:
  front:
    size: {w: 100, h: 40}
    components:
      placements:
        - {id: mgmt-eth, ref: std/rj45@1, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
        - {id: led-mgmt-l, ref: common/led-dot@1, at: [26.8, 15.0], group: mgmt-leds, rel-pos: 1, for: mgmt-eth, attrs: {function: link}}
""")

EDGE_TOL_OUTSIDE_FIXTURE = EDGE_TOL_INSIDE_FIXTURE.replace("[26.8, 15.0]", "[27.5, 15.0]")
assert EDGE_TOL_OUTSIDE_FIXTURE != EDGE_TOL_INSIDE_FIXTURE, "fixture edit must actually take"


def test_a_lamp_08mm_outside_the_box_is_lifted(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d9"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(EDGE_TOL_INSIDE_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "external-lamps" not in r.stdout, "0.8mm outside the old footprint is within LAMP_EDGE_TOL - still inside"
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt-eth"]["ref"] == "common/rj45-eth@1"
    assert "led-mgmt-l" not in pl, "the lamp is lifted into the jack's own states"
    assert "states" in pl["mgmt-eth"]


def test_a_lamp_15mm_outside_the_box_is_external(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d9"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(EDGE_TOL_OUTSIDE_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "external-lamps 1" in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt-eth"]["ref"] == "std/rj45@2"
    assert "led-mgmt-l" in pl, "beyond LAMP_EDGE_TOL - stays a separate placement, not lifted"
    assert "states" not in pl["mgmt-eth"]


# --- Fix round 4: orientation (a jack off a keyway-up part turns over) ----
#
# Controller ruling: all four NEW parts are pins-up, keyway-down when
# unrotated. common/rj45-port@4 and common/rj45-jack@2 (FLIP_ORIGIN) are the
# other way up, so a placement moved off either one needs its `rotate`
# flipped 180 to keep drawing the same, already-verified face.
FLIP_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d10
version: 1.0.0
manufacturer: Acme
model: D10
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
views:
  front:
    size: {w: 100, h: 40}
    components:
      placements:
        - {id: mgmt, ref: common/rj45-port@4, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
""")

FLIP_FIXTURE_ROTATED = FLIP_FIXTURE.replace(
    "{id: mgmt, ref: common/rj45-port@4, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}",
    "{id: mgmt, ref: common/rj45-port@4, at: [10.0, 10.0], rotate: 180, group: mgmt, rel-pos: 1, attrs: {role: mgmt}}",
)
assert FLIP_FIXTURE_ROTATED != FLIP_FIXTURE, "fixture edit must actually take"

# A jack already keyway-down (common/rj45-bezel@2 is not in FLIP_ORIGIN) must
# not have its rotate touched, and no flip reported - same size (17.0x14.9)
# as common/rj45-port@4, so the `at` does not move either, isolating the
# rotate behaviour under test.
NO_FLIP_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d11
version: 1.0.0
manufacturer: Acme
model: D11
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
views:
  front:
    size: {w: 100, h: 40}
    components:
      placements:
        - {id: console, ref: common/rj45-bezel@2, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: console}}
""")

# Handedness must key off the FINAL rotate: this jack has no rotate of its
# own, so before the flip it would present led-a/led-b unswapped, but the
# flip to 180 means the lower-x lamp (link) actually lands on screen-right.
HANDEDNESS_FLIP_FIXTURE = textwrap.dedent("""\
format: 1
kind: device
name: d12
version: 1.0.0
manufacturer: Acme
model: D12
chassis: {width: 100, height: 40, depth: 30}
groups:
  mgmt: {term: Port}
  mgmt-leds: {term: LED}
views:
  front:
    size: {w: 100, h: 40}
    components:
      placements:
        - {id: mgmt, ref: common/rj45-port@4, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}
        - {id: led-l, ref: common/led-dot@1, at: [11.2, 21.73], group: mgmt-leds, rel-pos: 1, for: mgmt, attrs: {function: link}}
        - {id: led-r, ref: common/led-dot@1, at: [22.8, 21.73], group: mgmt-leds, rel-pos: 2, for: mgmt, attrs: {function: activity}}
""")


def test_a_jack_off_rj45_port_4_gains_rotate_180(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d10"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(FLIP_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotation flipped 1" in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt"]["ref"] == "common/rj45-eth@1"
    assert pl["mgmt"]["rotate"] == 180


def test_a_jack_off_rj45_port_4_already_rotated_180_loses_the_rotate_key(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d10"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(FLIP_FIXTURE_ROTATED)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotation flipped 1" in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt"]["ref"] == "common/rj45-eth@1"
    assert "rotate" not in pl["mgmt"]


def test_a_jack_already_keyway_down_is_not_flipped(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d11"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(NO_FLIP_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotation flipped" not in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["console"]["ref"] == "std/rj45@2"
    assert "rotate" not in pl["console"]


def test_handedness_uses_the_final_rotate_after_the_flip(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d12"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(HANDEDNESS_FLIP_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt"]["rotate"] == 180
    # led-l (lower x, 11.2, function: link) is the LEFT lamp. Final rotate is
    # 180 (flipped from absent/0), so it presents on screen-right: led-b.
    assert pl["mgmt"]["states"]["led-b"] == ["off", {"name": "link"}]


# --- Fix round 5: a lifted lamp's description rides with it -------------

# Both lamps carry a description; led-mgmt-l's has an embedded apostrophe to
# exercise '' doubling.
DESC_FIXTURE = FIXTURE.replace(
    "           states: ['off', {name: link-1g, color: '#22c55e'}]}",
    "           states: ['off', {name: link-1g, color: '#22c55e'}],\n"
    "           description: 'per the QSG''s table 3'}",
).replace(
    "        - {id: led-mgmt-r, ref: common/led-dot@1, at: [22.8, 21.73], group: mgmt-leds, rel-pos: 2, for: mgmt-eth, attrs: {function: activity}}",
    "        - {id: led-mgmt-r, ref: common/led-dot@1, at: [22.8, 21.73], group: mgmt-leds, rel-pos: 2, for: mgmt-eth, attrs: {function: activity},\n"
    "           description: 'right lamp, HIG table 4'}",
)
assert DESC_FIXTURE != FIXTURE

# Same, but the jack already carries its own description to append after.
DESC_FIXTURE_EXISTING = DESC_FIXTURE.replace(
    "        - {id: mgmt-eth, ref: std/rj45@1, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}}",
    "        - {id: mgmt-eth, ref: std/rj45@1, at: [10.0, 10.0], group: mgmt, rel-pos: 1, attrs: {role: mgmt}, description: 'OOB jack'}",
)
assert DESC_FIXTURE_EXISTING != DESC_FIXTURE


def test_the_sweep_carries_lifted_descriptions_onto_the_jack(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d13"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(DESC_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "descriptions carried 2" in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt-eth"]["description"] == (
        "led-mgmt-l: per the QSG's table 3; led-mgmt-r: right lamp, HIG table 4"
    )


def test_the_sweep_appends_a_carried_description_after_an_existing_one(tmp_path, sweep_lib):
    d = tmp_path / "devices/acme/d14"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(DESC_FIXTURE_EXISTING)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(sweep_lib), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt-eth"]["description"].startswith(
        "OOB jack; led-mgmt-l: per the QSG's table 3; led-mgmt-r: "
    )


def test_the_sweep_adds_no_description_when_lamps_have_none(tmp_path, sweep_lib):
    out, text = sweep(tmp_path, sweep_lib, "--apply")
    assert "descriptions carried" not in out
    d = yaml.safe_load(text)
    pl = {p["id"]: p for p in d["views"]["front"]["components"]["placements"]}
    assert "description" not in pl["mgmt-eth"]


# The exporter dropped all four swept RJ45 refs (#Fix B): a Juniper 40GE
# MIC/DPC module with a lamped Ethernet jack and a bare console jack lost
# every one of those ports on export.
def test_build_module_exports_the_swept_rj45_family_refs():
    contract = {
        "kind": "module", "name": "m", "attrs": {"model": "m"},
        "parts": [
            {"id": "port-0-0", "ref": "common/rj45-ganged-eth@1", "attrs": {"media": "rj45"}},
            {"id": "console", "ref": "std/rj45@2"},
        ],
    }
    out = dx.build_module(contract, "Juniper")
    assert out["interfaces"] == [{"name": "port-0-0", "type": "1000base-t"}]
    assert out["console-ports"] == [{"name": "console", "type": "rj-45"}]


# Fix round: PART_CONSOLE briefly gained a version-less "std/rj45": "rj-45"
# entry, which caught every unswept std/rj45@1 too - turning nine real
# Juniper RE module types' Ethernet management jacks into exported console
# ports (RE-MX-104, RE-S-2000-4096, JNP10K-RE1, the MX2000 RCBs, and more).
# The family must be recognised by the FULL ref (with @major), so an
# unswept @1 keeps exactly its pre-family behaviour: dropped from export.
def test_build_module_leaves_unswept_rj45_at_1_exactly_as_before():
    contract = {
        "kind": "module", "name": "m", "attrs": {"model": "m"},
        "parts": [
            {"id": "ethernet", "ref": "std/rj45@1",
             "attrs": {"function": "out-of-band management"}},
        ],
    }
    out = dx.build_module(contract, "Juniper")
    assert "interfaces" not in out
    assert "console-ports" not in out


# The ganged sibling's console behaviour was never version-gated (it was
# already in PART_CONSOLE version-less before this family existed), so its
# @1 - not yet swept to @2 - keeps exporting as a console port, unchanged.
def test_build_module_keeps_unswept_rj45_ganged_at_1_as_console():
    contract = {
        "kind": "module", "name": "m", "attrs": {"model": "m"},
        "parts": [{"id": "console", "ref": "std/rj45-ganged@1"}],
    }
    out = dx.build_module(contract, "Juniper")
    assert out["console-ports"] == [{"name": "console", "type": "rj-45"}]
    assert "interfaces" not in out


RETIRED = ["common/rj45-hd@1", "common/rj45-hd-plain@1", "common/rj45-port@4", "common/rj45-bezel@2",
           "common/rj45-shielded@1", "common/rj45-shielded@2", "common/rj45-jack@2", "std/rj45@1", "std/rj45-ganged@1"]


def test_the_retired_rj45_parts_are_gone_and_unreferenced():
    """Gone from the library, and gone from every `ref:` - a device or component
    that still composed one would fail to build. Provenance prose is free to go
    on naming a retired part for history (the design doc and several surviving
    contracts do), so the search is for `ref:` lines, not any mention."""
    for ref in RETIRED:
        nsname, major = ref.rsplit("@", 1)
        assert not (LIB / "components" / nsname / f"v{major}").exists(), ref
    pattern = r"ref:\s*(" + "|".join(re.escape(r) for r in RETIRED) + r")\b"
    hits = subprocess.run(["grep", "-rlnE", pattern, str(LIB / "devices"), str(LIB / "components")],
                          capture_output=True, text=True).stdout.split()
    assert hits == [], hits


def test_no_lamp_placement_still_declares_for_a_lamped_rj45():
    """Checks `for:` declarations, not geometry: a lamped jack (common/rj45-eth@1,
    common/rj45-ganged-eth@1) already draws its own led-a/led-b, so a separate
    LED placement `for:` that same id would be a duplicate lamp - the case the
    retired L39 exemption used to excuse. A lamp `for:` a BARE jack (std/rj45@2,
    std/rj45-ganged@2) is the different, settled pattern nine devices use across
    four vendors - two discrete LEDs beside a jack that itself has none - and is
    not this."""
    LAMPED = {"common/rj45-eth@1", "common/rj45-ganged-eth@1"}
    for f in libwalk.iter_devices([LIB]):
        d = yaml.safe_load(f.read_text())
        for v in (d.get("views") or {}).values():
            pl = ((v or {}).get("components") or {}).get("placements") or []
            lamped = {p["id"] for p in pl if p.get("ref") in LAMPED}
            for p in pl:
                fr = p.get("for"); fr = fr if isinstance(fr, list) else [fr]
                assert not ("led" in p.get("ref", "") and any(x in lamped for x in fr)), f"{f}: {p['id']}"


# I1: #125 gave std/rj45@2 seven jobs, so the ref stopped being able to carry
# the DCIM type and seven Juniper timing jacks exported as CONSOLE PORTS. The
# placement's own words decide first now.
def test_a_timing_jack_exports_as_an_other_interface_not_a_console():
    contract = {
        "kind": "module", "name": "m", "attrs": {"model": "m"},
        "parts": [
            {"id": "tod", "ref": "std/rj45@2", "attrs": {"role": "timing"}},
            {"id": "bits", "ref": "std/rj45@2", "attrs": {"role": "timing"}},
            {"id": "con", "ref": "std/rj45@2"},
        ],
    }
    out = dx.build_module(contract, "Juniper")
    assert out["console-ports"] == [{"name": "con", "type": "rj-45"}]
    # BY NAME SINCE #267, not in the order the parts are listed. That order is
    # the order the jacks sit across the face, and half these cards are drawn
    # twice - once horizontally, once rotated - so it handed the DCIM whichever
    # drawing's x-order happened to be written last. What this test is about is
    # the TYPE and the LABEL, which is what #125 broke.
    assert out["interfaces"] == [{"name": "bits", "type": "other", "label": "BITS"},
                                 {"name": "tod", "type": "other", "label": "TOD"}]


def test_jnp10003_rcb_exports_no_console_named_bits_or_tod():
    c = yaml.safe_load((LIB / "components/juniper/jnp10003-rcb/v1/contract.yaml").read_text())
    out = dx.build_module(c, "Juniper")
    names = {p["name"] for p in out.get("console-ports") or []}
    assert "bits" not in names and "tod" not in names
    ifaces = {i["name"]: i for i in out["interfaces"]}
    assert ifaces["tod"] == {"name": "tod", "type": "other", "label": "TOD"}
    assert ifaces["bits"] == {"name": "bits", "type": "other", "label": "BITS"}
    assert names == {"usb", "con"}


# An id like "contact-1" or a group like "topology" must not be read as a
# timing function: the tokens are anchored on whitespace or a hyphen.
@pytest.mark.parametrize("pid", ["contact-1", "syncope", "topology"])
def test_an_unrelated_word_is_not_read_as_a_timing_function(pid):
    assert dx.rj45_timing_label({"id": pid}) is None


@pytest.mark.parametrize("pid,label", [("tod", "TOD"), ("bits-in", "BITS"),
                                       ("gm-ptp", "GM-PTP"), ("ieee-1588", "1588"),
                                       ("ics-0", "ICS"), ("clk-a", "CLK"),
                                       ("pps-in", "PPS"), ("sync-0", "SYNC")])
def test_the_timing_tokens_each_label_themselves(pid, label):
    assert dx.rj45_timing_label({"id": pid}) == label
