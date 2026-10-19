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


# ---- L56: a reseller lists hardware it sells, with no NOS --------------------

HW = "edgecore/as7726-32x"


def _reseller(monkeypatch, role="reseller", slug="testshop"):
    """A fixture vendor in the registry lint reads, and where its listing sits."""
    monkeypatch.setitem(lint.VENDORS, slug, {"display": "Test Shop", "role": role,
                                             "source": "fixture"})
    return LIB / "devices" / slug / "as7726-32x" / "listing.yaml"


def _resold():
    """What a reseller may say: its part number, names, catalogue words, source."""
    return {"format": 1, "kind": "listing", "hardware": HW, "version": "1.0.0",
            "model": "TS-7726", "aliases": [{"name": "TS 7726", "kind": "vendor"}],
            "portfolio": {"line": "Switches", "family": "Leaf"},
            "source": "Test Shop catalogue, TS-7726 page"}


def test_a_reseller_listing_lints_clean_and_matches_the_schema(monkeypatch):
    where, doc = _reseller(monkeypatch), _resold()
    assert not list(Draft202012Validator(SCHEMA).iter_errors(doc))
    assert not findings(lint.lint_listing, where, doc, [str(LIB)])


def test_a_reseller_listing_may_not_name_a_nos(monkeypatch):
    where = _reseller(monkeypatch)
    for key, value in (("nos", "arcos"), ("nos-versions", ">=7.0"),
                       ("interfaces", [{"physical": "mgmt-eth", "name": "eth0"}])):
        doc = dict(_resold(), **{key: value})
        if key == "nos-versions":
            doc["nos"] = "arcos"
        got = findings(lint.lint_listing, where, doc, [str(LIB)])
        assert any(r == "L56" and key in m and "reseller" in m for r, m in got), (key, got)


def test_a_nos_listing_still_needs_its_nos(monkeypatch):
    where = _reseller(monkeypatch, role="software")
    got = findings(lint.lint_listing, where, _resold(), [str(LIB)])
    assert any(r == "L56" and "`nos`" in m for r, m in got), got


def test_a_nos_listing_under_a_software_vendor_is_unchanged(monkeypatch):
    where = _reseller(monkeypatch, role="software")
    assert not findings(lint.lint_listing, where, dict(_resold(), nos="arcos"), [str(LIB)])


def test_l56_still_refuses_a_listing_under_a_hardware_only_vendor(monkeypatch):
    where = _reseller(monkeypatch, role="hardware")
    got = findings(lint.lint_listing, where, _resold(), [str(LIB)])
    assert any(r == "L56" and "reseller" in m and "role 'hardware'" in m for r, m in got), got


def test_a_maker_that_also_resells_is_a_vendor_and_a_reseller(monkeypatch):
    """FS makes hardware this library models and will resell APC's: one entry,
    `role: [hardware, reseller]`. Its namespace passes L55 and its listing L56."""
    where = _reseller(monkeypatch, role=["hardware", "reseller"])
    assert not findings(lint.lint_listing, where, _resold(), [str(LIB)])
    assert lint.vendor_roles(lint.VENDORS["testshop"]) == {"hardware", "reseller"}
    # a maker-and-reseller is not a NOS vendor: it may not list a NOS
    got = findings(lint.lint_listing, where, dict(_resold(), nos="arcos"), [str(LIB)])
    assert any(r == "L56" and "nos" in m for r, m in got), got


def test_a_maker_that_also_resells_passes_l55(monkeypatch, tmp_path):
    monkeypatch.setitem(lint.VENDORS, "testshop", {"display": "Test Shop",
                        "role": ["hardware", "reseller"], "source": "fixture"})
    (tmp_path / "devices" / "testshop").mkdir(parents=True)
    got = []
    real = lint.warn
    lint.warn = lambda path, rule, msg: got.append((rule, msg))
    try:
        lint.lint_vendor_registry(tmp_path)
    finally:
        lint.warn = real
    assert not [g for g in got if "testshop" in g[1]], got


def test_vendor_roles_reads_a_string_or_a_list():
    assert lint.vendor_roles({"role": "both"}) == {"hardware", "software"}
    assert lint.vendor_roles({"role": "software"}) == {"software"}
    assert lint.vendor_roles({"role": ["hardware", "reseller"]}) == {"hardware", "reseller"}
    assert lint.vendor_roles(None) == set()


def test_a_reseller_export_is_named_seller_slash_part():
    """`<seller display>/<part>`, with the comments a NOS listing gets less the
    NOS line."""
    from portrayal import dcim_export as dx
    listing = dict(_resold(), ns="testshop", manufacturer="Test Shop",
                   configurations={"ac": {"part-numbers": {"TS-7726-AC": {"part": "TS-7726-AC"}}}})
    doc = {"manufacturer": "Edgecore", "model": "7726-32X-O-AC-F", "slug": "edgecore-x",
           "comments": "Maker note."}
    out = dx.apply_listing(doc, listing, "ac")
    assert (out["manufacturer"], out["model"]) == ("Test Shop", "TS-7726-AC")
    assert dx.manufacturer_dir(out["manufacturer"]) + "/" + out["model"] == "Test Shop/TS-7726-AC"
    lines = out["comments"].split("\n")
    assert lines[0] == "Test Shop lists Edgecore 7726-32X-O-AC-F."
    assert lines[1] == "Test Shop also calls it: TS-7726, TS 7726."
    assert lines[2].startswith("Listed per: Test Shop catalogue")
    assert "NOS" not in out["comments"]
    assert out["comments"].endswith("Maker note.")


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


def test_l124_asks_the_exporter_which_sku_a_configuration_exports(tmp_path):
    """`{A-EU: cord EU, Y: none}` exports as Y - the cordless one. Lint used to
    check A-EU, so a second listing calling its box Y collided unseen."""
    a = {"configurations": {"ac": {"part-numbers": {"A-EU": {"power-cord": "EU"}, "Y": {}}}}}
    b = {"configurations": {"ac": {"model": "Y"}}}
    got = findings(lint.lint_library_listings, _two(tmp_path, a, b))
    assert any(r == "L124" and "'y'" in m for r, m in got), got


def test_l124_sees_an_override_that_takes_another_boxs_sku(tmp_path):
    """Across hardware: one listing renames its box to a SKU another listing
    of the same vendor inherits from its own hardware."""
    lib = tmp_path
    for ns, name, pn in (("ufispace", "hw-a", "SKU-A"), ("edgecore", "hw-b", "SKU-B")):
        hd = lib / "devices" / ns / name
        hd.mkdir(parents=True)
        (hd / "device.yaml").write_text(json.dumps(
            {"kind": "device", "configurations": {"ac": {"part-numbers": {pn: {}}}}}))
    a = {"hardware": "ufispace/hw-a", "configurations": {"ac": {"model": "SKU-B"}}}
    b = {"hardware": "edgecore/hw-b"}
    got = findings(lint.lint_library_listings, _two(lib, a, b))
    assert any(r == "L124" and "sku-b" in m for r, m in got), got


def test_l124_holds_an_alias_to_one_listing_unless_shared(tmp_path):
    a = {"aliases": [{"name": "NCP-96X6C-S", "kind": "oem"}]}
    got = findings(lint.lint_library_listings, _two(tmp_path, a, copy.deepcopy(a)))
    assert any(r == "L124" and "ncp-96x6c-s" in m for r, m in got), got
    s = {"aliases": [{"name": "NCP-96X6C-S", "kind": "oem", "shared": True}]}
    assert not findings(lint.lint_library_listings,
                        _two(tmp_path / "s", s, copy.deepcopy(s)))


def test_l124_needs_every_claimant_to_mark_a_shared_alias(tmp_path):
    s = {"aliases": [{"name": "NCP-96X6C-S", "kind": "oem", "shared": True}]}
    u = {"aliases": [{"name": "NCP-96X6C-S", "kind": "oem"}]}
    got = findings(lint.lint_library_listings, _two(tmp_path, s, u))
    assert any(r == "L124" and "ncp-96x6c-s" in m for r, m in got), got


def test_l124_checks_configuration_aliases_too(tmp_path):
    a = {"configurations": {"ac": {"aliases": [{"name": "NCP-40C-AC", "kind": "oem"}]}}}
    got = findings(lint.lint_library_listings, _two(tmp_path, a, copy.deepcopy(a)))
    assert any(r == "L124" and "ncp-40c-ac" in m for r, m in got), got


def test_l56_refuses_an_override_on_an_illustration(tmp_path):
    # The AS7726-32X ships no `kind: example` configuration, so the test gives a
    # copy of it one rather than skipping: a skip here would leave the rule
    # untested for as long as the real box has none.
    import shutil
    lib = tmp_path / "library"
    shutil.copytree(LIB / "devices/edgecore/as7726-32x", lib / "devices/edgecore/as7726-32x")
    dev = lib / "devices/edgecore/as7726-32x/device.yaml"
    hw = load_yaml(dev)
    base = next(iter(hw["configurations"]))
    hw["configurations"]["illustration"] = {
        **copy.deepcopy(hw["configurations"][base]), "kind": "example"}
    hw["configurations"]["illustration"].pop("part-numbers", None)
    dev.write_text(json.dumps(hw))
    doc = dict(load_yaml(ARRCUS), configurations={"illustration": {"model": "X"}})
    got = findings(lint.lint_listing, ARRCUS, doc, [str(lib)])
    assert any(r == "L56" and "example" in m for r, m in got), got


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


def test_an_override_that_renames_an_export_is_major_even_when_added():
    """An added `model` or `part-numbers` renames that configuration's exported
    type - `Arrcus/7726-32X-O-AC-F` becomes `NCP-...` - which removes a device
    type a DCIM keys on. That is major however it arrives."""
    doc = load_yaml(ARRCUS)
    old = devicelock.listing_entry(doc)
    renamed = dict(doc, configurations={"ac-f2b": {"part-numbers": {"X": {"part": "X"}}}})
    assert devicelock.listing_bump(old, devicelock.listing_entry(renamed)) == "major"
    changed = dict(doc, configurations={"ac-f2b": {"part-numbers": {"Y": {"part": "Y"}}}})
    assert devicelock.listing_bump(devicelock.listing_entry(renamed),
                                   devicelock.listing_entry(changed)) == "major"


def test_an_override_with_only_prose_is_minor_and_rewording_it_a_patch():
    doc = load_yaml(ARRCUS)
    old = devicelock.listing_entry(doc)
    added = dict(doc, configurations={"ac-f2b": {"description": "the AC build"}})
    assert devicelock.listing_bump(old, devicelock.listing_entry(added)) == "minor"
    reworded = dict(doc, configurations={"ac-f2b": {"description": "the AC one"}})
    assert devicelock.listing_bump(devicelock.listing_entry(added),
                                   devicelock.listing_entry(reworded)) == "patch"


def test_a_deleted_listing_leaves_a_finding_until_its_lock_goes(tmp_path):
    d = tmp_path / "devices" / "arrcus" / "gone"
    d.mkdir(parents=True)
    (d / devicelock.LISTING_LOCK_NAME).write_text("{}")
    got = devicelock.check_listings(tmp_path)
    assert [k for k, kind, _ in got if kind == "removed"] == ["arrcus/gone"], got
    devicelock.update_listings(tmp_path)
    assert not (d / devicelock.LISTING_LOCK_NAME).exists()


def test_a_listing_without_type_name_keeps_its_fingerprint():
    """`type-name` joined the names bucket later; a listing that does not set
    it must hash as it always did, or every existing lock moves at once."""
    doc = load_yaml(ARRCUS)
    assert "type-name" not in doc
    assert devicelock.listing_entry(doc)["names"] == \
        devicelock._digest({k: doc.get(k) for k in devicelock.LISTING_NAMES})
    renamed = dict(doc, **{"type-name": "{model} ({sku})"})
    assert devicelock.listing_bump(devicelock.listing_entry(doc),
                                   devicelock.listing_entry(renamed)) == "major"


def test_a_type_name_must_keep_the_sku():
    doc = dict(load_yaml(ARRCUS), **{"type-name": "NCP-40C"})
    assert list(Draft202012Validator(SCHEMA).iter_errors(doc))


def test_a_reworded_source_is_a_patch():
    doc = load_yaml(ARRCUS)
    old = devicelock.listing_entry(doc)
    new = dict(doc, source=doc["source"] + " Reworded.")
    assert devicelock.listing_bump(old, devicelock.listing_entry(new)) == "patch"
