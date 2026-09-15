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
