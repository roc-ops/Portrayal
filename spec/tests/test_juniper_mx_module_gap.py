"""The MPC2E-3D-NG and MPC3E-3D-NG carriers exist, carry their model numbers, and sit in the chassis that print them.

The MX Series Interface Module Reference lists both cards in Table 4 'MPCs Supported by MX240, MX480, MX960, MX10003,
MX10004, MX10016, MX2008, MX2010, and MX2020 Routers' (PDF pp. 33-34): model numbers MX-MPC2E-3D-NG and MX-MPC3E-3D-NG,
first supported on the MX240, MX480 and MX960 in 14.1R4, 14.2R3 and Junos Continuity 15.1. Each has its own column in the
MIC/MPC compatibility tables (Table 11 for the MPC2E-3D-NG, Table 12 for the MPC3E-3D-NG), and the MIC bays take that column.
"""
import pytest

from libdata import devices, components

CHASSIS = ("juniper/mx240", "juniper/mx480", "juniper/mx960")

# part -> (attrs.model, attrs.model-variants, watts in the chassis guide's FRU power table, MIC parts its column takes)
MODULES = {
    "juniper/mpc2e-3d-ng": ("MX-MPC2E-3D-NG", "MPC2E-3D-NG", 474, {
        "mic-3d-20ge-sfp", "mic-macsec-20ge", "mic-3d-2xge-xfp", "mic-3d-4xge-xfp", "mic-3d-10ge-sfp-e",
        "mic-3d-1oc192-xfp", "mic-3d-4oc3oc12-1oc48", "mic-3d-8oc3oc12-4oc48", "mic-3d-8oc3-2oc12-atm",
        "mic-3d-4choc3-2choc12", "mic-3d-8choc3-4choc12", "mic-3d-8ds3-e3", "mic-3d-16che1-t1-ce",
        "ms-mic-16g", "mx-mic-blank"}),
    "juniper/mpc3e-3d-ng": ("MX-MPC3E-3D-NG", "MPC3E-3D-NG", 534, {
        "mic-3d-20ge-sfp", "mic-macsec-20ge", "mic-3d-2xge-xfp", "mic-3d-4xge-xfp", "mic-3d-10ge-sfp-e",
        "mic-3d-1oc192-xfp", "mic-3d-4oc3oc12-1oc48", "mic-3d-8oc3oc12-4oc48", "mic-3d-8oc3-2oc12-atm",
        "mic-3d-4choc3-2choc12", "mic-3d-8choc3-4choc12", "mic-3d-8ds3-e3", "mic-3d-16che1-t1-ce",
        "ms-mic-16g", "mic3-3d-10xge-sfpp", "mic3-3d-2x40ge-qsfpp", "mic3-3d-1x100ge-cfp",
        "mic3-3d-1x100ge-cxp", "mx-mic-blank"}),
}
# the base cards whose slots the NG cards share
BASE = {"juniper/mpc2e-3d-ng": "juniper/mpc2e-3d@3", "juniper/mpc3e-3d-ng": "juniper/mpc3e-3d@3"}


def _contract(ref):
    found = [d for r, _, d in components() if r == ref]
    assert found, f"{ref} has no contract in the library"
    return max(found, key=lambda d: int(str(d["version"]).split(".")[0]))


def _bays(node):
    if isinstance(node, dict):
        if "id" in node and "accepts" in node:
            yield node
        for v in node.values():
            yield from _bays(v)
    elif isinstance(node, list):
        for v in node:
            yield from _bays(v)


def _names(accepts):
    return {a.split("/")[1].split("@")[0] for a in accepts}


@pytest.mark.parametrize("ref", MODULES)
def test_the_card_carries_its_model_numbers_and_power(ref):
    model, variants, watts, _ = MODULES[ref]
    doc = _contract(ref)
    assert doc["attrs"]["model"] == model
    assert doc["attrs"]["model-variants"] == variants
    assert doc["attrs"]["power-draw-max-w"] == watts


@pytest.mark.parametrize("ref", MODULES)
def test_the_mic_bays_take_the_columns_mics(ref):
    _, _, _, mics = MODULES[ref]
    doc = _contract(ref)
    assert sorted(doc["bays"]) == ["mic0", "mic1"], f"{ref}: the figure shows two MIC windows"
    for bay_id, bay in doc["bays"].items():
        assert _names(bay["accepts"]) == mics, f"{ref} {bay_id}: not the MIC column of its compatibility table"


@pytest.mark.parametrize("ref", MODULES)
@pytest.mark.parametrize("slug", CHASSIS)
def test_every_slot_that_takes_the_base_card_takes_the_ng_card(slug, ref):
    doc = dict(devices())[slug]
    version = str(_contract(ref)["version"]).split(".")[0]
    slots = [b for b in _bays(doc.get("views", doc)) if BASE[ref] in b["accepts"]]
    assert slots, f"{slug}: no slot takes {BASE[ref]}"
    missing = [b["id"] for b in slots if f"{ref}@{version}" not in b["accepts"]]
    assert not missing, f"{slug}: {', '.join(missing)} take {BASE[ref]} but not {ref}@{version}"


@pytest.mark.parametrize("ref", MODULES)
def test_no_other_chassis_lists_the_ng_card(ref):
    """The two tables name the MX240, MX480 and MX960 among the chassis this order wires; nothing else lists it."""
    _contract(ref)
    elsewhere = sorted(slug for slug, doc in devices() if slug not in CHASSIS
                       and any(a.startswith(ref + "@") for b in _bays(doc.get("views", doc)) for a in b["accepts"]))
    assert not elsewhere, f"{ref} is listed by {', '.join(elsewhere)}"
