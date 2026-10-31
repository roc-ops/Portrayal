"""A test that writes into library/dist runs in the overlay test's xdist group.

`test_overlay_library` holds that an overlay build leaves the public dist byte
for byte as it was: it hashes `library/dist` before the build and again after,
a minute or two apart. `test_part_conformance_report` writes
`library/dist/part-conformance.json` for preflight to read. Run on two xdist
workers, the report can land between the two hashes and the overlay test fails
with "an overlay build changed the public dist", though the overlay build never
touched the dist. Whether they overlap depends on how the shard splits the
suite, so it comes and goes with unrelated changes.

The fix is that both are in one `xdist_group`, which `--dist loadgroup` runs on
one worker, one test after the other. The overlay test is not loosened: it
still hashes everything. This holds the grouping for every module that writes
the report, so a second writer cannot be added outside it.
"""
import pathlib

import pytest

TESTS = pathlib.Path(__file__).resolve().parent
OVERLAY = "test_overlay_library.py"


def group_of(path):
    """The xdist group a module's `pytestmark` puts every test in, or None."""
    import importlib
    module = importlib.import_module(path.stem)
    marks = getattr(module, "pytestmark", [])
    marks = marks if isinstance(marks, list) else [marks]
    groups = [m.args[0] for m in marks if m.name == "xdist_group" and m.args]
    return groups[0] if groups else None


WRITES_THE_REPORT = "REPORT" + ".write_text("      # joined, so this file does not match itself


def writers():
    return sorted(p for p in TESTS.glob("test_*.py") if WRITES_THE_REPORT in p.read_text())


def test_the_overlay_test_is_in_a_group():
    assert group_of(TESTS / OVERLAY), (
        f"{OVERLAY} hashes library/dist across a build and must be in an xdist_group")


def test_the_part_conformance_report_is_a_writer_this_sees():
    assert "test_part_conformance_report.py" in [p.name for p in writers()]


@pytest.mark.parametrize("path", writers(), ids=lambda p: p.name)
def test_a_test_that_writes_into_the_dist_shares_the_overlay_tests_group(path):
    assert group_of(path) and group_of(path) == group_of(TESTS / OVERLAY), (
        f"{path.name} writes into library/dist, and {OVERLAY} hashes it across a build: "
        f"give both the same pytest.mark.xdist_group so one worker runs them in turn")
