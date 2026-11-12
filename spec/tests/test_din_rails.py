"""din-rails.json (#736): the DIN rail profiles as one sourced table. These pin the
published shape, that every figure names a document and a page of it, the figures
of the one profile the first build carries, and the slot rule that reproduces a
maker's own slot counts."""
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from portrayal import din_rails_index as dri

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def built():
    return dri.build()


def test_the_file_states_its_format_version_and_source(built):
    assert built["format"] == 1
    assert re.fullmatch(r"\d+\.\d+\.\d+", built["version"])
    assert built["generated-from"] == "spec/schemas/din-rails.yaml"


def test_every_source_is_a_public_https_url_with_a_page_count(built):
    assert built["sources"]
    for sid, s in built["sources"].items():
        assert s["title"] and s["url"].startswith("https://"), sid
        assert isinstance(s["pages"], int) and s["pages"] > 0, sid


def _figures(profile):
    """Every figure of a profile: the mappings that carry a `sources` list."""
    def walk(node, where):
        if isinstance(node, dict):
            if "sources" in node:
                yield where, node
            for k, v in node.items():
                if k != "sources":
                    yield from walk(v, f"{where}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{where}[{i}]")
    yield from walk(profile, "")


def test_every_figure_names_a_document_and_a_page_of_it(built):
    n = 0
    for pid, p in built["profiles"].items():
        for where, fig in _figures(p):
            n += 1
            assert fig["sources"], (pid, where)
            for ref in fig["sources"]:
                assert ref["id"] in built["sources"], (pid, where, ref)
                assert 1 <= ref["page"] <= built["sources"][ref["id"]]["pages"], (pid, where, ref)
    assert n >= 10, "the profile states hardly any figure - the walk is reading the wrong keys"


def test_the_first_build_carries_one_profile(built):
    assert list(built["profiles"]) == ["ts35x7.5"]
    assert built["profiles"]["ts35x7.5"]["id"] == "ts35x7.5"


def test_the_ts35x7_5_figures_are_the_ones_the_drawings_print(built):
    p = built["profiles"]["ts35x7.5"]
    s = p["section"]
    # AutomationDirect p1 and p4 (35.0, 7.5, 1.0, 27.0, 4.0 SYM.), RS PRO p3 (35, 7.5, 1, 27)
    assert (s["width"]["mm"], s["height"]["mm"], s["thickness"]["mm"]) == (35.0, 7.5, 1.0)
    assert (s["crown-outer"]["mm"], s["crown-inner"]["mm"], s["flange"]["mm"]) == (27.0, 25.0, 4.0)
    # 6.3 x 18 on 25 (AutomationDirect p1 and p4, Entrelec p1, ITC p2)
    sl = p["slot"]
    assert (sl["width"]["mm"], sl["length"]["mm"], sl["pitch"]["mm"]) == (6.3, 18.0, 25.0)
    # ITC p2: 0.35 kg per metre plain, 0.315 slotted
    assert (p["mass-kg-per-m"]["plain"], p["mass-kg-per-m"]["slotted"]) == (0.35, 0.315)


def test_the_two_crown_figures_are_one_measurement_taken_on_two_faces(built):
    # Entrelec p1 prints 25 and every other drawing 27: 27 less the sheet twice.
    s = built["profiles"]["ts35x7.5"]["section"]
    assert s["crown-inner"]["mm"] == s["crown-outer"]["mm"] - 2 * s["thickness"]["mm"]


def test_the_first_slot_centre_is_what_AutomationDirect_p4_draws(built):
    # p4: the last slot's end arc centres 6.7 from the cut end, an 18 long slot
    # with 6.3 wide ends, so its own centre is 6.7 + (18 - 6.3) / 2 from the end.
    sl = built["profiles"]["ts35x7.5"]["slot"]
    from_drawing = sl["end-to-arc-centre"]["mm"] + (sl["length"]["mm"] - sl["width"]["mm"]) / 2
    assert abs(from_drawing - sl["first-centre"]["mm"]) <= 0.1
    assert sl["first-centre"]["mm"] == sl["pitch"]["mm"] / 2


# AutomationDirect p4 (tTBL-126), "Steel DIN Rails Specifications (Pre-Cut Lengths)":
# length in millimetres and the number of slots the table lists.
AD_PRECUT = [(50, 2), (75, 3), (100, 4), (125, 5), (150, 6), (175, 7), (200, 8), (225, 9),
             (250, 10), (275, 11), (300, 12), (325, 13), (350, 14), (400, 16), (450, 18),
             (500, 20), (550, 22), (600, 24)]


@pytest.mark.parametrize("length,count", AD_PRECUT)
def test_the_slot_rule_gives_the_count_the_maker_lists(built, length, count):
    assert len(dri.slot_centres(built["profiles"]["ts35x7.5"], length)) == count


def test_a_slot_is_present_only_whole_and_the_first_is_half_a_pitch_in(built):
    p = built["profiles"]["ts35x7.5"]
    assert dri.slot_centres(p, 60) == [12.5, 37.5]
    assert dri.slot_centres(p, 20) == []
    assert dri.slot_centres(p, 1000)[-1] == 987.5


def test_a_slotless_length_is_a_length_not_an_error(built):
    assert dri.slot_centres(built["profiles"]["ts35x7.5"], 10) == []
    with pytest.raises(ValueError):
        dri.slot_centres(built["profiles"]["ts35x7.5"], 0)


def _doc():
    return copy.deepcopy(dri.load_table())


def test_the_shipped_table_has_no_problem():
    assert dri.problems(_doc()) == []


def test_a_figure_without_a_source_is_refused():
    d = _doc()
    d["profiles"]["ts35x7.5"]["section"]["width"]["sources"] = []
    assert any("section.width" in m and "no sources" in m for m in dri.problems(d))


def test_a_source_the_table_does_not_name_is_refused():
    d = _doc()
    d["profiles"]["ts35x7.5"]["section"]["width"]["sources"] = [{"id": "nobody", "page": 1}]
    assert any("unknown source 'nobody'" in m for m in dri.problems(d))


def test_a_page_the_document_does_not_have_is_refused():
    d = _doc()
    d["profiles"]["ts35x7.5"]["section"]["width"]["sources"] = [{"id": "rs-pro", "page": 9}]
    assert any("page 9" in m for m in dri.problems(d))


@pytest.mark.parametrize("key", ["width", "length", "pitch"])
def test_a_slot_figure_that_is_not_positive_is_refused(key):
    d = _doc()
    d["profiles"]["ts35x7.5"]["slot"][key]["mm"] = 0
    assert any(f"slot.{key}" in m and "positive" in m for m in dri.problems(d))


def test_a_slot_longer_than_its_pitch_is_refused():
    d = _doc()
    d["profiles"]["ts35x7.5"]["slot"]["length"]["mm"] = 30
    assert any("pitch" in m for m in dri.problems(d))


def test_a_profile_id_is_lower_case():
    d = _doc()
    d["profiles"]["TS35"] = d["profiles"].pop("ts35x7.5")
    assert any("id" in m for m in dri.problems(d))


def test_a_table_with_no_profile_is_refused():
    d = _doc()
    d["profiles"] = {}
    assert any("no profiles" in m for m in dri.problems(d))


def test_the_tool_writes_the_file_the_build_function_returns(built, tmp_path):
    subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/din_rails_index.py"),
                    "--schemas", str(ROOT / "spec/schemas"), "--out", str(tmp_path / "dist")],
                   check=True, capture_output=True, text=True)
    assert json.loads((tmp_path / "dist" / "din-rails.json").read_text()) == built


def test_the_build_runs_the_tool_with_no_library_walk():
    text = (ROOT / "build.sh").read_text()
    assert 'din_rails_index.py --schemas spec/schemas --out "$OUT"' in text
