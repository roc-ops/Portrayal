"""The projection from a fibre graph to DCIM ports.

Pure functions over an index entry - no I/O here, so these run without a build.
"""
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))

import lint as L  # noqa: E402
import optical_ports as P  # noqa: E402

LIB = [str(ROOT / "library")]


def run86(doc, path="t/contract.yaml"):
    L.ERRORS.clear()
    L.lint_component_optical_polish(path, doc)
    return [e for e in L.ERRORS if "[L86]" in e]


def test_a_polished_family_needs_a_polish():
    """An LC adapter is sold UPC and APC and the enum has no bare `lc`."""
    doc = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1"}],
           "optical": {"paths": [{"from": "lc1.1", "to": "lc1.2"}]}}
    got = run86(doc)
    assert len(got) == 1, got
    assert "polish" in got[0]


def test_stating_the_polish_is_quiet():
    doc = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1"}],
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
    assert run86({"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1"}]}) == []


def test_the_real_cassette_states_its_polish():
    c = yaml.safe_load(
        (ROOT / "library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml").read_text())
    assert (c["optical"]).get("polish") == "upc"
    assert run86(c) == []


def test_the_cassettes_polish_is_marked_as_the_assumption_it_is():
    """FS names the polish on 19 of its 81 catalogue rows and does NOT name one
    for 57016. Recording `upc` is the convention default, not a sourced fact,
    and the contract has to say which - the same distinction plan 4 drew for the
    polarity map."""
    c = yaml.safe_load(
        (ROOT / "library/components/fs/fhd-1mtp6lcd-os2-a/v1/contract.yaml").read_text())
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
    return idx["fs/fhd-1mtp6lcd-os2-a@1"], idx


def test_the_rear_mtp_is_one_port_with_twelve_positions():
    """C1: a rear MPO-12 exports as ONE rear port, not twelve."""
    import dcim_export as D
    e, idx = cassette_entry()
    got = P.ports(D.contract_view(e), idx.get)
    assert got["rear"] == [{"name": "MTP-1", "type": "mpo", "positions": 12}]


def test_every_front_fibre_is_its_own_port():
    """C1: per-fibre granularity is what makes the projection lossless for the
    22 breakouts, 4 conversions and 4 mesh cassettes."""
    import dcim_export as D
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
    import dcim_export as D
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
    """
    import dcim_export as D
    contract = {
        "name": "t-coupler",
        "parts": [
            {"id": "common", "ref": "common/lc-duplex-adapter@3"},
            {"id": "split", "ref": "common/lc-duplex-adapter@3"},
        ],
        "optical": {
            "polish": "upc",
            "paths": [{"from": "common.1",
                       "to": [{"at": "split.1", "ratio": 50},
                              {"at": "split.2", "ratio": 50}]}],
        },
    }
    doc = D.build_module(contract, "Vendor", lambda ref: None)
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
    import dcim_export as D
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
    entry = {"parts": [{"id": "lc1", "ref": "common/lc-duplex-v-adapter@1",
                        "at": [0, 0]}],
             "faces": {"rear": {"ref": "t/rear@1"}},
             "optical": {"media": "os2", "polish": "upc",
                         "paths": [{"from": "rear:mtp.1",
                                    "to": [{"at": "lc1.1", "ratio": 50},
                                           {"at": "lc1.2", "ratio": 50}]}]}}
    known = {"common/lc-duplex-v-adapter@1": {"optical": {"positions": 2}},
             "common/mpo-adapter@1": {"optical": {"positions": 12}},
             "t/rear@1": {"parts": [{"id": "mtp", "ref": "common/mpo-adapter@1"}]}}
    m = P.fibre_map(entry, known.get, "TAP")
    assert len(m["rows"]) == 2
    assert all(r["ratio"] == 50 for r in m["rows"])
    assert {r["front"] for r in m["rows"]} == {"1", "2"}
