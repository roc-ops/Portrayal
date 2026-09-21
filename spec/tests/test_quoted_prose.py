"""L107: a vendor's facts are transcribed, its prose is not reproduced (#451).

README promises it and NOTICE rests on it. #156 paraphrased the library back
into line once and nothing held it there, so this is the thing that holds it: a
census over every contract and manifest, an upper bound that each vendor's
paraphrasing pass lowers, and cases proving the quote pairing finds what it
should and nothing else - because a sweep that passes by finding nothing also
passes when its pattern has stopped matching.
"""
import pathlib

import pytest
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

# THE CEILING. 341 runs on the day L107 landed (2026-09-21). Lower it in the
# same commit that paraphrases some - an upper bound, not an equality, so
# fixing one never fails the suite, and adding one always does.
CEILING = 341


def _manifests():
    for p in sorted(LIB.glob("components/**/contract.yaml")):
        yield p
    for p in sorted(LIB.glob("devices/**/device.yaml")):
        yield p


def _runs():
    out = []
    for p in _manifests():
        for key, n, text in lint.long_quotes(yaml.safe_load(p.read_text())):
            out.append((str(p.relative_to(LIB)), key, n, text))
    return out


def test_l107_is_registered():
    assert lint.RULES["L107"][0] == "component, device"


def test_the_census_reads_the_library():
    """NON-VACUITY: the walk found the library, and the census found the
    backlog it is holding - if it read nothing, every bound below passes."""
    assert sum(1 for _ in _manifests()) > 700
    assert _runs(), "no long quotations anywhere - retire this census and make L107 an error"


def test_the_backlog_does_not_grow():
    runs = _runs()
    assert len(runs) <= CEILING, (
        f"{len(runs)} quoted runs over {lint.QUOTE_MAX_WORDS} words, up from {CEILING}. "
        "Paraphrase the new one and cite the section; a state table is transcribed as "
        "`state = meaning` pairs, not quoted.\n  " +
        "\n  ".join(f"{p} {k} ({n} words)" for p, k, n, _ in runs[:10]))


def test_the_distinct_passages_do_not_grow():
    """TWO NUMBERS, BECAUSE MOST OF THE BACKLOG IS COPIES. One guide paragraph
    sits in 23 contracts, so the run count above moves by 23 when that one
    passage is paraphrased and by 1 when a new passage arrives. Counting the
    distinct passages as well means a new one cannot hide inside the slack a
    big paraphrase leaves under the run ceiling."""
    distinct = {t for _, _, _, t in _runs()}
    assert len(distinct) <= 156, f"{len(distinct)} distinct long quotations, up from 156"


@pytest.mark.parametrize("text,runs", [
    # what #451 is about: a guide sentence quoted whole
    ('the guide says "' + " ".join(["word"] * 26) + '" and so', 1),
    ("the guide says “" + " ".join(["word"] * 26) + "”", 1),
    ("the guide says '" + " ".join(["word"] * 26) + "'", 1),
    # at the cap, not over it
    ('"' + " ".join(["word"] * 25) + '"', 0),
    # inch marks never open a quote, so a dimension row is not a quotation
    ('17.32" x 9.84" x 1.71" ' + " ".join(["w"] * 30) + ' 2"', 0),
    # quoted numerals are short quotes, not the start of a long one
    ("prints '1' and '3' above " + " ".join(["w"] * 30) + " and '2'", 0),
    # apostrophes inside words neither open nor close
    ("the vendor's guide doesn't " + " ".join(["w"] * 30) + " it's", 0),
])
def test_the_pairing_finds_quotations_and_nothing_else(text, runs):
    assert len(list(lint.long_quotes({"note": text}))) == runs, text


def test_the_key_path_names_where_the_quote_is():
    data = {"provenance": {"lamp": {"note": '"' + " ".join(["w"] * 30) + '"'}},
            "gaps": [{"note": "fine"}]}
    [(key, n, _)] = list(lint.long_quotes(data))
    assert (key, n) == ("provenance.lamp.note", 30)
