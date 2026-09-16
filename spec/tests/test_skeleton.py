"""Walking-skeleton tests: lint green, render deterministic, IDs addressable."""
import os
import subprocess
import sys

import pytest
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
DEVICE = LIB / "devices/edgecore/as7726-32x/device.yaml"
LAMPS = LIB / "devices/edgecore/as7946-30xb/device.yaml"
BLINK = LIB / "devices/ufispace/s9510-28dc/device.yaml"


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


@pytest.mark.skipif(os.environ.get("PORTRAYAL_LINT_ALREADY_RAN") == "1",
                    reason="lint ran as its own CI job before this suite started")
def test_lint_green():
    """THE THIRD LINT OF A CI RUN, and the only one that is not free.

    It shells out and lints the whole library at around 76 seconds, which makes
    it the critical path INSIDE the suite: it cannot be split across workers, so
    parallelism flattens after two of them. Locally it is worth every second -
    it is what stops a green test run over a library that does not lint. On CI
    it is guaranteed redundant, because the `lint` job gates the job this runs
    in and nothing can have reached here without it passing (#183).
    """
    r = run(SPEC / "tools/portrayal/lint.py", "--schemas", SPEC / "schemas", "--library", LIB)
    assert r.returncode == 0, r.stdout + r.stderr


def test_render_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for out in (a, b):
        r = run(SPEC / "tools/portrayal/render.py", DEVICE, "--library", LIB, "--out", out)
        assert r.returncode == 0, r.stdout + r.stderr
    for f in sorted(a.iterdir()):
        assert f.read_bytes() == (b / f.name).read_bytes(), f"nondeterministic: {f.name}"


def test_compiled_ids_and_attrs(tmp_path):
    run(SPEC / "tools/portrayal/render.py", DEVICE, "--library", LIB, "--out", tmp_path)
    front = (tmp_path / "as7726-32x.front.svg").read_text()
    rear = (tmp_path / "as7726-32x.rear.svg").read_text()
    # hierarchical per-instance ids (the <use> problem solved by flattening)
    assert 'id="port-1--led-1"' in front
    assert 'id="port-32--cage"' in front
    assert 'data-path="port-17/led-4"' in front
    # belly-to-belly bottom row is rotated; skins selectable per placement
    assert 'rotate(180' in front
    assert 'id="sfp-leds--lamp-2"' in front
    # grounding points exist on the rear
    assert 'id="ground-left--stud"' in rear
    # queryable attributes for class selection
    assert front.count('data-speed="100g"') == 32
    assert front.count('data-speed="10g"') == 2
    # regions are addressable and carry members
    assert 'data-path="region:mgmt-block"' in front
    # bays populated with modules, hierarchically addressable
    # composed parts flatten through bays: PSU module wraps a std/c14-inlet core
    assert 'id="psu-2--module--inlet--opening"' in rear
    assert 'data-path="psu-2/module/inlet/opening"' in rear
    assert 'data-ref="std/c14-inlet@1:' in rear
    assert rear.count('data-class="fan"') == 6
    # metadata embeds source + resolved versions, no timestamps
    assert '"resolved-components"' in front
    assert '"tool":"portrayal-render"' in front


def test_declared_states_reach_the_lamp_and_paint(tmp_path):
    """A state vocabulary declared on a group or a placement must reach the drawing.

    The bug this pins: `states:` used to exist only on the component, so the same
    common/led-dot was a generic four-state lamp whether it was a speed lamp on a
    QSFP28 or a link lamp beside it. The device's real semantics lived in
    attrs: {states: 'Blue = 100G, Green = 40G'} where nothing could read them - and
    the tree reads the INNERMOST data-states, so overriding only the outer <g>
    would have looked fixed and changed nothing.
    """
    run(SPEC / "tools/portrayal/render.py", LAMPS, "--library", LIB, "--out", tmp_path)
    front = (tmp_path / "as7946-30xb.front.svg").read_text()
    # declared once on the group, reaching all eighteen QSFP28 speed lamps...
    assert front.count('data-states="off 100g 40g"') == 36     # instance + lamp, x18
    assert 'id="led-port-4-a--lamp" ' in front
    assert front.count('data-states="off 400g 100g"') == 16    # the eight QSFP-DD, x2
    assert front.count('data-states="off linked partial activity"') == 52   # 26 link lamps
    # ...and a placement still overrides its group: LOC is not Green/Amber ok/fault
    assert 'id="led-loc"' in front and 'data-states="off locate"' in front
    assert 'data-states="off ok fault"' in front               # the other four status lamps
    # a declared state paints: an id rule beats the component's own rule
    assert "#led-port-4-a .state-100g" in front and "--led-color: #3b82f6" in front
    assert "#led-loc .state-locate" in front
    # the prose is kept, as prose, beside the tokens - not instead of them
    assert 'data-description="QSG Front LEDs callout 2' in front
    assert "Blue (100G), Green (40G)" in front
    # and the fake states string is gone from the embedded source manifest with it
    assert "Blue = 100G" not in front


def test_behaviour_is_part_of_the_state(tmp_path):
    """Solid and blinking of one colour are different facts, so both must compile.

    The S9510-28DC HIG draws four distinct meanings out of two colours and two
    behaviours on one lamp: solid green PWR is "system power good" and blinking
    green PWR is "power good but BMC power fail". A model carrying only colour
    collapses them, and a blinking state that renders solid is the same failure as
    a state class nothing paints.
    """
    run(SPEC / "tools/portrayal/render.py", BLINK, "--library", LIB, "--out", tmp_path)
    front = (tmp_path / "s9510-28dc.front.svg").read_text()
    assert 'data-states="off ok bmc-power-fail cpu-power-fail power-fail"' in front
    # same colour, different behaviour - so the colour rule covers both names and
    # only one of them animates
    assert "#led-pwr.state-ok" in front and "#led-pwr.state-bmc-power-fail" in front
    assert ".state-bmc-power-fail { animation: portrayal-blink" in front
    assert ".state-ok { animation:" not in front
    assert "@keyframes portrayal-blink" in front
    # alternating needs two colours and its own keyframes; this one is declared on
    # the ufispace PSU contract, so it lands at component scope
    assert "@keyframes portrayal-alternate" in front
    assert "--led-color: #22c55e; --led-color-alt: #ef4444;" in front
    assert "state-warning { animation: portrayal-alternate" in front
    # one component, two lamps, two vocabularies: a single list could not say this
    # (led-left/led-right until the RJ45 sweep lifted this jack onto
    # common/rj45-eth@1, whose two elements are led-a/led-b - #125; the
    # controller ruling kept the sweep's rotate: 180 flip for this jack, which
    # swaps which element carries which vocabulary, since led-a moves to
    # screen-right under that rotate and the screen-left lamp must keep the
    # link-1g vocabulary)
    assert 'data-path="mgmt/led-a" data-class="led" data-states="off link-100m activity-100m"' in front
    assert 'data-states="off link-1g activity-1g"' in front
    assert "#mgmt--led-a.state-activity-100m { animation: portrayal-blink" in front
