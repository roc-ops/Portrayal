"""A dual-wide MIC seats across both MIC windows of the carriers that list it
(docs/pcie-two-slot-bays-design.md: `slot-width` on the part, `span` on the bay).

Juniper's MX Series Interface Module Reference lists MIC-3D-40GE-TX for the
MPC1E, MPC2E and MPC2E-3D-NG (Tables 10 and 11) and for the MPC3E-3D-NG
(Table 12), where the MPC3E has a dash; it lists MIC3-100G-DWDM for the MPC3E
and the MPC3E-3D-NG (Table 12) and has no row for the MPC1E, MPC2E or
MPC2E-3D-NG. Each carrier's `mic0` accepts the MICs its column lists and spans
`mic1`, the window beside it. The kit's side is spec/tests/js/rack-dual-wide-mic.mjs.
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

TX = "juniper/mic-3d-40ge-tx@2"
DWDM = "juniper/mic3-100g-dwdm@2"
LISTED = {
    "juniper/mpc1e-3d@3": [TX],
    "juniper/mpc2e-3d@3": [TX],
    "juniper/mpc3e-3d@3": [DWDM],
    "juniper/mpc2e-3d-ng@1": [TX],
    "juniper/mpc3e-3d-ng@1": [TX, DWDM],
}
CARRIERS = list(LISTED)
SEATED = [(carrier, mic) for carrier, mics in LISTED.items() for mic in mics]


def _contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return load_yaml(LIB / f"components/{ns}/{name}/v{major}/contract.yaml")


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


# --- the parts say how wide they are, and where they seat ---------------------

@pytest.mark.parametrize("ref", [TX, DWDM])
def test_a_dual_wide_mic_states_its_width_and_is_seated(ref):
    mic = _contract(ref)
    assert slot_width(mic) == 2
    assert "unplaced" not in mic


@pytest.mark.parametrize("carrier", CARRIERS)
def test_mic0_spans_mic1_and_lists_the_mic_the_module_reference_lists(carrier):
    bays = _contract(carrier)["bays"]
    assert bays["mic0"]["span"] == ["mic1"]
    for mic in (TX, DWDM):
        assert (mic in bays["mic0"]["accepts"]) == (mic in LISTED[carrier])
    assert "span" not in bays["mic1"]
    for mic in (TX, DWDM):
        assert mic not in bays["mic1"]["accepts"], "mic1 has no bay beside it to cover"


@pytest.mark.parametrize("carrier,mic", SEATED)
def test_the_span_box_is_the_plate_of_the_mic(carrier, mic):
    bays = _contract(carrier)["bays"]
    at, size = span_box(bays["mic0"], bays, span_covers(bays["mic0"], 2))
    mic = _contract(mic)["size"]
    assert at == [37.7, 0.15]
    assert size == (pytest.approx(mic["w"]), pytest.approx(mic["h"]))


@pytest.mark.parametrize("carrier", CARRIERS)
def test_l185_is_quiet_on_the_carrier(carrier):
    parts = {TX: _contract(TX), DWDM: _contract(DWDM)}
    assert _rule(lint.lint_component_span, _contract(carrier), parts) == []


# --- L185 follows a span along the face as well as down it --------------------

def _pair(**mic1):
    box = {"size": [168.8, 29.2]}
    return {"kind": "module", "bays": {
        "mic0": {**box, "at": [37.7, 0.15], "span": ["mic1"]},
        "mic1": {**box, "at": [207.0, 0.15], **mic1}}}


def test_l185_accepts_a_span_to_the_bay_beside_it():
    assert _rule(lint.lint_component_span, _pair(), {}) == []


def test_l185_accepts_a_span_to_the_left_when_the_bay_is_turned():
    c = _pair(rotate=180)
    c["bays"]["mic0"]["rotate"] = 180
    c["bays"]["mic0"]["at"], c["bays"]["mic1"]["at"] = [207.0, 0.15], [37.7, 0.15]
    assert _rule(lint.lint_component_span, c, {}) == []


def test_l185_refuses_a_span_that_steps_sideways_or_skips_a_bay():
    c = _pair()
    c["bays"]["mic1"]["at"] = [207.0, 20.0]
    assert [m for _, m in _rule(lint.lint_component_span, c, {})][0].startswith(
        "bays/mic0: spans mic1, which is not the next bay below mic0")
    c = _pair()
    c["bays"]["mic1"]["at"] = [400.0, 0.15]
    assert _rule(lint.lint_component_span, c, {}), "a gap wider than a bay is no neighbour"
    c = _pair()
    c["bays"]["mic1"]["at"] = [37.7, 0.15]
    assert _rule(lint.lint_component_span, c, {}), "the same place is no neighbour"


def test_l185_refuses_the_bay_on_the_wrong_side_of_a_turned_span():
    c = _pair()
    c["bays"]["mic0"]["rotate"] = 180
    c["bays"]["mic1"]["rotate"] = 180
    assert _rule(lint.lint_component_span, c, {}), "at 180 the next bay is to the left"


# --- the build seats it ------------------------------------------------------------

def _build(tmp_path, bays):
    """The MX240 from a tmp copy with `bays` laid over its base configuration;
    (returncode, stderr, front SVG)."""
    d_dir = shutil.copytree(LIB / "devices/juniper/mx240", tmp_path / "mx240")
    f = d_dir / "device.yaml"
    d = yaml.safe_load(f.read_text())
    d["configurations"]["base"]["bays"] = {**d["configurations"]["base"]["bays"], **bays}
    f.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "out"
    r = warmrender.run([sys.executable, str(RENDER), str(f), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    svg = out / "mx240.base.front.svg"
    return r.returncode, r.stderr, svg.read_text() if svg.exists() else ""


def _tag(svg, path):
    at = svg.index(f'data-path="{path}"')
    return svg[svg.rindex("<", 0, at):svg.index(">", at)]


@pytest.mark.heavy
@pytest.mark.parametrize("carrier,mic", SEATED)
def test_the_build_seats_the_mic_in_mic0_and_covers_mic1(tmp_path, carrier, mic):
    rc, err, svg = _build(tmp_path, {"dpc2": carrier, "dpc2/mic0": mic, "dpc2/mic1": ""})
    assert rc == 0, err[-800:]
    assert f'data-ref="{mic}:' in _tag(svg, "dpc2/module/mic0/module")
    assert 'data-covered-by="dpc2/module/mic0"' in _tag(svg, "dpc2/module/mic1")
    assert 'data-path="dpc2/module/mic1/module"' not in svg


@pytest.mark.heavy
def test_the_build_refuses_the_mic_over_a_filled_mic1(tmp_path):
    rc, err, _svg = _build(tmp_path, {"dpc2": "juniper/mpc2e-3d@3", "dpc2/mic0": TX,
                                      "dpc2/mic1": "juniper/mx-mic-blank@2"})
    assert rc != 0
    assert "covers dpc2/mic1, which holds juniper/mx-mic-blank@2" in err
