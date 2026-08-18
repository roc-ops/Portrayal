"""Walking-skeleton tests: lint green, render deterministic, IDs addressable."""
import subprocess
import sys
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "ndv-library"
DEVICE = LIB / "devices/edgecore/as7726-32x/device.yaml"


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)


def test_lint_green():
    r = run(SPEC / "tools/ndv/lint.py", "--schemas", SPEC / "schemas", "--library", LIB)
    assert r.returncode == 0, r.stdout + r.stderr


def test_render_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for out in (a, b):
        r = run(SPEC / "tools/ndv/render.py", DEVICE, "--library", LIB, "--out", out)
        assert r.returncode == 0, r.stdout + r.stderr
    for f in sorted(a.iterdir()):
        assert f.read_bytes() == (b / f.name).read_bytes(), f"nondeterministic: {f.name}"


def test_compiled_ids_and_attrs(tmp_path):
    run(SPEC / "tools/ndv/render.py", DEVICE, "--library", LIB, "--out", tmp_path)
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
    assert '"tool":"ndv-render"' in front
