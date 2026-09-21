"""A swap survives a reload.

The explorer writes its swap state into its own URL - `swap=<k>~<ref>,<k>~`,
key and ref each `encodeURIComponent`-ed, an empty ref an emptied bay or cage
- and the m1. share codec carries the same map as array slot 7. Two promises
are held here beside the round trips: an older m1. link and an un-swapped
document encode and decode byte-identically to the codec before `swaps`
existed (hard-coded strings produced by that code), and a garbage `swap=`
value decodes to nothing rather than throwing.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/swap-state.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


MAP = {
    "slot-1/module/ppm-2": "generic/ppm-blank@1",
    "port-4": "generic/qsfp-lc@1",
    "slot-0": None,
    "port-9": None,
    "weird,key~x": "ns/odd@2",
}


def test_the_url_form_round_trips(out):
    assert out["roundTrip"] == MAP
    assert out["encodedAgain"] == out["encoded"]
    assert out["orderFree"], "the swap string must not depend on key order"
    assert out["empty"] == ""


def test_the_url_form_is_the_documented_one(out):
    parts = out["encoded"].split(",")
    assert len(parts) == len(MAP), "a separator inside a key leaked"
    assert all(p.count("~") == 1 for p in parts), parts
    assert "port-4~generic%2Fqsfp-lc%401" in parts
    assert "slot-0~" in parts and "port-9~" in parts
    assert "slot-1%2Fmodule%2Fppm-2~generic%2Fppm-blank%401" in parts


def test_garbage_decodes_to_nothing(out):
    assert out["garbage"] == [{}] * len(out["garbage"])
    assert out["partial"] == {"port-4": "generic/qsfp-lc@1"}
    assert out["protoClean"]


def test_an_unswapped_document_encodes_as_it_always_did(out):
    assert out["unswappedIdentical"] == [True, True]
    assert out["unswappedEmptyMapIdentical"] == [True, True]


def test_an_older_link_decodes_with_no_swaps(out):
    assert out["oldLinkSwaps"] == [{}, {}]
    assert out["oldLinkMarks"] == [2, 0]


def test_a_swapped_document_round_trips(out):
    assert out["swappedDiffers"] and out["swappedPrefix"]
    assert out["swappedBack"] == {"port-4": "generic/qsfp-lc@1", "slot-0": None,
                                  "slot-1/module/ppm-2": "generic/ppm-blank@1"}
    assert out["swappedRest"], "adding swaps changed another field"


def test_normalise_keeps_swaps_and_drops_junk(out):
    assert out["normaliseDefault"] == {}
    assert out["normaliseJunk"] == [{}, {}, {"b": "ns/x@1", "c": None}]


def test_the_query_string_is_read_and_written_raw(out):
    assert out["searchBack"] == MAP, "the swap string was decoded twice"
    assert out["search"].startswith("?device=s9510-28dc&config=dc&view=front&swap=")
    assert out["searchDevice"] == "s9510-28dc"
    assert out["searchTex"] == "flat", "a parameter the explorer does not own was dropped"
    assert out["searchNoSwap"] == "?device=a", "an empty swap map must remove the parameter"
    assert out["searchMissing"] is None
