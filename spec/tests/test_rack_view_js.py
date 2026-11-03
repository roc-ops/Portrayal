"""The rack views in the kit (kit/rack/view/, docs/rack-views-design.md): the
node scripts under spec/tests/js/view-*.mjs, each printing one JSON line of
{case: "ok" or its failure}. The drawing itself is compared on the page,
spec/tests/browser/rack-view-2d.html, by hand."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parent / "js"
SCRIPTS = ["view-skin-fetch", "view-ear-holes", "view-settable", "view-mount", "view-dist-at"]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.mark.parametrize("name", SCRIPTS)
def test_view_script(name):
    p = subprocess.run(["node", str(JS / f"{name}.mjs")], capture_output=True, text=True, cwd=str(JS))
    assert p.returncode == 0, p.stderr[-3000:]
    cases = json.loads(p.stdout.strip().splitlines()[-1])
    assert cases, f"{name} ran no case"
    failed = {k: v for k, v in cases.items() if v != "ok"}
    assert not failed, json.dumps(failed, indent=1)[:4000]
