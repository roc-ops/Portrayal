"""The `approvals` comparable fact: one heading for the marks a box carries.

`certifications` and `other-approvals` are lists of safety marks, EMC marks and
country approvals as the maker prints them. They recur on dozens of devices
from several makers and nothing lined them up. This module holds what the fact
reads, what it leaves alone, and that it says what it mixes.
"""
import json
import pathlib

import pytest

import libdata

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import comparable as F

LIB = ROOT / "library"
KEYS = {"certifications", "other-approvals"}


def dev(attrs):
    return {"kind": "device", "name": "d", "chassis": {}, "attrs": attrs, "groups": {}}


def test_approvals_reads_exactly_the_two_keys():
    assert "approvals" in F.BY_NAME
    fact = F.BY_NAME["approvals"]
    assert {k for k, _, _ in fact.sources} == KEYS
    assert fact.section == "compliance" and fact.kind == F.TEXT


def test_approvals_says_it_mixes_marks_and_is_not_split():
    note = F.BY_NAME["approvals"].note or ""
    for word in ("safety", "EMC", "country", "not split"):
        assert word in note, f"the fact's note should say {word!r}: {note!r}"


def test_a_value_is_one_reading_with_the_makers_words_whole():
    raw = "UL/CSA 60950-1 and IEC 62368-1 safety, CB, CE, EN 55032 Class A, FCC Part 15 Class A"
    res = F.resolve(dev({"compliance": {"certifications": raw}}))
    rs = res["approvals"]["readings"]
    assert len(rs) == 1
    assert rs[0]["value"] == raw and rs[0]["vendor"] == raw
    assert rs[0]["from"] == "compliance/certifications"


def test_other_approvals_is_a_reading_of_the_same_fact():
    res = F.resolve(dev({"compliance": {"other-approvals": "MTCTE; NOM"}}))
    rs = res["approvals"]["readings"]
    assert [r["value"] for r in rs] == ["MTCTE; NOM"]
    assert rs[0]["from"] == "compliance/other-approvals"


def test_a_blank_value_is_no_reading():
    assert "approvals" not in F.resolve(dev({"compliance": {"certifications": " "}}))


@pytest.mark.parametrize("key", ["certification", "product-compliance", "psu-approvals",
                                 "regulatory", "regulatory-model", "compliance-programme"])
def test_a_neighbouring_spelling_is_not_an_approvals_source(key):
    """These sit near the two keys in the census and say something else: a
    programme a box is accepted into, a model number for the regulator, a
    directive. A different claim in this column is the failure the layer is
    built against."""
    assert key not in {k for k, _, _ in F.BY_NAME["approvals"].sources}
    assert "approvals" not in F.resolve(dev({"compliance": {key: "CE, FCC"}}))


def test_the_two_keys_leave_the_census_of_unclaimed_spellings():
    d = dev({"compliance": {"certifications": "CE", "other-approvals": "NOM"}})
    assert F.unclaimed(d) == []


def test_approvals_is_unlike_safety_emc_and_nebs():
    """Held structurally by the no-shared-key test; here, that the three
    established compliance facts keep their own spellings."""
    mine = {k for k, _, _ in F.BY_NAME["approvals"].sources}
    for name in ("safety", "emc", "nebs", "environmental-directives"):
        assert not mine & {k for k, _, _ in F.BY_NAME[name].sources}, name


@pytest.mark.heavy
def test_every_device_that_carries_a_source_key_resolves_an_approvals_reading():
    """Walks library/devices, never dist, so it cannot skip."""
    carriers = 0
    for slug, doc in libdata.devices():
        flat = F._flat(doc)
        has = [k for k in sorted(KEYS) if str(flat.get(k, (None, ""))[1]).strip()]
        if not has:
            continue
        carriers += 1
        got = F.resolve(doc).get("approvals", {}).get("readings", [])
        assert [r["from"].split("/")[-1] for r in got] == has, slug
        assert [r["vendor"] for r in got] == [str(flat[k][1]) for k in has], slug
    assert carriers, "no device carries certifications or other-approvals"


@pytest.mark.heavy
def test_the_published_coverage_equals_the_devices_that_carry_a_key():
    """Relative, not a number: the built index and the manifests must agree.
    Needs a built library/dist."""
    p = LIB / "dist" / "comparable-facts.json"
    if not p.exists():
        pytest.skip("library/dist not built - run ./build.sh")
    doc = json.loads(p.read_text())
    assert "approvals" in doc["vocabulary"]
    want = sum(1 for _, d in libdata.devices()
               if any(str(F._flat(d).get(k, (None, ""))[1]).strip() for k in KEYS))
    assert doc["coverage"].get("approvals", 0) == want
    assert not KEYS & set(doc["unclaimed"])
