"""L107: a vendor's facts are transcribed, its prose is not reproduced (#451).

README promises it and NOTICE rests on it. #156 paraphrased the library back
into line once and nothing held it there. L107 landed as a census warning over
341 quoted runs (#472), the library was paraphrased vendor by vendor, and at
zero the rule became an error. These tests hold the zero, and prove the quote
pairing finds what it should and nothing else - because a sweep that passes by
finding nothing also passes when its pattern has stopped matching.
"""
import pathlib

import pytest
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def _manifests():
    for p in sorted(LIB.glob("components/**/contract.yaml")):
        yield p
    for p in sorted(LIB.glob("devices/**/device.yaml")):
        yield p


def test_l107_is_registered():
    assert lint.RULES["L107"][0] == "component, device"


def test_the_walk_reads_the_library():
    """NON-VACUITY: the zero below means nothing if the walk found nothing."""
    assert sum(1 for _ in _manifests()) > 700


def test_no_contract_or_manifest_quotes_a_long_passage():
    runs = [(str(p.relative_to(LIB)), key, n)
            for p in _manifests()
            for key, n, _ in lint.long_quotes(yaml.safe_load(p.read_text()))]
    assert not runs, (
        f"{len(runs)} quoted run(s) over {lint.QUOTE_MAX_WORDS} words. Paraphrase and cite "
        "the section; a state table is transcribed as `state = meaning` pairs, not quoted.\n  " +
        "\n  ".join(f"{p} {k} ({n} words)" for p, k, n in runs[:10]))


def test_l107_is_an_error_not_a_warning():
    """The census is over: a long quotation fails the build rather than joining
    a baseline. Planted, because the library itself now has none to find."""
    data = {"provenance": {"lamp": '"' + " ".join(["word"] * 30) + '"'}}
    with lint.collecting() as found:
        lint.lint_quoted_prose("planted/contract.yaml", data)
    assert [e for e in found.errors if "[L107]" in e]
    assert not [w for w in found.warnings if "[L107]" in w]


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
