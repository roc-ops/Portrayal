"""The m1. share link carries fields (#483).

The link has carried swaps since #441 (slot 7), so it reproduces which optic is
in which port - and nothing written ON a part: an optic's `latch-color` and
`label`, a supply's wattage. `marks.js` now carries `fields`, the shape of the
shell's `state.cfgFields` and of the 3D viewer's `setFields`, as slot 8.

Held beside the round trips, as the swap-state test holds it for swaps: every
link written before this, and every document without fields, encodes and
decodes byte-identically to the codec before `fields` existed (hard-coded
strings produced by that code). A document with fields and no swaps puts 0 in
slot 7, the value decode already reads as "no swaps".
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/share-fields.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_an_unfielded_document_encodes_as_it_always_did(out):
    assert out["unfieldedIdentical"] == [True, True]
    assert out["emptyFieldsIdentical"] == [True, True]
    assert out["junkFieldsIdentical"] == [True, True], "fields that normalise to nothing added a slot"


def test_an_older_link_decodes_with_no_fields(out):
    assert out["oldLinkFields"] == [{}, {}]
    assert out["oldLinkSwaps"] == [{"port-4": "generic/sfp-lc@1", "slot-0": None}, {}]


def test_fields_round_trip(out):
    assert out["roundTrip"] == {
        "port-4-occupant": {"latch-color": "#c22f2f", "label": "uplink-A"},
        "psu-1/module": {"watts": "750W", "label": None},
        "port-9-occupant": {"label": ""},
    }
    assert out["roundTripSwaps"] == {"port-4": "generic/sfp-lc@1", "slot-0": None}
    assert out["roundTripRest"], "adding fields changed another part of the document"
    assert out["reencoded"] and out["orderFree"]


def test_a_fields_only_document(out):
    assert out["fieldsOnlyBack"] == {"port-4-occupant": {"latch-color": "#2255aa"}}
    assert out["fieldsOnlySwaps"] == {}
    assert out["fieldsOnlyRest"]
    assert out["fieldsOnlyTail"], "slot 7 is not 0 in front of the fields"


def test_garbage_is_dropped_entry_by_entry(out):
    assert out["normaliseDefault"] == {}
    assert out["normaliseJunk"] == [
        {}, {}, {},
        {"p": {"label": "kept", "cleared": None, "empty": "", "ctl": "ab"}},
    ]
    assert out["protoClean"]
    assert out["rawJson"] == {"p": {"label": "L"}}
