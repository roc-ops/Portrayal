"""A card two slots wide seats across two bays (docs/pcie-two-slot-bays-design.md).

The card says how many slots it takes (`slot-width`), the bay which siblings
it can cover (`span`). These hold the build's side of it - the shared
helpers, lint L185 and L186, the drawing, components.json and the DCIM
rows - on synthetic parts first and then on a real riser: the Dell R740xd's
riser 1A, whose slot 1 covers slot 2, the opening with no connector behind
it. The kit's side is spec/tests/js/rack-two-slot.mjs.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal import dcim_export, lint
from portrayal.manifest import load_yaml, slot_width, span_box, span_clashes, span_covers

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
RENDER = ROOT / "spec/tools/portrayal/render.py"
RISER = LIB / "components/dell/riser-1a-14g/v2/contract.yaml"
BRACKET = "std/pcie-bracket-fh-2slot@1"

NIC, GPU, FILL = "acme/nic@1", "acme/gpu@1", "acme/filler@1"
PARTS = {NIC: {"size": {"w": 120.02, "h": 21.59}},
         GPU: {"size": {"w": 120.02, "h": 41.91}, "slot-width": 2},
         FILL: {"size": {"w": 120.02, "h": 21.59}}}


def slot(i, accepts=(NIC, GPU, FILL), span=True, **extra):
    b = {"at": [0, round(20.32 * (i - 1), 2)], "size": [120.02, 21.59],
         "accepts": list(accepts), "default": FILL, **extra}
    if span:
        b["span"] = [f"s{i + 1}"]
    return b


def riser(n=3):
    """n slots on the CEM pitch; each spans the next, and the last spans nothing
    and takes no two-slot card."""
    bays = {f"s{i}": slot(i) for i in range(1, n)}
    bays[f"s{n}"] = slot(n, accepts=(NIC, FILL), span=False)
    return {"kind": "module", "name": "riser", "bays": bays}


def run_rule(fn, data, parts=PARTS):
    """(rule, message) for every finding `fn` makes on `data`, with `parts` as
    the library."""
    got = []
    saved = lint.err, lint.resolve_component, lint.load_yaml
    lint.err = lambda path, rule, msg: got.append((rule, msg))
    lint.resolve_component = lambda ref, roots: ref if ref in parts else None
    lint.load_yaml = lambda ref: parts[ref]
    try:
        fn(Path("x/contract.yaml"), data, [str(LIB)])
    finally:
        lint.err, lint.resolve_component, lint.load_yaml = saved
    return got


# --- the helpers the build, lint and the kit share ---------------------------

def test_a_card_covers_the_first_bays_its_bay_spans():
    bays = riser()["bays"]
    assert slot_width(PARTS[GPU]) == 2 and slot_width(PARTS[NIC]) == 1 and slot_width(None) == 1
    assert span_covers(bays["s1"], 1) == []
    assert span_covers(bays["s1"], 2) == ["s2"]
    assert span_covers(bays["s3"], 2) is None, "the last slot has no bay beside it"
    assert span_box(bays["s2"], bays, ["s3"]) == ([0.0, 20.32], (120.02, 41.91))


def test_two_one_slot_cards_then_a_two_slot_card_refused_by_a_taken_neighbour_and_seated_in_a_free_pair():
    bays = riser(4)["bays"]
    key = lambda b: f"riser-1/{b}"
    res = PARTS.get
    two_nics = {"riser-1/s1": NIC, "riser-1/s2": NIC}
    assert span_clashes(bays, two_nics, key, res) == []
    # a two-slot card in s2 would cover s3, which still holds its filler
    taken = {**two_nics, "riser-1/s2": GPU}
    assert span_clashes(bays, taken, key, res) == [("s2", GPU, "s3", FILL)]
    # s3 emptied: the pair is free, and s4 beside it is untouched
    free = {**taken, "riser-1/s3": ""}
    assert span_clashes(bays, free, key, res) == []
    # and a two-slot card in the last slot, which spans nothing, is no seat at all
    assert span_clashes(bays, {"riser-1/s4": GPU}, key, res) == [("s4", GPU, None, None)]


# --- lint ---------------------------------------------------------------------

def test_l185_is_quiet_on_a_riser_whose_spans_run_down_the_pitch():
    assert run_rule(lint.lint_component_span, riser()) == []


def test_l185_refuses_a_span_into_another_carrier_or_the_wrong_side():
    r = riser()
    r["bays"]["s1"]["span"] = ["slot-9"]
    assert [m for _, m in run_rule(lint.lint_component_span, r)] == [
        "bays/s1: span names 'slot-9', which is not another bay of this component - "
        "a card spans its own carrier's bays only"]
    r = riser()
    r["bays"]["s2"]["span"] = ["s1"]              # above it, at rotate 0
    msgs = [m for _, m in run_rule(lint.lint_component_span, r)]
    assert len(msgs) == 1 and msgs[0].startswith("bays/s2: spans s1, which is not the next bay below s2")
    r = riser()
    r["bays"]["s1"]["span"] = ["s3"]              # skips a bay
    assert any("spans s3, which is not the next bay below s1" in m
               for _, m in run_rule(lint.lint_component_span, r))


def test_l185_a_turned_bay_spans_upward():
    r = riser()
    for b in r["bays"].values():
        b["rotate"] = 180
    r["bays"]["s2"]["span"] = ["s1"]
    r["bays"]["s1"].pop("span")
    r["bays"]["s1"]["accepts"] = [NIC, FILL]
    r["bays"]["s3"]["span"] = ["s2"]
    r["bays"]["s3"]["accepts"] = [NIC, GPU, FILL]
    assert run_rule(lint.lint_component_span, r) == []


def test_l185_a_bay_that_accepts_a_two_slot_card_spans_and_a_composer_is_as_wide():
    r = riser()
    r["bays"]["s3"]["accepts"].append(GPU)
    assert [m for _, m in run_rule(lint.lint_component_span, r)] == [
        f"bays/s3: accepts {GPU}, which is 2 slots wide, and names 0 bay(s) in `span` for it to cover"]
    card = {"kind": "module", "parts": [{"id": "bracket", "ref": GPU}]}
    assert [m for _, m in run_rule(lint.lint_component_span, card)] == [
        f"parts/bracket: composes {GPU}, which is 2 slots wide, and this part says it is 1 - "
        "give it `slot-width: 2`"]
    assert run_rule(lint.lint_component_span, {**card, "slot-width": 2}) == []


def test_l186_a_configuration_seats_a_two_slot_card_only_over_an_empty_bay():
    parts = {**PARTS, "acme/riser@1": riser()}
    dev = {"kind": "device",
           "views": {"rear": {"components": {"bays": [
               {"id": "riser-1", "at": [0, 0], "size": {"w": 130, "h": 70},
                "accepts": ["acme/riser@1"], "default": "acme/riser@1"}]}}},
           "configurations": {
               "full": {"bays": {"riser-1/s1": GPU}},
               "emptied": {"bays": {"riser-1/s1": GPU, "riser-1/s2": ""}}}}
    got = run_rule(lint.lint_device_span_exclusion, dev, parts)
    assert got == [("L186", f"configurations/full/bays: riser-1/s1 holds {GPU}, which covers "
                            f"riser-1/s2, and riser-1/s2 holds {FILL} - empty it (riser-1/s2: \"\")")]


def test_l186_a_carrier_does_not_ship_a_two_slot_default_over_a_shipped_one():
    r = riser()
    r["bays"]["s1"]["default"] = GPU
    assert run_rule(lint.lint_component_span_exclusion, r) == [
        ("L186", f"bays/s1: ships {GPU}, which covers s2, and s2 ships {FILL} - "
                 "a carrier ships one or the other")]


def test_the_rules_are_in_the_catalogue():
    assert {"L185", "L186"} <= set(lint.RULES)


# --- a real riser: the R740xd's riser 1A -------------------------------------

def test_riser_1a_slot_1_spans_slot_2_and_slot_3_spans_nothing():
    bays = load_yaml(RISER)["bays"]
    assert bays["slot-1"]["span"] == ["slot-2"]
    assert BRACKET in bays["slot-1"]["accepts"]
    assert "span" not in bays["slot-3"] and BRACKET not in bays["slot-3"]["accepts"]
    assert span_box(bays["slot-1"], bays, ["slot-2"]) == ([-13.41, -1.35], (120.02, 41.91)), (
        "the pair is one slot pitch plus one bracket across: figure 11-13's 41.91")


def test_the_two_slot_bracket_is_two_slots_wide_and_the_figure_11_13_size():
    c = load_yaml(LIB / "components/std/pcie-bracket-fh-2slot/v1/contract.yaml")
    assert c["slot-width"] == 2
    assert c["size"] == {"w": 120.07, "h": 41.91}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_kit_draws_the_card_in_the_box_the_build_does():
    """render.span_box and swap.js spanBox, on the real riser's bays."""
    bays = load_yaml(RISER)["bays"]
    host = {bid: {"at": b["at"], "size": {"w": b["size"][0], "h": b["size"][1]},
                  **({"span": b["span"]} if b.get("span") else {})} for bid, b in bays.items()}
    script = ("const {withSpan, spanBox} = await import(process.argv[1]);"
              "const host = JSON.parse(process.argv[2]);"
              "const e = withSpan(host['slot-1'], 'riser-1/module/slot-1', host);"
              "console.log(JSON.stringify(spanBox(e, {'slot-width': 2})));")
    p = subprocess.run(["node", "--input-type=module", "-e", script,
                        (ROOT / "kit/swap.js").as_uri(), json.dumps(host)],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    at, (w, h) = span_box(bays["slot-1"], bays, ["slot-2"])
    assert json.loads(p.stdout) == {"at": at, "size": {"w": w, "h": h}}


def _render(tmp_path, cfg_bays):
    """The R740xd with one example configuration holding `cfg_bays` on
    riser 1A, rendered from a tmp copy; (returncode, stderr, the rear SVG)."""
    d_dir = shutil.copytree(LIB / "devices/dell/r740xd", tmp_path / "r740xd")
    f = d_dir / "device.yaml"
    d = yaml.safe_load(f.read_text())
    c = d["configurations"]["sff24-rc4-1a2a3a-two-slot"]
    c["bays"] = {"riser-1": "dell/riser-1a-14g@2", "riser-2": "dell/riser-2a-14g@2",
                 "riser-3": "dell/riser-3a-14g@2", **cfg_bays}
    f.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "out"
    r = warmrender.run([sys.executable, str(RENDER), str(f), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    svg = out / "r740xd.sff24-rc4-1a2a3a-two-slot.rear.svg"
    return r.returncode, r.stderr, svg.read_text() if svg.exists() else ""


def _tag(svg, path):
    at = svg.index(f'data-path="{path}"')
    return svg[svg.rindex("<", 0, at):svg.index(">", at)]


def test_the_build_seats_the_bracket_across_slot_1_and_slot_2(tmp_path):
    rc, err, svg = _render(tmp_path, {"riser-1/slot-1": BRACKET, "riser-1/slot-2": ""})
    assert rc == 0, err[-800:]
    card = _tag(svg, "riser-1/module/slot-1/module")
    assert f'data-ref="{BRACKET}:' in card
    assert 'transform="translate(-13.41,-1.35)"' in card, card
    assert 'data-covered-by="riser-1/module/slot-1"' in _tag(svg, "riser-1/module/slot-2")
    assert "data-covered-by" not in _tag(svg, "riser-1/module/slot-3")
    assert 'data-path="riser-1/module/slot-2/module"' not in svg, "a covered bay holds nothing"
    assert svg.index('data-path="riser-1/module/slot-2"') < svg.index('data-path="riser-1/module/slot-1"'), (
        "the card's bay is drawn after the bay it covers, so the card paints over that opening")


@pytest.mark.parametrize("card", [BRACKET, "nvidia/a100-pcie-80gb@1"])
def test_a_two_slot_card_is_not_drawn_across_the_covered_slots_latch_row(tmp_path, card):
    """The plate's louvre row under slot 1 is slot 2's retention latch. A card
    that covers slot 2 is one bracket, so that row must not be drawn over it;
    the row under slot 2 belongs to slot 3 and stays."""
    rc, err, svg = _render(tmp_path, {"riser-1/slot-1": card, "riser-1/slot-2": ""})
    assert rc == 0, err[-800:]
    assert 'id="riser-1--module--plate--louvres-1"' not in svg
    assert 'id="riser-1--module--plate--louvres-2"' in svg
    assert 'id="riser-2--module--plate--louvres-1"' in svg, "another riser is untouched"


def test_the_latch_row_stays_when_slot_2_is_not_covered(tmp_path):
    rc, err, svg = _render(tmp_path, {"riser-1/slot-1": "std/pcie-bracket-fh@2"})
    assert rc == 0, err[-800:]
    assert 'id="riser-1--module--plate--louvres-1"' in svg


def test_the_build_refuses_the_bracket_over_slot_2s_filler(tmp_path):
    rc, err, _svg = _render(tmp_path, {"riser-1/slot-1": BRACKET})
    assert rc != 0
    assert ("riser-1/slot-1: std/pcie-bracket-fh-2slot@1 is 2 slots wide and covers riser-1/slot-2, "
            "which holds dell/pcie-filler-fh-14g@2") in err, err[-800:]


# --- what the index and the exports say ---------------------------------------

def test_components_json_publishes_the_span_and_the_width():
    f = DIST / "components.json"
    if not f.exists():
        pytest.skip("components.json not built")
    comps = {f"{c['ns']}/{c['name']}@{c['major'][1:]}": c for c in json.loads(f.read_text())["components"]}
    assert comps[BRACKET]["slot-width"] == 2
    assert "slot-width" not in comps["std/pcie-bracket-fh@2"], "one slot says nothing"
    riser = comps["dell/riser-1a-14g@2"]["bays"]
    assert riser["slot-1"]["span"] == ["slot-2"]
    assert "span" not in riser["slot-3"]


def test_a_dcim_bay_row_says_what_it_spans():
    row = dcim_export.bay_row("slot-1", ["dell/pcie-filler-fh-14g@2", BRACKET], ["slot-2"])
    assert row["description"].startswith("Spans slot-2 for a card 2 slots wide. Accepts: pcie-filler-fh-14g")
    assert "description" not in dcim_export.bay_row("slot-3") and \
        dcim_export.bay_row("slot-3", ["a/b@1"])["description"] == "Accepts: b"
