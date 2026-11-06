"""Four Edgecore supplies state their input as a token, and keep the range beside it.

A consumer that reads a build's supply type takes it from `attrs.input` of the
`psu` parts fitted in that configuration's bays. It accepts only `ac`, `dc` and
`hvdc`, with every fitted supply agreeing; any other text counts as "not stated".
These supplies carried the range as a sentence in `input`, so neither build of the
four devices that seat them read as AC or DC. The sentence now sits in
`attrs.input-note`, word for word, as the library's other supplies write it.
"""
import functools
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

TOKENS = {"ac", "dc", "hvdc"}

# ref -> (input, input-note)
SUPPLIES = {
    "edgecore/csr310-psu-ac": ("ac", "100 V - 240 V, 5 A"),
    "edgecore/csr310-psu-dc": ("dc", "36 V - 72 V, 10 A"),
    "edgecore/agr-psu-ac": ("ac", "100-120 V 12 A or 200-240 V 7.5 A, 50-60 Hz per PSU"),
    "edgecore/agr-psu-dc": ("dc", "-40 to -75 VDC, 40 A max per PSU"),
}

DEVICES = ("edgecore/csr310", "edgecore/csr430", "edgecore/as7946-30xb", "edgecore/as7946-74xksb")

# Every other attr and the size, as they were before the input moved.
UNCHANGED = {
    "edgecore/csr310-psu-ac": (
        {"model": "SPAACTN-03BG", "part": "131700000453A", "power-absent": "not-published",
         "inlet": "c14"},
        {"w": 54.1, "h": 40.4, "d": 300.0}),
    "edgecore/csr310-psu-dc": (
        {"model": "CRXT-T0T12BS", "part": "131700000434A", "power-absent": "not-published",
         "inlet": "dc-terminal"},
        {"w": 54.1, "h": 40.4, "d": 300.0}),
    "edgecore/agr-psu-ac": (
        {"power-absent": "not-published", "model": "AGR PSU (AC)"},
        {"w": 60.1, "h": 37.6, "d": 360.7}),
    "edgecore/agr-psu-dc": (
        {"power-absent": "not-published", "model": "AGR PSU (DC)", "inlet": "dc-terminal"},
        {"w": 60.1, "h": 37.6, "d": 360.7}),
}


def _component(ref):
    return yaml.safe_load((LIB / "components" / ref / "v1" / "contract.yaml").read_text())


@functools.lru_cache(maxsize=None)
def _device(ref):
    return yaml.safe_load((LIB / "devices" / ref / "device.yaml").read_text())


def _bays(node):
    """Every bay in a device document: a mapping with an `id` and `accepts`."""
    if isinstance(node, dict):
        if "id" in node and "accepts" in node:
            yield node
        for v in node.values():
            yield from _bays(v)
    elif isinstance(node, list):
        for v in node:
            yield from _bays(v)


def _bare(ref):
    return ref.split("@")[0]


def _fitted_supplies(device_ref):
    """configuration name -> (declared power, [(bay id, supply ref)]) for supply bays."""
    doc = _device(device_ref)
    bays = {b["id"]: b for b in _bays(doc)}
    out = {}
    for name, cfg in doc["configurations"].items():
        fitted = []
        for bay_id, bay in bays.items():
            part = (cfg.get("bays") or {}).get(bay_id) or bay.get("default")
            if not part:
                continue
            if _component(_bare(part)).get("class") == "psu":
                fitted.append((bay_id, _bare(part)))
        power = cfg.get("power")
        out[name] = (sorted(power) if isinstance(power, list) else [power], fitted)
    return out


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_the_supply_states_its_input_as_a_token(ref):
    assert _component(ref)["attrs"]["input"] == SUPPLIES[ref][0]


@pytest.mark.parametrize("ref", sorted(SUPPLIES))
def test_the_supply_keeps_its_range_sentence_in_input_note(ref):
    assert _component(ref)["attrs"]["input-note"] == SUPPLIES[ref][1]


@pytest.mark.parametrize("ref", DEVICES)
def test_every_fitted_supply_of_every_configuration_reads(ref):
    configs = _fitted_supplies(ref)
    assert configs
    for name, (power, fitted) in configs.items():
        assert fitted, f"{ref} {name}: no supply is fitted"
        stated = {s: _component(s)["attrs"].get("input") for _, s in fitted}
        assert all(v in TOKENS for v in stated.values()), f"{ref} {name}: {stated}"
        assert len(set(stated.values())) == 1, f"{ref} {name}: supplies disagree: {stated}"
        assert power in (["ac"], ["dc"]), f"{ref} {name}: power {power}"
        assert set(stated.values()) == set(power), f"{ref} {name}: {stated} against {power}"


@pytest.mark.parametrize("ref", sorted(UNCHANGED))
def test_nothing_else_about_the_supply_moved(ref):
    doc = _component(ref)
    attrs = {k: v for k, v in doc["attrs"].items() if k not in ("input", "input-note")}
    assert attrs == UNCHANGED[ref][0]
    assert doc["size"] == UNCHANGED[ref][1]
