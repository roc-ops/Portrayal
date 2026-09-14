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
