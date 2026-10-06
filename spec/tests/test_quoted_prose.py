"""L107: a vendor's facts are transcribed, its prose is not reproduced (#451).

README promises it and NOTICE rests on it. #156 paraphrased the library back
into line once and nothing held it there. L107 landed as a census warning over
341 quoted runs (#472), the library was paraphrased vendor by vendor, and at
zero the rule became an error. These tests hold the zero, and prove the quote
pairing finds what it should and nothing else - because a sweep that passes by
finding nothing also passes when its pattern has stopped matching.
"""
import pathlib
import re

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


# THE REST OF THE TREE (#661). L107 reads contracts and manifests, and its
# pairing stops at a line break - so a wrapped Markdown quotation was invisible,
# and one 46-word guide passage sat in docs/casa-modular-chassis.md for a month.
# This sweep reads every other place prose is written, with line breaks joined,
# and holds it to the same 25 words. No exemption list: the library's own
# example sentences keep under the cap too, which costs a few words each.
_DOCS = ("README.md", "CONTRIBUTING.md", "PRIOR-ART.md", "SECURITY.md",
         "CODE_OF_CONDUCT.md", "CHANGELOG.md", "AGENTS.md")


def _joined(text):
    return re.sub(r"\s*\n\s*", " ", text)


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)


def _prose_files():
    md = [ROOT / p for p in _DOCS if (ROOT / p).exists()]
    md += sorted(ROOT.glob("docs/**/*.md")) + sorted(ROOT.glob("spec/*.md"))
    # the changelog's unreleased entries, one file per pull request until a
    # version is cut and they are folded into CHANGELOG.md
    md += sorted(ROOT.glob("changelog.d/*.md"))
    ym = []
    for pattern in ("library/devices/**/layout.yaml", "library/labs/**/*.yaml",
                    "library/devices/**/listings/*.yaml",
                    "library/devices/**/overlays/*.yaml", "spec/schemas/*.yaml"):
        ym += sorted(ROOT.glob(pattern))
    return md, ym


def _long_runs_in(path):
    if path.suffix == ".md":
        texts = [_joined(path.read_text(encoding="utf-8"))]
    else:
        texts = [_joined(s) for s in _strings(yaml.safe_load(path.read_text(encoding="utf-8")))]
    return [(n, q) for t in texts for _, n, q in lint.long_quotes(t)]


def test_no_doc_or_other_yaml_quotes_a_long_passage():
    md, ym = _prose_files()
    assert len(md) > 20 and len(ym) > 20, "the prose walk found almost nothing - it is broken"
    hits = [(str(p.relative_to(ROOT)), n, q[:80]) for p in md + ym for n, q in _long_runs_in(p)]
    assert not hits, (
        f"{len(hits)} quoted run(s) over {lint.QUOTE_MAX_WORDS} words outside the manifests. "
        "Paraphrase vendor text; trim the library's own example sentences.\n  " +
        "\n  ".join(f"{p} ({n} words): {q}" for p, n, q in hits[:10]))


def test_a_quotation_wrapped_across_lines_is_still_seen(tmp_path):
    """The line-break blind spot, planted: 30 words split over three lines."""
    words = " ".join(["word"] * 10)
    planted = tmp_path / "planted.md"
    planted.write_text(f'The guide says "{words}\n{words}\n{words}" and so on.\n')
    assert [n for n, _ in _long_runs_in(planted)] == [30]
