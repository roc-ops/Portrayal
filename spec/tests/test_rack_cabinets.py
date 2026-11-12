"""A cabinet is a rack product, and a reseller lists it under its own name.

Two things arrive together. The rack product format learns what a cabinet has
that an open frame has not: an enclosure (doors, side panels, a roof), a base
(casters and levelling feet) and zero-U channels with slots for a PDU's
mounting buttons. And a reseller's listing may point at a rack product as well
as at a device, so a cabinet is modelled once under its maker and listed under
the seller that sells it: the APC NetShelter SX AR3100B2, listed by FS.com.

The tests hold the shape of each new key, the rules that cross keys (L193),
the version bump each change needs, the listing rule (L56), the two exports
that result, and the first cabinet itself against what its documents print.
"""
import copy
import json
import pathlib
import sys

import pytest
import yaml
from jsonschema import Draft202012Validator

from portrayal import dcim_export, devicelock, libwalk, lint, racks_index, registry_index
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/rack-product.schema.json").read_text())

CABINET = {
    "format": 1, "kind": "rack", "name": "cab-4p", "version": "1.0.0", "maturity": "modelled",
    "manufacturer": "Acme", "model": "CAB-4P", "form": "4-post-cabinet", "ru": 42,
    "numbering": {"direction": "bottom-up", "start": 1}, "width": 19,
    "holes": {"style": "square", "size": 9.5, "fixing": "M6"},
    "rails": [{"id": "front"}, {"id": "rear", "depth": {"min": 190, "max": 781, "step": 6,
                                                         "factory": 737}}],
    "enclosure": {
        "doors": [
            {"face": "front", "leaves": 1, "kind": "perforated", "open-area": 80,
             "hinge": "left", "reversible": True, "swing": 180, "clearance": 60.96,
             "lock": "key"},
            {"face": "rear", "leaves": 2, "kind": "perforated", "open-area": 80},
        ],
        "panels": {"per-side": 2, "split": "top-bottom", "removable": True, "lock": "key"},
        "roof": {"removable": True},
    },
    "base": {"casters": 4, "levellers": 4},
    "channels": [
        {"id": "left-rear", "point": "left-rear", "where": "inside",
         "slots": {"interface": "pdu-button", "first": 213, "pitch": 311, "count": 6},
         "moves": {"front-back": True}},
        {"id": "right-rear", "point": "right-rear", "where": "inside"},
    ],
}

# What each document prints for the AR3100B2, and what the sheets leave to a stand-in.
AR3100B2 = {
    "form": "4-post-cabinet", "ru": 42, "width": 19, "model": "AR3100B2",
    "numbering": {"direction": "bottom-up", "start": 1},
    "holes": {"style": "square", "size": 9.8, "fixing": "M6"},
    "hole-centres": 465, "opening": 450,
    "rails": [{"id": "front"},
              {"id": "rear", "depth": {"min": 190, "max": 781, "step": 6, "factory": 737}}],
    "max-device-depth": 915,
    "outer": {"w": 600, "h": 1991, "d": 1070},
    "weight-kg": 130.2,
    "load": {"static-kg": 1818, "rolling-kg": 1020.58},
    "base": {"casters": 4, "levellers": 4},
}


def validator():
    return Draft202012Validator(SCHEMA)


def errors(doc):
    return [e.message for e in validator().iter_errors(doc)]


def cabinet(**kw):
    d = copy.deepcopy(CABINET)
    d.update(kw)
    return d


def findings(fn, *args):
    got = []
    real = lint.err
    lint.err = lambda path, rule, msg: got.append((rule, msg))
    try:
        fn(*args)
    finally:
        lint.err = real
    return got


def l193(doc, name=None):
    where = LIB / "racks" / "acme" / (name or doc["name"]) / "rack.yaml"
    return [m for r, m in findings(lint.lint_rack, where, doc, [str(LIB)]) if r == "L193"]


# ---- the schema --------------------------------------------------------------------

def test_a_cabinet_passes_the_schema():
    assert errors(CABINET) == []


def test_every_new_key_says_what_it_is_for():
    """The published schema is read by people with no checkout: each cabinet key
    carries a description, and none cites a file of the repository."""
    props = SCHEMA["properties"]
    for key in ("enclosure", "base", "channels"):
        assert props[key].get("description", "").strip(), key
    missing = []

    def walk(node, path):
        if isinstance(node, dict):
            if "properties" in node:
                for k, v in node["properties"].items():
                    if not (isinstance(v, dict) and v.get("description", "").strip()):
                        missing.append(f"{path}/{k}")
            for k, v in node.items():
                walk(v, f"{path}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}/{i}")

    for key in ("enclosure", "base", "channels"):
        walk(props[key], key)
    assert not missing, missing


def test_keys_no_document_states_yet_are_still_refused():
    for key in ("baying", "options", "points"):
        assert errors(cabinet(**{key: {}})), key
    for door in ({"face": "front", "leaves": 1, "kind": "perforated", "colour": "black"},):
        enc = copy.deepcopy(CABINET["enclosure"])
        enc["doors"][0] = door
        assert errors(cabinet(enclosure=enc)), door
    enc = copy.deepcopy(CABINET["enclosure"])
    enc["entries"] = [{"where": "roof", "kind": "brush"}]
    assert errors(cabinet(enclosure=enc)), "entries"
    base = {"casters": 4, "levellers": 4, "anchors": {"holes": 4}}
    assert errors(cabinet(base=base)), "anchors"


@pytest.mark.parametrize("path,value", [
    (("enclosure", "doors", 0, "face"), "side"),
    (("enclosure", "doors", 0, "leaves"), 3),
    (("enclosure", "doors", 0, "kind"), "wooden"),
    (("enclosure", "doors", 0, "open-area"), 101),
    (("enclosure", "doors", 0, "hinge"), "top"),
    (("enclosure", "doors", 0, "lock"), "padlock"),
    (("enclosure", "panels", "per-side"), 0),
    (("enclosure", "panels", "split"), "diagonal"),
    (("base", "casters"), -1),
    (("channels", 0, "point"), "front"),
    (("channels", 0, "where"), "under"),
    (("channels", 0, "slots", "pitch"), 0),
])
def test_a_value_out_of_range_is_refused(path, value):
    doc = cabinet()
    node = doc
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = value
    assert errors(doc), path


def test_a_slot_column_states_its_positions_together_or_not_at_all():
    doc = cabinet()
    doc["channels"][0]["slots"] = {"interface": "pdu-button", "pitch": 311}
    assert errors(doc)
    doc["channels"][0]["slots"] = {"interface": "pdu-button"}
    assert errors(doc) == []


def test_a_door_leaves_and_an_open_area_are_not_required():
    doc = cabinet()
    doc["enclosure"]["doors"] = [{"face": "front", "leaves": 1, "kind": "solid"}]
    assert errors(doc) == []


# ---- L193 across the new keys ----------------------------------------------------------

def test_the_good_cabinet_passes_l193():
    assert l193(CABINET) == []


def test_an_open_frame_has_no_enclosure():
    got = l193(cabinet(form="4-post-frame", name="cab-4p"))
    assert any("enclosure" in m and "cabinet" in m for m in got), got


def test_a_door_face_is_stated_once():
    doc = cabinet()
    doc["enclosure"]["doors"].append(dict(doc["enclosure"]["doors"][0]))
    assert any("front" in m and "door" in m for m in l193(doc))


def test_a_door_that_reverses_has_a_hinge_side():
    doc = cabinet()
    doc["enclosure"]["doors"][1]["reversible"] = True
    assert any("reversible" in m and "hinge" in m for m in l193(doc))


def test_a_channel_stands_at_a_point_the_form_has():
    doc = cabinet()
    doc["channels"][0]["point"] = "left"           # a two-post point, on a four-post cabinet
    assert any("left" in m and "point" in m for m in l193(doc))


def test_a_channel_id_is_unique():
    doc = cabinet()
    doc["channels"][1]["id"] = "left-rear"
    assert any("left-rear" in m and "twice" in m for m in l193(doc))


def test_a_slot_interface_is_a_registered_key():
    doc = cabinet()
    doc["channels"][0]["slots"]["interface"] = "no-such-mount"
    assert any("no-such-mount" in m for m in l193(doc))


def test_a_cabinet_estimate_needs_a_gap_of_its_own_name():
    doc = cabinet(provenance={"channels": {"confidence": "estimated", "note": "a stand-in"}})
    assert any("channels" in m and "gaps" in m for m in l193(doc))
    doc["gaps"] = [{"what": "channels", "reason": "needs-drawing", "wanted": "the drawing"}]
    assert l193(doc) == []


# ---- the lock ------------------------------------------------------------------------------

def need(old, new):
    return devicelock.rack_bump(devicelock.rack_entry(old), devicelock.rack_entry(new))


def test_a_locked_open_frame_keeps_its_entry():
    """No cabinet key, no new field in the lock: every lock on file stays as it is."""
    entry = devicelock.rack_entry(load_yaml(LIB / "racks/apc/ar203a/rack.yaml"))
    assert set(entry) == {"version", "frame", "geometry", "stated", "surface"}
    assert devicelock.check_racks(LIB) == []


def test_a_new_channel_is_a_minor_and_a_gone_one_a_major():
    one = cabinet(channels=CABINET["channels"][:1])
    assert need(one, CABINET) == "minor"
    assert need(CABINET, one) == "major"


def test_a_moved_slot_is_a_major_because_a_saved_rack_positions_against_it():
    moved = cabinet()
    moved["channels"] = copy.deepcopy(CABINET["channels"])
    moved["channels"][0]["slots"]["pitch"] = 310
    assert need(CABINET, moved) == "major"
    renamed = cabinet()
    renamed["channels"] = copy.deepcopy(CABINET["channels"])
    renamed["channels"][0]["id"] = "left"
    assert need(CABINET, renamed) == "major"


def test_a_corrected_door_figure_is_a_patch():
    doc = cabinet()
    doc["enclosure"] = copy.deepcopy(CABINET["enclosure"])
    doc["enclosure"]["doors"][0]["open-area"] = 75
    assert need(CABINET, doc) == "patch"


def test_a_cabinet_key_stated_where_there_was_none_is_a_minor_and_a_gone_one_a_major():
    bare = cabinet()
    bare.pop("base")
    assert need(bare, CABINET) == "minor"
    assert need(CABINET, bare) == "major"
    bare = cabinet()
    bare.pop("enclosure")
    assert need(bare, CABINET) == "minor"
    assert need(CABINET, bare) == "major"


# ---- the first cabinet: APC's NetShelter SX AR3100B2 ----------------------------------------

def rack(key="apc/ar3100b2"):
    return load_yaml(LIB / "racks" / key / "rack.yaml")


def test_the_ar3100b2_is_in_the_library_under_its_maker():
    assert "apc/ar3100b2" in {libwalk.rack_key(f) for f in libwalk.iter_racks([LIB])}
    doc = rack()
    assert doc["manufacturer"] == "APC" and doc["name"] == "ar3100b2"
    assert errors(doc) == []


def test_every_printed_figure_is_the_documents():
    doc = rack()
    for k, v in AR3100B2.items():
        if k == "base":
            assert doc["base"] == v
        else:
            assert doc[k] == v, k


def test_the_enclosure_is_what_the_manual_and_the_drawing_state():
    enc = rack()["enclosure"]
    front = next(d for d in enc["doors"] if d["face"] == "front")
    rear = next(d for d in enc["doors"] if d["face"] == "rear")
    assert (front["leaves"], front["kind"], front["open-area"], front["hinge"]) == \
        (1, "perforated", 80, "left")
    assert front["reversible"] is True and front["swing"] == 180 and front["clearance"] == 60.96
    assert (rear["leaves"], rear["kind"], rear["open-area"]) == (2, "perforated", 80)
    assert enc["panels"]["per-side"] == 2 and enc["panels"]["split"] == "top-bottom"
    assert enc["roof"] == {"removable": True}


def test_the_channels_are_two_rear_zero_u_channels_with_pdu_button_slots():
    chans = {c["id"]: c for c in rack()["channels"]}
    assert set(chans) == {"left-rear", "right-rear"}
    for c in chans.values():
        assert c["where"] == "inside" and c["slots"]["interface"] == "pdu-button"
        assert c["slots"]["pitch"] == 311
        assert c["moves"] == {"front-back": True}
    assert chans["left-rear"]["point"] == "left-rear" and chans["right-rear"]["point"] == "right-rear"


def test_the_channel_positions_are_declared_as_the_estimate_they_are():
    doc = rack()
    assert doc["provenance"]["channels"]["confidence"] == "estimated"
    assert any(g["what"] == "channels" for g in doc["gaps"])


def test_every_stated_key_has_a_sourced_provenance_entry():
    doc = rack()
    for key in ("ru", "form", "numbering", "width", "holes", "rails", "max-device-depth",
                "outer", "weight-kg", "load", "enclosure", "channels", "base"):
        prov = doc["provenance"].get(key)
        assert prov and prov["note"].strip() and prov["confidence"], key


def test_the_sources_disagreements_are_in_gaps():
    gaps = {g["what"]: g for g in rack()["gaps"]}
    assert gaps["load"]["reason"] == "sources-disagree"
    assert "1814" in gaps["load"]["note"] and "1818" in gaps["load"]["note"]
    assert gaps["rails"]["reason"] in {"sources-disagree", "vendor-silent"}


def test_the_ar3100b2_says_nothing_private_and_ships_no_hash():
    text = (LIB / "racks/apc/ar3100b2/rack.yaml").read_text().lower()
    for word in ("okf", "/volumes", "/home/", "/data/", "customer", "agent", "worker"):
        assert word not in text, word
    doc = rack()
    for r in doc.get("references", []) + [doc.get("datasheet", {})]:
        assert "sha256" not in r


def test_the_ar3100b2_is_locked_and_passes_its_rule():
    assert (LIB / "racks/apc/ar3100b2/rack.lock.json").exists()
    path = LIB / "racks/apc/ar3100b2/rack.yaml"
    assert [m for r, m in findings(lint.lint_rack, path, rack(), [str(LIB)])] == []
    assert devicelock.check_racks(LIB) == []


# ---- L56: a listing points at a rack product as well as at a device --------------------------

FS_LISTING = LIB / "devices/fs/ar3100b2/listing.yaml"


def listing():
    return load_yaml(FS_LISTING)


def l56(doc, where=FS_LISTING):
    return [m for r, m in findings(lint.lint_listing, where, doc, [str(LIB)]) if r == "L56"]


def test_fs_is_a_maker_and_a_reseller():
    vendors = load_yaml(ROOT / "spec/schemas/vendors.yaml")["vendors"]
    assert lint.vendor_roles(vendors["fs"]) == {"hardware", "reseller"}


def test_the_fs_listing_matches_the_listing_schema_and_l56():
    schema = json.loads((ROOT / "spec/schemas/listing.schema.json").read_text())
    doc = listing()
    assert list(Draft202012Validator(schema).iter_errors(doc)) == []
    assert doc["hardware"] == "apc/ar3100b2"
    assert l56(doc) == []


def test_the_fs_listing_names_the_item_number_as_an_alias():
    doc = listing()
    assert doc["model"] == "AR3100B2"
    assert {"name": "368069", "kind": "vendor"} == {
        k: v for k, v in next(a for a in doc["aliases"] if a["name"] == "368069").items()
        if k in ("name", "kind")}


def test_l56_names_both_kinds_of_hardware_when_it_finds_neither():
    got = l56(dict(listing(), hardware="apc/nothing"))
    assert any("not a device" in m and "rack product" in m for m in got), got


def test_a_rack_listing_has_no_configurations():
    got = l56(dict(listing(), configurations={"ac": {"model": "X"}}))
    assert any("configuration" in m and "rack" in m for m in got), got


def test_a_nos_vendor_does_not_list_a_rack(monkeypatch):
    monkeypatch.setitem(lint.VENDORS, "testnos", {"display": "Test NOS", "role": "software",
                                                  "source": "fixture"})
    where = LIB / "devices/testnos/ar3100b2/listing.yaml"
    got = l56(dict(listing(), nos="testos"), where)
    assert any("rack" in m and "reseller" in m for m in got), got


def test_a_rack_listing_may_not_name_a_nos():
    got = l56(dict(listing(), nos="arcos"))
    assert any("nos" in m for m in got), got


def test_a_listing_of_a_device_is_still_checked_as_before():
    arrcus = LIB / "devices/arrcus/as7726-32x/listing.yaml"
    assert l56(load_yaml(arrcus), arrcus) == []
    got = l56(dict(load_yaml(arrcus), configurations={"ac-sideways": {"model": "X"}}), arrcus)
    assert any("ac-sideways" in m for m in got), got


def test_the_lock_of_the_fs_listing_is_on_file():
    assert (LIB / "devices/fs/ar3100b2/listing.lock.json").exists()
    assert devicelock.check_listings(LIB) == []


# ---- the exports -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cabinet-export")
    sys_argv = sys.argv
    sys.argv = ["registry_index", "--library", str(LIB), "--out", str(tmp / "dist")]
    try:
        registry_index.main()
    finally:
        sys.argv = sys_argv
    dcim_export.export_racks(tmp / "dist", tmp / "exports")
    return tmp / "exports"


def doc_at(root, target, maker, model):
    return yaml.safe_load((root / target / "rack-types" / maker / f"{model}.yaml").read_text())


def test_the_makers_rack_type_is_exported_to_both_targets(exported):
    nb = doc_at(exported, "netbox", "APC", "AR3100B2")
    assert (nb["manufacturer"], nb["model"], nb["form_factor"]) == ("APC", "AR3100B2", "4-post-cabinet")
    assert nb["u_height"] == 42 and nb["starting_unit"] == 1 and nb["desc_units"] is False
    assert (nb["outer_width"], nb["outer_height"], nb["outer_depth"]) == (600, 1991, 1070)
    assert (nb["weight"], nb["max_weight"], nb["weight_unit"]) == (130.2, 1818, "kg")
    assert "mounting_depth" not in nb
    nt = doc_at(exported, "nautobot", "APC", "AR3100B2")
    assert nt["name"] == "APC AR3100B2" and nt["type"] == "4-post-cabinet"
    assert "static load 1818 kg" in nt["comments"] and "rolling load 1020.58 kg" in nt["comments"]


def test_the_comments_carry_what_the_rack_type_has_no_field_for(exported):
    for target in ("netbox", "nautobot"):
        text = doc_at(exported, target, "APC", "AR3100B2")["comments"]
        assert "front door: 1 leaf, perforated, 80% open, hinged left, opens 180 degrees" in text
        assert "rear door: 2 leaves, perforated, 80% open" in text
        assert "side panels: 2 per side" in text
        assert "base: 4 casters, 4 levelling feet" in text
        assert "zero-U channels: left-rear, right-rear" in text


def test_the_reseller_files_the_same_cabinet_under_its_own_name(exported):
    nb = doc_at(exported, "netbox", "FS.com", "AR3100B2")
    assert (nb["manufacturer"], nb["model"], nb["slug"]) == ("FS.com", "AR3100B2", "fs-com-ar3100b2")
    assert nb["form_factor"] == "4-post-cabinet" and nb["u_height"] == 42
    assert nb["comments"].startswith("FS.com lists APC AR3100B2.")
    assert "368069" in nb["comments"]
    assert "Listed per: " in nb["comments"]
    nt = doc_at(exported, "nautobot", "FS.com", "AR3100B2")
    assert nt["name"] == "FS.com AR3100B2" and nt["comments"].startswith("FS.com lists APC AR3100B2.")


def test_a_listed_cabinet_is_the_makers_cabinet_with_its_own_name_only(exported):
    for target in ("netbox", "nautobot"):
        own = doc_at(exported, target, "APC", "AR3100B2")
        listed = doc_at(exported, target, "FS.com", "AR3100B2")
        skip = {"manufacturer", "slug", "comments", "name"}
        assert {k: v for k, v in own.items() if k not in skip} == \
            {k: v for k, v in listed.items() if k not in skip}
        assert listed["comments"].endswith(own["comments"])


def test_an_open_frame_exports_as_it_did(exported):
    nb = doc_at(exported, "netbox", "APC", "AR203A")
    assert "comments" in nb and "listed" not in nb["comments"].lower()
    committed = LIB / "exports/netbox/rack-types/APC/AR203A.yaml"
    assert (exported / "netbox/rack-types/APC/AR203A.yaml").read_text() == committed.read_text()


def test_two_listings_under_one_seller_with_one_model_are_refused(tmp_path):
    dist = tmp_path / "dist"
    racks_index.build([LIB], dist, ROOT / "spec/schemas")
    one = {"hardware": "apc/ar3100b2", "model": "SAME", "ns": "fs", "manufacturer": "FS.com",
           "source": "a catalogue page"}
    (dist / "listings.json").write_text(json.dumps(
        {"format": 1, "listings": {"fs/one": one, "fs/two": dict(one)}}))
    with pytest.raises(SystemExit) as stop:
        dcim_export.export_racks(dist, tmp_path / "out")
    assert "SAME" in str(stop.value)


def test_a_listing_of_a_rack_that_is_not_built_exports_nothing(tmp_path):
    dist = tmp_path / "dist"
    racks_index.build([LIB], dist, ROOT / "spec/schemas")
    (dist / "listings.json").write_text(json.dumps({"format": 1, "listings": {"fs/x": {
        "hardware": "apc/not-built", "model": "X", "ns": "fs", "manufacturer": "FS.com"}}}))
    dcim_export.export_racks(dist, tmp_path / "out")
    assert not list((tmp_path / "out").glob("*/rack-types/FS.com/X.yaml"))
