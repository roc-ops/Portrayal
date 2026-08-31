"""`portfolio` - where a device sits in its vendor's own catalogue.

The block is three free-text fields plus a list, and free text is the point:
the schema says the vocabulary is to be harvested from what accumulates, not
designed up front. What this file pins is not a vocabulary but a discipline -
the words are the VENDOR'S words, copied from the vendor's own pages, so that
someone reading a model here and then opening the vendor's site sees the same
labels. A paraphrase is a small lie that only shows up when somebody goes
looking for "Open Aggregation Router" and finds "aggregation switch".

The UfiSpace pass is the worked example. Their catalogue has two axes at once:
the top nav files a box under Telecoms / AI Networking / Cloud & Data Centers,
and within Telecoms the menu groups by marketing series. Both are recorded.
Data-center and AI boxes get no `series` because the vendor publishes none for
them - the grouping there is by port speed, and inventing a series to fill the
field would be the same small lie in the other direction.
"""
import pathlib
import re
import sys

import yaml

import libdata

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def devices(ns=None):
    """Over the once-parsed library - see libdata."""
    for slug, f, d in libdata.library():
        if ns and f.parent.parent.name != ns:
            continue
        yield f, d


# ---- the shape of the block -------------------------------------------------

def test_a_portfolio_block_carries_no_empty_fields():
    """An empty string is worse than an absent key: it reads as an answer."""
    bad = []
    for f, d in devices():
        for k, v in (d.get("portfolio") or {}).items():
            if isinstance(v, str) and not v.strip():
                bad.append(f"{f.parent.name}:{k}")
    assert not bad, bad


def test_also_listed_in_never_repeats_the_primary_line():
    """`also-listed-in` is where the device appears BESIDES `line`. Repeating
    the primary there would double-count it in any consumer that unions them."""
    bad = []
    for f, d in devices():
        p = d.get("portfolio") or {}
        if p.get("line") and p.get("line") in (p.get("also-listed-in") or []):
            bad.append(f.parent.name)
    assert not bad, bad


def test_a_device_listed_twice_is_reachable_from_both_categories():
    """THE POINT OF THE FIELD. A consumer filtering by category unions `line`
    with `also-listed-in`; a box the vendor files under two categories has to
    come back from either filter."""
    def in_category(d, cat):
        p = d.get("portfolio") or {}
        return cat == p.get("line") or cat in (p.get("also-listed-in") or [])

    found = {}
    for f, d in devices():
        for cat in ("Telecoms", "AI Networking", "Cloud & Data Centers"):
            if in_category(d, cat):
                found.setdefault(cat, set()).add(f.parent.name)

    # UfiSpace file these three under two categories each
    assert "s9720-56ed" in found["Telecoms"] and "s9720-56ed" in found["AI Networking"]
    assert "s9725-64e" in found["Telecoms"] and "s9725-64e" in found["AI Networking"]
    for m in ("s9321-64e", "s9321-64eo"):
        assert m in found["AI Networking"] and m in found["Cloud & Data Centers"], m


# ---- what UfiSpace publishes ------------------------------------------------

UFI_LINES = {"Telecoms", "AI Networking", "Cloud & Data Centers"}
UFI_SERIES = {"Fronthaul Series", "S9500 Series", "S9600 Series", "S9700 Series"}


def test_every_ufispace_device_says_where_it_sits():
    missing = [f.parent.name for f, d in devices("ufispace") if not (d.get("portfolio") or {})]
    assert not missing, missing


def test_ufispace_lines_are_the_vendors_own_nav_categories():
    bad = []
    for f, d in devices("ufispace"):
        p = d["portfolio"]
        for cat in [p.get("line")] + list(p.get("also-listed-in") or []):
            if cat not in UFI_LINES:
                bad.append(f"{f.parent.name}:{cat}")
    assert not bad, bad


def test_a_ufispace_series_is_one_the_vendor_actually_prints():
    """Spelled as the menu prints it, "S9600 Series" and not "S9600", because
    the whole reason to record it is that it matches what a reader sees on the
    vendor's site."""
    bad = [f"{f.parent.name}:{d['portfolio']['series']}"
           for f, d in devices("ufispace")
           if d["portfolio"].get("series") and d["portfolio"]["series"] not in UFI_SERIES]
    assert not bad, bad


def test_only_telecoms_boxes_carry_a_series():
    """UfiSpace publishes series names under Telecoms only - the data-center and
    AI catalogues group by port speed. A series on one of those would be
    invented, and the field is meant to be copied, not inferred."""
    bad = []
    for f, d in devices("ufispace"):
        p = d["portfolio"]
        listed = {p.get("line")} | set(p.get("also-listed-in") or [])
        if p.get("series") and "Telecoms" not in listed:
            bad.append(f"{f.parent.name}:{p['series']}")
    assert not bad, bad


def test_the_series_matches_the_model_number():
    """S96xx sits in the S9600 Series. That the vendor's own grouping is exactly
    by model-number prefix is what made the menu safe to read off - it is
    checked here so a future hand-edit that breaks the pattern gets looked at
    rather than absorbed."""
    bad = []
    for f, d in devices("ufispace"):
        s = d["portfolio"].get("series")
        if not s or not s.startswith("S9"):
            continue
        if not re.match(rf"^{s[:3]}\d", f.parent.name.upper()):
            bad.append(f"{f.parent.name} is filed under {s}")
    assert not bad, bad
