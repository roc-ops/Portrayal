"""dc_inventory.py: which DC ends the library has, and whether a cable lands on them (P-0046).

TWO KINDS OF TEST, and the split is the point. The logic of the tool is shown on
a small library made in tmp_path, whose every part is there to plant one case:
a terminal drawn as skin art, a terminal that is a slot, a supply that composes
one, an AC supply that must NOT be listed, a polarity that is stated in a field,
in a sentence, and nowhere. Those pass whatever the real library becomes.

The real library is held to INVARIANTS and to the four parts the order named,
listed and never pinned to "not a cable end": the fix that follows this note
turns those into cable ends, and a test that said they are not would then have
to be rewritten by the change it should be watching. What stays true is that they
are in the inventory, that an answer of `yes` names a registered interface and a
plug, and that every counted total is the sum of its rows.
"""
import json
import textwrap

import pytest
import yaml

from portrayal_dev import dc_inventory as D


def put(root, path, text):
    f = root / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(textwrap.dedent(text))


def comp(root, ref, body):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    put(root, f"components/{ns}/{name}/v{major}/contract.yaml", "format: 1\nkind: component\nname: %s\n%s" % (name, textwrap.dedent(body)))


@pytest.fixture()
def lib(tmp_path):
    root = tmp_path / "lib"
    # a lug that IS a cable end: a class port part that mates terminal-stud
    comp(root, "generic/lug@1", """\
        class: port
        mates: terminal-stud
        """)
    # a terminal drawn as art: two elements, no interface, polarity in the element ids
    comp(root, "t/art-block@1", """\
        class: inlet
        description: Two-pole terminal block.
        attrs: {inlet: dc-terminal}
        elements:
          terminal-rtn: {class: inlet, description: '+Return, the positive terminal'}
          terminal-48v: {class: inlet, description: '-48 Vdc, the negative terminal'}
        provenance: {terminals: 'Two terminals.'}
        """)
    # a terminal that is a slot: presents a registered interface a port part mates
    comp(root, "t/stud@1", """\
        class: screw
        interface: terminal-stud
        """)
    comp(root, "t/slot-block@1", """\
        class: inlet
        attrs: {inlet: dc-terminal}
        parts:
          - {ref: t/stud@1, id: lug-1}
          - {ref: t/stud@1, id: lug-2}
        """)
    # a supply that only composes the slot block
    comp(root, "t/psu-x@1", """\
        class: psu
        parts:
          - {ref: t/slot-block@1, id: terminal}
        """)
    # an AC supply: not listed
    comp(root, "t/psu-ac@1", """\
        class: psu
        description: A supply whose DC OK lamp is green.
        attrs: {input: ac, inlet: c14}
        elements:
          led-dc-ok: {class: led}
        """)
    # polarity only in a sentence
    comp(root, "t/prose@1", """\
        class: inlet
        attrs: {inlet: dc-terminal}
        provenance:
          terminals: 'The feed lands on a terminal marked -48 V and one marked RTN.'
        """)
    # polarity nowhere
    comp(root, "t/silent@1", """\
        class: inlet
        attrs: {inlet: dc-terminal}
        """)
    # a device that places the art block and the slot block, one with a DC feed and no part
    put(root, "devices/v/box/device.yaml", """\
        kind: device
        chassis: {power: dc}
        views:
          rear:
            components:
              placements:
                - {ref: t/art-block@1, id: in-a}
                - {ref: t/art-block@1, id: in-b}
                - {ref: t/slot-block@1, id: in-c}
        """)
    put(root, "devices/v/bare/device.yaml", """\
        kind: device
        chassis: {power: dc}
        gaps:
          - {what: dc-terminals, note: 'The DC feed terminals are decor, not a part.'}
        views: {rear: {components: {placements: []}}}
        """)
    put(root, "devices/v/acbox/device.yaml", """\
        kind: device
        chassis: {power: ac}
        views:
          rear:
            components:
              bays:
                - {id: psu-0, accepts: ['t/psu-ac@1'], default: 't/psu-ac@1'}
        """)
    return root


@pytest.fixture()
def inv(lib):
    return D.inventory(lib)


def part(inv, ref):
    return next((p for p in inv["parts"] if p["ref"] == ref), None)


@pytest.mark.heavy
def test_a_terminal_drawn_as_art_is_listed_and_is_not_a_cable_end(inv):
    p = part(inv, "t/art-block@1")
    assert p and p["cable_end"] == "no" and "presents no interface" in p["why_not"]
    assert p["drawing"]["elements"] == ["terminal-rtn", "terminal-48v"]


@pytest.mark.heavy
def test_a_registered_interface_a_port_part_mates_is_a_cable_end(inv):
    p = part(inv, "t/stud@1")
    assert p["cable_end"] == "yes" and p["interface"] == "terminal-stud" and p["plugs"] == ["generic/lug@1"]


@pytest.mark.heavy
def test_a_part_that_composes_a_slot_lands_by_it_and_a_supply_by_the_part(inv):
    block, psu = part(inv, "t/slot-block@1"), part(inv, "t/psu-x@1")
    assert block["cable_end"] == "via-parts" and [v["path"] for v in block["via"]] == ["/lug-1", "/lug-2"]
    assert psu["cable_end"] == "via-parts" and [v["path"] for v in psu["via"]] == ["/terminal/lug-1", "/terminal/lug-2"]
    assert psu["signals"] == ["part:terminal"]       # found only by what it composes, on the second pass


@pytest.mark.heavy
def test_the_lug_is_a_cable_end_part_and_not_a_dc_end(inv):
    assert part(inv, "generic/lug@1") is None
    assert [e["ref"] for e in inv["cable_end_parts"]] == ["generic/lug@1"]


@pytest.mark.heavy
def test_an_ac_supply_is_not_listed_even_with_a_dc_ok_lamp(inv):
    assert part(inv, "t/psu-ac@1") is None


@pytest.mark.heavy
def test_polarity_is_what_a_source_states_and_where(inv):
    structured = part(inv, "t/art-block@1")["polarity"]
    assert structured["via"] == "structured" and set(structured["conductors"]) >= {"RTN", "-48V"}
    assert any("element id `terminal-rtn`" in e for e in structured["evidence"])
    prose = part(inv, "t/prose@1")["polarity"]
    assert prose["via"] == "prose" and set(prose["conductors"]) == {"-48V", "RTN"}
    silent = part(inv, "t/silent@1")["polarity"]
    assert silent == {"conductors": [], "via": "none stated", "evidence": []}


@pytest.mark.heavy
def test_a_device_counts_its_placements_and_says_whether_any_part_lands(inv):
    by = {d["device"]: d for d in inv["devices"]}
    assert by["v/box"]["placements"] == {"t/art-block@1": 2, "t/slot-block@1": 1}
    assert by["v/box"]["lands"] == "yes"
    assert part(inv, "t/art-block@1")["placements"] == 2 and part(inv, "t/art-block@1")["devices"] == 1


@pytest.mark.heavy
def test_a_dc_device_with_no_dc_part_is_named_with_its_own_note(inv):
    by = {d["device"]: d for d in inv["devices"]}
    assert by["v/bare"]["lands"] == "no part" and "decor" in by["v/bare"]["note"]
    assert "v/acbox" not in by


@pytest.mark.heavy
def test_the_counts_add_up_and_the_report_says_them(inv):
    c = D.counts(inv)
    for key in ("by_kind", "by_vendor", "by_role", "by_cable_end", "by_polarity"):
        assert sum(c[key].values()) == c["parts"], key
    md = D.render_md(inv)
    assert f"**{c['parts']} component contracts carry a DC end" in md
    assert "`t/art-block@1`" in md and "none stated" in md


@pytest.mark.heavy
def test_main_writes_the_report_and_the_json(lib, tmp_path, capsys):
    out, js = tmp_path / "inv.md", tmp_path / "inv.json"
    assert D.main(["--library", str(lib), "--out", str(out), "--json", str(js)]) == 0
    assert out.read_text().startswith("# DC power in the library")
    doc = json.loads(js.read_text())
    assert doc["counts"]["parts"] == len(doc["parts"]) == 6


# ── the real library ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def real():
    return D.inventory(D.ROOT / "library")


@pytest.mark.heavy
def test_the_parts_that_showed_the_problem_are_in_the_inventory(real):
    refs = {p["ref"] for p in real["parts"]}
    for ref in ("supermicro/psu-pws-601s-1r@1", "nokia/lpwr-f@1", "amphenol-ns/output-terminal@1",
                "ufispace/psu-132-dc@1", "common/dc-terminal-24@1", "amphenol-ns/output-p40@1",
                "common/terminal-header-508-5f@2", "common/dc-barrel@1"):
        assert ref in refs, ref
    assert "ufispace/s9701-82dc" in {d["device"] for d in real["devices"]}


@pytest.mark.heavy
def test_a_yes_names_a_registered_interface_and_a_plug(real):
    reg = yaml.safe_load((D.ROOT / "spec/schemas/connectors.yaml").read_text())["interfaces"]
    for p in real["parts"]:
        if p["cable_end"] == "yes":
            assert p["interface"] in reg and p["plugs"], p["ref"]
        if p["cable_end"] == "via-parts":
            assert p["via"], p["ref"]
        if p["cable_end"] == "no":
            assert p["why_not"], p["ref"]


@pytest.mark.heavy
def test_every_stated_polarity_has_evidence_and_no_ground_is_listed_as_a_dc_end(real):
    for p in real["parts"]:
        pol = p["polarity"]
        assert bool(pol["conductors"]) == bool(pol["evidence"]) == (pol["via"] != "none stated"), p["ref"]
        assert p["class"] != "ground", p["ref"]


@pytest.mark.heavy
def test_the_real_counts_add_up(real):
    c = D.counts(real)
    assert c["parts"] > 50 and c["devices_with_dc"] > 100
    for key in ("by_kind", "by_vendor", "by_role", "by_cable_end", "by_polarity"):
        assert sum(c[key].values()) == c["parts"], key
    assert sum(c["devices_by_vendor"].values()) == sum(c["devices_by_lands"].values()) == c["devices_with_dc"]
