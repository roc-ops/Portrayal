"""The facts extractor must be wrong in only one direction.

It is allowed to miss a fact - a person still reads the document. It is not
allowed to state one the source does not, or to let an empty result look like a
vendor who published nothing. Those two turn a lookup into a confident wrong
answer, which is worse than no tool at all.

Fixtures are synthetic on purpose: the real intake is gitignored, and a test
that needs it would pass or fail depending on whose machine it ran on.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
from portrayal import facts as F


def make(tmp_path, name, body):
    d = tmp_path / "converted" / name
    d.mkdir(parents=True)
    (d / "doc.md").write_text(body)
    return d


def test_a_numeral_the_converter_broke_is_still_read():
    """docling drops spaces into numbers - `87. 7`, `19 . 86`. Read as 87 the
    fraction disappears silently, and a chassis is 0.7mm short forever."""
    assert F._num("87. 7") == 87.7
    assert F._num("19 . 86") == 19.86
    assert F._num("436") == 436.0
    assert F._num("not a number") is None


def test_dimensions_come_back_with_the_line_they_were_read_from(tmp_path):
    make(tmp_path, "x-datasheet",
         "## PHYSICAL\n\n2RU, 436 x 762 x 87. 7 mm\n\nWeight: 19 . 86 kg\n")
    f = F.collect(tmp_path, "x")
    assert f["summary"]["ru"] == 2
    got = [e for e in f["dimensions"] if e["mm"] == [436.0, 762.0, 87.7]]
    assert got, f["dimensions"]
    assert got[0]["source"].endswith("doc.md:3"), got[0]["source"]
    assert "436" in got[0]["text"]
    assert any(abs(e["kg"] - 19.86) < 1e-9 for e in f["weight"])


def test_two_documents_agreeing_is_reported_as_agreement(tmp_path):
    """A datasheet and an installation guide stating the same triple is
    evidence. Neither is visible while the numbers sit in two PDFs nobody read
    side by side."""
    make(tmp_path, "x-datasheet", "## PHYSICAL\n\n2RU, 436 x 762 x 87.7 mm\n")
    make(tmp_path, "x-hig",
         "## Component Physical Information\n\n"
         "| Dimension | X (W x D x H) | 17.16' x 30' (436 x 762 x 87.7mm) |\n")
    f = F.collect(tmp_path, "x")
    corr = f["summary"]["corroborated-dimensions"]
    assert len(corr) == 1
    assert corr[0]["mm"] == [436.0, 762.0, 87.7]
    assert corr[0]["stated-in"] == ["x-datasheet", "x-hig"]


def test_a_document_that_names_specs_and_states_none_says_so(tmp_path):
    """THE TRAP THIS EXISTS FOR. A vendor datasheet set in outlined glyphs
    converts to its LABELS and none of its VALUES: 93 distinct words, every one
    of them a disclaimer or a heading, and not one number. A word count calls
    that a full document. An empty facts file then looks exactly like a vendor
    who publishes nothing, and only one of those is a claim about the world."""
    d = make(tmp_path, "x-datasheet",
             "## KEY FEATURES\n\n- ■\n- ■\n\n"
             "Power Supply\n\nMemory\n\nProcessor\n\nSpecifications\n\n"
             "All information provided herein is subject to change without notice\n")
    (d / "fig-0001.png").write_bytes(b"")
    f = F.collect(tmp_path, "x")
    assert "text-free" in f, "a labels-only document must be called out"
    tf = f["text-free"][0]
    assert tf["values-extracted"] == 0
    assert tf["images"] == 1
    assert "vendor is silent" in tf["meaning"]


def test_a_document_with_values_is_not_flagged_text_free(tmp_path):
    """The flag has to be specific or it is noise: a real document names specs
    AND states them."""
    make(tmp_path, "x-datasheet",
         "## PHYSICAL\n\nPower Supply\n\nMemory\n\nProcessor\n\n"
         "2RU, 436 x 762 x 87.7 mm\n")
    f = F.collect(tmp_path, "x")
    assert "text-free" not in f


def test_ordering_lines_are_picked_out_because_they_decide_which_part(tmp_path):
    """An ordering line names what a chassis can actually be bought with, which
    is what decides which library component a bay may seat. Three near-identical
    fans differ only by this suffix."""
    make(tmp_path, "x-datasheet",
         "## Available to Order\n\n## Fan Types\n\n"
         "FAN-803816-HC, exhaust air flow\n\n## Power Supply Types\n\n"
         "PSU-202-AESR, 2000W AC, exhaust air flow\n")
    f = F.collect(tmp_path, "x")
    assert f["summary"]["ordering-parts"] == ["FAN-803816-HC", "PSU-202-AESR"]
    fan = [e for e in f["ordering"] if e["part"].startswith("FAN")][0]
    assert fan["section"] == "Fan Types"


def test_a_value_whose_label_is_on_another_line_is_still_found(tmp_path):
    """FOUND BY THE FIRST DEVICE THIS TOOL WAS TRUSTED ON. The converter reflows
    a two-column spec block into `Power Consumption`, blank, `1300 Watts
    maximum`. A rule wanting the label and the number in one line finds neither
    and reports the chassis's whole power figure as absent - and an agent that
    believed the empty field would ship a model with no wattage at all."""
    make(tmp_path, "x-qsg",
         "## SPECS\n\nPower Consumption\n\n1300 Watts maximum\n")
    f = F.collect(tmp_path, "x")
    hit = [e for e in f["power"] if e.get("watts") == 1300.0]
    assert hit, f["power"]
    assert hit[0]["label"].startswith("Power Consumption")
    assert hit[0]["source"].endswith(":5")


def test_an_ordering_table_is_read_as_well_as_ordering_lines(tmp_path):
    """Vendors write the same fact two ways. One lists `PSU-202-AESR, 2000W AC`;
    another gives a five-column markdown table of model and part numbers. Both
    name what the chassis can actually be BOUGHT with, which is what decides
    which library component a bay may seat - so a tool that reads only one
    format is silently empty for half the corpus."""
    make(tmp_path, "x-datasheet",
         "## Ordering Information\n\n"
         "| ModelNumber | PartNumber | PSU | Airflow |\n"
         "|---|---|---|---|\n"
         "| 9716-32D-O-AC-F-US | FP5ZZ8632400A | DualACPSUs | Front-to-Back |\n"
         "| 9716-32D-O-AC-B-EU | FP5ZZ8632201A | DualACPSUs | Back-to-Front |\n")
    f = F.collect(tmp_path, "x")
    parts = f["summary"]["ordering-parts"]
    assert "9716-32D-O-AC-F-US" in parts and "9716-32D-O-AC-B-EU" in parts
    assert "ModelNumber" not in parts, "the header row is not a part"
    row = [e for e in f["ordering"] if e["part"].endswith("F-US")][0]
    assert "FP5ZZ8632400A" in row["row"], "the whole row is kept, not just the id"


def test_the_summary_never_says_the_vendor_is_silent(tmp_path):
    """The one sentence this file must always carry: absence is the tool's, not
    the vendor's."""
    make(tmp_path, "x-datasheet", "## PHYSICAL\n\n2RU\n")
    f = F.collect(tmp_path, "x")
    assert "NOT that the vendor is silent" in f["summary"]["note"]
