"""The MX2000 line-card adapter seats every MX240-form card Table 4 prints a release for on the MX2000 line.

MX Series Interface Module Reference, Table 4 'MPCs Supported by MX240, MX480, MX960, MX10003, MX10004, MX10016, MX2008,
MX2010, and MX2020 Routers' (printed pp. 23 to 25): each of MX-MPC1-3D-Q, MX-MPC1E-3D-Q, MX-MPC2-3D-Q, MX-MPC2E-3D-Q,
MX-MPC2-3D-EQ, MX-MPC2E-3D-EQ, MX-MPC2E-3D-P, MX-MPC2E-3D-NG-Q and MX-MPC3E-3D-NG-Q prints a release for the MX2008
(15.1F7), the MX2010 and the MX2020. They are the MX240 form card, so they reach an MX2000 slot through the line-card
adapter like the other carriers of that form.
"""
import pytest

from libdata import components

ADAPTER = "juniper/mx2000-lc-adapter"

# part -> the maker numbers it stands for (its model and model-variants)
CARDS = {
    "juniper/mpc1-3d-q": ("MX-MPC1-3D-Q", "MX-MPC1E-3D-Q"),
    "juniper/mpc2e-3d-q": ("MX-MPC2E-3D-Q", "MX-MPC2-3D-Q", "MX-MPC2-3D-EQ", "MX-MPC2E-3D-EQ"),
    "juniper/mpc2e-3d-p": ("MX-MPC2E-3D-P",),
    "juniper/mpc2e-3d-ng-q": ("MX-MPC2E-3D-NG-Q",),
    "juniper/mpc3e-3d-ng-q": ("MX-MPC3E-3D-NG-Q",),
}
NUMBERS = sorted(n for numbers in CARDS.values() for n in numbers)


def _latest(name):
    found = [d for r, _, d in components() if r.split("@")[0] == name]
    assert found, f"{name} has no contract in the library"
    return max(found, key=lambda d: int(str(d["version"]).split(".")[0]))


def _ref(name):
    return f"{name}@{str(_latest(name)['version']).split('.')[0]}"


def _numbers(doc):
    attrs = doc.get("attrs") or {}
    out = {str(attrs.get("model", "")).strip()}
    out.update(v.strip() for v in str(attrs.get("model-variants", "")).split(","))
    return out - {""}


@pytest.mark.parametrize("name", CARDS)
def test_the_adapter_seats_the_card(name):
    bay = _latest(ADAPTER)["bays"]["mpc"]
    assert _ref(name) in bay["accepts"], f"the adapter's bay does not list {_ref(name)}"


@pytest.mark.parametrize("name", CARDS)
def test_the_card_stands_for_its_numbers(name):
    got = _numbers(_latest(name))
    missing = [n for n in CARDS[name] if n not in got]
    assert not missing, f"{name} does not name {', '.join(missing)} as its model or model-variants"


@pytest.mark.parametrize("number", NUMBERS)
def test_each_number_is_one_part(number):
    owners = sorted({r.split("@")[0] for r, _, d in components() if number in _numbers(d)})
    assert len(owners) == 1, f"{number} is named by {', '.join(owners) or 'no part'}"


def test_every_card_the_adapter_seats_fills_its_bay():
    adapter = _latest(ADAPTER)
    bay = adapter["bays"]["mpc"]
    want = (bay["size"][1], bay["size"][0])
    by_ref = {f"{r}@{str(d['version']).split('.')[0]}": d for r, _, d in components()}
    wrong = {}
    for ref in bay["accepts"]:
        size = (by_ref[ref]["size"]["w"], by_ref[ref]["size"]["h"])
        if size != want:
            wrong[ref] = size
    assert not wrong, f"cards whose face is not the bay's {want} turned: {wrong}"
