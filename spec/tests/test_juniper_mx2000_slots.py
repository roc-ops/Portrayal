"""The MX2000 line-card slots take the cards the Module Reference's Table 4 prints a release for.

MX Series Interface Module Reference, Table 4 'MPCs Supported by MX240, MX480, MX960, MX10003, MX10004, MX10016, MX2008,
MX2010, and MX2020 Routers' (PDF pp. 33-35): MX-MPC2E-3D-NG and MX-MPC3E-3D-NG are supported on the MX2008 (15.1F7),
the MX2010 and the MX2020; MX2K-MPC8E and MX2K-MPC9E are supported on the MX2008 (15.1F7) as well as the MX2010
and the MX2020. The MX2008 Hardware Guide prints the same MX2008 releases in its own copy of the table and lists
both MX2K cards in its FRU power tables, and says that the MPC6E, MPC8E and MPC9E need no adapter card in the MX2008.
The two NG cards are the MX240 form MPC, so they reach an MX2000 slot through the line-card adapter like the other
carriers of that form.
"""
import pytest

from libdata import devices, components

pytestmark = pytest.mark.heavy

ADAPTER = "juniper/mx2000-lc-adapter"
NG_CARDS = ("juniper/mpc2e-3d-ng", "juniper/mpc3e-3d-ng")
MX2K_CARDS = ("juniper/mx2k-mpc8e-v2k", "juniper/mx2k-mpc9e-v2k")


def _latest(name):
    found = [d for r, _, d in components() if r.split("@")[0] == name]
    assert found, f"{name} has no contract in the library"
    return max(found, key=lambda d: int(str(d["version"]).split(".")[0]))


def _ref(name):
    return f"{name}@{str(_latest(name)['version']).split('.')[0]}"


def _bays(node):
    if isinstance(node, dict):
        if "id" in node and "accepts" in node:
            yield node
        for v in node.values():
            yield from _bays(v)
    elif isinstance(node, list):
        for v in node:
            yield from _bays(v)


def _fpcs(slug):
    doc = dict(devices())[slug]
    return [b for b in _bays(doc.get("views", doc)) if b["id"].startswith("fpc")]


@pytest.mark.parametrize("name", NG_CARDS)
def test_the_adapter_seats_the_ng_cards(name):
    bay = _latest(ADAPTER)["bays"]["mpc"]
    assert _ref(name) in bay["accepts"], f"the adapter's bay does not list {_ref(name)}"


@pytest.mark.parametrize("slug", ("juniper/mx2008", "juniper/mx2010", "juniper/mx2020"))
def test_every_slot_that_takes_the_adapter_takes_what_the_adapter_seats(slug):
    seated = set(_latest(ADAPTER)["bays"]["mpc"]["accepts"])
    slots = _fpcs(slug)
    assert slots, f"{slug}: no line-card slots found"
    assert all(_ref(ADAPTER) in s["accepts"] for s in slots), f"{slug}: a slot does not take the adapter"
    assert all(_ref(n) in seated for n in NG_CARDS), "the adapter does not seat both NG cards"


@pytest.mark.parametrize("name", MX2K_CARDS)
def test_every_mx2008_slot_takes_the_mx2k_cards_the_table_prints(name):
    slots = _fpcs("juniper/mx2008")
    assert len(slots) == 10
    missing = [s["id"] for s in slots if _ref(name) not in s["accepts"]]
    assert not missing, f"juniper/mx2008: {', '.join(missing)} do not take {_ref(name)}"


@pytest.mark.parametrize("name", MX2K_CARDS)
def test_the_mx2k_card_says_the_mx2008_takes_it(name):
    desc = " ".join(str(_latest(name)["description"]).split())
    assert "MX2008" in desc, f"{name}: the description does not name the MX2008"
