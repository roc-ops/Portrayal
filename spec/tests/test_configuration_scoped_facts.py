"""A configuration says what occupies a bay AND what is true of a part.

roc-ops/Portrayal#193, and `docs/what-a-configuration-cannot-say.md` is the design note it
came from. Two vendors hit the same wall from opposite sides:

  - The Casa C40G ships AC or DC and the two are different machines at the
    bottom of the rear: DC is two power entry modules in openings, AC is ONE
    bolted panel across the same band. The panel was modelled and could not be
    attached.
  - The Cisco ASR 9001-S is the same sheet metal as the 9001 with two of its
    four SFP+ ports and one of its two modular bays disabled until a licence is
    applied. The cages are physically present and identical.

The note costed two schema changes for this. NEITHER WAS NEEDED, and that is the
thing this file is really pinning:

  - PRESENCE was already sayable. `only-in:` scopes a placement or a bay to named
    configurations. An AC chassis has the panel and no PEM openings; a DC one has
    the openings and no panel. They are never both present, so the overlap that
    killed route 2 of the note never arises.
  - PROPERTY needed one lookup. `component-attrs` was keyed by component NAME,
    which says a true thing about every copy of a part and nothing about one of
    them - both chassis draw six `std/sfp-ganged`, so keying by the component
    marks the two CLUSTER ports too. It now takes a placement id as well, and
    `bay-attrs` already took a bay path and had never been used by anything.

Still open, and filed on the device rather than papered over: a DEVICE attr that
changes with the configuration - the 9001-S's 60 Gbps against the 9001's 120.
"""
import pathlib
import re
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
from portrayal import lint
from portrayal import libwalk


def dev(slug):
    return yaml.safe_load((LIB / "devices" / slug / "device.yaml").read_text())


# --- presence: the C40G -------------------------------------------------------

def test_the_panel_and_the_pem_bays_are_scoped_to_opposite_configurations():
    d = dev("casa/c40g")
    rear = d["views"]["rear"]["components"]
    panel = next(p for p in rear["placements"] if p["id"] == "ac-inlet-panel")
    assert panel["only-in"] == ["ac-power"], panel.get("only-in")
    for bid in ("pem-1", "pem-2"):
        bay = next(b for b in rear["bays"] if b["id"] == bid)
        assert "ac-power" not in bay["only-in"], f"{bid} must not exist on an AC chassis"
        assert "dc-power" in bay["only-in"]


@pytest.mark.skipif(not (DIST / "c40g.ac-power.rear.svg").exists(), reason="needs a build")
def test_each_c40g_rear_draws_what_that_chassis_has():
    """END TO END, and the check the issue actually asked for. The AC rear used
    to render as an empty band."""
    ac = (DIST / "c40g.ac-power.rear.svg").read_text()
    dc = (DIST / "c40g.dc-power.rear.svg").read_text()
    assert 'id="ac-inlet-panel"' in ac, "the AC rear must draw its inlet panel"
    assert 'id="ac-inlet-panel"' not in dc, "the DC rear must not"
    assert re.search(r'id="pem-[12]"', dc), "the DC rear must draw its PEM bays"
    assert not re.search(r'id="pem-[12]"', ac), "the AC rear must not"


# --- property: the ASR 9001-S -------------------------------------------------

def test_only_the_two_licence_disabled_ports_are_marked():
    d = dev("cisco/asr-9001")
    ca = d["configurations"]["asr-9001-s"]["component-attrs"]
    assert set(ca) == {"sfp-plus-2", "sfp-plus-3"}, ca
    for v in ca.values():
        assert v["enabled"] == "no" and v["enabled-by"] == "A9K-9001-120G-LIC"
    assert d["configurations"]["asr-9001-s"]["bay-attrs"] == {
        "mpa-1": {"enabled": "no", "enabled-by": "A9K-9001-120G-LIC"}}


def test_the_full_9001_marks_nothing():
    """NON-VACUITY, and the point of per-instance keying: the same six
    `std/sfp-ganged` are on both chassis."""
    assert "component-attrs" not in dev("cisco/asr-9001")["configurations"]["asr-9001"]


@pytest.mark.skipif(not (DIST / "asr-9001.asr-9001-s.front.svg").exists(), reason="needs a build")
def test_the_drawing_disables_two_ports_and_not_six():
    """THE DEFECT THE NOTE RECORDS, checked against pixels. Keying by component
    name would mark all six instances - the two CLUSTER ports included."""
    def disabled(name):
        t = (DIST / name).read_text()
        return sorted(set(re.findall(r'id="([^"]+)"[^>]*data-enabled="no"', t)) |
                      set(re.findall(r'data-enabled="no"[^>]*id="([^"]+)"', t)))
    s = disabled("asr-9001.asr-9001-s.front.svg")
    assert s == ["mpa-1--module", "sfp-plus-2", "sfp-plus-3"], s
    assert disabled("asr-9001.asr-9001.front.svg") == [], "the full 9001 disables nothing"


# --- the rule that keeps a widened key honest ---------------------------------

def run(doc):
    with lint.collecting() as _found:
        lint.lint_device_component_attrs_resolve("d.yaml", doc)
    return [e for e in _found.errors if "[L94]" in e]


def device_with(**cfg):
    return {"views": {"front": {"components": {
                "placements": [{"id": "sfp-plus-0", "ref": "std/sfp-ganged@1"}],
                "bays": [{"id": "mpa-0", "accepts": ["cisco/a9k-mpa-1x40ge@1"]}]}}},
            "configurations": {"c": cfg}}


def test_a_component_name_resolves():
    assert run(device_with(**{"component-attrs": {"sfp-ganged": {"x": "1"}}})) == []


def test_a_placement_id_resolves():
    assert run(device_with(**{"component-attrs": {"sfp-plus-0": {"x": "1"}}})) == []


def test_a_key_that_matches_nothing_is_reported():
    """The cost of widening a key is that more typos look like intent: before
    there was one way to be right, now two, and the same silence when wrong."""
    found = run(device_with(**{"component-attrs": {"sfp-plus-9": {"x": "1"}}}))
    assert len(found) == 1 and "sfp-plus-9" in found[0], found


def test_a_bay_attrs_key_is_checked_too():
    """It had no user in the whole library until #193, so its first key is its
    first chance to be wrong."""
    assert run(device_with(**{"bay-attrs": {"mpa-0": {"x": "1"}}})) == []
    found = run(device_with(**{"bay-attrs": {"mpa-7": {"x": "1"}}}))
    assert len(found) == 1 and "mpa-7" in found[0], found


def test_the_whole_library_passes_it():
    bad = []
    for p in libwalk.iter_devices([LIB]):
        with lint.collecting() as found:
            lint.lint_device_component_attrs_resolve(p, yaml.safe_load(p.read_text()) or {})
        bad += [e for e in found.errors if "[L94]" in e]
    assert not bad, bad[:4]


def test_the_remaining_third_is_filed_and_not_forgotten():
    """A configuration still cannot override a DEVICE attr. That is recorded as a
    gap on the device it bites, not as silence."""
    g = [x for x in dev("cisco/asr-9001")["gaps"] if x["what"] == "config-scoped-device-attrs"]
    assert len(g) == 1, "the open third should be one gap"
    assert "60 Gbps" in g[0]["note"]
