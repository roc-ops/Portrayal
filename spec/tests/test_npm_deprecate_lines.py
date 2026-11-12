"""The helper that prints the `npm deprecate` lines for stale packages (#526).

It prints text and runs nothing, so what is pinned here is the text and the
choice of names: a package npm holds that this build no longer ships is
printed; one the build ships is not; the two scope packages that are published
by hand or deprecated once are never printed; and a list that is not a list of
this scope's packages is refused before anything is printed. The build is a
small dist made here.
"""
import ast
import json
import pathlib
import shlex

import pytest

from portrayal import npm_packages as P
from portrayal_dev import npm_deprecate_lines as D

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / "spec/tools/dev/npm_deprecate_lines.py"


@pytest.fixture
def dist(tmp_path):
    d = tmp_path / "dist"
    (d / "components").mkdir(parents=True)
    (d / "devices.json").write_text(json.dumps({"contract": 2, "devices": [
        {"name": "box-1", "ns": "acme"}, {"name": "box-2", "ns": "acme"}]}))
    (d / "components" / "acme--knob--v1--default.svg").write_text("<svg/>")
    (d / "rack-products.json").write_text(json.dumps({"racks": [
        {"vendor": "acme", "name": "frame", "file": "racks/acme-frame.json"}]}))
    return d


def _held(tmp_path, *names):
    f = tmp_path / "held.txt"
    f.write_text("\n".join(names) + "\n")
    return str(f)


def _lines(capsys, dist, held):
    assert D.main(["--dist", str(dist), "--held", held]) == 0
    return capsys.readouterr().out.splitlines()


def test_a_held_package_the_build_no_longer_ships_is_printed(dist, tmp_path, capsys):
    held = _held(tmp_path, "@portrayal/acme-box-1", "@portrayal/acme-old-box")
    lines = _lines(capsys, dist, held)
    assert [ln.split()[2] for ln in lines] == ["@portrayal/acme-old-box"]


def test_every_package_the_build_ships_is_left_alone(dist, tmp_path, capsys):
    held = _held(tmp_path, *P.package_names(dist))
    assert _lines(capsys, dist, held) == []


def test_the_line_is_npm_deprecate_name_and_the_message(dist, tmp_path, capsys):
    (line,) = _lines(capsys, dist, _held(tmp_path, "@portrayal/acme-old-box"))
    assert shlex.split(line) == ["npm", "deprecate", "@portrayal/acme-old-box", D.MESSAGE]
    assert "@portrayal/index" in D.MESSAGE


def test_the_names_come_out_sorted_and_once_each(dist, tmp_path, capsys):
    held = _held(tmp_path, "@portrayal/acme-z", "@portrayal/acme-a", "@portrayal/acme-z")
    assert [ln.split()[2] for ln in _lines(capsys, dist, held)] == [
        "@portrayal/acme-a", "@portrayal/acme-z"]


def test_blank_lines_and_comments_in_the_list_are_ignored(dist, tmp_path, capsys):
    held = _held(tmp_path, "", "# from npm access list", "@portrayal/acme-old-box", "  ")
    assert [ln.split()[2] for ln in _lines(capsys, dist, held)] == ["@portrayal/acme-old-box"]


@pytest.mark.parametrize("name", ["@portrayal/kit", "@portrayal/components"])
def test_a_package_that_is_not_made_by_the_build_is_never_printed(dist, tmp_path, capsys, name):
    """The kit is published by hand from kit/; `@portrayal/components` is the
    one package that was split and is deprecated once, by hand."""
    assert name in D.NOT_FROM_THE_BUILD
    assert _lines(capsys, dist, _held(tmp_path, name, "@portrayal/acme-old-box")) == [
        shlex.join(["npm", "deprecate", "@portrayal/acme-old-box", D.MESSAGE])]


@pytest.mark.parametrize("bad", ["acme-old-box", "@other/acme-old-box", "@portrayal/Bad Name",
                                 "@portrayal/"])
def test_a_name_outside_the_scope_is_an_error_and_prints_nothing(dist, tmp_path, capsys, bad):
    held = _held(tmp_path, "@portrayal/acme-old-box", bad)
    with pytest.raises(SystemExit) as e:
        D.main(["--dist", str(dist), "--held", held])
    assert e.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert bad in err


def test_a_list_with_nothing_stale_prints_nothing_and_says_so(dist, tmp_path, capsys):
    assert D.main(["--dist", str(dist), "--held", _held(tmp_path, "@portrayal/index")]) == 0
    out, err = capsys.readouterr()
    assert out == "" and "0 lines" in err


def test_nothing_but_the_lines_goes_to_standard_output(dist, tmp_path, capsys):
    D.main(["--dist", str(dist), "--held", _held(tmp_path, "@portrayal/acme-old-box")])
    out = capsys.readouterr().out
    assert out.endswith("\n")
    assert all(ln.startswith("npm deprecate ") for ln in out.splitlines())


def test_the_list_is_a_file_the_maintainer_made_not_a_call_to_npm(dist, tmp_path):
    with pytest.raises(SystemExit) as e:
        D.main(["--dist", str(dist)])
    assert e.value.code == 2


def test_the_module_runs_no_program_and_reaches_no_network():
    src = MODULE.read_text()
    for word in ("subprocess", "os.system", "socket", "urllib", "requests", "http"):
        assert word not in src, word
    imported = set()
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            imported.add(n.module.split(".")[0])
    assert not imported & {"subprocess", "os", "socket", "urllib", "requests", "http", "shutil"}
