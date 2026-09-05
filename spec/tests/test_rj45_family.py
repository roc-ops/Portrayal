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
    assert c["version"] == "1.2.0"
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


def test_the_sweep_holds_the_cutouts_own_centre_not_the_parts(tmp_path):
    d = tmp_path / "devices/acme/d2"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(CUTOUT_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
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
def test_the_sweep_skips_retired_rj45_wrapper_contracts(tmp_path):
    lib = tmp_path / "lib"
    for rel in ("components/common/rj45-hd-plain", "components/std/rj45-ganged"):
        shutil.copytree(LIB / rel, lib / rel)
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


def test_the_sweep_scopes_ids_to_their_own_view(tmp_path):
    d = tmp_path / "devices/acme/d3"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(SCOPING_FIXTURE)
    subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"], check=True)
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


def test_the_sweep_dedupes_and_respects_legend_boundaries(tmp_path):
    d = tmp_path / "devices/acme/d4"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(LEGEND_FIXTURE)
    subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"], check=True)
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


def test_the_sweep_flips_handedness_for_a_rotated_jack(tmp_path):
    d = tmp_path / "devices/acme/d"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(ROTATED_FIXTURE)
    subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"], check=True)
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


def test_the_sweep_leaves_a_jack_bare_when_its_lamps_are_external(tmp_path):
    d = tmp_path / "devices/acme/d6"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(EXTERNAL_LAMPS_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
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


def test_the_sweep_rederives_a_derived_cutout(tmp_path):
    d = tmp_path / "devices/acme/d7"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(DERIVED_CUTOUT_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
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


def test_the_sweep_drops_a_skin_the_new_part_lacks(tmp_path):
    d = tmp_path / "devices/acme/d8"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(SKIN_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
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
def test_the_sweep_reports_an_emptied_group(tmp_path):
    out, _ = sweep(tmp_path, "--apply")
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


def test_the_sweep_does_not_report_a_group_that_keeps_a_member(tmp_path):
    d = tmp_path / "devices/acme/d"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(KEPT_GROUP_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
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


def test_a_lamp_08mm_outside_the_box_is_lifted(tmp_path):
    d = tmp_path / "devices/acme/d9"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(EDGE_TOL_INSIDE_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "external-lamps" not in r.stdout, "0.8mm outside the old footprint is within LAMP_EDGE_TOL - still inside"
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt-eth"]["ref"] == "common/rj45-eth@1"
    assert "led-mgmt-l" not in pl, "the lamp is lifted into the jack's own states"
    assert "states" in pl["mgmt-eth"]


def test_a_lamp_15mm_outside_the_box_is_external(tmp_path):
    d = tmp_path / "devices/acme/d9"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(EDGE_TOL_OUTSIDE_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
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


def test_a_jack_off_rj45_port_4_gains_rotate_180(tmp_path):
    d = tmp_path / "devices/acme/d10"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(FLIP_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotation flipped 1" in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt"]["ref"] == "common/rj45-eth@1"
    assert pl["mgmt"]["rotate"] == 180


def test_a_jack_off_rj45_port_4_already_rotated_180_loses_the_rotate_key(tmp_path):
    d = tmp_path / "devices/acme/d10"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(FLIP_FIXTURE_ROTATED)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotation flipped 1" in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt"]["ref"] == "common/rj45-eth@1"
    assert "rotate" not in pl["mgmt"]


def test_a_jack_already_keyway_down_is_not_flipped(tmp_path):
    d = tmp_path / "devices/acme/d11"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(NO_FLIP_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rotation flipped" not in r.stdout
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["console"]["ref"] == "std/rj45@2"
    assert "rotate" not in pl["console"]


def test_handedness_uses_the_final_rotate_after_the_flip(tmp_path):
    d = tmp_path / "devices/acme/d12"; d.mkdir(parents=True)
    (d / "device.yaml").write_text(HANDEDNESS_FLIP_FIXTURE)
    r = subprocess.run([sys.executable, str(SWEEP), "--library", str(LIB), "--devices", str(tmp_path / "devices"), "--apply"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    data = yaml.safe_load((d / "device.yaml").read_text())
    pl = {p["id"]: p for p in data["views"]["front"]["components"]["placements"]}
    assert pl["mgmt"]["rotate"] == 180
    # led-l (lower x, 11.2, function: link) is the LEFT lamp. Final rotate is
    # 180 (flipped from absent/0), so it presents on screen-right: led-b.
    assert pl["mgmt"]["states"]["led-b"] == ["off", {"name": "link"}]
    assert pl["mgmt"]["states"]["led-a"] == ["off", {"name": "activity"}]
