"""The dcTrack model list, written from the committed NetBox device types.

dcTrack holds a model by its make and model name, and an item names one of them
(its import template says the make and model must match an entry of the Models
Library). The list has one row for each model, under the maker that built it: a
NOS vendor's relisting of a box is the same metal and is not a second model.
The headers are the names the Models Library prints for its grid, except one
that is a declared stand-in.

The list is not committed: these tests read the committed device types, write
into a temporary folder and compare structure, never a row count or a version.
Nothing needs a build.
"""
import csv
import functools
import pathlib

import pytest
import yaml

from portrayal_dev import dctrack_export as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
TYPES = ROOT / "library/exports/netbox/device-types"
NOS = {"Arrcus", "IP Infusion", "DriveNets", "SONiC"}


@functools.lru_cache(maxsize=1)
def built():
    return D.models(TYPES)


@pytest.fixture(scope="module")
def written(tmp_path_factory):
    out = tmp_path_factory.mktemp("dctrack")
    D.write(out, TYPES)
    return out


def table(out):
    with open(out / "models.csv", newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def head(path):
    """The fields the list takes from one type file, read as YAML."""
    text = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(text.split("\ninterfaces:", 1)[0].split("\nconsole-ports:", 1)[0]
                         .split("\ncomments:", 1)[0].split("\nmodule-bays:", 1)[0]
                         .split("\npower-ports:", 1)[0].split("\nfront_image:", 1)[0]) or {}
    return doc


def by_key(rows):
    return {(r["make"], r["model"]): r for r in rows}


def test_one_row_per_make_and_model_and_none_for_a_relisting():
    rows, report = built()
    keys = [(r["make"], r["model"]) for r in rows]
    assert len(keys) == len(set(keys)), "a make and model is listed twice"
    assert report["relistings"] > 0
    assert not ({r["make"] for r in rows} & NOS)
    files = len(list(TYPES.glob("*/*.yaml")))
    assert len(rows) + report["relistings"] - report["relisted_without_own"] == files


def test_a_relisted_box_is_listed_once_under_its_real_maker():
    names = by_key(built()[0])
    assert ("UfiSpace", "S8901-54XC") in names
    for nos in NOS:
        assert (nos, "S8901-54XC") not in names
    assert not [k for k in names if k[1].startswith("NCP-")]


def test_a_makers_own_type_is_never_dropped():
    present = by_key(built()[0])
    for path in sorted(TYPES.glob("*/*.yaml"))[::25]:
        doc = head(path)
        if doc["manufacturer"] in NOS:
            continue
        assert (doc["manufacturer"], doc["model"]) in present, path


def test_the_headers_are_the_models_library_names_and_one_declared_stand_in(written):
    rows, _ = built()
    assert D.HEADERS == ("Make", "Model Name", "Height (RUs)", "Weight (kg)")
    assert D.PRINTED == ("Make", "Model Name", "Height (RUs)")
    assert D.STAND_INS == ("Weight (kg)",)
    assert set(D.PRINTED) | set(D.STAND_INS) == set(D.HEADERS)
    for r in rows:
        assert r["make"].strip() and r["model"].strip(), r
    lines = table(written)
    assert tuple(lines[0]) == D.HEADERS
    assert all(len(line) == len(D.HEADERS) for line in lines)
    assert len(lines) - 1 == len(rows)


def test_a_part_number_is_not_written_because_the_models_library_names_no_such_field(written):
    assert not any("part" in h.lower() for h in D.HEADERS)
    assert not any("part_number" in r for r in built()[0])
    text = (written / "README.md").read_text(encoding="utf-8")
    assert "part number" in text.lower()


def test_rows_are_sorted_by_make_then_model():
    keys = [(r["make"].casefold(), r["model"].casefold(), r["make"], r["model"]) for r in built()[0]]
    assert keys == sorted(keys)


def test_weight_is_the_files_own_in_kilograms():
    rows = by_key(built()[0])
    doc = head(TYPES / "Cisco/ASR-9006-AC-V2.yaml")
    row = rows[("Cisco", "ASR-9006-AC-V2")]
    assert float(row["weight_kg"]) == doc["weight"] and doc["weight_unit"] == "kg"
    for path in sorted(TYPES.glob("*/*.yaml"))[::30]:
        doc = head(path)
        row = rows.get((doc["manufacturer"], doc["model"]))
        if row is None:
            continue
        assert row["weight_kg"] == ("" if doc.get("weight") is None else D.number_text(doc["weight"]))


def test_a_fact_the_file_does_not_state_is_a_blank_cell_not_a_guess():
    rows, report = built()
    blank_weight = [r for r in rows if r["weight_kg"] == ""]
    assert blank_weight
    assert report["no_weight"] == len(blank_weight)
    assert not [r for r in rows if r["u_height"] == ""]


def test_a_weight_in_another_unit_is_not_written_as_kilograms(tmp_path):
    root = tmp_path / "device-types"
    (root / "Acme").mkdir(parents=True)
    (root / "Acme" / "Y1.yaml").write_text(
        "---\nmanufacturer: Acme\nmodel: Y1\nu_height: 1.0\nweight: 10.0\nweight_unit: lb\n", encoding="utf-8")
    rows, _ = D.models(root)
    assert rows[0]["weight_kg"] == "4.5359"


def test_u_height_is_the_device_types_as_written_half_and_zero_included():
    rows, report = built()
    by = by_key(rows)
    assert by[("Fibrain", "XCU10-51ID")]["u_height"] == "0.5"
    assert by[("Cisco", "ASR-9006-AC-V2")]["u_height"] == "10"
    assert report["half_units"] == len([r for r in rows if float(r["u_height"]) % 1]) > 0
    assert report["zero_u"] == len([r for r in rows if r["u_height"] == "0"]) > 0


@pytest.mark.heavy
def test_the_tool_run_twice_writes_identical_bytes(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    D.write(first, TYPES)
    D.write(second, TYPES)
    assert sorted(p.name for p in first.iterdir()) == ["README.md", "models.csv"]
    for name in ("models.csv", "README.md"):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_nothing_is_written_unless_the_tool_is_told_where(capsys):
    with pytest.raises(SystemExit) as exc:
        D.main([])
    assert exc.value.code == 2
    assert "--out" in capsys.readouterr().err
    assert not (ROOT / "library/exports/dctrack").exists()


def test_the_readme_names_the_stand_in_and_every_left_out_fact(written):
    text = (written / "README.md").read_text(encoding="utf-8")
    for header in D.HEADERS:
        assert f"`{header}`" in text, header
    assert "stand-in" in text
    for left_out in ("ports", "images", "connections", "port types", "Class", "Mounting", "Form Factor"):
        assert left_out in text, left_out
    assert "Nothing here has been loaded into a dcTrack" in text


def test_a_relisting_with_no_own_file_is_written_under_the_real_maker(tmp_path):
    root = tmp_path / "device-types"
    (root / "Arrcus").mkdir(parents=True)
    (root / "Acme").mkdir()
    (root / "Arrcus" / "X1.yaml").write_text(
        "---\nmanufacturer: Arrcus\nmodel: X1\nu_height: 2.0\nweight: 5.5\nweight_unit: kg\n"
        "part_number: ARC-X1\n"
        'comments: "Arrcus lists Acme X1 (NOS: arcos).\\nListed per: a list"\n', encoding="utf-8")
    (root / "Acme" / "Y1.yaml").write_text(
        "---\nmanufacturer: Acme\nmodel: Y1\nu_height: 1.0\npart_number: P-Y1\n", encoding="utf-8")
    rows, report = D.models(root)
    assert rows == [
        {"make": "Acme", "model": "X1", "u_height": "2", "weight_kg": "5.5"},
        {"make": "Acme", "model": "Y1", "u_height": "1", "weight_kg": ""}]
    assert report["relisted_without_own"] == 1
