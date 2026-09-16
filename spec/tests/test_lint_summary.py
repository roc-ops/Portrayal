"""The linter's last line is a verdict, not a file count.

`LINT: ok (600 files)` used to print under 24 warning blocks, and exit 0. A PR
body read the last line and wrote "lint clean at 600 files" over a run carrying
95 warnings, and the L66 finding that re-opened #109 walked in behind it. The
warnings are census rules - they are supposed to be there and shrink - so a
warning run is still a passing run; what must not happen is the summary hiding
that there were any.

Two halves. The last line names the warning count whenever it is not zero, so
a tail of the output cannot read as clean. And `--strict` turns warnings into a
non-zero exit, so a caller that wants "no warnings" can ask for it in status
rather than by reading.
"""
import subprocess
import sys
from pathlib import Path


from portrayal import lint

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
# a device that carries census warnings today (L29, L58, L61), so a partial run
# on it has something for the summary to count
NOISY = "s9510-28dc"


def test_a_clean_run_says_ok_and_the_count():
    assert lint.summary_line(600, []) == "LINT: ok (600 files)"


def test_a_warning_run_cannot_read_as_clean():
    ws = ["a.yaml: [L29] one", "b.yaml: [L29] two", "c.yaml: [L61] three"]
    line = lint.summary_line(600, ws)
    assert line == "LINT: ok (600 files, 3 warnings in 2 rules)", line


def test_one_warning_reads_grammatically():
    assert lint.summary_line(1, ["a: [L1] x"]) == "LINT: ok (1 file, 1 warning in 1 rule)"


def run(*extra):
    return subprocess.run([sys.executable, str(SPEC / "tools/portrayal/lint.py"),
                           "--schemas", str(SPEC / "schemas"), "--library", str(LIB),
                           "--device", NOISY, *extra],
                          capture_output=True, text=True)


def test_the_last_line_of_a_real_run_carries_its_warnings():
    r = run()
    last = r.stdout.rstrip().splitlines()[-1]
    assert r.returncode == 0, r.stdout + r.stderr
    assert last.startswith("LINT: ok ("), last
    assert "warning" in last, f"the summary hides its warnings: {last!r}"


def test_strict_turns_warnings_into_a_failing_status():
    r = run("--strict")
    assert r.returncode == 2, (r.returncode, r.stdout[-400:])
    last = r.stdout.rstrip().splitlines()[-1]
    assert last.startswith("LINT: failed --strict"), last
    assert "warning" in last, last
