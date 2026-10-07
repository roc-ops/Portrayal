"""What a consumer outside this repository can rely on, and how they would know.

`kit/` reads `devices.json` and there was no version in it, no git tag and no
CHANGELOG - so a consumer had no way to tell a breaking change to the dist from
a Tuesday (#185).

And a device's `name` is its filename in `dist/`, which carries no vendor:
`library/dist/mx204.base.front.svg`. Two vendors shipping a model of the same
name would render over each other and the index would list one of them twice,
silently, because neither the build nor the picker has any way to notice.
"""
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library/dist"

from portrayal import changelog, devices_index   # noqa: E402


def _devices_json():
    p = DIST / "devices.json"
    if not p.exists():
        pytest.skip("library/dist not built - run ./build.sh")
    return json.loads(p.read_text())


def test_the_build_states_a_contract_version():
    d = _devices_json()
    assert d.get("contract") == devices_index.CONTRACT
    assert isinstance(d["contract"], int) and d["contract"] >= 1


def test_the_changelog_exists_and_names_the_current_contract():
    """Read with the fragments folded in: the pull request that raises the
    contract announces it in a fragment under changelog.d/, and the number
    reaches CHANGELOG.md itself only when a version is cut."""
    body = changelog.unreleased(ROOT)
    assert f"contract: {devices_index.CONTRACT}" in body, (
        "neither CHANGELOG.md nor a fragment in changelog.d/ mentions the "
        "contract version the build writes")


def test_every_device_name_is_unique():
    """The condition the index now refuses to write through."""
    names = [x["name"] for x in _devices_json()["devices"]]
    assert len(names) == len(set(names)), (
        [n for n in names if names.count(n) > 1])


def test_the_index_refuses_to_write_a_collision():
    """THE REAL GUARD, CALLED. Written inline first, which meant the only way to
    test it was to rebuild the check in the test - a mirror of the guard rather
    than the guard. It is a function now and this calls it."""
    with pytest.raises(SystemExit) as e:
        devices_index.check_unique_names([
            {"name": "clash", "ns": "vendor-a"},
            {"name": "clash", "ns": "vendor-b"},
        ])
    msg = str(e.value)
    assert "clash" in msg and "vendor-a" in msg and "vendor-b" in msg, msg


def test_the_guard_passes_the_library_it_guards():
    devices_index.check_unique_names(_devices_json()["devices"])


def test_a_dist_filename_carries_no_vendor():
    """The reason the guard exists, asserted so the premise cannot rot. If dist
    ever namespaces its filenames, the collision stops mattering and this test
    is the one that should be deleted first."""
    svgs = sorted(DIST.glob("*.svg"))
    if not svgs:
        pytest.skip("library/dist not built")
    names = {x["name"] for x in _devices_json()["devices"]}
    assert any(s.name.split(".")[0] in names for s in svgs[:20]), (
        "dist filenames no longer start with the device name; the collision "
        "guard's premise has changed")
