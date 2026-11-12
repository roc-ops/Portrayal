"""Timing standards are read as timing, and a programme key holds programmes.

Three UfiSpace S9600 devices stated "IEEE 802.1CM fronthaul; ITU-T G.8273.2 T-BC
Class C" under `compliance-programme`. Those are timing and fronthaul standards,
so a comparison of timing support could not see them, while the key's other
value ("OCP Accepted and TIP DCSG compliant") is a programme a box is accepted
into. The statement now sits in each device's `timing` value, which the
`timing` fact reads, and the programme key is left to the programme.

These tests walk `library/devices`, never `library/dist`, so they cannot skip.
"""
import re

import pytest

import libdata
from portrayal import comparable as F

S9600 = ["ufispace/s9600-30dx", "ufispace/s9600-32x", "ufispace/s9600-72xc"]

# what a timing or synchronisation standard looks like in a value
TIMING_STANDARD = re.compile(
    r"G\.82\d\d|IEEE\s*1588|\bPTP\b|SyncE|Synchronous Ethernet|802\.1CM", re.I)


def _doc(slug):
    return dict(libdata.devices())[slug]


def _readings(slug, fact):
    return F.resolve(_doc(slug)).get(fact, {}).get("readings", [])


def test_no_programme_key_holds_a_timing_standard():
    seen = [(s, str(F._flat(d)["compliance-programme"][1]))
            for s, d in libdata.devices() if "compliance-programme" in F._flat(d)]
    assert seen, "no device carries a compliance-programme key"
    bad = [(s, v) for s, v in seen if TIMING_STANDARD.search(v)]
    assert not bad, f"a timing standard is filed as a programme: {bad}"


@pytest.mark.parametrize("slug", S9600)
def test_the_fronthaul_standards_are_in_the_timing_reading(slug):
    readings = _readings(slug, "timing")
    assert len(readings) == 1, "the standards belong to the one timing statement"
    text = readings[0]["vendor"]
    for needle in ("IEEE 802.1CM", "ITU-T G.8273.2 T-BC Class C"):
        assert needle in text, f"{slug}: timing does not state {needle}"


@pytest.mark.parametrize("slug", S9600)
def test_the_timing_statement_still_says_what_it_said_before(slug):
    text = _readings(slug, "timing")[0]["vendor"]
    for needle in ("Stratum 3E OCXO", "Time Sensitive Networking",
                   "asterisk against the whole"):
        assert needle in text, f"{slug}: timing lost {needle!r}"


def test_a_programme_key_is_not_a_source_of_any_fact():
    """The programme value must not turn up in a timing column."""
    claimed = {k for f in F.FACTS for (k, _, _) in f.sources}
    assert "compliance-programme" not in claimed
    assert "compliance-programme" in F.unclaimed(_doc("ufispace/s9500-30xs"))
