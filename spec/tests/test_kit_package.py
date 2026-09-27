"""What `npm pack` puts in the kit's tarball.

The kit is published as `@portrayal/kit` (#527). Apache-2.0 asks a
redistribution to carry the licence and the NOTICE, and npm only picks up a
LICENSE from the package's own directory, which `kit/` does not have. So
`prepack` copies both in from the repository root and `postpack` removes them.
build.sh does the same for `library/dist`, for the same reason.

What this pins is the tarball, not package.json: a `files` entry for a file
that is not there is silently dropped by npm, and that is the failure to catch.
"""
import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.fixture(scope="module")
def packed():
    out = subprocess.run(["npm", "pack", "--dry-run", "--json"], cwd=KIT,
                         capture_output=True, text=True, check=True)
    return {f["path"] for f in json.loads(out.stdout)[0]["files"]}


def test_the_tarball_carries_the_licence_and_the_notice(packed):
    assert {"LICENSE", "NOTICE"} <= packed


def test_packing_leaves_no_copies_behind(packed):
    # `postpack` removes them. A copy left in kit/ would drift from the root.
    assert not (KIT / "LICENSE").exists()
    assert not (KIT / "NOTICE").exists()


def test_every_export_is_in_the_tarball(packed):
    pkg = json.loads((KIT / "package.json").read_text())
    missing = [t for t in pkg["exports"].values() if t.removeprefix("./") not in packed]
    assert not missing, f"exported but not packed: {missing}"
