"""`lint.py --list-rules --out PATH` writes the listing to a file, and build.sh uses it.

`build.sh` used to write `library/dist/lint-rules.json` with a shell redirect. A
build that is driven one step at a time from a script cannot redirect a command's
output, so it never made the file, and `test_lint_rule_whys.py`'s dist-copy check
failed. `--out` lets the step write its own file. These tests hold three things:
the file is the bytes the standard-output form prints, the standard-output form is
unchanged, and `build.sh` asks for the file with `--out` instead of a redirect.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "spec" / "tools" / "portrayal"

from portrayal import lint

FORMS = {"plain": [], "markdown": ["--markdown"], "json": ["--json"]}


def run_main(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["lint.py", *argv])
    return lint.main()


@pytest.mark.parametrize("form", FORMS)
def test_out_writes_the_bytes_standard_output_prints(form, monkeypatch, capsys, tmp_path):
    flags = FORMS[form]
    assert run_main(monkeypatch, "--list-rules", *flags) == 0
    printed = capsys.readouterr().out
    assert printed
    out = tmp_path / "lint-rules.out"
    assert run_main(monkeypatch, "--list-rules", *flags, "--out", str(out)) == 0
    assert capsys.readouterr().out == ""
    assert out.read_bytes() == printed.encode("utf-8")


def test_the_standard_output_json_form_is_unchanged(monkeypatch, capsys):
    assert run_main(monkeypatch, "--list-rules", "--json") == 0
    assert capsys.readouterr().out == json.dumps(lint.rules_json(), indent=1, ensure_ascii=False) + "\n"


def test_out_creates_the_folders_and_replaces_a_file(monkeypatch, tmp_path):
    out = tmp_path / "a" / "b" / "lint-rules.json"
    assert run_main(monkeypatch, "--list-rules", "--json", "--out", str(out)) == 0
    first = out.read_bytes()
    assert first
    out.write_bytes(b"stale")
    assert run_main(monkeypatch, "--list-rules", "--json", "--out", str(out)) == 0
    assert out.read_bytes() == first


def test_out_without_list_rules_is_an_error(monkeypatch, capsys, tmp_path):
    out = tmp_path / "lint-rules.json"
    with pytest.raises(SystemExit) as stop:
        run_main(monkeypatch, "--out", str(out))
    assert stop.value.code == 2
    assert "--out" in capsys.readouterr().err
    assert not out.exists()


def test_the_command_line_writes_the_same_bytes(tmp_path):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    lint_py = str(TOOLS / "lint.py")
    printed = subprocess.run([sys.executable, lint_py, "--list-rules", "--json"],
                             capture_output=True, env=env)
    assert printed.returncode == 0, printed.stderr
    out = tmp_path / "dist" / "lint-rules.json"
    written = subprocess.run([sys.executable, lint_py, "--list-rules", "--json", "--out", str(out)],
                             capture_output=True, env=env)
    assert written.returncode == 0, written.stderr
    assert written.stdout == b""
    assert out.read_bytes() == printed.stdout
    assert json.loads(out.read_text(encoding="utf-8")) == lint.rules_json()


def _build_lines():
    return [ln for ln in (ROOT / "build.sh").read_text().splitlines()
            if not ln.lstrip().startswith("#")]


def test_build_sh_writes_lint_rules_with_out_not_a_redirect():
    lines = [ln for ln in _build_lines() if "--list-rules" in ln]
    assert len(lines) == 1, lines
    assert '--list-rules --json --out "$OUT/lint-rules.json"' in lines[0]
    for ln in lines:
        assert ">" not in ln.split("--list-rules", 1)[1], (
            f"{ln!r}: a redirect cannot be used when a build is driven step by step from a script, "
            "which is why the step writes its own file with --out")


def test_build_sh_still_parses():
    done = subprocess.run(["bash", "-n", str(ROOT / "build.sh")], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
