"""The RJ45 family: two bare jacks, two lamped ones (docs/rj45-family-design.md).

Every figure here is from TE customer drawing 1734264 rev A2 unless a test says
otherwise. The drawings are under working/intake/standards/rj45/ and are not
committed; the numbers are.
"""
import pathlib
import re
import subprocess
import sys
import textwrap

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))
import lint  # noqa: E402

STANDARDS = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]

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
        assert tiers[2]["w"] == SLOT_W and "h" not in tiers[2], "the slot runs to the edge; no height is sourced"


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
    lint.ERRORS.clear(); lint.WARNINGS.clear()
    if not lint.STANDARDS:
        lint.STANDARDS.update(STANDARDS)
    data = lint.lint_component(p, jsonschema.Draft202012Validator(schema))
    lint._skin_checks(p, data)        # L3 (every element id in the skin) and L4 (viewBox = size)
    assert not [e for e in lint.ERRORS if "[L9]" in e or "[L1]" in e or "[L3]" in e or "[L4]" in e], lint.ERRORS


def test_std_rj45_ganged_v2_is_the_cell():
    c = contract("std/rj45-ganged@2")
    assert c["size"] == {"w": 12.7, "h": 11.0, "d": 18.6}
    assert c["conforms"] == "rj45-ganged" and c["interface"] == "rj45"
    assert c["relief"]["size"] == {"w": 11.91, "h": 10.5}
    assert c["connection-points"]["mate"] == {"at": [6.35, 5.1], "direction": "front"}
    widths = tier_widths(cavity_path("std/rj45-ganged@2"))
    assert 11.91 in widths and 4.06 in widths and 2.805 in widths and 1.12 in widths, widths


def test_the_v1_jacks_no_longer_claim_the_standard():
    """They keep drawing until the sweeps retire them, but they were the 16 x 14
    aperture and must not assert conformance to a housing they are not."""
    assert "conforms" not in contract("std/rj45@1")
    assert "conforms" not in contract("std/rj45-ganged@1")


def test_common_rj45_eth_composes_the_housing_and_adds_two_lamps():
    c = contract("common/rj45-eth@1")
    assert c["size"] == {"w": 15.8, "h": 13.2, "d": 18.6}
    assert c["parts"] == [{"ref": "std/rj45@2", "id": "jack", "at": [0.0, 0.0], "behind": True}]
    assert c["elements"]["led-a"]["at"] == [1.2, 11.83] and c["elements"]["led-a"]["size"] == [2.0, 1.1]
    assert c["elements"]["led-b"]["at"] == [12.6, 11.83]
    for el in ("led-a", "led-b"):
        assert c["elements"][el]["class"] == "led"
        assert c["elements"][el]["states"] == ["off", "link", "activity"], "names only, no colours asserted"
    assert c["connection-points"]["net"] == {"at": [7.9, 6.6], "direction": "front"}
    assert "conforms" not in c, "the wrapper composes the standard; it does not restate it"


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
    for el in ("led-a", "led-b"):
        assert c["elements"][el]["states"] == ["off", "link", "activity"]
    assert c["connection-points"]["net"] == {"at": [6.35, 5.1], "direction": "front"}
    s = skin("common/rj45-ganged-eth@1")
    assert 'fill-rule="evenodd"' in s and 'id="led-b"' in s


def test_the_dell_carrier_attaches_ism_meanings_to_the_new_lamps():
    c = contract("dell/rj45-port-14g@1")
    assert c["version"] == "1.1.0"
    part = c["parts"][0]
    assert part["ref"] == "common/rj45-eth@1"
    assert set(part["states"]) == {"led-a", "led-b"}, "the carrier names the new part's lamps"
    names = [s if isinstance(s, str) else s["name"] for s in part["states"]["led-a"]]
    assert "off" in names and len(names) >= 3, "ISM table 11's LINK vocabulary survives"


def test_the_base_stylesheet_renders_the_link_state():
    """`link` is a bare token in common/rj45-eth@1 and common/rj45-ganged-eth@1,
    so it takes its presentation from the renderer's base stylesheet, as `up`
    and `activity` already do. Without a rule the lamp declares a state nothing
    paints, which test_state_css catches on a build - this catches it on the
    source."""
    import render
    assert ".state-link" in render.STATE_CSS
    assert ".state-up" in render.STATE_CSS


def _dev(placements, groups=None):
    return {"kind": "device", "name": "d", "version": "1.0.0",
            "chassis": {"width": 100, "height": 40, "depth": 30},
            "groups": groups or {"mgmt": {"term": "Port"}, "console": {"term": "Port"}},
            "views": {"front": {"size": {"w": 100, "h": 40},
                                "components": {"placements": placements}}}}


def l76(data):
    lint.WARNINGS.clear()
    lint.lint_device_rj45_lamps(pathlib.Path("d/device.yaml"), data, [str(LIB)])
    return [w for w in lint.WARNINGS if "[L76]" in w]


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


SWEEP = ROOT / "spec/tools/portrayal/sweep_rj45.py"

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


def sweep(tmp_path, *args):
    d = tmp_path / "devices/acme/d"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(FIXTURE)
    # the tool resolves component classes through --library; give it the real library
    # for components and the tmp tree for devices
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), *args],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout, (d / "device.yaml").read_text()


def test_the_sweep_reports_and_changes_nothing_without_apply(tmp_path):
    out, text = sweep(tmp_path)
    assert "mgmt-eth" in out and "console" in out
    assert text == FIXTURE


def test_the_sweep_moves_by_role_and_holds_the_centre(tmp_path):
    _, text = sweep(tmp_path, "--apply")
    d = yaml.safe_load(text)
    pl = {p["id"]: p for p in d["views"]["front"]["components"]["placements"]}
    assert pl["mgmt-eth"]["ref"] == "common/rj45-eth@1"
    assert pl["mgmt-eth"]["at"] == [10.1, 10.4]          # (16-15.8)/2, (14-13.2)/2
    assert pl["console"]["ref"] == "std/rj45@2"
    assert pl["console"]["at"] == [40.1, 10.4]


def test_the_sweep_lifts_the_lamps_into_the_jack(tmp_path):
    _, text = sweep(tmp_path, "--apply")
    d = yaml.safe_load(text)
    pl = {p["id"]: p for p in d["views"]["front"]["components"]["placements"]}
    assert "led-mgmt-l" not in pl and "led-mgmt-r" not in pl
    assert pl["mgmt-eth"]["states"]["led-a"] == ["off", {"name": "link-1g", "color": "#22c55e"}]
    assert pl["mgmt-eth"]["states"]["led-b"] == ["off", {"name": "activity"}]
    legends = [s["for"] for s in d["views"]["front"]["silkscreen"]]
    assert legends == ["mgmt-eth", "mgmt-eth"]


def test_the_sweep_resizes_the_cutouts_and_bumps_major(tmp_path):
    _, text = sweep(tmp_path, "--apply")
    d = yaml.safe_load(text)
    cuts = {c["id"]: c for c in d["views"]["front"]["panel"]["cutouts"]}
    assert cuts["mgmt-eth"]["size"] == [15.8, 13.2] and cuts["mgmt-eth"]["at"] == [10.1, 10.4]
    assert d["version"] == "2.0.0", "two ids were removed"
    # and the prose survived: textual edit, not a dump
    assert "text: MGMT" in text


def test_the_sweep_is_minor_when_no_id_is_removed(tmp_path):
    # strip both lamp placements (led-mgmt-l's spans two lines) and the
    # silkscreen entry that names one of them, leaving valid YAML with no
    # lamp id anywhere for the sweep to remove
    lone = re.sub(r"      - \{at: \[12, 32\].*?for: led-mgmt-l\}\n", "", FIXTURE)
    lone = re.sub(r"        - \{id: led-mgmt-l.*?\n.*?\n", "", lone)
    lone = re.sub(r"        - \{id: led-mgmt-r.*?\n", "", lone)
    d = tmp_path / "devices/acme/d"; d.mkdir(parents=True); (d / "device.yaml").write_text(lone)
    subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"], check=True)
    assert yaml.safe_load((d / "device.yaml").read_text())["version"] == "1.3.0"
