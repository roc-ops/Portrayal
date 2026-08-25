"""Walking-skeleton tests: lint green, render deterministic, IDs addressable."""
import subprocess
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
DEVICE = LIB / "devices/edgecore/as7726-32x/device.yaml"
LAMPS = LIB / "devices/edgecore/as7946-30xb/device.yaml"


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


def test_lint_green():
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
    # composed parts flatten through bays: PSU module wraps a std/c13-inlet core
    assert 'id="psu-2--module--inlet--opening"' in rear
    assert 'data-path="psu-2/module/inlet/opening"' in rear
    assert 'data-ref="std/c13-inlet@1:' in rear
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
    assert 'id="led-p4-a--lamp" ' in front
    assert front.count('data-states="off 400g 100g"') == 16    # the eight QSFP-DD, x2
    assert front.count('data-states="off linked partial activity"') == 52   # 26 link lamps
    # ...and a placement still overrides its group: LOC is not Green/Amber ok/fault
    assert 'id="led-loc"' in front and 'data-states="off locate"' in front
    assert 'data-states="off ok fault"' in front               # the other four status lamps
    # a declared state paints: an id rule beats the component's own rule
    assert "#led-p4-a .state-100g" in front and "--led-color: #3b82f6" in front
    assert "#led-loc .state-locate" in front
    # the prose is kept, as prose, beside the tokens - not instead of them
    assert 'data-description="QSG Front LEDs callout 2' in front
    assert "Blue (100G), Green (40G)" in front
    # and the fake states string is gone from the embedded source manifest with it
    assert "Blue = 100G" not in front
