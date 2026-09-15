"""The optical projection, checked against the built artefacts.

These read library/dist and library/exports rather than the contracts, because
what a DCIM consumes is the build - and the build is where the fibre graph was
missing entirely until this plan.
"""
import json
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
EXPORTS = ROOT / "library" / "exports"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import optical as O  # noqa: E402


def index():
    f = DIST / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    return {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
            for e in json.loads(f.read_text())["components"]}


def test_the_index_carries_a_connectors_positions():
    """Without this the exporter cannot count a single fibre."""
    idx = index()
    mpo = idx["common/mpo-adapter@1"]
    assert (mpo.get("optical") or {}).get("positions") == 12


def test_the_index_carries_a_modules_paths():
    idx = index()
    c = idx["fs/fhd-1mtp6lcd-os2-a@1"]
    opt = c.get("optical") or {}
    assert opt.get("media") == "os2"
    assert len(opt.get("paths") or []) == 12


def test_an_entry_with_no_optical_omits_the_key():
    """700-odd entries are not fibre; an empty dict on each is bytes for nothing."""
    idx = index()
    assert "optical" not in idx["std/pcie-bracket-fh@1"]


def test_capacities_answers_from_the_built_index():
    """The index flattens `faces` and the optical helpers do not.

    `contract_view` is the adapter. If it stops being applied, this is what
    notices - the rear face's twelve positions simply vanish from the answer.
    """
    import dcim_export as D
    idx = index()
    caps = O.capacities(D.contract_view(idx["fs/fhd-1mtp6lcd-os2-a@1"]),
                        lambda ref: idx.get(ref))
    assert caps == {"lc1": 2, "lc2": 2, "lc3": 2, "lc4": 2, "lc5": 2, "lc6": 2,
                    "rear:mtp": 12}


def test_the_cassette_is_an_orderable_module():
    """`kind` says whether it is orderable; `class` says what it is.

    The cassette declared `kind: component` with `class: module`, which is the
    two fields the wrong way round - every Smartoptics module declares
    `kind: module` with a descriptive class. The cost was silent: `Dist.modules()`
    selects on `kind`, so the part simply never reached the exporter.
    """
    idx = index()
    c = idx["fs/fhd-1mtp6lcd-os2-a@1"]
    assert c["kind"] == "module"
    assert c["class"] != "module", "`class: module` says nothing; name the thing"


def test_the_rear_face_is_not_separately_orderable():
    """A face is a drawing of the part, not a second product to order."""
    idx = index()
    assert idx["fs/fhd-1mtp6lcd-rear@1"]["kind"] == "component"


def test_a_vendor_with_no_device_can_still_ship_modules():
    import sys as _s
    _s.path.insert(0, str(ROOT / "spec/tools/portrayal"))
    from artifacts import Dist
    d = Dist(str(DIST))
    assert d.manufacturer_of("fs") == "FS.com"


def test_the_device_lookup_still_wins_over_the_registry():
    """NOT incidental. `dell` reports `Dell` from its devices and `Dell
    Technologies` from vendors.yaml; `juniper` and `edgecore` differ the same
    way. A vendors-first lookup would rename the manufacturer on several hundred
    existing export files."""
    from artifacts import Dist
    d = Dist(str(DIST))
    assert d.manufacturer_of("dell") == "Dell"
    assert d.manufacturer_of("juniper") == "Juniper"


def test_a_namespace_with_no_vendor_is_still_not_orderable():
    """`common/` and `std/` are absent from vendors.yaml, so the property
    `manufacturer_of` documents holds by data rather than by a special case."""
    from artifacts import Dist
    d = Dist(str(DIST))
    assert d.manufacturer_of("common") is None
    assert d.manufacturer_of("std") is None


def test_the_fibre_map_is_published_beside_the_two_targets():
    f = EXPORTS / "fibre-maps" / "FS.com" / "FHD-1MTP6LCDOS2A.yaml"
    if not EXPORTS.exists():
        pytest.skip("library/exports not built - run ./publish.sh --no-images")
    assert f.exists(), "no fibre map for the one cassette that has fibres"
    m = yaml.safe_load(f.read_text())
    assert len(m["rows"]) == 12
