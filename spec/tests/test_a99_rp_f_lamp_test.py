"""The A99-RP-F's LAMP TEST push button is modelled, drawn and labelled.

Cisco's drawing of the card and a photograph of a real one show a round LAMP
TEST push button at the right of the face, two concentric circles with the
legend under it and to its left. The Overview and Reference Guide describes
the button ("Push Buttons": when pushed, the status LEDs light until it is
released). The contract carried it only as a provenance note; the nine lamps
and ten ports were modelled and the button was not.

What this holds of the library:

  - the contract has a `lamp-test` element of class `button`, round, wholly on
    the card;
  - the skin draws it: a node with that id, centred where the element is, with
    its plunger inside the bezel;
  - the legend LAMP over TEST is silkscreened under the button and to its left;
  - the button has a relief feature, as every other Cisco panel button does;
  - the provenance says where the button's place came from and how good it is.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[2]
PART = ROOT / "library/components/cisco/a99-rp-f/v1"
SVG = "{http://www.w3.org/2000/svg}"


def _contract():
    return yaml.safe_load((PART / "contract.yaml").read_text())


def _skin():
    return ET.parse(PART / "skins/default.svg").getroot()


def _by_id(root, ident):
    for el in root.iter():
        if el.get("id") == ident:
            return el
    return None


def _centre(el):
    x, y = el["at"]
    w, h = el["size"]
    return x + w / 2, y + h / 2


def test_the_button_is_an_element():
    el = _contract()["elements"].get("lamp-test")
    assert el is not None, "no `lamp-test` element"
    assert el["class"] == "button"
    w, h = el["size"]
    assert abs(w - h) < 0.2, "the button is round: its box should be square, got %s x %s" % (w, h)


def test_the_button_is_on_the_card():
    c = _contract()
    x, y = c["elements"]["lamp-test"]["at"]
    w, h = c["elements"]["lamp-test"]["size"]
    assert x >= 0 and y >= 0
    assert x + w <= c["size"]["w"] and y + h <= c["size"]["h"]


def test_the_skin_draws_the_button_where_the_element_is():
    c = _contract()
    cx, cy = _centre(c["elements"]["lamp-test"])
    node = _by_id(_skin(), "lamp-test")
    assert node is not None, "no skin node with id `lamp-test`"
    assert node.tag == SVG + "circle"
    assert abs(float(node.get("cx")) - cx) < 0.05
    assert abs(float(node.get("cy")) - cy) < 0.05
    w = c["elements"]["lamp-test"]["size"][0]
    assert abs(2 * float(node.get("r")) - w) < 0.6


def test_the_plunger_is_inside_the_bezel():
    root = _skin()
    bezel = _by_id(root, "lamp-test")
    plunger = _by_id(root, "lamp-test-plunger")
    assert bezel is not None and plunger is not None, "two concentric circles are drawn"
    assert plunger.tag == SVG + "circle"
    assert float(plunger.get("cx")) == float(bezel.get("cx"))
    assert float(plunger.get("cy")) == float(bezel.get("cy"))
    assert 0 < float(plunger.get("r")) < float(bezel.get("r"))


def test_the_legend_is_under_and_left_of_the_button():
    c = _contract()
    cx, cy = _centre(c["elements"]["lamp-test"])
    texts = {t.text.strip(): t for t in _skin().iter(SVG + "text") if t.text}
    assert "LAMP" in texts and "TEST" in texts, "legend LAMP over TEST is not silkscreened"
    lamp, test = texts["LAMP"], texts["TEST"]
    for t in (lamp, test):
        assert float(t.get("x")) < cx, "the legend is left of the button's centre"
        assert float(t.get("y")) > cy, "the legend is under the button's centre"
    assert float(test.get("y")) > float(lamp.get("y")), "LAMP is above TEST"


def test_the_button_stands_proud_like_the_other_panel_buttons():
    feats = {f["node"]: f for f in _contract()["relief"]["features"]}
    assert "lamp-test" in feats
    assert "cyl" in feats["lamp-test"]
    assert feats["lamp-test"]["confidence"] == "estimated"


def test_the_provenance_says_how_the_place_was_found():
    prov = _contract()["provenance"]["lamp-test"]
    assert "estimated" in prov.lower()
    assert "Push Buttons" in prov
