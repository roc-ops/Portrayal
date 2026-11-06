"""The terminal block of the Edgecore CSR310 and CSR430 DC supply is drawn dark, as the vendor's guides show it.

The supply used to draw its three-pole barrier block light grey with white plates under the screws, where the quick start guides and the data
sheet show a dark plastic block with silver screws (and, in the CSR430 guide's photograph, grey metal plates under them). Only the colours
change, and they are estimates read off the guides' pictures, which give no colour code:

  - the block's plate (the raised plate of the contract's `inlet` relief, too), its two lips and its middle are dark, darker than the module's
    face, and the plates under the screws are grey metal; the screws keep their silver;
  - nothing moves: every id of the block's drawing, its places and sizes and the supply's elements are as before;
  - the contract says so (`block-colour`), says the colours are estimates and says that nothing is moved or resized.

These read the contract and the skin and render nothing.
"""
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "library/components/edgecore/csr310-psu-dc/v1"
NS = "{http://www.w3.org/2000/svg}"
FACE = "#3a3e43"

# id -> (x, y, width, height) of the block's rectangles, as they were drawn before the recolour
PLACES = {
    "inlet": (7.0, 19.7, 30.5, 14.4),
    "block-lip-top": (7.5, 20.2, 29.5, 2.7),
    "block-lip-bottom": (7.5, 30.9, 29.5, 2.7),
    "block-mid": (7.5, 23.0, 29.5, 7.8),
}
POLE_PLATES = [(10.4, 23.3, 7.0, 7.2), (19.0, 23.3, 7.0, 7.2), (27.8, 23.3, 7.0, 7.2)]
SCREWS = [(13.9, 26.9, 2.0), (22.5, 26.9, 2.0), (31.3, 26.9, 2.0)]


def contract():
    return yaml.safe_load((FOLDER / "contract.yaml").read_text())


def skin():
    return ET.parse(FOLDER / "skins/default.svg").getroot()


def by_id(root):
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def brightness(colour):
    h = colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b


def test_the_block_is_dark_and_darker_than_the_modules_face():
    e = by_id(skin())
    for ident in ("inlet", "block-lip-top", "block-lip-bottom", "block-mid"):
        assert brightness(e[ident].get("fill")) < brightness(FACE), ident
    assert e["inlet"].get("fill") == "#1e2125"


def test_the_plates_under_the_screws_are_grey_metal_and_the_screws_stay_silver():
    e = by_id(skin())
    assert e["poles"].get("fill") == "#6b7076"
    assert 80 < brightness(e["poles"].get("fill")) < 140
    assert e["screws"].get("fill") == "#c3c9cf"


def test_the_raised_plate_of_the_inlet_relief_takes_the_blocks_colour():
    feature = next(f for f in contract()["relief"]["features"] if f["node"] == "inlet")
    assert feature["color"] == by_id(skin())["inlet"].get("fill") == "#1e2125"
    assert feature["out"] == 9.5


def test_nothing_of_the_blocks_drawing_moved_or_was_resized():
    root = skin()
    e = by_id(root)
    for ident, (x, y, w, h) in PLACES.items():
        got = tuple(float(e[ident].get(k)) for k in ("x", "y", "width", "height"))
        assert got == (x, y, w, h), ident
    plates = [tuple(float(r.get(k)) for k in ("x", "y", "width", "height")) for r in e["poles"] if r.tag == f"{NS}rect"]
    assert plates == POLE_PLATES
    circles = [tuple(float(c.get(k)) for k in ("cx", "cy", "r")) for c in e["screws"] if c.tag == f"{NS}circle"]
    assert circles == SCREWS
    block = next(g for g in root if g.get("id") == "block")
    assert {x.get("id") for x in block.iter()} >= {"inlet", "block-lip-top", "block-lip-bottom", "block-mid", "poles", "screws", "slots"}
    assert [g.get("id") for g in root if g.tag == f"{NS}g"] == ["warnings", "block", "pole-labels", "silkscreen"]


def test_the_supply_is_a_patch_and_keeps_its_elements_seats_and_port():
    d = contract()
    assert d["version"] == "1.1.1"
    assert d["elements"] == {"inlet": {"at": [7.0, 19.7], "size": [30.5, 14.4], "class": "inlet"},
                             "handle": {"at": [41.5, 3.6], "size": [3.5, 21.3], "class": "handle"},
                             "latch": {"at": [46.5, 32.0], "size": [6.5, 7.4], "class": "latch"}}
    assert [(p["ref"], p["id"], p["at"], p["lift"]) for p in d["parts"]] == [
        ("common/terminal-screw-34@1", "pole-gnd", [12.2, 25.2], 9.5), ("common/terminal-screw-34@1", "pole-batt", [20.8, 25.2], 9.5),
        ("common/terminal-screw-34@1", "pole-rtn", [29.6, 25.2], 9.5)]
    assert [(q["role"], q["slot"]) for q in d["dc"]["ports"][0]["poles"]] == [("gnd", "pole-gnd"), ("batt", "pole-batt"), ("rtn", "pole-rtn")]


def test_the_contract_says_the_colours_are_estimates_read_off_the_pictures_and_that_nothing_moved():
    text = " ".join(str(contract()["provenance"]["block-colour"]).split())
    assert text.startswith("estimated") and "no document gives a colour code" in text
    assert "a change of colours only" in text and "Nothing is moved or resized" in text
    for colour in ("#1e2125", "#2b2f34", "#24282c", "#6b7076", "#c3c9cf"):
        assert colour in text, colour
