"""#709: the kit picker offers a NOS vendor's listings under that vendor.

`pickerEntries` (kit/devsel.js) turns listings.json into entries beside the
hardware: filed under the listing's manufacturer and portfolio, labelled with
the metal it runs on, loading the hardware's drawing, and findable by the
vendor's words. Run under node; skipped where node is not installed.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/picker-entries.mjs"


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_a_listing_is_an_entry_under_its_vendor_that_loads_the_hardware(out):
    a = out["arrcus"]
    assert a["manufacturer"] == "Arrcus"
    assert a["name"] == "as7726-32x", "choosing it must load the hardware's drawing"
    assert a["listing"] == "arrcus/as7726-32x"
    assert a["line"] == "Switching (XGS)", "filed by the vendor's portfolio, not the ODM's"


def test_a_listing_is_labelled_with_the_metal_and_the_vendors_own_name(out):
    assert out["arrcus"]["label"] == "Edgecore AS7726-32X"
    assert out["drivenets"]["label"] == "NCP-40C — UfiSpace S9700-53DX"
    assert out["drivenets"]["model"] == "NCP-40C"


def test_the_filter_finds_a_listing_by_the_vendors_words_and_the_hardwares(out):
    assert all(out["arrcus"]["finds"]), out["arrcus"]["finds"]


def test_the_hardware_entry_is_unchanged(out):
    h = out["hardware"]
    assert h == {"label": "DCS204 — AS7726-32X", "listing": None, "manufacturer": "Edgecore"}


def test_a_listing_of_a_box_this_build_lacks_is_no_entry(out):
    assert "sonic/gone" not in out["keys"]
    assert out["bare"] == 2, "without listings the picker is what it always was"


def test_every_listing_in_the_build_is_an_entry(out):
    if "dist" not in out:
        pytest.skip("library/dist not built")
    d = out["dist"]
    assert d["listings"] and d["entries"] == d["listings"]
    assert d["unique"]
