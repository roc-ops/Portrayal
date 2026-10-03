"""Telling the backlog from the thing you just broke.

roc-ops/Portrayal#180. A clean tree reports 1392 warnings across 23 rules, and L61 alone is
645. Somebody who clones the repository, changes one device and runs the gate
could not tell "this was already here" from "I did that" - the only way to know
was to run lint before and after and diff the two by hand, which is not
discoverable and is what I had been doing all session.

TWO MECHANISMS, AND THEY ANSWER DIFFERENT QUESTIONS.

`library/lint-baseline.json` records what is merely NOT DONE YET, as a count per
file per rule. Counts rather than message text: an L61 message carries
coordinates - "is 0.92mm off centre ... it sits at 51.42" - so keying on the
sentence would churn the baseline on every re-measurement and bury the new
warning among the moved ones.

`lint: {waive: {L44: "..."}}` on a device records what somebody has ARGUED. The
Casa C40G is the case it exists for: it keeps a rear vent field L44 reports as
100% buried, and its provenance already said why at length, in prose no tool
reads. A waived warning is separated and printed WITH ITS REASON - never hidden,
still counted.

WHY L61 IS NOT WAIVED. 645 warnings across 39 devices looks like the obvious
thing to wave away, and it is not: `sweep_alignment.py` exists to correct them
and, run today, moves nothing on the two worst devices. Its own docstring
records why - a second pass that shifted whole sets took L61 from 656 to 36 and
made the drawings WORSE, 704 items closer to what they name and 626 further
away. The residue "needs a reader with the figure open". That is backlog, not a
decision, so it belongs in the baseline where it stays visible and countable.
"""
import json
import pathlib
import subprocess
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
LINT = ROOT / "spec/tools/portrayal/lint.py"
BASELINE = LIB / "lint-baseline.json"
import onebuild
from portrayal import lint as L
from portrayal import libwalk


def run(*args):
    return subprocess.run([sys.executable, str(LINT), "--schemas", str(ROOT / "spec/schemas"),
                           "--library", str(LIB), *args], capture_output=True, text=True)


# --- the baseline -------------------------------------------------------------

def test_the_baseline_exists_and_is_counts_not_sentences():
    b = json.loads(BASELINE.read_text())
    assert b, "the baseline is empty"
    for f, rules in b.items():
        assert isinstance(rules, dict) and rules
        for code, n in rules.items():
            assert code.startswith("L") and isinstance(n, int) and n > 0, (f, code, n)


@pytest.mark.xdist_group("full-lint")
def test_a_clean_tree_reports_no_change():
    """THE POINT OF THE WHOLE THING. The tail has to say the backlog is the
    backlog, or the 1392 above it reads as an accusation.

    ONE LINT ANSWERS THREE TESTS. This, the baseline's drift and the waiver's
    printing each ran the same command for a different line of the same output,
    at about 45 seconds a run. `onebuild.full_lint` is that run, made once."""
    r = onebuild.full_lint()
    assert r.returncode == 0, r.stdout[-2000:]
    assert "no change against the baseline" in r.stdout, r.stdout[-800:]


def test_new_only_prints_nothing_on_a_clean_tree():
    r = run("--new-only")
    assert r.returncode == 0
    body = [l for l in r.stdout.splitlines() if l.startswith("  library/")]
    assert not body, body[:5]


def test_the_delta_names_a_warning_the_baseline_does_not_have():
    """The mechanism, without editing the library: a baseline missing an entry
    is indistinguishable from a tree that grew one."""
    base = json.loads(BASELINE.read_text())
    victim = next(f for f, r in base.items() if r)
    code = sorted(base[victim])[0]
    n = base[victim][code]
    # ONE FILE'S WORTH, or every other entry in the baseline reads as fixed -
    # which is correct behaviour and would drown the thing under test
    shrunk = {victim: {code: n - 1}}
    warnings = [f"{victim}: [{code}] something"] * n
    new, gone = L.baseline_delta(warnings, shrunk)
    assert new.get(victim, {}).get(code) == 1, new
    assert not gone, gone


def test_a_fixed_warning_is_reported_as_fixed():
    base = {"a.yaml": {"L61": 3}}
    new, gone = L.baseline_delta(["a.yaml: [L61] x"], base)
    assert not new and gone == {"a.yaml": {"L61": 2}}


@pytest.mark.xdist_group("full-lint")
def test_the_baseline_matches_the_library_today():
    """A committed baseline that has drifted from the tree is worse than none -
    it reports phantom fixes and hides real additions. This is the guard that
    `expand.py --check` did not have, and #168 is what happens without it."""
    r = onebuild.full_lint()
    assert "NEW since the baseline" not in r.stdout, r.stdout[-1200:]


# --- the waiver ---------------------------------------------------------------

def test_the_c40g_states_its_l44_decision():
    d = yaml.safe_load((LIB / "devices/casa/c40g/device.yaml").read_text())
    reason = ((d.get("lint") or {}).get("waive") or {}).get("L44")
    assert reason and len(reason) >= 40, reason
    assert "3D" in reason, "the reason should say why the field is kept"


@pytest.mark.xdist_group("full-lint")
def test_a_waived_warning_is_separated_and_its_reason_printed():
    r = onebuild.full_lint()
    assert "waived by the device that raised them" in r.stdout
    assert "[L44] " in r.stdout
    assert "100% buried in 2D" in r.stdout, "the argument belongs in the output"


def test_the_schema_requires_a_reason_of_some_length():
    """A waiver whose reason is `n/a` is how a rule gets turned off for everyone
    who copies the device."""
    import jsonschema
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    v = jsonschema.Draft202012Validator(schema)
    dev = {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
           "maturity": "modelled", "profile": "networking", "manufacturer": "M", "model": "M",
           "chassis": {"width": 1.0, "height": 1.0, "depth": 1.0},
           "views": {"front": {"size": {"w": 10.0, "h": 4.0}}}}
    assert list(v.iter_errors({**dev, "lint": {"waive": {"L44": "n/a"}}})), "a stub reason should fail"
    assert not list(v.iter_errors({**dev, "lint": {"waive": {
        "L44": "the field is buried in 2D and is what punches the panel in 3D"}}}))
    assert list(v.iter_errors({**dev, "lint": {"waive": {"nonsense": "x" * 50}}})), \
        "a waiver key should be a rule code"


def test_changing_a_waiver_asks_for_a_version():
    """An unfingerprinted claim can be retyped with no version asked for - the
    gap `portfolio` had, and then `profile` in #170."""
    from portrayal import devicelock
    d = yaml.safe_load((LIB / "devices/casa/c40g/device.yaml").read_text())
    before = devicelock.buckets(d)
    after = devicelock.buckets({**d, "lint": {"waive": {"L44": "x" * 50}}})
    assert before["surface"] != after["surface"]


def test_waivers_have_not_become_the_answer():
    """The count that matters if this field goes wrong. One device when this
    landed; a library where waiving is how warnings are dealt with would show
    here first.

    SIX IS THE CSR440's L76, and the cap moved only after the alternative was
    built and rejected BY LINT ITSELF. Its BITS jack carries two lamps inside the
    bezel, so it is drawn with the Ethernet part that has them and waives the rule
    that reserves that part for Ethernet. Drawing it the way L76 wants - bare jack
    plus two placed lamps - lints as `[L39] two holes cannot share metal`, because
    an integrated lamp shares the jack's opening. The waiver records that disproof
    rather than asserting a preference, and the export is unaffected: dcim_export
    reads the group, so the port still leaves as `other`/BITS.

    RAISING THIS NUMBER IS NOT THE NORMAL WAY TO PASS. The CSR440's warning has no
    fix inside a device - it needs a lamped, media-neutral jack added to the RJ45
    family, at which point this can go back to five. Before raising it again, check
    whether the warning is right; on the CSR310 it was, ten times, and the fix was
    arithmetic rather than a sixth entry here.

    SEVEN IS THE AIS800-32D's L39, and it moved the cap the same way the CSR440 did:
    the alternative was built and rejected BY LINT ITSELF. Its thirty-two port lamps
    are common/qsfp-lane-leds-column@1, a column of four windows, and expand.py
    declines by design to punch a multi-window lamp because one 1.8 x 11.4 slot would
    claim metal the elevation shows as four 1.4 mm windows on a 3.04 mm pitch. The
    four true windows were tried as explicit cutouts: L39's coverage test accepts a
    lamp only when ONE hole covers more than half its footprint, and each window covers
    about 7.5%, so the honest holes do not count and the only hole that would is the
    false slot. The warning is right, the fix lint would take is wrong, and the
    waiver records that disproof. What would let this go back to six is a coverage
    test that sums the windows a multi-window lamp declares - a change to L39, not to
    the device. Its L61 offsets, by contrast, went to the baseline like every other
    device's, because L61 is deliberately never waived (see the module docstring).

    EIGHT IS THE DS6001's L125 (#734), and its fix is wrong for the same reason.
    L125 asks a rack device for `ru`, and the DS6001 is an Open Rack v3 tray: 2OU
    of 48 mm, a unit `ru` cannot hold - 96 mm is 2.16 U and the tray does not fit
    an EIA rack at all - so the only `ru` that would silence it is invented. What
    would let this go back to seven is an Open Rack value for `chassis.mount`."""
    waived = [p for p in libwalk.iter_devices([LIB])
              if ((yaml.safe_load(p.read_text()) or {}).get("lint") or {}).get("waive")]
    assert len(waived) <= 8, f"{len(waived)} devices waive a rule: {[p.parent.name for p in waived]}"


# --- render's half ------------------------------------------------------------

def test_render_reports_a_bad_ref_as_a_message(tmp_path):
    """README's own compile command produced a forty-line traceback ending in a
    perfectly good sentence."""
    src = (LIB / "devices/edgecore/as7726-32x/device.yaml").read_text()
    bad = tmp_path / "device.yaml"
    bad.write_text(src.replace("common/qsfp28-cage@3", "common/qsfp28-cage-nope@3"))
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(bad),
                        "--library", str(LIB), "--out", str(tmp_path / "out")],
                       capture_output=True, text=True)
    assert r.returncode == 1, r.stdout[-500:]
    assert "Traceback" not in r.stderr, r.stderr[-500:]
    assert r.stderr.startswith("render: "), r.stderr[:200]
    assert "qsfp28-cage-nope" in r.stderr


def test_render_still_succeeds_on_a_good_device(tmp_path):
    """NON-VACUITY: a wrapper that turns everything into exit 1 would pass the
    test above and break the build."""
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"),
                        str(LIB / "devices/edgecore/as7726-32x/device.yaml"),
                        "--library", str(LIB), "--out", str(tmp_path / "out")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]
