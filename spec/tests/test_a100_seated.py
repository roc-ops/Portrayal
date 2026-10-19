"""The NVIDIA A100 80GB PCIe seats in a riser bay that spans, and exports its
power port (docs/pcie-two-slot-bays-design.md, docs/connectors-gpu-design.md
section 7).

The card says it is two slots wide (`slot-width: 2`); riser 1A's `slot-1` says it
spans `slot-2`. The CPU 8-pin on the far end is std/eps12v-header@1 on the card's
rear face and the three NVLink connectors under the caps on the top edge are
nvidia/nvlink-a100-connector@1 on its plan face; the card exports the first as a
power port. The R740xd's example configuration seats the card across riser 1's
two openings.
"""
import copy
import shutil
import sys
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal import dcim_export as dx
from portrayal import lint
from portrayal.manifest import load_yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
A100 = "nvidia/a100-pcie-80gb@1"
CARD = LIB / "components/nvidia/a100-pcie-80gb/v1/contract.yaml"
RISER = LIB / "components/dell/riser-1a-14g/v2/contract.yaml"
CONFIG = "sff24-rc4-1a2a3a-a100"
EPS12V = "std/eps12v-header@1"
NVLINK = "nvidia/nvlink-a100-connector@1"


def _contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return load_yaml(LIB / f"components/{ns}/{name}/v{major}/contract.yaml")


def _library_ref(ref):
    return _contract(ref)


def _rule(fn, data, parts):
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


# --- the card is two slots wide, and a bay that spans takes it -------------------

def test_the_card_declares_its_width_and_is_no_longer_unplaced():
    card = load_yaml(CARD)
    assert card["slot-width"] == 2
    assert "unplaced" not in card, "riser 1A's slot-1 seats it now"


def test_riser_1a_slot_1_accepts_the_card_and_slot_3_does_not():
    bays = load_yaml(RISER)["bays"]
    assert A100 in bays["slot-1"]["accepts"] and bays["slot-1"]["span"] == ["slot-2"]
    assert A100 not in bays["slot-3"]["accepts"] and "span" not in bays["slot-3"]
    assert A100 not in bays["slot-2"]["accepts"]


def test_l185_is_quiet_on_riser_1a_with_the_card_in_slot_1():
    parts = {A100: load_yaml(CARD)}
    assert _rule(lint.lint_component_span, load_yaml(RISER), parts) == []


def test_l185_refuses_the_card_in_a_one_slot_bay_with_no_span():
    # load_yaml hands every caller in the process the same dict, and the lock
    # hashes it: edit a copy
    riser = copy.deepcopy(load_yaml(RISER))
    riser["bays"]["slot-3"]["accepts"] = [*riser["bays"]["slot-3"]["accepts"], A100]
    parts = {A100: load_yaml(CARD)}
    assert [m for _, m in _rule(lint.lint_component_span, riser, parts)] == [
        f"bays/slot-3: accepts {A100}, which is 2 slots wide, and names 0 bay(s) in `span` "
        "for it to cover"]


def test_the_card_is_its_own_two_slot_width_when_it_is_composed():
    """A part that composes the card is at least as wide as it."""
    parts = {A100: load_yaml(CARD)}
    holder = {"kind": "module", "parts": [{"id": "gpu", "ref": A100}]}
    assert [m for _, m in _rule(lint.lint_component_span, holder, parts)] == [
        f"parts/gpu: composes {A100}, which is 2 slots wide, and this part says it is 1 - "
        "give it `slot-width: 2`"]


# --- the connectors: composed the way the headers expect --------------------------

def test_the_far_end_composes_the_eps12v_header_as_aux_power():
    tail = _contract(f"{A100.split('@')[0]}-tail@1")
    ports = {p["id"]: p for p in tail["parts"]}
    assert ports["aux-power"]["ref"] == EPS12V
    assert _contract(EPS12V)["interface"] == "eps12v-8pin"


def test_the_top_edge_composes_three_nvlink_connectors_under_the_caps():
    top = _contract(f"{A100.split('@')[0]}-top@1")
    links = {p["id"]: p for p in top["parts"]}
    assert sorted(links) == ["nvlink-1", "nvlink-2", "nvlink-3"]
    assert {p["ref"] for p in links.values()} == {NVLINK}
    # PNY's render: 13.5, 70.7 and 126.1 behind the bracket's outer face
    assert [links[i]["at"][1] for i in sorted(links)] == [13.5, 70.7, 126.1]
    assert load_yaml(CARD)["faces"]["plan"]["ref"] == f"{A100.split('@')[0]}-top@1"


def test_the_stand_in_is_gone():
    assert not (LIB / "components/nvidia/a100-eps12v-standin").exists()


# --- the export -----------------------------------------------------------------

def test_the_card_exports_its_power_port_with_the_connector_as_its_label():
    doc = dx.build_module(load_yaml(CARD), "NVIDIA", _library_ref)
    assert doc["power-ports"] == [
        {"name": "aux-power", "type": "other", "label": dx.POWER_LABEL["std/eps12v-header"]}]
    assert "interfaces" not in doc, "an NVLink connector is no port of either DCIM"
    assert "slot-width: 2 (seated, it also covers the bay beside its own" in doc["comments"]


def test_a_card_whose_back_draws_no_inlet_gains_no_power_port():
    card = {"name": "t", "attrs": {"model": "T"}, "faces": {"rear": {"ref": "acme/back@1"}},
            "parts": []}
    back = {"parts": [{"ref": "std/rj45@1", "id": "p0"}]}
    assert "power-ports" not in dx.build_module(card, "X", {"acme/back@1": back}.get)


# --- the example configuration ---------------------------------------------------

def _render(tmp_path, cfg_bays=None):
    """The R740xd as the library has it, rendered from a tmp copy with
    `cfg_bays` laid over the example's `bays`; (returncode, stderr, rear SVG)."""
    d_dir = shutil.copytree(LIB / "devices/dell/r740xd", tmp_path / "r740xd")
    f = d_dir / "device.yaml"
    if cfg_bays is not None:
        d = yaml.safe_load(f.read_text())
        d["configurations"][CONFIG]["bays"] = {
            **d["configurations"][CONFIG]["bays"], **cfg_bays}
        f.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "out"
    r = warmrender.run([sys.executable, str(RENDER), str(f), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    svg = out / f"r740xd.{CONFIG}.rear.svg"
    return r.returncode, r.stderr, svg.read_text() if svg.exists() else ""


def _tag(svg, path):
    at = svg.index(f'data-path="{path}"')
    return svg[svg.rindex("<", 0, at):svg.index(">", at)]


def test_the_example_configuration_seats_the_card_in_slot_1_and_empties_slot_2():
    dev = load_yaml(LIB / "devices/dell/r740xd/device.yaml")
    cfg = dev["configurations"][CONFIG]
    assert cfg["kind"] == "example"
    assert cfg["bays"]["riser-1"] == "dell/riser-1a-14g@2"
    assert cfg["bays"]["riser-1/slot-1"] == A100 and cfg["bays"]["riser-1/slot-2"] == ""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_example_builds_and_the_card_covers_slot_2(tmp_path):
    rc, err, svg = _render(tmp_path)
    assert rc == 0, err[-800:]
    card = _tag(svg, "riser-1/module/slot-1/module")
    assert f'data-ref="{A100}:' in card
    assert 'transform="translate(-13.41,-1.35)"' in card, card
    assert 'data-covered-by="riser-1/module/slot-1"' in _tag(svg, "riser-1/module/slot-2")
    assert 'data-path="riser-1/module/slot-2/module"' not in svg


def test_the_build_refuses_the_card_over_slot_2s_filler(tmp_path):
    rc, err, _svg = _render(tmp_path, {"riser-1/slot-2": "dell/pcie-filler-fh-14g@2"})
    assert rc != 0
    assert (f"riser-1/slot-1: {A100} is 2 slots wide and covers riser-1/slot-2, "
            "which holds dell/pcie-filler-fh-14g@2") in err, err[-800:]
