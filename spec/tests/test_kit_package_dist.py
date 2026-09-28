"""The kit reading a device from its npm package (#526, #528).

dist.js `packageDist` maps every path the kit fetches onto the package that
holds it: a device's files onto `@portrayal/<vendor>-<device>`, the skins onto
`@portrayal/components`, everything else onto `@portrayal/index`, each at the
exact version the index's `packages.json` names. Checked here against the real
build, packaged into a temporary directory the way npm_packages.py ships it,
with fetch answered from those files: every file the kit can ask for has to
land in a package that holds it.
"""
import json
import pathlib
import shutil
import subprocess

import pytest

from portrayal import npm_packages

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
SCRIPT = ROOT / "spec/tests/js/package-dist.mjs"


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    if not (DIST / "devices.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    out = tmp_path_factory.mktemp("packages")
    npm_packages.build(DIST, out, ROOT)
    p = subprocess.run(["node", str(SCRIPT), str(out)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_latest_is_pinned_before_anything_else_is_read(result):
    """`latest` moves; the page must not mix two releases, so it asks once
    what `latest` is and reads everything else at that exact version."""
    assert result["firstAsked"] == [
        "https://cdn.test/npm/@portrayal/index@latest/package.json",
        f"https://cdn.test/npm/@portrayal/index@{result['indexVersion']}/packages.json"]


def test_every_file_the_kit_can_ask_for_lands_in_the_package_that_holds_it(result):
    assert result["checked"] > 3000, "measured almost nothing; the build is not the library"
    assert not result["unresolved"], result["unresolved"]


def test_a_build_directory_still_works_as_it_did(result):
    assert result["flat"] == ["../dist/a.svg", "../dist/a.svg"]
    assert result["resolverKeepsAFunction"] is True
    assert result["resolverFromString"] == "../dist/devices.json"


def test_an_index_version_npm_does_not_have_says_so(result):
    assert "HTTP 404" in result["pinnedMissing"]


def test_an_empty_dist_is_the_default_as_it_was(result):
    """`opts.dist || default` before #691: an empty string is not a base."""
    assert result["resolverFromEmpty"] == "../dist/devices.json"


def test_a_crafted_index_is_refused_before_any_request(result):
    """`?index=` goes into a URL, so it is held to a version or a dist-tag:
    with path segments it would walk off @portrayal/index onto other content
    the CDN serves, whose faces are then parsed as markup."""
    assert "not an index version" in result["crafted"]["error"]
    assert result["crafted"]["requests"] == 0
    assert dict(result["indexForms"]) == {
        "latest": True, "next": True, "1.2.3": True, "0.1.0-rc.1": True,
        "0/../x": False, "1.2.3/x": False, "": False, "Latest?": False}
