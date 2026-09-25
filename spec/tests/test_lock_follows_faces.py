"""A part seen from another direction is drawn, so its device's lock must see it.

`_composed` walked every part and every shipped default, transitively, and never
followed `faces:` - the key a module uses to name its OTHER drawings: a
cassette's back (`faces.rear`, drawn by the build as the rear projection of the
seated module) and a riser's top view (`faces.plan`, or the legacy `plan:`,
landed in a device's plan view). So a cassette's rear could be redrawn and no
device that seats the cassette re-locked.

Found in review, and not hypothetically: the FS FHD rears' MPO bulkhead openings
went from 13.1 x 7.0 to 12.9 x 8.0 and fs/fhd-1ufce, which seats every one of
those cassettes, stayed at 3.2.4 while devicelock reported 0 findings - the
silent redraw roc-ops/Portrayal#405 exists to prevent.
"""
import json
import pathlib
import shutil

import yaml

from portrayal import devicelock as dl
from portrayal import manifest
from portrayal.faces import DIRECTIONS, face_ref

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

SKIN = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<rect id="body" x="0" y="0" width="10" height="10" fill="#aaa"/></svg>')


def _component(lib, ref, extra=""):
    base, _, major = ref.partition("@")
    vendor, name = base.split("/")
    d = lib / "components" / vendor / name / f"v{major}"
    (d / "skins").mkdir(parents=True)
    (d / "contract.yaml").write_text(
        f"format: 1\nkind: module\nname: {name}\nversion: 1.0.0\nclass: psu\n"
        "size: {w: 10.0, h: 10.0}\nstates: [absent]\nskins: [default]\n" + extra)
    (d / "skins" / "default.svg").write_text(SKIN)
    return d


def _device(lib, seats):
    doc = {
        "format": 1, "kind": "device", "name": "thing", "version": "1.0.0",
        "manufacturer": "Acme", "model": "Thing",
        "chassis": {"width": 100.0, "height": 44.0, "depth": 200.0, "ru": 1},
        "groups": {"slots": {"term": "Slot", "index-origin": 1}},
        "views": {"front": {"size": {"w": 100.0, "h": 44.0}, "components": {
            "bays": [{"id": "slot-1", "at": [0, 0], "size": {"w": 10.0, "h": 10.0},
                      "group": "slots", "accepts": [seats], "default": seats}]}}},
    }
    d = lib / "devices" / "acme" / "thing"
    d.mkdir(parents=True)
    (d / "device.yaml").write_text(yaml.safe_dump(doc))
    return doc


def _cassette_library(tmp_path, faces_block):
    """A module whose other drawing composes a part of its own - the shape of an
    FHD cassette: front, `faces.rear` -> a back, and a bulkhead on the back."""
    lib = tmp_path / "library"
    _component(lib, "acme/cassette@1", faces_block)
    _component(lib, "acme/cassette-back@1",
               "parts:\n  - {id: mtp1, ref: acme/bulkhead@1, at: [0, 0]}\n")
    _component(lib, "acme/bulkhead@1")
    doc = _device(lib, "acme/cassette@1")
    return lib, doc


def _redraw(lib, ref):
    base, _, major = ref.partition("@")
    vendor, name = base.split("/")
    skin = lib / "components" / vendor / name / f"v{major}" / "skins" / "default.svg"
    skin.write_text(SKIN.replace('fill="#aaa"', 'fill="#c0453f"'))


def _unbumped(lib):
    return [f for f in dl.check(lib) if f[1] == "unbumped"]


def test_a_redrawn_rear_is_a_finding_on_the_device_that_seats_the_module(tmp_path):
    lib, _ = _cassette_library(tmp_path, "faces:\n  rear: {ref: acme/cassette-back@1}\n")
    dl.update(lib)
    assert dl.check(lib) == []
    _redraw(lib, "acme/cassette-back@1")
    found = _unbumped(lib)
    assert found, "the cassette's back was redrawn and its device said nothing"
    assert "acme/cassette-back@1" in found[0][2], found


def test_a_part_on_the_rear_is_followed_too(tmp_path):
    """TRANSITIVELY, the same way parts are: the bulkhead is two hops from the
    device and one of them is a face."""
    lib, _ = _cassette_library(tmp_path, "faces:\n  rear: {ref: acme/cassette-back@1}\n")
    dl.update(lib)
    _redraw(lib, "acme/bulkhead@1")
    found = _unbumped(lib)
    assert found and "acme/bulkhead@1" in found[0][2], found


def test_the_legacy_plan_spelling_is_followed(tmp_path):
    """`plan:` means exactly `faces.plan` (faces.py), and eleven risers still
    spell it that way - a walk that read only `faces:` would miss every one."""
    lib, doc = _cassette_library(tmp_path, "plan: {ref: acme/cassette-back@1}\n")
    refs = dl.entry(doc, dl.component_versions(lib))["composed-refs"]
    assert {"acme/cassette-back@1", "acme/bulkhead@1"} <= set(refs), refs


def test_a_module_with_no_faces_composes_what_it_did(tmp_path):
    """Nothing else about the walk moves: no face, no new refs."""
    lib, doc = _cassette_library(tmp_path, "")
    refs = dl.entry(doc, dl.component_versions(lib))["composed-refs"]
    assert set(refs) == {"acme/cassette@1"}, refs


def test_every_face_a_device_reaches_is_in_what_it_composes():
    """THE LIBRARY, NOT A FIXTURE. For every device, every face of every part it
    composes is itself composed - and the census counts what it checked, so an
    empty walk cannot pass it."""
    versions = dl.component_versions(LIB)
    checked, missing = 0, []
    for path in dl.device_files(LIB):
        doc = manifest.load_yaml(path) or {}
        refs = dl.entry(doc, versions)["composed-refs"]
        for ref in refs:
            base, _, major = ref.partition("@")
            ct = LIB / "components" / base / f"v{major}" / "contract.yaml"
            if not ct.exists():
                continue
            contract = manifest.load_yaml(ct) or {}
            for d in DIRECTIONS:
                face = face_ref(contract, d)
                if face:
                    checked += 1
                    if face not in refs:
                        missing.append((dl.slug(path, LIB), ref, d, face))
    assert checked > 0, "no device reached a face - the census measured nothing"
    assert not missing, f"{len(missing)} face(s) unfollowed, e.g. {missing[:3]}"


def test_fhd_1ufce_sees_a_redrawn_flange_adapter(tmp_path):
    """The case that found it, on a copy of the real library: the MPO flange
    adapter is reached from fs/fhd-1ufce only through its cassettes' rears."""
    lib = tmp_path / "library"
    shutil.copytree(LIB / "components", lib / "components")
    shutil.copytree(LIB / "devices" / "fs" / "fhd-1ufce",
                    lib / "devices" / "fs" / "fhd-1ufce")
    dl.update(lib)
    assert dl.check(lib) == []
    skin = next((lib / "components" / "common" / "mpo-flange-adapter" / "v2"
                 / "skins").glob("*.svg"))
    skin.write_text(skin.read_text() + "<!-- redrawn -->")
    found = _unbumped(lib)
    assert [n for n, _, _ in found] == ["fs/fhd-1ufce"], found
    assert "common/mpo-flange-adapter@2" in found[0][2], found
