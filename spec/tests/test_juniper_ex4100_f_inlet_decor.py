"""The dark box round the AC inlet on the EX4100-F rear faces is drawn as what it is.

The four EX4100-F switches with a built-in AC supply place a C14 inlet on the
rear face and draw the moulded surround the inlet sits in. That surround is
the housing round a placed inlet, not a connector, so its decor kind must not
be one of the connector names in spec/schemas/connector-decor-names.yaml, and
the placed inlet must still sit inside it.
"""

import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVS = ROOT / "library/devices/juniper"
NAMES = ROOT / "spec/schemas/connector-decor-names.yaml"

MODELS = ["ex4100-f-24p", "ex4100-f-24t", "ex4100-f-48p", "ex4100-f-48t"]


def _connector_names():
    data = yaml.safe_load(NAMES.read_text())
    return set(data.get("names", data))


def _rear_view(model):
    dev = yaml.safe_load((DEVS / model / "device.yaml").read_text())
    return dev["views"]["rear"]


def _rear(model):
    return _rear_view(model)["panel"]


def _box(entry):
    x, y = entry["at"]
    w, h = entry["size"]
    return x, y, x + w, y + h


@pytest.mark.parametrize("model", MODELS)
def test_the_inlet_surround_is_not_named_as_a_connector(model):
    decor = _rear(model)["decor"]
    surround = [d for d in decor if d["id"] == "inlet-housing"]
    assert len(surround) == 1
    assert surround[0].get("kind") not in _connector_names()


@pytest.mark.parametrize("model", MODELS)
def test_the_placed_inlet_sits_inside_its_surround(model):
    panel = _rear(model)
    surround = next(d for d in panel["decor"] if d["id"] == "inlet-housing")
    inlet = next(c for c in panel["cutouts"] if c["id"] == "ac-inlet")
    sx0, sy0, sx1, sy1 = _box(surround)
    ix0, iy0, ix1, iy1 = _box(inlet)
    assert sx0 <= ix0 and sy0 <= iy0 and ix1 <= sx1 and iy1 <= sy1
    placements = _rear_view(model)["components"]["placements"]
    placed = [p for p in placements if p["id"] == "ac-inlet"]
    assert [p["ref"] for p in placed] == ["std/c14-inlet@1"]
