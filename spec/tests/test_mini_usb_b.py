"""The Mini-USB B receptacle in the standards registry and the connector slots.

Written before the entry, and each assertion below was seen failing against a
tree without it. The figures come from one maker's drawing, read as data:

  Molex sales drawing SD-54819-026, "USB Series Mini-B Receptacle Ass'y -Lead
  Free-", part 54819-0519, revision A (EC J2009-1533, 2009/06/25), sheets 1 and 2.

No other document was used. Mini-B is not Micro-B and not Mini-AB.
"""
import pathlib

import yaml

from portrayal import lint as L
from portrayal import render as render_mod

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "spec/schemas"

L.STANDARDS.update(L.load_yaml(SCHEMAS / "standards.yaml")["standards"])


def _std():
    return yaml.safe_load((SCHEMAS / "standards.yaml").read_text())["standards"]


def test_the_entry_carries_the_drawings_figures():
    """Molex SD-54819-026 sheet 1, front view: the shield case is 7.7 wide
    over its widest line and 3.9 high (the 3.1 opening plus two 0.4 walls; the
    side view's printed 3.95 runs from the shell's top to the seating plane, and
    the front view's 3.55 from the top of the opening to the base); the side
    view gives the part 9 long overall. The plug opening inside it is 6.9 wide (front
    view) by 3.1 high. Sheet 2's 4.2 and 4.5 are bracketed reference heights
    that include the spring tabs, so they are not the panel aperture."""
    e = _std()["mini-usb-b"]
    assert (e["w"], e["h"], e["depth"]) == (7.7, 3.9, 9.0)
    assert e["confidence"] == "drawing" and e["depth-confidence"] == "drawing"
    for cited in ("Molex", "54819-0519", "SD-54819-026", "rev A",
                  "molex.com/content/dam/molex/molex-dot-com/products/automated/"
                  "en-us/salesdrawingpdf/548/54819/548190519_sd.pdf"):
        assert cited in e["registry"], cited
    assert "6.9" in e["notes"] and "3.1" in e["notes"]
    assert "Micro-B" in e["notes"] and "Mini-AB" in e["notes"]


def _lint_l9(tmp_path, w, h):
    doc = {"format": 1, "kind": "component", "name": "mini-usb-fixture",
           "version": "1.0.0", "class": "port", "profile": "networking",
           "size": {"w": w, "h": h, "d": 9.0}, "conforms": "mini-usb-b"}
    p = tmp_path / "contract.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))

    class _NoSchema:
        def iter_errors(self, _data):
            return iter(())

    with L.collecting() as found:
        L.lint_component(p, _NoSchema())
    return [e for e in found.errors if "[L9]" in e]


def test_a_component_at_the_registered_size_passes_and_half_a_millimetre_wider_fails(tmp_path):
    assert _lint_l9(tmp_path, 7.7, 3.9) == []
    wide = _lint_l9(tmp_path, 8.2, 3.9)
    assert len(wide) == 1 and "7.7" in wide[0], wide


def test_the_connector_registry_lists_mini_usb_b_beside_the_other_usb_receptacles():
    reg = render_mod._connector_registry()
    assert {"usb-a", "micro-usb-b", "mini-usb-b", "usb-c"} <= set(reg)
    assert reg["mini-usb-b"]["standard"] == "mini-usb-b"
    assert "Mini-B" in reg["mini-usb-b"]["note"]
    assert "Micro-B" in reg["mini-usb-b"]["note"]
