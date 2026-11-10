"""The queuing, P and NG-queuing MPC carriers exist, carry their model numbers and power, take their own MIC column and sit in
the chassis slots that take the card they are the sibling of.

The MX Series Interface Module Reference lists each card in Table 4 'MPCs Supported by MX240, MX480, MX960, MX10003,
MX10004, MX10016, MX2008, MX2010, and MX2020 Routers' (PDF pp. 33-34) with its model number. Each has its own column in
the MIC/MPC compatibility tables (Table 10 for the MPC1 family, Table 11 for the MPC2 family, Table 12 for the MPC3 family),
and the MIC bays take that column. The MX240 hardware guide's FRU power table (Table 93) gives the watts.
"""
import pytest

from libdata import devices, components

pytestmark = pytest.mark.heavy

CHASSIS = ("juniper/mx240", "juniper/mx480", "juniper/mx960")

QUEUING_MICS = {"mic-3d-8oc3-2oc12-atm", "mic-3d-4choc3-1oc12", "mic-3d-4choc3-2choc12", "mic-3d-8choc3-4choc12"}
COMMON = {"mic-3d-20ge-sfp", "mic-macsec-20ge", "mic-3d-2xge-xfp", "mic-3d-1oc192-xfp", "mic-3d-8ds3-e3", "ms-mic-16g",
          "mx-mic-blank"}
OC3 = {"mic-3d-4oc3oc12-1oc48", "mic-3d-8oc3oc12-4oc48"}

# part -> (attrs.model, attrs.model-variants or None, watts in the chassis guide's FRU power table, MIC parts its column takes,
#          the dual-wide MICs the column also lists, the card whose slots it shares)
MODULES = {
    "juniper/mpc1-3d-q": ("MX-MPC1-3D-Q", "MX-MPC1E-3D-Q", 175,
                          COMMON | OC3 | QUEUING_MICS | {"mic-3d-16che1-t1-ce"}, {"mic-3d-40ge-tx"}, "juniper/mpc1e-3d"),
    "juniper/mpc2e-3d-q": ("MX-MPC2E-3D-Q", "MX-MPC2-3D-Q, MX-MPC2-3D-EQ, MX-MPC2E-3D-EQ", 294,
                           COMMON | OC3 | QUEUING_MICS | {"mic-3d-16che1-t1-ce", "mic-3d-4xge-xfp"}, {"mic-3d-40ge-tx"},
                           "juniper/mpc2e-3d"),
    "juniper/mpc2e-3d-p": ("MX-MPC2E-3D-P", None, 294,
                           COMMON | {"mic-3d-4choc3-1oc12", "mic-3d-4xge-xfp"}, {"mic-3d-40ge-tx"}, "juniper/mpc2e-3d"),
    "juniper/mpc2e-3d-ng-q": ("MX-MPC2E-3D-NG-Q", "MPC2E-3D-NG-Q", 529,
                              COMMON | OC3 | QUEUING_MICS | {"mic-3d-16che1-t1-ce", "mic-3d-4xge-xfp", "mic-3d-10ge-sfp-e"},
                              {"mic-3d-40ge-tx"}, "juniper/mpc2e-3d-ng"),
    "juniper/mpc3e-3d-ng-q": ("MX-MPC3E-3D-NG-Q", "MPC3E-3D-NG-Q", 583,
                              COMMON | OC3 | QUEUING_MICS | {"mic-3d-16che1-t1-ce", "mic-3d-4xge-xfp", "mic-3d-10ge-sfp-e",
                                                             "mic3-3d-10xge-sfpp", "mic3-3d-2x40ge-qsfpp",
                                                             "mic3-3d-1x100ge-cfp", "mic3-3d-1x100ge-cxp"},
                              {"mic-3d-40ge-tx", "mic3-100g-dwdm"}, "juniper/mpc3e-3d-ng"),
}


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
    model, variants, watts, *_ = MODULES[ref]
    doc = _contract(ref)
    assert doc["attrs"]["model"] == model
    assert doc["attrs"].get("model-variants") == variants
    assert doc["attrs"]["power-draw-max-w"] == watts


@pytest.mark.parametrize("ref", MODULES)
def test_the_mic_bays_take_the_columns_mics(ref):
    _, _, _, mics, dual, _ = MODULES[ref]
    doc = _contract(ref)
    assert sorted(doc["bays"]) == ["mic0", "mic1"], f"{ref}: the module page states two MIC slots"
    for bay_id, bay in doc["bays"].items():
        column = mics | dual if bay_id == "mic0" else mics
        assert _names(bay["accepts"]) == column, f"{ref} {bay_id}: not the MIC column of its compatibility table"
    assert doc["bays"]["mic0"]["span"] == ["mic1"], f"{ref}: the dual-wide MICs seat across both windows"


@pytest.mark.parametrize("ref", MODULES)
def test_the_card_is_drawn_at_the_family_envelope_with_two_windows_at_the_mic_plate(ref):
    doc = _contract(ref)
    assert (doc["size"]["w"], doc["size"]["h"]) == (413.5, 29.5)
    for bay in doc["bays"].values():
        assert bay["size"] == [168.8, 29.2]


@pytest.mark.parametrize("ref", MODULES)
def test_the_skin_prints_the_model_name_the_figure_prints(ref):
    skin = (ref.split("/")[1])
    path = [p for r, p, _ in components() if r == ref]
    assert path, f"{ref} is not a component"
    svg = (path[0].parent / "skins" / "default.svg").read_text()
    label = {"mpc1-3d-q": "MX-MPC1-3D-Q", "mpc2e-3d-q": "MX-MPC2E-3D-Q", "mpc2e-3d-p": "MX-MPC2E-3D-P",
             "mpc2e-3d-ng-q": "MPC2E-3D-NG-Q", "mpc3e-3d-ng-q": "MPC3E-3D-NG-Q"}[skin]
    assert f">{label}</text>" in svg


@pytest.mark.parametrize("ref", MODULES)
@pytest.mark.parametrize("slug", CHASSIS)
def test_every_slot_that_takes_the_sibling_card_takes_this_one(slug, ref):
    sibling = MODULES[ref][5]
    version = str(_contract(ref)["version"]).split(".")[0]
    doc = dict(devices())[slug]
    slots = [b for b in _bays(doc.get("views", doc)) if any(a.startswith(sibling + "@") for a in b["accepts"])]
    assert slots, f"{slug}: no slot takes {sibling}"
    missing = [b["id"] for b in slots if f"{ref}@{version}" not in b["accepts"]]
    assert not missing, f"{slug}: {', '.join(missing)} take {sibling} but not {ref}@{version}"


@pytest.mark.parametrize("ref", MODULES)
def test_no_other_chassis_lists_the_card(ref):
    """The MX240, MX480 and MX960 take the card; no other chassis lists it yet (the MX2000 line seats a vertical form)."""
    _contract(ref)
    elsewhere = sorted(slug for slug, doc in devices() if slug not in CHASSIS
                       and any(a.startswith(ref + "@") for b in _bays(doc.get("views", doc)) for a in b["accepts"]))
    assert not elsewhere, f"{ref} is listed by {', '.join(elsewhere)}"
