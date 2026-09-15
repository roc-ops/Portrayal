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


# ---------------------------------------------------------------------------
# Section D's library-wide sweeps.
#
# `fibre_modules(idx)` selects on `optical.paths` and `kind == "module"`, which
# is every module carrying a fibre graph - the one FS cassette AND the six
# Smartoptics PPM modules (ppm-dcm-10/20/40/80, ppm-ocu-50-50, ppm-ocu-97-3)
# whose connectors are all on one faceplate and whose paths run front-to-front
# (`common.1 -> split.1/2`, never a `rear:`-prefixed endpoint). Those six
# declare no `faces.rear`, so `build_module`/`export_modules` in dcim_export.py
# deliberately export no front-ports, no rear-ports and no fibre map for them:
# nothing in the vocabulary says which of their endpoints is the trunk, and
# netbox#21830 refuses front ports without rear ports.
#
# So every sweep below is scoped to `projecting_modules(idx)` - modules that
# declare a rear face, via the SAME accessor the exporter uses
# (`dcim_export.contract_view` + `faces.face_ref(view, "rear")`) - rather than
# the raw `fibre_modules` selection, which would fail every one of them.
def fibre_modules(idx):
    return [e for e in idx.values()
            if (e.get("optical") or {}).get("paths") and e.get("kind") == "module"]


def projecting_modules(idx):
    """`fibre_modules`, narrowed to those the exporter actually projects.

    Uses `dcim_export.contract_view` + `faces.face_ref(view, "rear")` - the
    same accessor `build_module`/`export_modules` gate on - never the raw
    flattened `faces` shape the index carries.
    """
    import dcim_export as D
    from faces import face_ref
    out = []
    for e in fibre_modules(idx):
        view = D.contract_view(e)
        if face_ref(view, "rear"):
            out.append(e)
    return out


def test_the_sweep_finds_fibre_modules_at_all():
    """Guard the guard: every sweep below passes vacuously on an empty list."""
    assert fibre_modules(index()), "no fibre modules found - the sweeps are vacuous"


def test_the_populations_split_as_the_controller_ruling_expects():
    """Pin the ruling with a number, not merely an assertion that passes.

    Seven modules carry `optical.paths` today: one FS cassette with a declared
    rear face, and six Smartoptics PPMs with none. A future cassette that joins
    the library moves one of these two counts, and this is what a reviewer
    notices moving.
    """
    idx = index()
    all_fibre = fibre_modules(idx)
    projecting = projecting_modules(idx)
    excluded = [e["name"] for e in all_fibre if e not in projecting]
    assert len(all_fibre) == 7, sorted(e["name"] for e in all_fibre)
    assert len(projecting) == 1, [e["name"] for e in projecting]
    assert sorted(excluded) == sorted([
        "ppm-dcm-10", "ppm-dcm-20", "ppm-dcm-40", "ppm-dcm-80",
        "ppm-ocu-50-50", "ppm-ocu-97-3",
    ]), excluded


def test_a_fibre_module_with_no_rear_face_exports_nothing_optical():
    """The controller ruling, pinned by a test rather than merely implemented.

    A fibre module with no declared rear face - the six Smartoptics PPMs, whose
    connectors are all on one faceplate and whose paths run front-to-front - is
    NOT a smaller, degenerate case of the exporter's usual output: it must
    produce no front-ports, no rear-ports and no fibre map at all, because
    nothing in the vocabulary says which of its endpoints is the trunk.
    """
    import dcim_export as D
    idx = index()
    all_fibre = fibre_modules(idx)
    projecting = projecting_modules(idx)
    unfaced = [e for e in all_fibre if e not in projecting]
    assert unfaced, "no unfaced fibre module found - this guard is vacuous"
    for e in unfaced:
        # build_module takes the RAW entry, not contract_view's shape - it
        # calls contract_view(contract) internally to do its own rear-face gate.
        doc = D.build_module(e, "Smartoptics", idx.get)
        assert "front-ports" not in doc, e["name"]
        assert "rear-ports" not in doc, e["name"]
        if EXPORTS.exists():
            model = str((e.get("attrs") or {}).get("model") or e["name"])
            hits = list((EXPORTS / "fibre-maps").rglob(
                model.replace("/", "-") + ".yaml"))
            assert not hits, f"{model}: fibre map exported with no rear face"


def test_every_fibre_module_exports_ports_matching_its_graph():
    """Section D: the count a module exports equals the count its graph carries."""
    import dcim_export as D
    import optical_ports as P
    idx = index()
    for e in projecting_modules(idx):
        view = D.contract_view(e)
        caps = O.capacities(view, idx.get)
        got = P.ports(view, idx.get)
        front_fibres = sum(n for k, n in caps.items() if ":" not in k)
        rear_fibres = sum(n for k, n in caps.items() if ":" in k)
        assert len(got["front"]) == front_fibres, e["name"]
        assert sum(p["positions"] for p in got["rear"]) == rear_fibres, e["name"]


def test_every_fibre_map_row_names_ports_that_exist():
    """Section D: a row pointing at a port nobody exported is a silent drop."""
    import dcim_export as D
    import optical_ports as P
    idx = index()
    for e in projecting_modules(idx):
        view = D.contract_view(e)
        model = str((e.get("attrs") or {}).get("model") or e["name"])
        got = P.ports(view, idx.get)
        m = P.fibre_map(view, idx.get, model)
        fronts = {p["name"] for p in got["front"]}
        rears = {p["name"] for p in got["rear"]}
        for r in m["rows"]:
            assert r["front"] in fronts, f"{model}: front {r['front']!r}"
            assert r["rear"] in rears, f"{model}: rear {r['rear']!r}"


def test_no_exported_front_port_is_left_without_a_rear_port():
    """Section D, and netbox#21830: we do not get to omit rear ports."""
    import dcim_export as D
    import optical_ports as P
    idx = index()
    for e in projecting_modules(idx):
        view = D.contract_view(e)
        model = str((e.get("attrs") or {}).get("model") or e["name"])
        got = P.ports(view, idx.get)
        m = P.fibre_map(view, idx.get, model)
        bound = {r["front"] for r in m["rows"]}
        orphans = sorted({p["name"] for p in got["front"]} - bound)
        assert not orphans, f"{model}: front ports bound to nothing: {orphans}"


def test_every_vendor_fibre_module_actually_reaches_the_exports():
    """The failure that started this plan was SILENT.

    The cassette modelled in plan 4 exported nothing at all, because `kind` and
    `class` were the wrong way round and FS had no device to learn a
    manufacturer from. Nothing noticed: the gates were green, the file simply
    did not exist. This is what notices next time.

    Scoped to `projecting_modules`: the six unfaced PPMs are checked by the
    guard above instead, which asserts they export nothing rather than
    something under their own model number.
    """
    if not EXPORTS.exists():
        pytest.skip("library/exports not built - run ./publish.sh --no-images")
    idx = index()
    missing = []
    for e in projecting_modules(idx):
        if e.get("ns") in ("common", "std"):
            continue
        model = str((e.get("attrs") or {}).get("model") or e["name"])
        hits = list((EXPORTS / "netbox" / "module-types").rglob(
            model.replace("/", "-") + ".yaml"))
        if not hits:
            missing.append(model)
    assert not missing, f"modelled, has fibres, exports nothing: {missing}"
