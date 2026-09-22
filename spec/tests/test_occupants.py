"""What is plugged in is a configuration, not a different device.

A populated port is the same cage with an optic in it. `occupants:` sits beside
`bays:` so a switch can be drawn bare or fitted without either being a separate
model, and it is sugar: the renderer expands it into the `mate-to` placements
that already existed, so there is one positioning path and one interface check.

THE LIBRARY SHIPS NO FITTED DEVICE (docs/pluggables-design.md decision 2), so
these tests seat a generic on a COPY of a device in tmp_path - the idiom
test_mate_forwarding already uses, because a corpus other tests read is not a
scratch pad. They test the two halves that can rot independently: that the sugar
really is sugar (the optic lands where the mate points meet, not near them), and
that the check reaches it (a QSFP in an SFP cage is an error wherever it was
declared).
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"

from portrayal import lint
from portrayal import libwalk

SRC = LIB / "devices/ufispace/s9510-28dc"
PORTS = ["port-4", "port-5", "port-6", "port-7"]


def fitted_copy(tmp_path, occupants):
    """The DC build of the S9510-28DC with `occupants` injected, on a copy."""
    dev = tmp_path / "s9510-28dc" / "device.yaml"
    shutil.copytree(SRC, dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["dc"]["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def render(dev, out):
    r = subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]
    return (out / "s9510-28dc.dc.front.svg").read_text()


def errors_for(dev, data):
    with lint.collecting() as got:
        lint.lint_device_occupants(dev, data, [str(LIB)])
    return [e for e in got.errors if "[L12]" in e]


def test_bare_and_fitted_are_the_same_device(tmp_path):
    """One manifest, two drawings."""
    bare = render(SRC / "device.yaml", tmp_path / "bare")
    fitted = render(fitted_copy(tmp_path, {p: "generic/sfp-lc@1" for p in PORTS}),
                    tmp_path / "fitted")
    assert bare.count('data-ref="generic/sfp-lc@1') == 0
    assert fitted.count('data-ref="generic/sfp-lc@1') == 4


def test_the_optic_lands_where_the_mate_points_meet(tmp_path):
    """Not "near the port" - ON it. If this drifts, occupants grew their own
    positioning path and the whole reason for the sugar is gone."""
    svg = render(fitted_copy(tmp_path, {"port-4": "generic/sfp-lc@1"}), tmp_path / "o")
    grab = lambda p: [float(v) for v in re.search(
        rf'<g[^>]*data-path="{p}"[^>]*transform="translate\(([^)]+)\)"', svg).group(1).split(",")]
    hx, hy = grab("port-4")
    ox, oy = grab("port-4-occupant")
    hm = yaml.safe_load((LIB / "components/std/sfp-ganged/v1/contract.yaml")
                        .read_text())["connection-points"]["mate"]["at"]
    om = yaml.safe_load((LIB / "components/generic/sfp-lc/v1/contract.yaml")
                        .read_text())["connection-points"]["mate"]["at"]
    assert abs((hx + hm[0]) - (ox + om[0])) < 0.01
    assert abs((hy + hm[1]) - (oy + om[1])) < 0.01


def test_the_optic_lands_where_the_mate_points_meet_in_a_rotated_cage(tmp_path):
    """The same claim on `port-3`, a `common/qsfp-cage@3` drawn at rotate 180
    (the lower of the S9510-28DC's QSFP28 pair - docs/pluggables-3d-design.md, S3):
    the optic turns with its cage (D3) and its mate point meets the cage's
    TURNED one. Before this it was seated as if upright - translate only, the
    same offset from its cage as port-0's - and missed. Both groups'
    transforms are applied numerically (rotate about the given centre, then
    translate); test_seat_rotation.py has the upright port beside it."""
    import math
    svg = render(fitted_copy(tmp_path, {"port-3": "generic/qsfp-lc@1"}), tmp_path / "o")

    def device_point(path, local):
        tf = re.search(rf'<g[^>]*data-path="{path}"[^>]*transform="([^"]+)"', svg).group(1)
        m = re.fullmatch(r"translate\(([^,]+),([^)]+)\) rotate\(([^ ]+) ([^ ]+) ([^)]+)\)", tf)
        assert m, (path, tf)
        tx, ty, deg, cx, cy = (float(v) for v in m.groups())
        assert deg == 180
        c, s_ = math.cos(math.radians(deg)), math.sin(math.radians(deg))
        x, y = local
        return (tx + cx + (x - cx) * c - (y - cy) * s_,
                ty + cy + (x - cx) * s_ + (y - cy) * c)

    # The cage's point is FORWARDED from the aperture it composes, so it is
    # read the way the build reads it (manifest.presented_interface).
    from portrayal.manifest import presented_interface
    from portrayal.render import Library
    lib = Library([str(LIB)])
    _, hm, _ = presented_interface(lib.resolve("common/qsfp-cage@3")[0],
                                   lambda r: lib.resolve(r)[0])
    om = yaml.safe_load((LIB / "components/generic/qsfp-lc/v1/contract.yaml")
                        .read_text())["connection-points"]["mate"]["at"]
    hx, hy = device_point("port-3", hm)
    ox, oy = device_point("port-3-occupant", om)
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, ((hx, hy), (ox, oy))


def test_the_interface_check_reaches_a_configuration(tmp_path):
    """A QSFP generic declared into an SFP cage is an error wherever it was
    declared - right about position, silent about fit would be the worse half."""
    dev = fitted_copy(tmp_path, {"port-4": "generic/qsfp-lc@1"})
    errs = errors_for(dev, yaml.safe_load(dev.read_text()))
    assert any("mates 'qsfp'" in e and "presents 'sfp'" in e for e in errs), errs


def test_an_occupant_must_plug_into_something(tmp_path):
    dev = fitted_copy(tmp_path, {"port-999": "generic/sfp-lc@1"})
    errs = errors_for(dev, yaml.safe_load(dev.read_text()))
    assert any("names no placement in any view" in e for e in errs), errs


# --- a device-level occupants key can itself be chained ----------------------
#
# `occupants: {port-4: optic, port-4-occupant: plug, port-4-occupant-occupant:
# boot}` is exactly what render.py's fixed-point expansion draws (test_chained_
# seats.py exercises the build side; test_seat_depth.py's chained mate-to does
# too). L12 used to know only about placements gathered from the views, so a
# key naming a chained occupant read as "names no placement in any view" - the
# wrong error for a manifest the renderer built without complaint. The fix
# shares manifest.chained_occupant_ref with nested_key_host (#484's cage-on-a-
# card resolver) rather than growing a second walk of the same shape.

def test_a_device_level_chain_lints_clean(tmp_path):
    dev = fitted_copy(tmp_path, {
        "port-4": "generic/sfp-lc-simplex@2",
        "port-4-occupant": "generic/lc-plug@1",
        "port-4-occupant-occupant": "common/lc-boot@1",
    })
    assert errors_for(dev, yaml.safe_load(dev.read_text())) == []


def test_a_chained_key_whose_ref_does_not_mate_is_an_l12_error(tmp_path):
    """A boot seated directly on the optic - the plug it wraps skipped - mates
    'lc-plug' against a host that presents 'lc'. The chain must be walked to
    reach the mismatch at all: before the fix, this key read as unhosted."""
    dev = fitted_copy(tmp_path, {
        "port-4": "generic/sfp-lc-simplex@2",
        "port-4-occupant": "common/lc-boot@1",
    })
    errs = errors_for(dev, yaml.safe_load(dev.read_text()))
    assert any("mates 'lc-plug'" in e and "presents 'lc'" in e for e in errs), errs


def test_a_chained_key_naming_an_occupant_no_key_seats_is_an_error(tmp_path):
    """`port-4-occupant` with no `port-4` (or anything else producing that
    id) names nothing - a typo, not a chain. The OLD "names no placement in
    any view" wording is a substring of the new message too (see below), so
    this asserts the clause only the new chain-lookup path prints - the one
    the old code never reasoned about at all, because it never went looking
    for a sibling occupant to begin with."""
    dev = fitted_copy(tmp_path, {"port-4-occupant": "generic/lc-plug@1"})
    errs = errors_for(dev, yaml.safe_load(dev.read_text()))
    assert any("no occupant of this configuration seats it either" in e
               for e in errs), errs


def test_a_spec_with_id_renames_the_chain(tmp_path):
    """`id:` is what a chained key names, not `<host>-occupant` - the same
    override `occupant_local_id` honours for the nested (card) branch."""
    dev = fitted_copy(tmp_path, {
        "port-4": {"ref": "generic/sfp-lc-simplex@2", "id": "the-plug-spot"},
        "the-plug-spot": "generic/lc-plug@1",
    })
    assert errors_for(dev, yaml.safe_load(dev.read_text())) == []


def test_a_chain_cycling_back_on_itself_is_an_error(tmp_path):
    """Two keys, neither a placement, each named as the other's occupant by
    `id:` - the chain never grounds. render.py's own fixed-point expansion
    just drops a device-level occupant that never resolves (occupants for a
    host in another view are skipped, not an error); L12 is the check that
    catches what would otherwise silently vanish from the drawing."""
    dev = fitted_copy(tmp_path, {
        "loop-a": {"ref": "generic/lc-plug@1", "id": "loop-b"},
        "loop-b": {"ref": "common/lc-boot@1", "id": "loop-a"},
    })
    errs = errors_for(dev, yaml.safe_load(dev.read_text()))
    assert any("cycles back" in e for e in errs), errs


def test_the_library_is_clean():
    for man in libwalk.iter_devices([LIB]):
        assert not errors_for(man, yaml.safe_load(man.read_text())), man
