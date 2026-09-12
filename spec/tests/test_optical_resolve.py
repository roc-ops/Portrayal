"""The optical graph, resolved from a contract.

A connector states how many fibre positions it presents, ONCE, and every module
that composes it inherits that. The alternative - restating capacity per module -
is 77 chances to type 12 as 21 on the FS line alone.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))


def contract(ref):
    """`common/lc-duplex-adapter@3` -> its parsed contract."""
    name, major = ref.split("@")
    return yaml.safe_load(
        (LIB / "components" / name / f"v{major}" / "contract.yaml").read_text())


def test_the_lc_duplex_adapter_presents_two_fibre_positions():
    c = contract("common/lc-duplex-adapter@3")
    assert (c.get("optical") or {}).get("positions") == 2, (
        "an LC DUPLEX adapter is two bores. If this is absent, every module "
        "composing it has no capacity to check its paths against")
