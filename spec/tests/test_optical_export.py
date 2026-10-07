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

from portrayal import optical as O


def index():
    f = DIST / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    return {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
            for e in json.loads(f.read_text())["components"]}


def dist():
    """A published build to read, or a skip when the tree was never built.

    `Dist` raises SystemExit for a missing artefact, and pytest reports that as
    a FAILURE - so five tests here failed rather than skipped on any fresh clone
    or worktree, `library/dist` being gitignored build output. The message named
    build.sh and devices.json, which reads as a broken build rather than as an
    unbuilt one.

    The gate is on the DIRECTORY and not on the individual artefact, which is
    the distinction worth keeping: `library/dist` absent means nobody has run
    publish.sh and there is nothing to test; `library/dist` present but short of
    devices.json is a BROKEN build, and Dist's own exit is the right loud answer
    to that. Only the first is a skip. CI builds before it runs the suite, so
    this skip never fires there and the assertions below always do.
    """
    if not DIST.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    from portrayal.artifacts import Dist
    return Dist(str(DIST))


def test_the_index_carries_a_connectors_positions():
    """Without this the exporter cannot count a single fibre."""
    idx = index()
    mpo = idx["common/mpo-adapter@2"]
    assert (mpo.get("optical") or {}).get("positions") == 12


def test_the_index_carries_a_modules_paths():
    idx = index()
    c = idx["fs/fhd-1mtp6lcd-os2-a@4"]
    opt = c.get("optical") or {}
    assert opt.get("media") == "os2"
    assert len(opt.get("paths") or []) == 12


def test_an_entry_with_no_optical_omits_the_key():
    """700-odd entries are not fibre; an empty dict on each is bytes for nothing."""
    idx = index()
    assert "optical" not in idx["std/pcie-bracket-fh@2"]


def test_capacities_answers_from_the_built_index():
    """The index flattens `faces` and the optical helpers do not.

    `contract_view` is the adapter. If it stops being applied, this is what
    notices - the rear face's twelve positions simply vanish from the answer.
    """
    from portrayal import dcim_export as D
    idx = index()
    caps = O.capacities(D.contract_view(idx["fs/fhd-1mtp6lcd-os2-a@4"]),
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
    c = idx["fs/fhd-1mtp6lcd-os2-a@4"]
    assert c["kind"] == "module"
    assert c["class"] != "module", "`class: module` says nothing; name the thing"


def test_the_rear_face_is_not_separately_orderable():
    """A face is a drawing of the part, not a second product to order."""
    idx = index()
    assert idx["fs/fhd-1mtp6lcd-rear@3"]["kind"] == "component"


def test_the_registry_fallback_still_answers_for_a_deviceless_namespace():
    """PLAN 5'S FALLBACK, AND THIS IS WHAT WATCHES IT.

    `manufacturer_of` checks devices first and falls back to vendors.yaml, so a
    vendor that ships parts before it ships a chassis is still orderable. FS was
    that vendor until the FHD-1UFCE landed; now it resolves from its device, and
    the old test passed through the device path while claiming to prove the
    fallback. This drives the fallback directly instead.
    """
    d = dist()
    assert d.manufacturer_of("fs") == "FS.com"      # now via the device
    # a namespace that exists in vendors.yaml and has no device at all
    deviceless = [ns for ns in d.vendors
                  if not any(x.get("ns") == ns for x in d.devices)]
    assert deviceless, "every vendor now has a device - the fallback is unwatched"
    ns = deviceless[0]
    assert d.manufacturer_of(ns) == d.vendors[ns]["display"]


def test_the_device_lookup_still_wins_over_the_registry():
    """NOT incidental. `dell` reports `Dell` from its devices and `Dell
    Technologies` from vendors.yaml; `juniper` and `edgecore` differ the same
    way. A vendors-first lookup would rename the manufacturer on several hundred
    existing export files."""
    d = dist()
    assert d.manufacturer_of("dell") == "Dell"
    assert d.manufacturer_of("juniper") == "Juniper"


def test_a_namespace_with_no_vendor_is_still_not_orderable():
    """`common/` and `std/` are absent from vendors.yaml, so the property
    `manufacturer_of` documents holds by data rather than by a special case."""
    d = dist()
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
# is every module carrying a fibre graph. The exporter projects one when it has
# a trunk - a declared rear face, or a stated `optical.trunk` (#246) - which is
# `optical_ports.projects`, the one gate `build_module` and `export_modules`
# both ask. The eight Smartoptics PPMs are single-faced and state a trunk;
# every FS and Fibrain module has a rear face. L131 makes a path-bearing module
# with neither an error, so the two lists are the same list, and a test below
# keeps the gate itself honest with a contract built to fail it.
def fibre_modules(idx):
    return [e for e in idx.values()
            if (e.get("optical") or {}).get("paths") and e.get("kind") == "module"]


def projecting_modules(idx):
    """`fibre_modules`, narrowed to those the exporter actually projects.

    Asks `optical_ports.projects` of `dcim_export.contract_view(e)` - the same
    gate and the same shape `build_module`/`export_modules` use - never the raw
    flattened `faces` shape the index carries.
    """
    from portrayal import dcim_export as D
    from portrayal import optical_ports as P
    return [e for e in fibre_modules(idx) if P.projects(D.contract_view(e))]


def rear_faced_modules(idx):
    """The projecting modules whose trunk is a rear face - the FS and Fibrain
    population that exported before `optical.trunk` existed."""
    from portrayal import dcim_export as D
    from portrayal.faces import face_ref
    return [e for e in projecting_modules(idx) if face_ref(D.contract_view(e), "rear")]


def test_the_sweep_finds_fibre_modules_at_all():
    """Guard the guard: every sweep below passes vacuously on an empty list."""
    assert fibre_modules(index()), "no fibre modules found - the sweeps are vacuous"


def test_the_populations_split_as_the_controller_ruling_expects():
    """Pin the ruling with a number, not merely an assertion that passes.

    Twenty-eight modules carry `optical.paths` today: twenty-two FS cassettes with
    a declared rear face - the five OS2 Type A ones (fhd-1mtp6lcd-os2-a,
    fhd-splice-12-lc, fhd-2mtp12-lc-os2-a, fhd-1mtp12-sc-os2-a and
    fhd-1mtp24-lc-os2-a), their five polarity twins (fhd-1mtp6lcd-os2-af
    and -os2-u, fhd-2mtp12-lc-os2-af and -os2-u, fhd-1mtp24-lc-os2-af) and
    ten media twins in OM4, OM5 and OM3 (fhd-1mtp6lcd-om4-a, -om4-u, -om5-a;
    fhd-2mtp12-lc-om4-a, -om4-u, -om5-a, -om3-a; fhd-1mtp24-lc-om4-a,
    -om5-a, -om3-a), the 36-fibre pair (fhd-3mtp18-lc-os2-a, -om4-a) - and six
    Smartoptics PPMs with none.

    FORTY-ONE AND THIRTY-FIVE SINCE THE FHD ADAPTER PANELS (2026-09-25):
    thirteen fibre panels, each a pass-through with a declared rear face -
    LC 24F in OS2 UPC and APC, OM4 and OM5 (fhd-fap12lcd-os2, -apc-os2, -om4,
    -om5), LC 36F (fhd-fap18lcd-os2, -om4), SC (fhd-fap6scd-apc-os2, -os2,
    -om4) and MTP (fhd-fap12mtp-a, -b, fhd-fap8mtp-b, fhd-fap12mtp16-a). The
    modular panel and the blank carry no fibre and are in neither count. A future cassette that joins the library
    moves one of these two counts, and this is what a reviewer notices
    moving.

    FORTY-FIVE AND THIRTY-NINE SINCE THE FIBRAIN HD HOLDERS (2026-10-06): four
    SC adapter holders, each a pass-through with a declared rear face -
    xmi1041ga and xmi1051ga (6 ports), xmn1041gb and xmn1051gb (12).

    SIXTY-ONE AND FIFTY-FIVE SINCE THE REST OF THAT FAMILY (2026-10-06): ten
    LC duplex holders (6 and 12 port, each in OM3, OM4, OM5, single-mode and
    single-mode APC) and the six multimode SC ones (6 and 12 port in OM3, OM4
    and OM5), all pass-throughs with a declared rear face.

    SIXTY-THREE, ALL PROJECTING, SINCE THE TRUNK (#246): the six PPMs that
    were excluded state `optical.trunk` and export, and the two AD1 add/drop
    filters gained their glass in the same change. Fifty-five rear-faced, eight
    single-faced with a stated trunk, none left out.
    """
    idx = index()
    all_fibre = fibre_modules(idx)
    projecting = projecting_modules(idx)
    rear_faced = rear_faced_modules(idx)
    excluded = [e["name"] for e in all_fibre if e not in projecting]
    assert len(all_fibre) == 63, sorted(e["name"] for e in all_fibre)
    assert len(projecting) == 63, [e["name"] for e in projecting]
    assert len(rear_faced) == 55, [e["name"] for e in rear_faced]
    assert not excluded, excluded
    assert sorted(e["name"] for e in projecting if e not in rear_faced) == sorted([
        "ppm-ad1-1510", "ppm-ad1-1625",
        "ppm-dcm-10", "ppm-dcm-20", "ppm-dcm-40", "ppm-dcm-80",
        "ppm-ocu-50-50", "ppm-ocu-97-3",
    ])


def test_a_fibre_module_with_no_trunk_exports_nothing_optical():
    """The gate, against a contract built to fail it - the library has none.

    A module with paths and neither a rear face nor `optical.trunk` is a lint
    error (L131), so no shipped part exercises this branch. It must still
    export no front-ports, no rear-ports and no fibre map: front ports with no
    rear port are what netbox#21830 rejected. The adapters resolve to two
    positions each, so the gate - not an empty capacity - is what stops it.
    """
    from portrayal import dcim_export as D
    from portrayal import optical_ports as P
    contract = {
        "name": "t-coupler", "kind": "module",
        "parts": [{"id": "common", "ref": "common/lc-duplex-adapter@6"},
                  {"id": "split", "ref": "common/lc-duplex-adapter@6"}],
        "optical": {"polish": "upc",
                    "paths": [{"from": "common.1",
                               "to": [{"at": "split.1", "ratio": 50},
                                      {"at": "split.2", "ratio": 50}]}]},
    }
    known = {"common/lc-duplex-adapter@6": {"optical": {"positions": 2}}}
    assert not P.projects(D.contract_view(contract))
    doc = D.build_module(contract, "Vendor", known.get)
    assert "front-ports" not in doc and "rear-ports" not in doc
    contract["optical"]["trunk"] = ["common"]
    assert P.projects(D.contract_view(contract))
    doc = D.build_module(contract, "Vendor", known.get)
    assert [p["name"] for p in doc["front-ports"]] == ["3", "4"]
    assert doc["rear-ports"] == [{"name": "COMMON-1", "type": "lc-upc", "positions": 2}]


def test_every_fibre_module_exports_ports_matching_its_graph():
    """Section D: the count a module exports equals the count its graph carries."""
    from portrayal import dcim_export as D
    from portrayal import optical_ports as P
    idx = index()
    for e in projecting_modules(idx):
        view = D.contract_view(e)
        caps = O.capacities(view, idx.get)
        got = P.ports(view, idx.get)
        # A STATED TRUNK MOVES ITS POSITIONS FROM THE FRONT COUNT TO THE REAR
        trunk = sum(len(v) for v in P.trunk_positions(view, idx.get).values())
        front_fibres = sum(n for k, n in caps.items() if ":" not in k) - trunk
        rear_fibres = sum(n for k, n in caps.items() if ":" in k) + trunk
        # POSITIONS, not ports, on both faces: a front LC bore is one port of
        # one position, but a front MPO adapter (the FHD MTP panels) is one
        # port of twelve or sixteen, as a rear connector always was
        assert sum(p["positions"] for p in got["front"]) == front_fibres, e["name"]
        assert sum(p["positions"] for p in got["rear"]) == rear_fibres, e["name"]


def test_every_fibre_map_row_names_ports_that_exist():
    """Section D: a row pointing at a port nobody exported is a silent drop."""
    from portrayal import dcim_export as D
    from portrayal import optical_ports as P
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
    from portrayal import dcim_export as D
    from portrayal import optical_ports as P
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


# ---------------------------------------------------------------------------
# Section D: "every fibre-map row's endpoints exist in the EXPORTED ports."
#
# Every assertion above either re-derives `optical_ports.ports()` in-process or
# checks that a file merely exists. Neither notices `export_modules` dropping
# the `load_ref` argument at its `build_module` call site: `optical.capacities`
# would then answer `{}` for every part - both YAMLs would ship with no
# `front-ports` and no `rear-ports` - while `export_modules` still writes the
# twelve-row fibre map naming `MTP-1` and fronts `1..12`, because `fibre_map`
# is built from the same contract independently of what `build_module` wrote.
# Every test above stays green through that: the in-process re-derivation still
# has a real `load_ref` (`idx.get`), and the file-existence checks do not look
# inside the file. So the tests below read the ACTUAL EXPORTED YAML - never
# re-deriving it - and cross-check it against the fibre map and against the
# projection.
def _exported_module_doc(target, manufacturer, model):
    """The actual exported module-type YAML, read off disk - not re-derived."""
    f = (EXPORTS / target / "module-types" / manufacturer
         / (model.replace("/", "-") + ".yaml"))
    if not f.exists():
        return None
    return yaml.safe_load(f.read_text())


def _exported_fibre_map(manufacturer, model):
    f = EXPORTS / "fibre-maps" / manufacturer / (model.replace("/", "-") + ".yaml")
    if not f.exists():
        return None
    return yaml.safe_load(f.read_text())


def test_the_exported_module_files_carry_the_ports_the_graph_implies():
    """Read the file. Not `optical_ports.ports()` again - the file.

    For every projecting module, in BOTH targets: `front-ports` and
    `rear-ports` are non-empty, and their name sets exactly equal what
    `optical_ports.ports()` derives from the same contract. Dropping the
    `load_ref` argument at the `export_modules` call site makes the exported
    file's port lists empty while this stays the one place that would notice,
    because everything else on this branch re-derives instead of reading.
    """
    if not EXPORTS.exists():
        pytest.skip("library/exports not built - run ./publish.sh --no-images")
    from portrayal import dcim_export as D
    from portrayal import optical_ports as P
    d = dist()
    idx = index()
    depths = D.seating_depths(d)
    checked = 0
    for e in projecting_modules(idx):
        man = d.manufacturer_of(e.get("ns"))
        if not man:
            continue
        model = str((e.get("attrs") or {}).get("model") or e["name"])
        view = D.contract_view(e)
        expected = P.ports(view, idx.get)
        # The file carries the names bay-scoped (dcim_export.tokenize_module).
        base_front = {D.module_scoped(p["name"]) for p in expected["front"]}
        base_rear = {D.module_scoped(p["name"]) for p in expected["rear"]}
        assert base_front and base_rear, \
            f"{model}: the graph itself carries no ports - this guard is vacuous"
        # NAUTOBOT NAMES THE BAY CHAIN of a module seated only in a nested bay
        # (dcim_export.seat_names, #765), so its expected names go through the
        # same rename at the model's one depth.
        seated = depths.get((man, model)) or set()
        depth = next(iter(seated)) if len(seated) == 1 else None
        for target in D.TARGETS:
            doc = _exported_module_doc(target, man, model)
            assert doc is not None, f"{model} ({target}): no exported file"
            if target == "nautobot" and "This module splits" in (doc.get("comments") or ""):
                # several front ports on one rear position: Nautobot has no
                # spelling, so the type states neither list (for_target)
                assert "front-ports" not in doc and "rear-ports" not in doc, model
                continue
            exp_front, exp_rear = base_front, base_rear
            if target == "nautobot":
                seat = D.seat_names({"front-ports": [{"name": n} for n in base_front],
                                     "rear-ports": [{"name": n} for n in base_rear]}, depth)
                exp_front = {r["name"] for r in seat["front-ports"]}
                exp_rear = {r["name"] for r in seat["rear-ports"]}
            got_front = {p["name"] for p in doc.get("front-ports") or []}
            got_rear = {p["name"] for p in doc.get("rear-ports") or []}
            assert got_front, f"{model} ({target}): exported front-ports is empty"
            assert got_rear, f"{model} ({target}): exported rear-ports is empty"
            assert got_front == exp_front, \
                f"{model} ({target}): exported front-ports {got_front} != {exp_front}"
            assert got_rear == exp_rear, \
                f"{model} ({target}): exported rear-ports {got_rear} != {exp_rear}"
            checked += 1
    assert checked, "no projecting module was checked - this guard is vacuous"


def test_every_fibre_map_row_names_ports_in_the_exported_file():
    """Section D, read literally: a row's endpoints exist in the EXPORTED ports.

    `test_every_fibre_map_row_names_ports_that_exist` above checks the row
    against `optical_ports.ports()` re-derived in-process, which stays right
    even when the exported file itself is empty. This reads the file the fibre
    map is meant to describe.
    """
    if not EXPORTS.exists():
        pytest.skip("library/exports not built - run ./publish.sh --no-images")
    from portrayal import dcim_export as D
    d = dist()
    idx = index()
    checked = 0
    for e in projecting_modules(idx):
        man = d.manufacturer_of(e.get("ns"))
        if not man:
            continue
        model = str((e.get("attrs") or {}).get("model") or e["name"])
        doc = _exported_module_doc("netbox", man, model)
        assert doc is not None, f"{model}: no exported netbox file"
        fronts = {p["name"] for p in doc.get("front-ports") or []}
        rears = {p["name"] for p in doc.get("rear-ports") or []}
        m = _exported_fibre_map(man, model)
        assert m is not None, f"{model}: no exported fibre map"
        assert m["rows"], f"{model}: exported fibre map has no rows"
        for r in m["rows"]:
            assert r["front"] in fronts, \
                f"{model}: fibre-map row front {r['front']!r} not among exported front-ports {fronts}"
            assert r["rear"] in rears, \
                f"{model}: fibre-map row rear {r['rear']!r} not among exported rear-ports {rears}"
        checked += 1
    assert checked, "no projecting module was checked - this guard is vacuous"


def test_a_module_that_exports_front_ports_also_exports_a_rear_port():
    """netbox#21830, pinned against the file: we do not get to omit rear ports.

    `build_module` sets `rear-ports` and `front-ports` under two INDEPENDENT
    `if` statements, so a front-only export is structurally possible even
    though nothing in today's library exercises it. Swept across every
    exported module type in both targets, not just the fibre modules, so a
    future module that trips this shape is caught wherever it lands.
    """
    if not EXPORTS.exists():
        pytest.skip("library/exports not built - run ./publish.sh --no-images")
    from portrayal import dcim_export as D
    checked = 0
    for target in D.TARGETS:
        for f in sorted((EXPORTS / target / "module-types").rglob("*.yaml")):
            doc = yaml.safe_load(f.read_text())
            if doc.get("front-ports"):
                checked += 1
                assert doc.get("rear-ports"), \
                    f"{f}: front-ports with no rear-ports (netbox#21830)"
    assert checked, "no exported module carries front-ports - this guard is vacuous"


def test_no_exported_port_has_a_null_type():
    """`optical_ports.FAMILY` is a table a ref can be absent from - a rear
    connector like `mpo16-adapter` with no entry yet - and `port_type` answers
    None for an unknown family, which serializes to `type: null` and passes
    every sweep that only checks port NAMES. MPO-8 and MPO-16 are the next
    connectors the bulk build needs, so this checks every exported port in
    every module-type file, in both targets, carries a real `type`.
    """
    if not EXPORTS.exists():
        pytest.skip("library/exports not built - run ./publish.sh --no-images")
    from portrayal import dcim_export as D
    checked = 0
    for target in D.TARGETS:
        for f in sorted((EXPORTS / target / "module-types").rglob("*.yaml")):
            doc = yaml.safe_load(f.read_text())
            for kind in ("front-ports", "rear-ports"):
                for p in doc.get(kind) or []:
                    checked += 1
                    assert p.get("type"), \
                        f"{f} ({kind}): port {p.get('name')!r} exported type " \
                        f"{p.get('type')!r}"
    assert checked, "no exported module carries any port - this guard is vacuous"
