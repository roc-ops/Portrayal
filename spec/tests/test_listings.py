"""#674: a NOS vendor LISTS the hardware it supports.

NetBox and Nautobot file a disaggregated box once per manufacturer that sells
it - UfiSpace's S9510-28DC, and Arrcus's, and IP Infusion's. A listing is that
entry: `devices/<nos vendor>/<id>/listing.yaml`, pointing at one device and
carrying only what the NOS vendor changes. These tests hold the shape, the two
lint rules that keep a listing honest about its hardware (L56) and its names
(L124), the lock that versions it, and that it stays out of every walk that
means "the metal".
"""
import copy
import json
import pathlib

from jsonschema import Draft202012Validator

from portrayal import devicelock, lint, libwalk
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/listing.schema.json").read_text())
ARRCUS = LIB / "devices/arrcus/as7726-32x/listing.yaml"


def findings(fn, *args):
    got = []
    real = lint.err
    lint.err = lambda path, rule, msg: got.append((rule, msg))
    try:
        fn(*args)
    finally:
        lint.err = real
    return got


# ---- shape -------------------------------------------------------------------

def test_every_listing_in_the_library_matches_the_schema():
    v = Draft202012Validator(SCHEMA)
    files = libwalk.iter_listings([LIB])
    assert files, "no listing to validate; this test proved nothing"
    for f in files:
        errors = [e.message for e in v.iter_errors(load_yaml(f))]
        assert not errors, (f, errors)


def test_a_listing_must_say_where_the_vendor_lists_it():
    doc = copy.deepcopy(load_yaml(ARRCUS))     # load_yaml caches: never mutate its answer
    doc.pop("source")
    assert list(Draft202012Validator(SCHEMA).iter_errors(doc))


def test_the_old_identity_block_is_gone():
    """`identity:` on an overlay was the first answer to this; a listing is
    the whole answer, and the two must not coexist."""
    doc = dict(load_yaml(ARRCUS), identity={"vendor": "arrcus"})
    assert list(Draft202012Validator(SCHEMA).iter_errors(doc))
    assert not (ROOT / "spec/schemas/overlay.schema.json").exists()
    assert not list(LIB.glob("devices/*/*/overlays"))


# ---- walks -------------------------------------------------------------------

def test_a_listing_is_in_no_device_walk():
    """A listing draws nothing. It must not be rendered, device-locked, or
    counted in a device census - so it is not a device.yaml."""
    devices = {str(p.parent) for p in libwalk.iter_devices([LIB])}
    for f in libwalk.iter_listings([LIB]):
        assert str(f.parent) not in devices
        assert libwalk.listing_key(f) == f"{f.parent.parent.name}/{f.parent.name}"


# ---- L56: the hardware and the registry agree --------------------------------

def test_the_library_passes_l56():
    for f in libwalk.iter_listings([LIB]):
        assert not findings(lint.lint_listing, f, load_yaml(f), [str(LIB)]), f


def test_l56_refuses_a_port_the_metal_has_not_got():
    doc = copy.deepcopy(load_yaml(ARRCUS))
    doc["interfaces"][0]["range"] = "1-33"
    got = findings(lint.lint_listing, ARRCUS, doc, [str(LIB)])
    assert any(r == "L56" and "port-33" in m for r, m in got), got


def test_l56_refuses_a_component_the_metal_has_not_got():
    doc = copy.deepcopy(load_yaml(ARRCUS))
    doc["entity-map"].append({"match": "fan9", "to": "fan-9"})
    got = findings(lint.lint_listing, ARRCUS, doc, [str(LIB)])
    assert any(r == "L56" and "fan-9" in m for r, m in got), got


def test_l56_refuses_a_configuration_the_hardware_does_not_have():
    doc = dict(load_yaml(ARRCUS), configurations={"ac-sideways": {"model": "X"}})
    got = findings(lint.lint_listing, ARRCUS, doc, [str(LIB)])
    assert any(r == "L56" and "ac-sideways" in m for r, m in got), got


def test_l56_refuses_hardware_that_is_not_modelled():
    doc = dict(load_yaml(ARRCUS), hardware="ufispace/nothing")
    got = findings(lint.lint_listing, ARRCUS, doc, [str(LIB)])
    assert any(r == "L56" and "not a device" in m for r, m in got), got


def test_l56_refuses_a_listing_under_a_hardware_vendor():
    """Edgecore files its own box under its own `manufacturer:`. A listing
    under edgecore/ would be a second copy of the metal's own entry."""
    where = LIB / "devices/edgecore/as7726-32x/listing.yaml"
    got = findings(lint.lint_listing, where, load_yaml(ARRCUS), [str(LIB)])
    assert any(r == "L56" and "role 'hardware'" in m for r, m in got), got


# ---- L124: one name, one box, per vendor -------------------------------------

def _two(tmp_path, a, b):
    """Two listings under drivenets/ in a scratch library."""
    for name, doc in (("s9700-53dx", a), ("cor550", b)):
        d = tmp_path / "devices" / "drivenets" / name
        d.mkdir(parents=True)
        (d / "listing.yaml").write_text(json.dumps(doc))
    return [str(tmp_path)]


def test_l124_refuses_two_listings_exporting_one_model(tmp_path):
    """DriveNets certifies the NCP-40C on a UfiSpace box and an Edgecore one.
    Both exporting `NCP-40C` would write one DCIM file twice."""
    a = {"configurations": {"ac": {"model": "NCP-40C"}}}
    b = {"configurations": {"dc": {"part-numbers": {"NCP-40C": {}}}}}
    got = findings(lint.lint_library_listings, _two(tmp_path, a, b))
    assert any(r == "L124" and "ncp-40c" in m for r, m in got), got


def test_l124_lets_two_listings_share_a_display_name(tmp_path):
    """The vendor's name for the box may cover two - what must differ is
    what a DCIM keys on."""
    a = {"model": "NCP-40C", "configurations": {"ac": {"model": "NCP-40C-U"}}}
    b = {"model": "NCP-40C", "configurations": {"ac": {"model": "NCP-40C-E"}}}
    assert not findings(lint.lint_library_listings, _two(tmp_path, a, b))


def test_l124_holds_an_alias_to_one_listing_unless_shared(tmp_path):
    a = {"aliases": [{"name": "NCP-96X6C-S", "kind": "oem"}]}
    got = findings(lint.lint_library_listings, _two(tmp_path, a, copy.deepcopy(a)))
    assert any(r == "L124" and "ncp-96x6c-s" in m for r, m in got), got
    s = {"aliases": [{"name": "NCP-96X6C-S", "kind": "oem", "shared": True}]}
    assert not findings(lint.lint_library_listings,
                        _two(tmp_path / "s", s, copy.deepcopy(s)))


# ---- the lock ----------------------------------------------------------------

def test_every_listing_is_locked_and_the_lock_agrees():
    assert not [f for f in devicelock.check_listings(LIB)], devicelock.check_listings(LIB)
    for f in libwalk.iter_listings([LIB]):
        assert (f.parent / devicelock.LISTING_LOCK_NAME).exists(), f


def test_a_renamed_port_is_a_major_change():
    doc = load_yaml(ARRCUS)
    old = devicelock.listing_entry(doc)
    new = copy.deepcopy(doc)
    new["interfaces"][1]["name"] = "eth0"
    assert devicelock.listing_bump(old, devicelock.listing_entry(new)) == "major"


def test_an_added_configuration_override_is_minor_and_a_changed_one_major():
    doc = load_yaml(ARRCUS)
    old = devicelock.listing_entry(doc)
    added = dict(doc, configurations={"ac-f2b": {"part-numbers": {"X": {"part": "X"}}}})
    assert devicelock.listing_bump(old, devicelock.listing_entry(added)) == "minor"
    changed = dict(doc, configurations={"ac-f2b": {"part-numbers": {"Y": {"part": "Y"}}}})
    assert devicelock.listing_bump(devicelock.listing_entry(added),
                                   devicelock.listing_entry(changed)) == "major"


def test_a_reworded_source_is_a_patch():
    doc = load_yaml(ARRCUS)
    old = devicelock.listing_entry(doc)
    new = dict(doc, source=doc["source"] + " Reworded.")
    assert devicelock.listing_bump(old, devicelock.listing_entry(new)) == "patch"
