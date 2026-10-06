"""Module envelopes are registry entries, so L9 holds a generic's drawn size to
its MSA the way it holds a cage's (docs/pluggables-generics-design.md section 2).
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
REG = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]

MODULES = {
    "sfp-module": "SFF-8432",
    "qsfp-module": "SFF-8661",
    "qsfp-dd-module": "QSFP-DD",
    "osfp-module": "OSFP Module Specification",
    "xfp-module": "INF-8077i",
    "cfp-module": "CFP MSA Hardware Specification",
    "cfp2-module": "CFP2 Baseline Drawing",
    "cfp4-module": "CFP4 Baseline Drawing",
    "cxp-module": "SFF-8642",
}


def test_every_module_envelope_is_in_the_registry():
    for key, spec in MODULES.items():
        e = REG.get(key)
        assert e, f"{key} missing"
        assert spec in e["registry"], (key, e["registry"])
        for f in ("w", "h", "depth", "confidence", "depth-confidence", "notes"):
            assert f in e, (key, f)
        assert e["confidence"] in ("verified", "measured", "registry"), key


def test_each_entry_names_its_figure():
    for key in MODULES:
        e = REG[key]
        assert re.search(r"(Fig(ure)? \d|Table \d)", e["registry"]), (key, e["registry"])
        assert "depth-notes" in e, key
