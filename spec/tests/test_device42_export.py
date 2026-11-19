"""The Device42 hardware-model sheet, written from the committed NetBox device types.

Device42's spreadsheet import takes a hardware model by name, with a type, a
size and a manufacturer all optional. The sheet lists each model once, under
the maker that built it: a NOS vendor's relisting of a box is the same metal
and is not a second model. The README says which column headers Device42's
import pages name and which are stand-ins the pages do not settle.

The sheet is not committed: these tests read the committed device types, write
into a temporary folder and compare structure, never a row count or a version.
Nothing needs a build.
"""
import csv
import functools
import pathlib

import pytest
import yaml

from portrayal_dev import device42_export as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
TYPES = ROOT / "library/exports/netbox/device-types"


@functools.lru_cache(maxsize=1)
def built():
    return D.hardware_models(TYPES)


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    out = tmp_path_factory.mktemp("device42")
    D.write(out, TYPES)
    return out


def table(out):
    with open(out / "hardware-models.csv", newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def head(path):
    """manufacturer, model and u_height of one type file, read as YAML."""
    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text.split("\ninterfaces:", 1)[0].split("\nconsole-ports:", 1)[0]
                         .split("\ncomments:", 1)[0]) or {}
    return doc.get("manufacturer"), doc.get("model"), doc.get("u_height")


def test_one_row_per_maker_and_model_and_none_for_a_relisting():
    rows, report = built()
    keys = [(r["manufacturer"], r["name"]) for r in rows]
    assert len(keys) == len(set(keys)), "a maker and model is listed twice"
    nos = {"Arrcus", "IP Infusion", "DriveNets", "SONiC"}
    assert report["relistings"] > 0
    # no NOS vendor is written as a maker of a box it only lists
    listed = {r["manufacturer"] for r in rows}
    assert not (listed & nos), listed & nos
    # every type file is either one row or one skipped relisting
    files = len(list(TYPES.glob("*/*.yaml")))
    assert len(rows) + report["relistings"] - report["relisted_without_own"] == files


def test_a_relisted_box_is_listed_once_under_its_real_maker():
    rows, _ = built()
    names = [(r["manufacturer"], r["name"]) for r in rows]
    assert ("UfiSpace", "S8901-54XC") in names
    assert ("Arrcus", "S8901-54XC") not in names
    assert ("IP Infusion", "S8901-54XC") not in names
    assert ("SONiC", "S8901-54XC") not in names
    # a name the NOS vendor gave the box is not a model of its own
    assert not [n for n in names if n[1].startswith("NCP-")]


def test_a_makers_own_type_is_never_dropped():
    rows, _ = built()
    present = {(r["manufacturer"], r["name"]) for r in rows}
    for path in sorted(TYPES.glob("*/*.yaml"))[::25]:
        maker, model, _ = head(path)
        if maker in {"Arrcus", "IP Infusion", "DriveNets", "SONiC"}:
            continue
        assert (maker, model) in present, path


def test_every_row_has_a_name_and_the_declared_columns_in_sequence(written):
    rows, _ = built()
    assert D.COLUMNS == ("name", "size", "manufacturer")
    for r in rows:
        assert list(r) == list(D.COLUMNS)
        assert r["name"].strip(), r
        assert r["manufacturer"].strip(), r
    lines = table(written)
    assert tuple(lines[0]) == D.COLUMNS
    assert all(len(line) == len(D.COLUMNS) for line in lines)
    assert len(lines) - 1 == len(rows)


def test_rows_are_sorted_by_maker_then_model():
    rows, _ = built()
    keys = [(r["manufacturer"].casefold(), r["name"].casefold(), r["manufacturer"], r["name"]) for r in rows]
    assert keys == sorted(keys)


def test_size_is_the_device_types_u_height_as_written():
    rows, report = built()
    by = {(r["manufacturer"], r["name"]): r["size"] for r in rows}
    fibrain = TYPES / "Fibrain/XCU10-51ID.yaml"
    maker, model, u = head(fibrain)
    assert (maker, model, u) == ("Fibrain", "XCU10-51ID", 0.5)
    assert by[(maker, model)] == "0.5"
    maker, model, u = head(TYPES / "Cisco/ASR-9006-AC-V2.yaml")
    assert by[(maker, model)] == "10"
    halves = [k for k, v in by.items() if float(v) % 1]
    assert len(halves) == report["half_units"] > 0
    for path in sorted(TYPES.glob("*/*.yaml"))[::40]:
        maker, model, u = head(path)
        if (maker, model) in by:
            assert float(by[(maker, model)]) == float(u)


def test_the_tool_run_twice_writes_identical_bytes(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    D.write(first, TYPES)
    D.write(second, TYPES)
    assert sorted(p.name for p in first.iterdir()) == ["README.md", "hardware-models.csv"]
    for name in ("hardware-models.csv", "README.md"):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_nothing_is_written_unless_the_tool_is_told_where(capsys):
    with pytest.raises(SystemExit) as exc:
        D.main([])
    assert exc.value.code == 2
    assert "--out" in capsys.readouterr().err
    assert not (ROOT / "library/exports/device42").exists()


def test_the_readme_names_every_header_as_named_on_the_page_or_as_a_stand_in(written):
    text = (written / "README.md").read_text(encoding="utf-8")
    assert not set(D.NAMED) & set(D.STAND_INS), "a header is both named and a stand-in"
    for column in D.NAMED + D.STAND_INS:
        assert f"`{column}`" in text, column
    assert "not confirmed against the import page" in text
    for left_out in ("ports", "images", "cables"):
        assert left_out in text
    assert "`type`" in text, "the README says why no type column is written"


def test_the_sheet_columns_are_headers_the_page_names():
    # the hardware-model sheet writes only parameters the import page names
    assert set(D.COLUMNS) <= set(D.NAMED)
    assert "type" in D.NAMED and "type" not in D.COLUMNS


def test_the_readme_says_what_the_pages_do_not_settle(written):
    text = (written / "README.md").read_text(encoding="utf-8")
    # the sheets are CSV; the pages name .xls and .xlsx and no other format
    assert ".xlsx" in text and "CSV" in text
    # the sample files' first three rows are not written
    assert "API endpoint, request method" in text
    assert "not written" in text


NOTE = ROOT / "docs/device42-export-design.md"


def test_the_design_note_rests_on_the_three_pages_it_cites():
    text = NOTE.read_text(encoding="utf-8")
    assert "was **not read**" not in text
    for title in ("Importing Data from Existing Spreadsheets",
                  "Spreadsheet Imports and Exports",
                  "Tutorial: Loading Data Using Spreadsheets"):
        assert title in text, title
    # what the pages say of the first three rows, the formats and the order
    for phrase in ("/api/1.0/buildings/", "Save the file as .xls or .xlsx", "Add Vendors"):
        assert phrase in text, phrase


def test_the_design_note_lists_each_header_as_named_or_a_stand_in():
    text = NOTE.read_text(encoding="utf-8")
    for column in D.NAMED + D.STAND_INS:
        assert f"`{column}`" in text, column
    assert "stand-in" in text


def test_a_model_name_shared_by_two_makers_is_counted():
    rows, report = built()
    seen = {}
    for r in rows:
        seen.setdefault(r["name"], set()).add(r["manufacturer"])
    shared = sorted(n for n, makers in seen.items() if len(makers) > 1)
    assert report["shared_names"] == len(shared)


def test_a_relisting_with_no_own_file_is_written_under_the_real_maker(tmp_path):
    root = tmp_path / "device-types"
    (root / "Arrcus").mkdir(parents=True)
    (root / "Acme").mkdir()
    (root / "Arrcus" / "X1.yaml").write_text(
        "---\nmanufacturer: Arrcus\nmodel: X1\nu_height: 2.0\n"
        'comments: "Arrcus lists Acme X1 (NOS: arcos).\\nListed per: a list"\n', encoding="utf-8")
    (root / "Acme" / "Y1.yaml").write_text(
        "---\nmanufacturer: Acme\nmodel: Y1\nu_height: 1.0\n", encoding="utf-8")
    rows, report = D.hardware_models(root)
    assert rows == [{"name": "X1", "size": "2", "manufacturer": "Acme"},
                    {"name": "Y1", "size": "1", "manufacturer": "Acme"}]
    assert report["relisted_without_own"] == 1
