"""The projection from a fibre graph to DCIM ports.

Pure functions over an index entry - no I/O here, so these run without a build.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]

from portrayal import lint as L
from portrayal import optical_ports as P

LIB = [str(ROOT / "library")]


def run86(doc, path="t/contract.yaml"):
    with L.collecting() as _found:
        L.lint_component_optical_polish(path, doc)
    return [e for e in _found.errors if "[L86]" in e]


def test_a_polished_family_needs_a_polish():
    """An LC adapter is sold UPC and APC and the enum has no bare `lc`."""
    doc = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@4"}],
           "optical": {"paths": [{"from": "lc1.1", "to": "lc1.2"}]}}
    got = run86(doc)
    assert len(got) == 1, got
    assert "polish" in got[0]


def test_stating_the_polish_is_quiet():
    doc = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@4"}],
           "optical": {"polish": "upc",
                       "paths": [{"from": "lc1.1", "to": "lc1.2"}]}}
    assert run86(doc) == []


def test_an_unpolished_family_needs_nothing():
    """MPO, ST, MDC and splice have one form in the enum, so there is nothing
    for a contract to state and demanding it would be noise."""
    doc = {"parts": [{"id": "mtp", "ref": "common/mpo-adapter@1"}],
           "optical": {"paths": [{"from": "mtp.1", "to": "mtp.2"}]}}
    assert run86(doc) == []


def test_a_module_with_no_paths_is_not_this_rules_business():
    assert run86({"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@4"}]}) == []


def test_the_real_cassette_states_its_polish():
    c = yaml.safe_load(
        (ROOT / "library/components/fs/fhd-1mtp6lcd-os2-a/v3/contract.yaml").read_text())
    assert (c["optical"]).get("polish") == "upc"
    assert run86(c) == []


def test_the_cassettes_polish_is_marked_as_the_assumption_it_is():
    """FS names the polish on 19 of its 81 catalogue rows and does NOT name one
    for 57016. Recording `upc` is the convention default, not a sourced fact,
    and the contract has to say which - the same distinction plan 4 drew for the
    polarity map."""
    c = yaml.safe_load(
        (ROOT / "library/components/fs/fhd-1mtp6lcd-os2-a/v3/contract.yaml").read_text())
    note = (c.get("provenance") or {}).get("optical") or ""
    assert "polish" in note.lower(), "provenance says nothing about the polish"
    assert "ASSUM" in note.upper() or "not name" in note.lower(), \
        "the polish must be marked as an assumption, not stated flatly"


def cassette_entry():
    """The real cassette and its rear, as the index publishes them."""
    import json
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    return idx["fs/fhd-1mtp6lcd-os2-a@3"], idx


def test_the_rear_mtp_is_one_port_with_twelve_positions():
    """C1: a rear MPO-12 exports as ONE rear port, not twelve."""
    from portrayal import dcim_export as D
    e, idx = cassette_entry()
    got = P.ports(D.contract_view(e), idx.get)
    assert got["rear"] == [{"name": "MTP-1", "type": "mpo", "positions": 12}]


def test_every_front_fibre_is_its_own_port():
    """C1: per-fibre granularity is what makes the projection lossless for the
    22 breakouts, 4 conversions and 4 mesh cassettes."""
    from portrayal import dcim_export as D
    e, idx = cassette_entry()
    got = P.ports(D.contract_view(e), idx.get)
    assert len(got["front"]) == 12
    assert got["front"][0] == {"name": "1", "type": "lc-upc", "positions": 1}
    assert got["front"][-1] == {"name": "12", "type": "lc-upc", "positions": 1}


def test_the_front_numbering_reproduces_the_faceplate():
    """The DERIVATION is placement order; the faceplate is the check on it.

    The contract records the numbering only in prose - "2 above 1 at the left
    end, 12 above 11 at the right" - so the projection derives it from the
    adapters' x order and each adapter's fibre positions. This asserts the
    derivation lands where the vendor's labels do: adapter lc1 carries 1 and 2,
    lc6 carries 11 and 12.
    """
    from portrayal import dcim_export as D
    e, idx = cassette_entry()
    view = D.contract_view(e)
    assert P.front_label(view, "lc1.1", idx.get) == "1"
    assert P.front_label(view, "lc1.2", idx.get) == "2"
    assert P.front_label(view, "lc6.1", idx.get) == "11"
    assert P.front_label(view, "lc6.2", idx.get) == "12"


def test_a_single_faced_module_with_paths_exports_no_ports():
    """A module with `optical.paths` but no declared rear face states no
    trunk. `common` and `split` (an OCU coupler's own part ids) are a
    modeller's names, not roles, and path direction does not settle which
    part is the trunk either - see the gate's comment in `build_module`. So a
    single-faced module, however many fibre positions it carries, projects to
    neither `front-ports` nor `rear-ports` rather than guessing: exporting one
    side alone is exactly what netbox#21830 rejected.

    THE LOOKUP RESOLVES FOR REAL. A `lambda ref: None` stub makes every part's
    fibre count zero regardless of the gate this test exists to check - delete
    the rear-face gate in `build_module` and `ports()` still answers empty
    fronts, because `optical.capacities` cannot see any positions either way.
    So this uses the same `known` dict shape `test_a_split_carries_its_ratio`
    uses below: the adapters genuinely resolve to two fibre positions each,
    which is what makes the gate the thing standing between this contract and
    a non-empty `front-ports`.
    """
    from portrayal import dcim_export as D
    contract = {
        "name": "t-coupler",
        "parts": [
            {"id": "common", "ref": "common/lc-duplex-adapter@4"},
            {"id": "split", "ref": "common/lc-duplex-adapter@4"},
        ],
        "optical": {
            "polish": "upc",
            "paths": [{"from": "common.1",
                       "to": [{"at": "split.1", "ratio": 50},
                              {"at": "split.2", "ratio": 50}]}],
        },
    }
    known = {"common/lc-duplex-adapter@4": {"optical": {"positions": 2}}}
    doc = D.build_module(contract, "Vendor", known.get)
    assert "front-ports" not in doc
    assert "rear-ports" not in doc


def test_the_real_ppm_coupler_export_has_no_ports():
    """PPM-OCU-50-50 in the built export: the same gate, against the actual
    corpus rather than a literal dict. It has two adapters and a live optical
    graph but only one face, so it must carry neither key."""
    f = (ROOT / "library/exports/netbox/module-types/Smartoptics"
         / "PPM-OCU-50-50.yaml")
    if not f.exists():
        pytest.skip("library/exports not built - run ./publish.sh --no-images")
    doc = yaml.safe_load(f.read_text())
    assert "front-ports" not in doc
    assert "rear-ports" not in doc


def test_the_fibre_map_carries_one_row_per_leg():
    from portrayal import dcim_export as D
    e, idx = cassette_entry()
    m = P.fibre_map(D.contract_view(e), idx.get, "FHD-1MTP6LCDOS2A")
    assert m["model"] == "FHD-1MTP6LCDOS2A"
    assert m["media"] == "os2"
    assert m["polarity"] == "a"
    assert len(m["rows"]) == 12
    assert m["rows"][0] == {"front": "1", "front_position": 1,
                            "rear": "MTP-1", "rear_position": 1}
    assert m["rows"][-1] == {"front": "12", "front_position": 1,
                             "rear": "MTP-1", "rear_position": 12}


def test_a_split_carries_its_ratio():
    """C3: the ratio has no field in the type format, so it rides the map.

    Built here rather than read from the library, because no modelled part
    splits yet - the taps arrive in plan 6, and a rule with no test until then
    is a rule nobody has run.
    """
    entry = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@4",
                        "at": [0, 0]}],
             "faces": {"rear": {"ref": "t/rear@1"}},
             "optical": {"media": "os2", "polish": "upc",
                         "paths": [{"from": "rear:mtp.1",
                                    "to": [{"at": "lc1.1", "ratio": 50},
                                           {"at": "lc1.2", "ratio": 50}]}]}}
    known = {"common/lc-duplex-v-adapter@4": {"optical": {"positions": 2}},
             "common/mpo-adapter@1": {"optical": {"positions": 12}},
             "t/rear@1": {"parts": [{"id": "mtp", "ref": "common/mpo-adapter@1"}]}}
    m = P.fibre_map(entry, known.get, "TAP")
    assert len(m["rows"]) == 2
    assert all(r["ratio"] == 50 for r in m["rows"])
    assert {r["front"] for r in m["rows"]} == {"1", "2"}


def test_a_splice_rear_exports_as_one_splice_port():
    """C2, and upstream's own convention: the devicetype-library ships ADC's
    PPP-SC-SM with `rear-ports: [{name, type: splice, positions: 1}]`."""
    entry = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-adapter@4",
                        "at": [0, 0]}],
             "faces": {"rear": {"ref": "t/splice-rear@1"}},
             "optical": {"media": "os2", "polish": "upc", "rear-kind": "splice",
                         "paths": [{"from": "lc1.1", "to": "rear:splice.1"},
                                   {"from": "lc1.2", "to": "rear:splice.2"}]}}
    known = {"common/lc-duplex-adapter@4": {"optical": {"positions": 2}},
             "common/fibre-splice@1": {"optical": {"positions": 2}},
             "t/splice-rear@1": {"parts": [{"id": "splice",
                                            "ref": "common/fibre-splice@1"}]}}
    got = P.ports(entry, known.get)
    assert got["rear"] == [{"name": "SPLICE-1", "type": "splice", "positions": 2}]
    assert len(got["front"]) == 2


def test_a_declared_rear_kind_does_not_override_a_known_family():
    """`rear-kind` used to type EVERY rear port (`t = rear_kind or
    port_type(...)`), so a module with a splice tray AND an MPO adapter on one
    rear face would export both as `type: splice`. The connector family wins
    when it is known; `rear-kind` is only the fallback for a part - like a
    splice tray - that composes nothing `FAMILY` recognises."""
    entry = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-adapter@4",
                        "at": [0, 0]}],
             "faces": {"rear": {"ref": "t/mixed-rear@1"}},
             "optical": {"media": "os2", "polish": "upc", "rear-kind": "splice",
                         "paths": [{"from": "lc1.1", "to": "rear:splice.1"},
                                   {"from": "lc1.2", "to": "rear:mtp.1"}]}}
    known = {"common/lc-duplex-adapter@4": {"optical": {"positions": 2}},
             "common/fibre-splice@1": {"optical": {"positions": 2}},
             "common/mpo-adapter@1": {"optical": {"positions": 12}},
             "t/mixed-rear@1": {"parts": [
                 {"id": "splice", "ref": "common/fibre-splice@1"},
                 {"id": "mtp", "ref": "common/mpo-adapter@1"}]}}
    got = P.ports(entry, known.get)
    types = {r["name"]: r["type"] for r in got["rear"]}
    assert types == {"SPLICE-1": "splice", "MTP-1": "mpo"}, types


def run87(doc, path="t/contract.yaml"):
    with L.collecting() as _found:
        L.lint_component_optical_rear_kind(path, doc)
    return [e for e in _found.errors if "[L87]" in e]


def test_declaring_a_splice_rear_without_a_rear_face_is_an_error():
    """`rear-kind` describes a rear face. Saying it with no rear face to describe
    is a claim about a drawing that does not exist."""
    got = run87({"optical": {"rear-kind": "splice",
                             "paths": [{"from": "a.1", "to": "b.1"}]}})
    assert len(got) == 1, got
    assert "rear face" in got[0]


def test_a_splice_rear_with_a_rear_face_is_quiet():
    assert run87({"faces": {"rear": {"ref": "t/x@1"}},
                  "optical": {"rear-kind": "splice",
                              "paths": [{"from": "a.1", "to": "rear:b.1"}]}}) == []


def test_saying_nothing_about_the_rear_kind_is_quiet():
    """Every cassette built so far has a connector on the back and says nothing."""
    assert run87({"faces": {"rear": {"ref": "t/x@1"}},
                  "optical": {"paths": [{"from": "a.1", "to": "rear:b.1"}]}}) == []


def test_front_numbering_follows_at_x_not_id_order(tmp_path):
    """`_front_parts` orders adapters "across the face by `at.x`", by its own
    docstring - but until now nothing proved the BUILT index it actually reads
    at runtime carries `at.x` at all.

    `components_index.py` published only `ref`, `id` and `attrs` per part.
    Every part's `at` therefore read as the shared default `[0, 0]`, and
    `_front_parts`' sort fell through to comparing the part-id STRING - quiet
    for every real cassette so far only because their ids (`lc1`..`lc6` on
    fhd-1mtp6lcd-os2-a, `lc01`..`lc12` on fhd-2mtp12-lc-os2-a) already sort in
    face order. `id lc9` at x=10.0 (physically first) and `id lc10` at x=90.0
    (physically second) disagree with their string order
    (`"lc10" < "lc9"`), so this is the case that tells the two failure modes
    apart: the fix must publish `at` on the built index entry, not merely
    leave `_front_parts` alone.

    This runs the REAL `components_index.py` CLI against a throwaway
    component (composing the real common/lc-duplex-v-adapter@4, resolved from
    this library) rather than constructing an index entry by hand, because a
    hand-built entry that already carries `at` cannot tell a working
    `_front_parts` apart from a `components_index.py` that silently drops it
    before the projection ever sees it - which is exactly the bug that
    shipped. Confirmed to fail against components_index.py before `at` was
    added to its `parts` projection (labels came out lc10->1,2 / lc9->3,4 -
    backwards) and to pass after.
    """
    import json
    import subprocess

    comp = tmp_path / "components" / "t" / "lctest" / "v1"
    (comp / "skins").mkdir(parents=True)
    (comp / "contract.yaml").write_text("""\
format: 1
kind: module
name: lctest
version: 1.0.0
class: cassette
description: throwaway component proving components_index publishes `at` on parts.
size: {w: 100.0, h: 20.0}
attrs: {media: fiber}
parts:
  - {id: lc10, ref: common/lc-duplex-v-adapter@4, at: [90.0, 3.0]}
  - {id: lc9, ref: common/lc-duplex-v-adapter@4, at: [10.0, 3.0]}
optical:
  polish: upc
  paths:
    - {from: lc9.1, to: lc9.2}
    - {from: lc10.1, to: lc10.2}
skins: [default]
""")
    (comp / "skins" / "default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100.0mm" height="20.0mm" '
        'viewBox="0 0 100.0 20.0"><rect x="0" y="0" width="100.0" height="20.0"/></svg>\n')

    out = tmp_path / "dist"
    subprocess.run(
        [sys.executable, str(ROOT / "spec/tools/portrayal/components_index.py"),
         "--library", str(ROOT / "library"), "--library", str(tmp_path),
         "--out", str(out)],
        check=True, capture_output=True, text=True)

    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads((out / "components.json").read_text())["components"]}
    e = idx["t/lctest@1"]
    assert all("at" in p for p in e["parts"]), \
        f"components_index dropped `at` from the built entry: {e['parts']}"

    from portrayal import dcim_export as D
    view = D.contract_view(e)
    assert P.front_label(view, "lc9.1", idx.get) == "1"
    assert P.front_label(view, "lc9.2", idx.get) == "2"
    assert P.front_label(view, "lc10.1", idx.get) == "3"
    assert P.front_label(view, "lc10.2", idx.get) == "4"


def test_the_two_row_cassette_follows_its_front_order():
    """`optical.front-order` states the vendor's own row-then-row numbering
    explicitly - prove the projection actually follows it rather than
    falling back to `at.x`, which would produce the column-major order this
    same module shipped with by accident before `front-order` existed (see
    its own provenance.parts for the two retractions).
    """
    import json
    from portrayal import dcim_export as D
    f = ROOT / "library" / "dist" / "components.json"
    if not f.exists():
        pytest.skip("library/dist not built - run ./publish.sh --no-images")
    idx = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
           for e in json.loads(f.read_text())["components"]}
    e = idx["fs/fhd-2mtp12-lc-os2-a@3"]
    view = D.contract_view(e)
    want = [str(n) for n in range(1, 25)]
    got = []
    for pid in ("lc01", "lc02", "lc03", "lc04", "lc05", "lc06",
                "lc07", "lc08", "lc09", "lc10", "lc11", "lc12"):
        got += [P.front_label(view, f"{pid}.1", idx.get),
                P.front_label(view, f"{pid}.2", idx.get)]
    assert got == want, got


def run88(doc, path="t/contract.yaml"):
    with L.collecting() as _found:
        L.lint_component_optical_front_order(path, doc)
    return [e for e in _found.errors if "[L88]" in e]


TWO_ROW_PARTS = [
    {"id": "a", "ref": "common/lc-duplex-v-adapter@4", "at": [5.0, 3.0]},
    {"id": "b", "ref": "common/lc-duplex-v-adapter@4", "at": [20.0, 15.0]},
]
TWO_ROW_PATHS = [{"from": "a.1", "to": "a.2"}, {"from": "b.1", "to": "b.2"}]


def test_a_two_row_fibre_face_without_front_order_is_l88():
    """The case geometry cannot answer: two fibre parts at two distinct
    `at.y` values, and no `optical.front-order` to resolve which row the
    vendor numbers first."""
    got = run88({"parts": TWO_ROW_PARTS,
                 "optical": {"paths": TWO_ROW_PATHS}})
    assert len(got) == 1, got
    assert "front-order" in got[0]


def test_a_single_row_fibre_face_needs_nothing():
    """One `at.y` among the fibre parts - `at.x` alone is a safe reading, the
    same case every cassette built before this rule already models."""
    one_row = [{"id": "a", "ref": "common/lc-duplex-v-adapter@4", "at": [5.0, 3.0]},
               {"id": "b", "ref": "common/lc-duplex-v-adapter@4", "at": [20.0, 3.0]}]
    assert run88({"parts": one_row, "optical": {"paths": TWO_ROW_PATHS}}) == []


def test_stating_front_order_silences_l88():
    assert run88({"parts": TWO_ROW_PARTS,
                 "optical": {"front-order": ["a", "b"], "paths": TWO_ROW_PATHS}}) == []


def test_a_module_with_no_paths_is_not_l88s_business():
    assert run88({"parts": TWO_ROW_PARTS}) == []
