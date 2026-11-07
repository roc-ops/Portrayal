"""The helper that prints the `npm trust` lines for the packages (#526).

It prints text and runs nothing, so what is pinned here is the text: the flags
npm's command asks for, the order `package_names` gives, and that the three
constants the line is built from are the workflow's own file name and the
environment its job names. The list is read off a small dist built here.
"""
import ast
import json
import pathlib

import pytest
import yaml

from portrayal import npm_packages as P
from portrayal_dev import npm_trust_lines as T

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE = ROOT / "spec/tools/dev/npm_trust_lines.py"

FLAGS = ["--file", "release.yml", "--repository", "roc-ops/Portrayal",
         "--environment", "npm", "--allow-publish", "--yes"]


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


def _lines(capsys, *argv):
    assert T.main(list(argv)) == 0
    out = capsys.readouterr().out
    return out.splitlines()


def test_one_line_per_package_in_the_order_of_the_list(dist, capsys):
    names = P.package_names(dist)
    lines = _lines(capsys, "--dist", str(dist))
    assert len(names) == 5
    assert [ln.split()[3] for ln in lines] == names


def test_every_line_carries_every_flag_the_command_asks_for(dist, capsys):
    for ln in _lines(capsys, "--dist", str(dist)):
        words = ln.split()
        assert words[:3] == ["npm", "trust", "github"]
        assert words[3].startswith("@portrayal/")
        assert words[4:] == FLAGS


def test_the_line_is_exactly_the_one_in_the_notes(dist, capsys):
    assert _lines(capsys, "--dist", str(dist))[-1] == (
        "npm trust github @portrayal/index --file release.yml "
        "--repository roc-ops/Portrayal --environment npm --allow-publish --yes")


def test_only_one_name_prints_one_line(dist, capsys):
    lines = _lines(capsys, "--dist", str(dist), "--only", "@portrayal/acme-box-2")
    assert len(lines) == 1 and lines[0].split()[3] == "@portrayal/acme-box-2"


def test_only_keeps_the_order_of_the_list_not_of_the_arguments(dist, capsys):
    lines = _lines(capsys, "--dist", str(dist), "--only", "@portrayal/index",
                   "@portrayal/acme-box-1")
    assert [ln.split()[3] for ln in lines] == ["@portrayal/acme-box-1", "@portrayal/index"]


def test_an_unknown_name_is_an_error_and_prints_nothing(dist, capsys):
    with pytest.raises(SystemExit) as e:
        T.main(["--dist", str(dist), "--only", "@portrayal/acme-box-1",
                "@portrayal/not-a-package"])
    assert e.value.code == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "@portrayal/not-a-package" in err


def test_nothing_but_the_lines_goes_to_standard_output(dist, capsys):
    T.main(["--dist", str(dist)])
    out = capsys.readouterr().out
    assert out.endswith("\n")
    assert all(ln.startswith("npm trust github ") for ln in out.splitlines())


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


def test_the_constants_are_the_workflows_own():
    """The file name is a file that exists, and the environment is the one the
    job names, so a rename of either fails here and not at the next `npm trust`."""
    assert T.WORKFLOW.endswith((".yml", ".yaml"))
    workflow = ROOT / ".github/workflows" / T.WORKFLOW
    assert workflow.is_file()
    (job,) = yaml.safe_load(workflow.read_text())["jobs"].values()
    assert job["environment"] == T.ENVIRONMENT
    owner, _, repo = T.REPOSITORY.partition("/")
    assert owner and repo and "/" not in repo
