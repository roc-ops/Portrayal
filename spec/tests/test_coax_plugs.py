"""The generic coax plugs (#650, docs/connectors-coax-design.md section 5).

Each is the #621 cable-end shape seen from the face: a coupling part, a
strain relief `cyl`, and a 30 mm stub `cyl` sized by `cable-od`, with the
`cable` point on the stub's far end.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# plug -> (interface it mates, default cable-od, the jack it seats in)
PLUGS = {
    "generic/sma-plug@1": ("sma", 2.49, "std/sma@1"),
    "generic/smb-plug@1": ("smb", 2.49, "std/smb@1"),
    "generic/mcx-plug@1": ("mcx", 2.49, "std/mcx@1"),
}
EACH = pytest.mark.parametrize("ref", sorted(PLUGS))
NODES = ("coupling", "relief-boot", "stub")


def doc(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / f"components/{ns}/{name}/v{major}/contract.yaml").read_text())


def skin(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return (LIB / f"components/{ns}/{name}/v{major}/skins/default.svg").read_text()


@EACH
def test_it_is_a_plug_that_mates_its_interface(ref):
    d = doc(ref)
    assert d["class"] == "port" and "behaviour" not in d
    assert d["mates"] == PLUGS[ref][0]
    assert d["conforms"] == f"{PLUGS[ref][0]}-plug"


@EACH
def test_its_fields_are_the_cable(ref):
    f = doc(ref)["fields"]
    assert set(f) == {"cable-od", "jacket-color"}
    assert f["cable-od"]["default"] == pytest.approx(PLUGS[ref][1], abs=0.1)


@EACH
def test_a_generic_states_no_impedance(ref):
    if PLUGS[ref][0] == "f-type":
        assert doc(ref)["attrs"]["impedance"] == 75
    else:
        assert "impedance" not in (doc(ref).get("attrs") or {})


@EACH
def test_the_stub_is_30_long_from_the_end_of_the_relief(ref):
    feats = {f["node"]: f for f in doc(ref)["relief"]["features"]}
    boot, stub = feats["relief-boot"], feats["stub"]
    assert stub["cyl"] == pytest.approx(30)
    assert stub["lift"] == pytest.approx(boot["lift"] + boot["cyl"])


@EACH
def test_the_cable_leaves_from_the_stub(ref):
    cps = doc(ref)["connection-points"]
    assert cps["cable"]["on"] == "stub"
    assert "mate" in cps


@EACH
def test_the_stub_circle_is_bound_to_the_fields(ref):
    s = skin(ref)
    for node in NODES:
        assert f'id="{node}"' in s, node
    stub = s[s.index('id="stub"'):].split("/>", 1)[0]
    assert 'data-r-from="cable-od"' in stub
    assert 'data-fill-from="jacket-color"' in stub
    r = float(stub.split('r="', 1)[1].split('"', 1)[0])
    assert r == pytest.approx(PLUGS[ref][1] / 2, abs=0.05)
