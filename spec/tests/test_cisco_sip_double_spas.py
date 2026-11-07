"""The two double-height ASR 9000 shared port adapters seat in a SIP-700.

Cisco's SIP and SPA Hardware Installation Guide lists SPA-2XCHOC12/DS0 and
SPA-1XCHOC48/DS3 as double-height (Table 10). Its figures draw each plate twice
a single's thickness (Figures 6 and 8), and a SIP-700 with such a plate in each
row of its faceplate (Figure 2); Table 7 and Figure 3 put one in "Bay 3" beside
a single in "Bay 0". The guide numbers the bays Bay 2 (top left), Bay 0 (top
right), Bay 3 (bottom left) and Bay 1 (bottom right). So a double covers one
row: Bay 2 and Bay 0, or Bay 3 and Bay 1.

Each double states `slot-width: 2`. On both SIP-700 types the left bay of each
row (`bay-2`, `bay-3`) lists the doubles and spans the bay beside it (`bay-0`,
`bay-1`), which lint L185 accepts at `rotate: 0`; the right bays list no double,
because no bay lies to their right. The 22 single-width SPAs stay listed in all
four bays.
"""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal import lint
from portrayal.manifest import load_yaml, slot_width, span_box, span_covers

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"

SIPS = ["cisco/a9k-sip-700@2", "cisco/a9k-sip-700-8g@2"]
DOUBLES = ["cisco/spa-1xchoc48-ds3@1", "cisco/spa-2xchoc12-ds0@1"]
CARRYING = {"bay-2": "bay-0", "bay-3": "bay-1"}
COVERED = ["bay-0", "bay-1"]
BAYS = ["bay-0", "bay-1", "bay-2", "bay-3"]


def _path(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return LIB / f"components/{ns}/{name}/v{major}/contract.yaml"


def _contract(ref):
    return load_yaml(_path(ref))


def _singles():
    """Every Cisco SPA contract that is one slot wide."""
    out = []
    for f in sorted((LIB / "components/cisco").glob("spa-*/v1/contract.yaml")):
        ref = f"cisco/{f.parent.parent.name}@1"
        if ref not in DOUBLES:
            out.append(ref)
    return out


def _rule(fn, data, parts):
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


# --- the adapters say how wide they are, and are seated -------------------------

@pytest.mark.parametrize("ref", DOUBLES)
def test_a_double_states_its_width_and_is_seated(ref):
    spa = _contract(ref)
    assert slot_width(spa) == 2
    assert "unplaced" not in spa


@pytest.mark.parametrize("ref", DOUBLES)
def test_a_double_no_longer_says_it_seats_in_a_single_subslot(ref):
    spa = _contract(ref)
    assert "Seats in a SIP-700 SPA subslot" not in spa["description"]


@pytest.mark.parametrize("ref", _singles())
def test_a_single_is_one_slot_wide(ref):
    assert slot_width(_contract(ref)) == 1


# --- the SIP lists them where the guide's numbering puts a double ---------------

@pytest.mark.parametrize("sip", SIPS)
@pytest.mark.parametrize("ref", DOUBLES)
def test_exactly_the_left_bay_of_each_row_accepts_a_double(sip, ref):
    bays = _contract(sip)["bays"]
    assert sorted(b for b, v in bays.items() if ref in v["accepts"]) == sorted(CARRYING)


@pytest.mark.parametrize("sip", SIPS)
def test_the_carrying_bay_spans_the_bay_beside_it(sip):
    bays = _contract(sip)["bays"]
    for bay, beside in CARRYING.items():
        assert bays[bay]["span"] == [beside]
    for bay in COVERED:
        assert "span" not in bays[bay]


@pytest.mark.parametrize("sip", SIPS)
def test_the_bays_stay_four_and_where_they_were(sip):
    bays = _contract(sip)["bays"]
    assert sorted(bays) == BAYS
    assert bays["bay-2"]["at"] == [6.77, 27.71] and bays["bay-0"]["at"] == [24.05, 27.71]
    assert bays["bay-3"]["at"] == [6.77, 195.59] and bays["bay-1"]["at"] == [24.05, 195.59]


@pytest.mark.parametrize("sip", SIPS)
def test_l185_is_quiet_on_the_sip(sip):
    parts = {ref: _contract(ref) for ref in DOUBLES}
    parts.update({ref: _contract(ref) for ref in _singles()})
    assert _rule(lint.lint_component_span, _contract(sip), parts) == []


@pytest.mark.parametrize("sip", SIPS)
@pytest.mark.parametrize("ref", DOUBLES)
def test_the_span_box_is_the_plate_of_the_double(sip, ref):
    bays = _contract(sip)["bays"]
    spa = _contract(ref)["size"]
    for bay in CARRYING:
        at, size = span_box(bays[bay], bays, span_covers(bays[bay], 2))
        assert at == bays[bay]["at"]
        assert size == (pytest.approx(spa["w"], abs=0.02), pytest.approx(spa["h"], abs=0.02))


@pytest.mark.parametrize("sip", SIPS)
def test_a_double_is_refused_in_a_bay_with_nothing_beside_it(sip):
    c = _contract(sip)
    for bay in COVERED:
        c["bays"][bay]["accepts"] = c["bays"][bay]["accepts"] + [DOUBLES[0]]
    parts = {DOUBLES[0]: _contract(DOUBLES[0])}
    got = _rule(lint.lint_component_span, c, parts)
    assert [m.split(":")[0] for _, m in got] == ["bays/bay-0", "bays/bay-1"]


@pytest.mark.parametrize("sip", SIPS)
def test_the_singles_are_still_listed_in_all_four_bays(sip):
    bays = _contract(sip)["bays"]
    singles = _singles()
    assert len(singles) == 22
    for bay in BAYS:
        assert set(singles) <= set(bays[bay]["accepts"]), bay
        assert set(bays[bay]["accepts"]) - set(singles) <= (
            set(DOUBLES) if bay in CARRYING else set())


@pytest.mark.parametrize("sip", SIPS)
def test_the_provenance_no_longer_says_the_doubles_are_not_listed(sip):
    text = " ".join(str(v) for v in _contract(sip)["provenance"].values())
    assert "THE TWO DOUBLES ARE NOT LISTED" not in text
    assert "an occupant that spans two bays has no representation" not in text


# --- the build seats it -------------------------------------------------------------

def _build(tmp_path, bays):
    """The ASR 9010 from a tmp copy with `bays` laid over its base configuration;
    (returncode, stderr, front SVG)."""
    d_dir = shutil.copytree(LIB / "devices/cisco/asr-9010", tmp_path / "asr-9010")
    f = d_dir / "device.yaml"
    d = yaml.safe_load(f.read_text())
    d["configurations"]["base"]["bays"] = {**d["configurations"]["base"]["bays"], **bays}
    f.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "out"
    r = warmrender.run([sys.executable, str(RENDER), str(f), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    svg = out / "asr-9010.base.front.svg"
    return r.returncode, r.stderr, svg.read_text() if svg.exists() else ""


def _tag(svg, path):
    at = svg.index(f'data-path="{path}"')
    return svg[svg.rindex("<", 0, at):svg.index(">", at)]


@pytest.mark.heavy
@pytest.mark.parametrize("sip", SIPS)
@pytest.mark.parametrize("ref", DOUBLES)
@pytest.mark.parametrize("carry,beside", sorted(CARRYING.items()))
def test_the_build_seats_a_double_and_covers_the_bay_beside_it(tmp_path, sip, ref, carry, beside):
    rc, err, svg = _build(tmp_path, {"slot-1": sip, f"slot-1/{carry}": ref,
                                     f"slot-1/{beside}": ""})
    assert rc == 0, err[-800:]
    assert f'data-ref="{ref}:' in _tag(svg, f"slot-1/module/{carry}/module")
    assert f'data-covered-by="slot-1/module/{carry}"' in _tag(svg, f"slot-1/module/{beside}")
    assert f'data-path="slot-1/module/{beside}/module"' not in svg


@pytest.mark.heavy
def test_the_build_seats_a_double_in_the_bottom_row_beside_a_single_above(tmp_path):
    single = "cisco/spa-8xoc3-pos@1"
    rc, err, svg = _build(tmp_path, {"slot-1": SIPS[0], "slot-1/bay-3": DOUBLES[1],
                                     "slot-1/bay-1": "", "slot-1/bay-0": single})
    assert rc == 0, err[-800:]
    assert f'data-ref="{DOUBLES[1]}:' in _tag(svg, "slot-1/module/bay-3/module")
    assert f'data-ref="{single}:' in _tag(svg, "slot-1/module/bay-0/module")
    assert 'data-covered-by="slot-1/module/bay-3"' in _tag(svg, "slot-1/module/bay-1")


@pytest.mark.heavy
def test_the_build_refuses_a_double_over_a_filled_bay(tmp_path):
    rc, err, _svg = _build(tmp_path, {"slot-1": SIPS[0], "slot-1/bay-2": DOUBLES[0],
                                      "slot-1/bay-0": "cisco/spa-8xoc3-pos@1"})
    assert rc != 0
    assert "covers slot-1/bay-0, which holds cisco/spa-8xoc3-pos@1" in err
