"""Pictures asked for are pictures made, or the run says why not (#462).

Without the `render` extra there is no cairosvg, `dcim_export.rasterize`
answers None, and `./publish.sh` used to finish, exit 0 and leave 0 PNGs -
the README said to just run it. Now the exporter refuses `--images` (without
`--no-raster`) up front, and publish.sh refuses once before the build.

TESTED BY TAKING CAIROSVG AWAY, as the issue asks, not only by the happy
path: a decoy `cairosvg` package that raises ImportError is put first on
PYTHONPATH, so the import fails whether or not the real one is installed.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library/dist"


@pytest.fixture
def no_cairosvg(tmp_path):
    pkg = tmp_path / "blocked" / "cairosvg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("raise ImportError('cairosvg removed for this test')\n")
    env = {**os.environ,
           "PYTHONPATH": f"{pkg.parent}:{ROOT / 'spec/tools'}"}
    return env


def _export(env, out, *flags):
    return subprocess.run(
        [sys.executable, "-m", "portrayal.dcim_export", "--dist", str(DIST),
         "--out", str(out), "--device", "eps201", *flags],
        capture_output=True, text=True, env=env, cwd=ROOT, timeout=300)


@pytest.mark.skipif(not (DIST / "devices.json").exists(), reason="dist not built; run ./build.sh")
def test_the_exporter_refuses_images_it_cannot_draw(no_cairosvg, tmp_path):
    r = _export(no_cairosvg, tmp_path / "out", "--images")
    assert r.returncode != 0, "exited 0 with no way to draw a picture"
    assert '.[render]' in r.stderr and "--no-images" in r.stderr, r.stderr[-400:]
    assert not (tmp_path / "out").exists() or not any((tmp_path / "out").rglob("*.yaml")), \
        "it wrote exports before refusing"


@pytest.mark.skipif(not (DIST / "devices.json").exists(), reason="dist not built; run ./build.sh")
def test_the_exporter_writes_the_yaml_when_pictures_were_not_asked_for(no_cairosvg, tmp_path):
    """`--no-raster` is what CI runs: the image booleans without the PNGs. It
    needs no cairosvg and must not start needing it."""
    r = _export(no_cairosvg, tmp_path / "out", "--images", "--no-raster")
    assert r.returncode == 0, r.stderr[-400:]
    assert any((tmp_path / "out").rglob("*.yaml"))


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_publish_refuses_before_the_build(no_cairosvg, tmp_path):
    """Once, before ./build.sh spends a minute and the parallel export prints
    the refusal once per device. OUT is a tmp dir, so nothing real is touched."""
    r = subprocess.run(["bash", str(ROOT / "publish.sh"), str(tmp_path / "dist")],
                       capture_output=True, text=True, env=no_cairosvg, cwd=ROOT, timeout=120)
    assert r.returncode == 1, (r.returncode, r.stderr[-400:])
    assert '.[render]' in r.stderr and "--no-images" in r.stderr, r.stderr[-400:]
    assert not (tmp_path / "dist").exists(), "the build ran before the check"
