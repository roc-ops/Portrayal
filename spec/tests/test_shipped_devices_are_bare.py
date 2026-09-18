"""Portrayal ships its device models bare. Populating is a downstream tool's job
(docs/pluggables-design.md, decision 2); five UfiSpace configurations shipped
fitted with optics before this and were the only ones that did."""
import pathlib

import yaml

from portrayal import libwalk

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def test_no_shipped_configuration_seats_an_optic():
    fitted = []
    for man in libwalk.iter_devices([LIB]):
        d = yaml.safe_load(man.read_text()) or {}
        for name, cfg in (d.get("configurations") or {}).items():
            if (cfg or {}).get("occupants"):
                fitted.append(f"{man.parent.name}:{name}")
    assert fitted == [], fitted
