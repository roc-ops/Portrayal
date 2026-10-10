"""L39 reads a composed leaf with no registry entry as the part's opening (#413).

casa/ground-strap@2 is a 15 x 7.9 marked plate composing common/esd-jack@1, a
6.0 jack with no `conforms`, off-centre at [0.0, 1.1]. Its cutout is the
jack's. `_aperture_of`, which test_cutout_derivation mirrors, already took the
leaf's own size as the opening; `_composed_aperture`, which L39's "sits in its
own cutout" check calls, counted only registry-sized children, measured the
plate's footprint instead and reported it 4.5 mm off-centre. A lamp, a latch or
printing is not an opening, and still falls back to the footprint.
"""
import pathlib

import pytest

from portrayal import lint as L

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _write(lib, ref, body):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    d = lib / "components" / ns / name / f"v{major}"
    (d / "skins").mkdir(parents=True)
    (d / "contract.yaml").write_text(body)


def _lib(tmp_path, leaf_class):
    lib = tmp_path / "library"
    _write(lib, "t/jack@1", f"""format: 1
kind: component
name: jack
version: 1.0.0
class: {leaf_class}
size: {{w: 6.0, h: 6.0}}
skins: [default]
""")
    _write(lib, "t/plate@1", """format: 1
kind: component
name: plate
version: 1.0.0
class: ground
size: {w: 15.0, h: 7.9}
parts:
  - {ref: t/jack@1, id: jack, at: [0.0, 1.1]}
skins: [default]
""")
    return [str(lib)]


def off_centre(lib, cut_at, cut_size):
    view = {"panel": {"cutouts": [{"id": "strap", "at": cut_at, "size": cut_size, "shape": "circle"}]},
            "components": {"placements": [{"ref": "t/plate@1", "id": "strap", "at": [100.0, 50.0]}]}}
    with L.collecting() as found:
        L.lint_device_cutouts("t/device.yaml", "front", view, lib)
    return [w for w in found.warnings if "[L39]" in w and "does not sit in its own cutout" in w]


def test_the_jack_is_the_opening_and_its_cutout_passes(tmp_path):
    assert off_centre(_lib(tmp_path, "ground"), [100.0, 51.1], [6.0, 6.0]) == []


@pytest.mark.parametrize("cls", ["led", "latch", "marking"])
def test_a_lamp_latch_or_printing_is_not_an_opening(tmp_path, cls):
    """THE PLANTED FAULT: the same leaf as a lamp, a latch or printing is no
    opening, so the plate is measured by its footprint and the off-centre hole
    is reported - which is exactly what every composed leaf got before #413."""
    got = off_centre(_lib(tmp_path, cls), [100.0, 51.1], [6.0, 6.0])
    assert len(got) == 1 and "strap" in got[0], got


def test_a_cutout_that_misses_the_jack_is_still_reported(tmp_path):
    """NON-VACUITY: with the jack as the opening, a hole 3 mm off it fires."""
    got = off_centre(_lib(tmp_path, "ground"), [103.0, 51.1], [6.0, 6.0])
    assert len(got) == 1, got


def test_the_c100g_strap_reads_as_its_jack():
    lib = [str(ROOT / "library")]
    got = L._composed_aperture("casa/ground-strap@2", lib)
    assert got == ((6.0, 6.0), (0.0, 1.1))
