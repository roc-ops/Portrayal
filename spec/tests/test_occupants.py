"""What is plugged in is a configuration, not a different device.

A populated port is the same cage with an optic in it. `occupants:` sits beside
`bays:` so a switch can be drawn bare or fitted without either being a separate
model, and it is sugar: the renderer expands it into the `mate-to` placements
that already existed, so there is one positioning path and one interface check.

These test the two halves that can rot independently - that the sugar really is
sugar (the optic lands where the mate points meet, not near them), and that the
check reaches it (a QSFP in an SFP cage is an error wherever it was declared).
"""
import subprocess
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
sys.path.insert(0, str(SPEC / "tools/portrayal"))

import lint  # noqa: E402

DEV = LIB / "devices/ufispace/s9510-28dc/device.yaml"


def errors_for(data):
    saved_e = lint.ERRORS[:]
    lint.ERRORS.clear()
    try:
        lint.lint_device_occupants(DEV, data, [str(LIB)])
        return [e for e in lint.ERRORS if "[L12]" in e]
    finally:
        lint.ERRORS[:] = saved_e


def test_bare_and_fitted_are_the_same_device(tmp_path):
    """The point of the exercise: one manifest, two drawings."""
    subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(DEV),
                    "--library", str(LIB), "--out", str(tmp_path)],
                   check=True, capture_output=True)
    bare = (tmp_path / "s9510-28dc.dc.front.svg").read_text()
    fitted = (tmp_path / "s9510-28dc.dc-populated.front.svg").read_text()
    assert bare.count('data-ref="common/sfp-lc-duplex@1') == 0
    assert fitted.count('data-ref="common/sfp-lc-duplex@1') == 4


def test_the_optic_lands_where_the_mate_points_meet(tmp_path):
    """Not "near the port" - ON it. If this drifts, occupants grew their own
    positioning path and the whole reason for the sugar is gone."""
    import re
    subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(DEV),
                    "--library", str(LIB), "--out", str(tmp_path)],
                   check=True, capture_output=True)
    svg = (tmp_path / "s9510-28dc.dc-populated.front.svg").read_text()
    grab = lambda p: [float(v) for v in re.search(
        rf'<g[^>]*data-path="{p}"[^>]*transform="translate\(([^)]+)\)"', svg).group(1).split(",")]
    hx, hy = grab("port-4")
    ox, oy = grab("port-4-occupant")
    hm = yaml.safe_load((LIB / "components/std/sfp-ganged/v1/contract.yaml")
                        .read_text())["connection-points"]["mate"]["at"]
    om = yaml.safe_load((LIB / "components/common/sfp-lc-duplex/v1/contract.yaml")
                        .read_text())["connection-points"]["mate"]["at"]
    assert abs((hx + hm[0]) - (ox + om[0])) < 0.01
    assert abs((hy + hm[1]) - (oy + om[1])) < 0.01


def test_the_interface_check_reaches_a_configuration():
    """An occupant lives in a configuration and names a receptacle in any view,
    so the per-view L12 pass never met it: before this, a QSFP transceiver
    declared into an SFP cage linted clean and the drawing placed it perfectly.
    Right about position, silent about fit, which is the worse half to get
    wrong."""
    data = yaml.safe_load(DEV.read_text())
    data["configurations"]["dc-populated"]["occupants"]["port-4"] = \
        "common/qsfp-transceiver@1"
    errs = errors_for(data)
    assert any("mates 'qsfp'" in e and "presents 'sfp'" in e for e in errs), errs


def test_an_occupant_must_plug_into_something():
    data = yaml.safe_load(DEV.read_text())
    data["configurations"]["dc-populated"]["occupants"]["port-999"] = \
        "common/sfp-lc-duplex@1"
    errs = errors_for(data)
    assert any("names no placement in any view" in e for e in errs), errs


def test_the_library_is_clean():
    for man in sorted(LIB.glob("devices/*/*/device.yaml")):
        assert not errors_for(yaml.safe_load(man.read_text())), man
