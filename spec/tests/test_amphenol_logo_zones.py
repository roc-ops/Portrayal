"""The printed Amphenol mark has a reserved place on the 300CB08 family fronts.

The maker prints an underlined logotype with a tagline at the left of the centre
plate. It is never drawn; its place is a region `logo-zone`, whose box was read
from the installation guide's front figures. The faces whose front is not the
panel the figure shows are named here too, so the next change sees them.
"""
import pathlib

import pytest
import yaml

from portrayal import lint as L

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "amphenol-ns"

# device -> (at, size) of the reserved mark, in millimetres of the front view
ZONES = {
    "300cb08-c": ([173.4, 4.3], {"w": 32.8, "h": 9.2}),
    "300cb08-sc": ([173.4, 4.3], {"w": 32.8, "h": 9.2}),
    "nrg300cb08-sens-c": ([173.2, 4.4], {"w": 32.6, "h": 9.5}),
    "nrg300cb08-sens": ([173.2, 4.4], {"w": 32.6, "h": 9.5}),
    "nrg300cb08-sens-sc": ([173.2, 4.4], {"w": 32.6, "h": 9.5}),
}

# Left out: the control variants have a different centre plate from the one in
# the figure (other card-slot bar, other parts, other legends), and no
# photograph of their front is held.
LEFT_OUT = ("nrg300cb08-ctrl", "nrg300cb08-ctrl-c", "nrg300cb08-ctrl-sc")


def front(name):
    doc = yaml.safe_load((DEVICES / name / "device.yaml").read_text())
    return doc, doc["views"]["front"]


@pytest.mark.parametrize("name", sorted(ZONES))
def test_the_front_reserves_one_logo_zone(name):
    doc, view = front(name)
    zones = [r for r in view.get("regions") or [] if r["id"].startswith("logo")]
    assert len(zones) == 1, zones
    zone = zones[0]
    assert zone["id"] == "logo-zone"
    at, size = ZONES[name]
    assert zone["at"] == at
    assert zone["size"] == size
    assert "not drawn" in zone["label"]
    assert size["w"] > 0 and size["h"] > 0
    assert at[0] >= 0 and at[1] >= 0
    assert at[0] + size["w"] <= view["size"]["w"]
    assert at[1] + size["h"] <= view["size"]["h"]


@pytest.mark.parametrize("name", sorted(ZONES))
def test_the_reserved_place_lints_clean_and_the_text_stays(name):
    doc, view = front(name)
    with L.collecting() as found:
        L.lint_device_logo_zone(name, doc)
    assert [e for e in found.errors if "L172" in e] == []
    texts = {s.get("text") for s in view.get("silkscreen") or []}
    assert {"Amphenol", "NETWORK SOLUTIONS"} <= texts


@pytest.mark.parametrize("name", LEFT_OUT)
def test_a_face_left_out_has_no_zone(name):
    doc, view = front(name)
    assert not [r for r in view.get("regions") or [] if r["id"].startswith("logo")]
