"""pytest keeps only a failing test's temporary directory.

The default policy keeps every test's tmp_path for the last three runs. This
suite renders into them, and with several checkouts running it on one machine
the user temp directory reached 31 GB and filled the disk mid-run. The policy
is set in pyproject.toml; this pins it, and checks that the setting is one the
installed pytest reads, so a typo cannot quietly restore the default.
"""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_only_failures_keep_their_tmp_path(pytestconfig):
    opts = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    assert opts.get("tmp_path_retention_policy") == "failed", opts
    assert pytestconfig.getini("tmp_path_retention_policy") == "failed"
