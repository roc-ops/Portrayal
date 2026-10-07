"""The 300CB08 is fed twice, once per side, and its device type says so (#822).

An earlier head exported four power ports, one per pole of each feed. Only the
committed export held the fix, so a change back to four would have regenerated
cleanly and passed. These export the device from the build and read the
committed files, in both trees: exactly `input-a` and `input-b`, both
`dc-terminal`.
"""
import pathlib

import pytest
import yaml

from portrayal import dcim_export as dx

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
EXPORTS = ROOT / "library" / "exports"
WANT = [{"name": "input-a", "type": "dc-terminal"},
        {"name": "input-b", "type": "dc-terminal"}]
FILE = pathlib.Path("device-types") / "Amphenol Network Solutions" / "300CB08.yaml"


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    """The device exported from library/dist, as publish.sh exports it, but
    without pictures (images=None never rasterises)."""
    if not DIST.exists():
        pytest.skip("library/dist not built - run ./build.sh")
    from portrayal.artifacts import Dist
    out = tmp_path_factory.mktemp("dcim")
    dx.export_device(Dist(str(DIST)), "300cb08", out, None)
    return out


@pytest.mark.parametrize("tree", dx.TARGETS)
def test_the_panel_exports_one_dc_terminal_per_feed(exported, tree):
    doc = yaml.safe_load((exported / tree / FILE).read_text())
    assert doc["power-ports"] == WANT


@pytest.mark.parametrize("tree", dx.TARGETS)
def test_the_committed_export_has_one_dc_terminal_per_feed(tree):
    doc = yaml.safe_load((EXPORTS / tree / FILE).read_text())
    assert doc["power-ports"] == WANT
