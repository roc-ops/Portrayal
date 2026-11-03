"""Part conformance over the real build, as a REPORT: it never fails the suite.

docs/part-conformance-design.md, section 8, step 1. The runner
(`spec/tools/dev/part_conformance.py`) tries every cable end and every state of
the fixed sample (`part_conformance_sample.json`) and of the devices this change
touches, in the library under `library/dist`, and the result is written to
`library/dist/part-conformance.json`, where `preflight.py` reads it.

Nothing here asserts a finding. A blocking code the runner reports is printed in
the run's summary and kept in the report; the day the codes block, one `assert`
at the end of this file turns it on. What the test does hold is that the report
is written and that it walked something, and it holds them as warnings, because
a report-only gate that fails the suite is not report-only.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import time
import warnings

import pytest

from portrayal import preflight

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "spec/tools/dev/part_conformance.py"
SAMPLE = ROOT / "spec/tools/dev/part_conformance_sample.json"
DIST = ROOT / "library" / "dist"
REPORT = ROOT / preflight.CONFORMANCE_REPORT
SAMPLE_SECONDS = 15           # the budget of section 6.4: the sample under 15 s
RUN_TIMEOUT = 300             # seconds; a runner that hangs is a warning, not a stuck suite
TOUCHED_LIMIT = 40           # devices a change may add to the sample (the touched set under 60 s)

pytestmark = [
    # the report goes into library/dist, which test_overlay_library hashes across
    # a build: one worker runs the two in turn (test_dist_writers_share_a_group.py)
    pytest.mark.xdist_group("public-dist"),
    pytest.mark.skipif(shutil.which("node") is None, reason="node not installed"),
    pytest.mark.skipif(not (DIST / "devices.json").exists(), reason="library/dist not built - run ./build.sh"),
]


def touched_devices():
    """The devices this change touches, by the dist name, as preflight works the set out for lint.

    Empty when there is no merge base to compare with (a shallow clone, a tarball), or when the
    change is one lint cannot scope to devices; the sample still runs."""
    try:
        mbase = preflight.merge_base(ROOT, "origin/main")
        ctx = preflight.Context(ROOT, mbase, preflight.changed_files(ROOT, mbase))
        devices, _contracts, full, _majors = preflight.lint_plan(ctx)
    except (Exception, SystemExit) as e:           # no git, no origin/main (preflight exits): the sample alone
        warnings.warn(f"part conformance: the touched set is unknown ({type(e).__name__})")
        return []
    if full:
        return []
    built = {p.name[: -len(".configs.json")] for p in DIST.glob("*.configs.json")}
    return sorted(d.name for d in devices if d.name in built)


def refs_of_sample():
    data = json.loads(SAMPLE.read_text())
    parts = data["parts"] if isinstance(data, dict) else data
    return [p["ref"] if isinstance(p, dict) else p for p in parts]


def test_part_conformance_report(tmp_path):
    """Run the sample and the touched devices, write the report, fail on nothing."""
    try:
        _report(tmp_path)
    except (Exception, SystemExit) as e:    # report-only: nothing in here may fail the suite
        warnings.warn(f"part conformance: the report could not be made ({type(e).__name__}: {e})")


def _report(tmp_path):
    sample = refs_of_sample()
    touched = touched_devices()
    extra = [d for d in touched if d not in sample][:TOUCHED_LIMIT]
    out = tmp_path / "report.json"
    started = time.monotonic()
    try:
        p = subprocess.run([sys.executable, str(TOOL), "--dist", str(DIST), "--refs", *sample, *extra, "--out", str(out)],
                           capture_output=True, text=True, cwd=ROOT, timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        warnings.warn(f"part conformance: the runner did not finish in {RUN_TIMEOUT} s")
        return
    took = time.monotonic() - started
    if p.returncode != 0 or not out.exists():
        warnings.warn("part conformance: the runner did not finish: " + (p.stderr or p.stdout)[-800:])
        return
    report = json.loads(out.read_text())
    report["run"] = {"sample": sample, "touched": touched, "extra": extra, "seconds": round(took, 1),
                     "budget-seconds": SAMPLE_SECONDS, "mode": "report-only"}
    try:
        REPORT.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    except OSError as e:
        warnings.warn(f"part conformance: the report cannot be written ({e})")
    blocking = {c: r.get("n") for c, r in report.get("summary", {}).items() if r.get("level") == "block"}
    print(f"\npart conformance (report only): {len(report.get('parts', []))} parts in {took:.1f} s; "
          f"blocking codes found: {blocking or 'none'}; report: {preflight.CONFORMANCE_REPORT}")
    if not extra and took > SAMPLE_SECONDS:
        warnings.warn(f"part conformance: the sample took {took:.1f} s, over its {SAMPLE_SECONDS} s budget")
    walked = sum((row.get("cabling") or {}).get("counts", {}).get("judged", 0)
                 for part in report.get("parts", []) for row in part.get("configs", []))
    if not walked:
        warnings.warn("part conformance: the runner judged no cable end; it checked nothing")
