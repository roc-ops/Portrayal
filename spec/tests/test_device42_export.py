"""The Device42 hardware-model sheet, written from the committed NetBox device types.

Device42's spreadsheet import takes a hardware model by name, with a type, a
size and a manufacturer all optional. The sheet lists each model once, under
the maker that built it: a NOS vendor's relisting of a box is the same metal
and is not a second model. The column headers are the issue's own field names,
declared as stand-ins in the README until the import page is read.

These tests read the committed files and write to a temporary folder; nothing
needs a build.
"""
import csv
import functools
import pathlib

import pytest
import yaml

from portrayal import device42_export as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
TYPES = ROOT / "library/exports/netbox/device-types"
OUT = ROOT / "library/exports/device42"


@functools.lru_cache(maxsize=1)
def built():
    return D.hardware_models(TYPES)


def committed():
    with open(OUT / "hardware-models.csv", newline="", encoding="utf-8") as fh:
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


def test_every_row_has_a_name_and_the_declared_columns_in_sequence():
    rows, _ = built()
    assert D.COLUMNS == ("name", "size", "manufacturer")
    for r in rows:
        assert list(r) == list(D.COLUMNS)
        assert r["name"].strip(), r
        assert r["manufacturer"].strip(), r
    table = committed()
    assert tuple(table[0]) == D.COLUMNS
    assert all(len(line) == len(D.COLUMNS) for line in table)


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


def test_the_committed_sheet_is_what_the_tool_writes(tmp_path):
    D.write(tmp_path, TYPES)
    for name in ("hardware-models.csv", "README.md"):
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes(), name


def test_the_readme_names_every_stand_in_header():
    text = (OUT / "README.md").read_text(encoding="utf-8")
    for column in D.STAND_INS:
        assert f"`{column}`" in text, column
    assert "not confirmed against the import page" in text
    for left_out in ("ports", "images", "cables"):
        assert left_out in text
    assert "`type`" in text, "the README says why no type column is written"


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
