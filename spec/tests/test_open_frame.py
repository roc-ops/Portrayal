"""An open-frame face: empty bays open into the chassis, not into pockets.

The CommScope CH3000 is an open frame - card-guide rails top and bottom, a
mid-plane across the top rear, and nothing between the slots - so an empty slot
is seen straight through, front to rear. Before `open-frame`, every empty bay
compiled to a pocket as deep as its deepest occupant with four walls, a floor and
a back, and the 3D chassis read as sixteen closed tubes. A view that declares
`open-frame: true` compiles each bay as a see-through mouth (no floor, no back)
flagged so the kit builds no walls round it; a seated module is drawn over it.
"""
import json
from pathlib import Path

import jsonschema
import pytest

from portrayal import render

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
# any library card will do; this one is 380 deep, which the pocket test reads back
CARD = "casa/ds-8x8@1"


def _device(open_frame, seated=None):
    front = {
        "size": {"w": 70.0, "h": 350.0},
        "components": {"bays": [
            {"id": "slot-1", "at": [2.0, 2.0], "size": {"w": 30.47, "h": 345.5},
             "accepts": [CARD], "group": "slots", "rel-pos": 1},
            {"id": "slot-2", "at": [34.0, 2.0], "size": {"w": 30.47, "h": 345.5},
             "accepts": [CARD], "group": "slots", "rel-pos": 2},
        ]},
    }
    if open_frame:
        front = {"size": front["size"], "open-frame": True, "components": front["components"]}
    return {
        "format": 1, "kind": "device", "name": "t", "version": "0.1.0", "maturity": "draft",
        "manufacturer": "T", "model": "T",
        "chassis": {"width": 70.0, "height": 350.0, "depth": 400.0},
        "groups": {"slots": {"term": "Slot", "role": "traffic", "index-origin": 1}},
        "views": {"front": front},
    }, {"bays": {"slot-1": seated}} if seated else {}


def _openings(svg):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(svg) if isinstance(svg, (str, bytes)) else svg
    return root, {el.get("id"): el for el in root.iter()
                  if (el.get("id") or "").endswith("--opening")}


def _render(open_frame, seated=None):
    lib = render.Library([str(LIB)])
    dev, cfg = _device(open_frame, seated)
    out = render.render_view(dev, "front", dev["views"]["front"], lib, config=cfg)
    return out[0] if isinstance(out, tuple) else out


def test_an_empty_bay_on_an_open_frame_is_see_through_and_wall_less():
    _, ops = _openings(_render(open_frame=True))
    for bid in ("slot-1--opening", "slot-2--opening"):
        el = ops[bid]
        assert el.get("data-see-through") == "1", bid
        assert el.get("data-open-frame") == "1", bid
        assert el.get("data-depth"), f"{bid}: a mouth with no depth is not a cavity at all"


def test_a_seated_bay_on_an_open_frame_is_the_same_open_mouth():
    """Occupied or not, as an open-backed bay's is: a pulled module must leave the
    open frame an empty build shows, not a dark box. The seated module is drawn
    over the mouth from unpunched art (relief.js `openBack`), so it still shows."""
    root, ops = _openings(_render(open_frame=True, seated=CARD))
    for bid in ("slot-1", "slot-2"):
        el = ops[f"{bid}--opening"]
        assert el.get("data-see-through") == "1", bid
        assert el.get("data-open-frame") == "1", bid
    bays = {el.get("id"): el for el in root.iter() if el.get("data-open-back") == "1"}
    assert {"slot-1", "slot-2"} <= set(bays)
    seated = [el for el in root.iter() if (el.get("data-ref") or "").startswith(CARD)]
    assert seated, "the seated module must still be drawn"


def test_without_open_frame_an_empty_bay_is_still_a_pocket():
    _, ops = _openings(_render(open_frame=False))
    el = ops["slot-1--opening"]
    assert el.get("data-see-through") is None
    assert el.get("data-open-frame") is None
    assert el.get("data-depth") == "380"


def test_the_face_itself_says_it_is_an_open_frame():
    root, _ = _openings(_render(open_frame=True))
    assert root.get("data-open-frame") == "1"
    root, _ = _openings(_render(open_frame=False))
    assert root.get("data-open-frame") is None


def test_the_schema_accepts_open_frame_on_a_view():
    schema = json.loads((SPEC / "schemas/device.schema.json").read_text())
    view = schema["properties"]["views"]["additionalProperties"]
    assert "open-frame" in view["properties"]
    jsonschema.validate({"size": {"w": 1, "h": 1}, "open-frame": True}, view)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"size": {"w": 1, "h": 1}, "open-frame": "yes"}, view)
