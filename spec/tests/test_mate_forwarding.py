"""A composed cage presents the interface of the aperture it wraps (#54).

Seating an optic worked end to end and was used by ONE configuration on ONE
device, out of 7,058 ports - because on most ports it could not be written. A
port that PLACES `std/sfp-ganged` could host; a port that COMPOSES the same
aperture inside a vendor cage could not, since the checks read only the
wrapper's own `interface` and its own `mate` point.
"""
import glob
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec" / "tools" / "portrayal"))

from manifest import presented_interface  # noqa: E402


def resolve(ref):
    if not ref or "/" not in ref or "@" not in ref:
        return None
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    found = sorted(glob.glob(str(ROOT / f"library/components/{ns}/{name}/v{major}/contract.yaml")))
    return yaml.safe_load(open(found[-1])) if found else None


def contract(rel):
    return yaml.safe_load(open(ROOT / f"library/components/{rel}/contract.yaml"))


def test_a_direct_declaration_is_returned_unchanged():
    iface, at = presented_interface(contract("std/qsfp-ganged/v1"), resolve)
    assert iface == "qsfp" and at == [9.25, 4.79]


def test_a_composed_cage_forwards_its_apertures_interface():
    iface, at = presented_interface(contract("common/qsfp28-cage/v3"), resolve)
    assert iface == "qsfp", "the cage wraps std/qsfp-ganged, which presents qsfp"
    assert at == [9.5, 8.99], "the aperture's mate, offset by the part's own `at`"


def test_the_forwarded_point_is_where_the_author_already_put_it():
    """The forwarding is not a new claim about geometry. Ten of the thirteen
    wrappers already declare a connection-point at exactly this position - they
    had put the point in the right place and could not give it the name the
    mating code looks for."""
    agree = disagree = 0
    for p in sorted(glob.glob(str(ROOT / "library/components/*/*/v*/contract.yaml"))):
        d = yaml.safe_load(open(p)) or {}
        if d.get("class") != "port" or d.get("interface"):
            continue
        iface, at = presented_interface(d, resolve)
        if not iface or not at:
            continue
        own = [v["at"] for v in (d.get("connection-points") or {}).values()]
        if any(all(abs(a - b) < 0.05 for a, b in zip(o, at)) for o in own):
            agree += 1
        else:
            disagree += 1
    assert agree >= 10, f"only {agree} wrappers agree with the forwarded point"
    assert disagree <= 1, f"{disagree} wrappers disagree; investigate before relaxing"


def test_a_multi_bore_adapter_declines_rather_than_guessing():
    """`lc-duplex-adapter` composes TWO LC bores and its own point is their
    midpoint. A fibre landing on a ferrule is not a module entering a cage, and
    picking one of the two bores would be inventing which."""
    iface, at = presented_interface(contract("common/lc-duplex-adapter/v3"), resolve)
    assert iface is None and at is None


def test_the_optical_form_factors_can_all_host():
    """Every optical aperture in the library presents an interface, so nothing
    blocks an optic being seated once the optic itself is modelled."""
    want = {"sfp", "qsfp", "qsfp-dd", "xfp", "cfp", "cfp2", "cxp"}
    presented = set()
    for p in glob.glob(str(ROOT / "library/components/*/*/v*/contract.yaml")):
        d = yaml.safe_load(open(p)) or {}
        if d.get("class") != "port":
            continue
        iface, at = presented_interface(d, resolve)
        if iface and at:
            presented.add(iface)
    missing = sorted(want - presented)
    assert not missing, f"no port presents {missing}"


def test_the_two_modelled_optics_have_a_cage_that_will_take_them():
    """Both directions of the join: an optic's `mates` must be presented by
    something, or the optic can never be seated anywhere."""
    presented = set()
    for p in glob.glob(str(ROOT / "library/components/*/*/v*/contract.yaml")):
        d = yaml.safe_load(open(p)) or {}
        if d.get("class") == "port":
            iface, at = presented_interface(d, resolve)
            if iface and at:
                presented.add(iface)
    for p in glob.glob(str(ROOT / "library/components/*/*/v*/contract.yaml")):
        d = yaml.safe_load(open(p)) or {}
        if d.get("class") != "transceiver" or not d.get("mates"):
            continue
        assert d["mates"] in presented, \
            f"{d['name']} mates {d['mates']!r} and no port presents it"
