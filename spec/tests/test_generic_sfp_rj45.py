"""generic/sfp-rj45: the copper SFP, ungated by the head
(docs/pluggables-heads-design.md section 4.7)."""
import json
import pathlib

import jsonschema
import yaml

from portrayal import lint
from test_nested_occupants import presented_interface, _contract

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/sfp-rj45/v1/contract.yaml"
D = yaml.safe_load(P.read_text())
lint.STANDARDS.update(lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])


def errors(fn):
    with lint.collecting() as got:
        fn(P, D)
    return got.errors


def test_it_validates_and_conforms_to_the_sfp_envelope():
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    jsonschema.validate(D, schema)
    assert D["conforms"] == "sfp-module" and D["mates"] == "sfp"
    assert D["size"] == {"w": 13.55, "h": 8.55, "d": 47.50}
    # L9 (size against the registry) is checked by the library-wide lint run, not here


def test_the_head_is_finisars_and_says_what_it_exceeds():
    h = D["head"]
    assert h["size"] == {"w": 13.55, "h": 13.20, "d": 22.70}
    assert {e["dimension"] for e in h["exceeds"]} == {"above", "below", "length"}
    assert all(e["source"].strip() for e in h["exceeds"])
    assert not [e for e in errors(lint.lint_component_head) if "[L121]" in e]


def test_it_is_a_generic():
    assert not [e for e in errors(lint.lint_component_generic) if "[L99]" in e]
    for k in ("speed", "reach", "power-draw-max-w"):
        assert k not in (D.get("attrs") or {})


def test_it_presents_rj45_through_the_composed_jack():
    jack = next(p for p in D["parts"] if p["id"] == "jack")
    assert jack["ref"] == "std/rj45-ganged@2"
    assert jack["lift"] == 22.70
    iface, _mate, lift = presented_interface(_contract("generic/sfp-rj45@1"), _contract)
    assert iface == "rj45" and lift == 22.70
