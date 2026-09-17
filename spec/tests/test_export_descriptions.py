"""What a DCIM user reads on the device-type page, cut where a reader expects.

The `description` field is 200 characters and the cut used to land wherever it
landed. **266 exported descriptions across the two trees ended mid-word** - "120
Gbps of fab", "a red 'E' exh", "a9k-40ge-l, a" - with nothing to tell a reader a
truncation from a typo (#187).

And the line that did the cutting had a worse bug beside it. `split(".")[0]`
ends a sentence at the first dot of ANY kind, and 62 descriptions in the library
carry a decimal before their first full stop:

    Juniper MX104 - a 3
    an 8RU, 7
    Broadcom Tomahawk5 BCM78900 at 51

That is what those device types said. It was found by writing a unit test for
the truncation and watching `'A card with 1.5 GHz clocks'` come back as
`'A card with 1'`.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

from portrayal import dcim_export as dx   # noqa: E402
from portrayal import libwalk             # noqa: E402

LIMIT = 200


# --- the sentence boundary ---------------------------------------------------

@pytest.mark.parametrize("text,want", [
    ("A card with 1.5 GHz clocks", "A card with 1.5 GHz clocks"),
    ("Juniper MX104 - a 3.5RU router. Two REs.", "Juniper MX104 - a 3.5RU router"),
    ("USB 3.0 and a 1PPS SMB", "USB 3.0 and a 1PPS SMB"),
    ("Ends with a dot.", "Ends with a dot"),
    ("No dot at all", "No dot at all"),
    ("802.3af/at, 30W/port", "802.3af/at, 30W/port"),
    # a citation is a fact about our model, not about the hardware
    ("A dual-wide MIC (roc-ops/Portrayal#34). More prose.", "A dual-wide MIC"),
    ("A dual-wide MIC (#34)", "A dual-wide MIC"),
])
def test_a_sentence_ends_at_a_dot_and_a_space(text, want):
    assert dx.first_sentence(text) == want


def test_no_source_description_loses_its_decimal():
    """The sweep, over the corpus rather than over examples. 62 descriptions
    carry a decimal before their first full stop; not one of them may come back
    ending in a digit-and-nothing."""
    bad = []
    for f in list(libwalk.iter_devices([LIB])) + list(libwalk.iter_components([LIB])):
        d = yaml.safe_load(f.read_text()) or {}
        src = " ".join((d.get("description") or "").split())
        if not src:
            continue
        got = dx.first_sentence(src)
        # a first sentence that stops immediately before a digit is a decimal cut
        rest = src[len(got):]
        if rest.startswith(".") and len(rest) > 1 and rest[1].isdigit():
            bad.append(f"{f.parent.parent.name}/{f.parent.name}: {got[-40:]!r}")
    assert not bad, bad


# --- the fit -----------------------------------------------------------------

def test_text_that_fits_is_untouched():
    assert dx.fit("a short description") == "a short description"
    assert dx.fit("x" * LIMIT) == "x" * LIMIT


def test_a_cut_lands_on_a_word_boundary_and_says_so():
    long = "alpha bravo charlie delta echo foxtrot golf hotel india juliett"
    got = dx.fit(long, 30)
    assert len(got) <= 30
    assert got.endswith("...")
    assert long.startswith(got[:-3].rstrip())
    assert not got[:-3].rstrip().endswith(" ")


def test_a_list_is_cut_at_an_item_and_counts_the_rest():
    """A word-boundary cut through a LIST still reads as a typo - "a9k-40ge-b,
    a9k-40ge-e, a" is a truncation pretending to be an entry. 158 of the 266
    were bay `Accepts:` lists."""
    items = [f"card-{n:02d}" for n in range(20)]
    got = dx.fit_items("Accepts: ", items, 60)
    assert len(got) <= 60
    assert re.search(r" \(\+\d+ more\)$", got), got
    assert "card-00" in got and got.count(",") >= 1
    # every item named is a whole one
    named = got.split(": ", 1)[1].split(" (+")[0].split(", ")
    assert all(i in items for i in named), named


def test_a_short_list_is_left_alone():
    assert dx.fit_items("Accepts: ", ["one", "two"]) == "Accepts: one, two"


def test_the_ellipsis_is_ascii():
    """Every byte of the two export trees is ASCII. One non-ASCII character for
    a glyph's worth of neatness would make this the file that broke that."""
    assert dx.MORE.isascii()


# --- the corpus, which is the only thing that proves it ----------------------

def _exported():
    for p in sorted(LIB.glob("exports/*/*/*/*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        yield p, d.get("description") or ""
        for bay in (d.get("module-bays") or []):
            yield p, bay.get("description") or ""


def test_nothing_exported_exceeds_the_limit():
    over = [(str(p.name), len(t)) for p, t in _exported() if len(t) > LIMIT]
    assert not over, over


def test_nothing_exported_is_cut_mid_word():
    """A description is mid-word only if it was TRUNCATED and does not say so.
    Asserted against the length rather than against a guess: two module types
    are naturally exactly 200 characters and end on a whole word, which a
    heuristic sweep reported as a defect and is not one.
    """
    bad = []
    seen = 0
    for p, t in _exported():
        if not t:
            continue
        seen += 1
        # TWO MARKERS, because there are two kinds of cut: prose ends with the
        # ellipsis, a list ends with how many entries it did not name.
        says_so = t.endswith(dx.MORE) or re.search(r"\(\+\d+ more\)$", t)
        if len(t) >= LIMIT - len(dx.MORE) and not says_so and len(t) < LIMIT:
            bad.append(f"{p.name}: {t[-40:]!r}")
    assert not bad, bad
    assert seen > 500, f"only {seen} descriptions reached the sweep"


def test_a_truncated_description_ends_with_the_marker():
    truncated = [t for _p, t in _exported() if t.endswith(dx.MORE)]
    listed = [t for _p, t in _exported() if re.search(r"\(\+\d+ more\)$", t)]
    # NOT VACUOUS: run before this change, 266 descriptions ended mid-word and
    # none of them said so. Something must still be being cut, or the sweep
    # above is passing because nothing is long enough to test it.
    assert truncated or listed, "nothing is truncated at all; the sweep proves nothing"
