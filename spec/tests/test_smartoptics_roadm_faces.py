"""The two DCP-R ROADM faceplates, against Smartoptics' own stencil.

Every figure here is measured off the stencil masters `r-34d-cs.gif` and
`r-9d-csx.jpeg` in `working/intake/dcp-r-v260105/`, which are not committed.
The numbers are.

These exist because all four defects they cover were invisible to lint. Three
were sub-millimetre placement drift that only reads as wrong to an eye on the
rendered face, and the fourth could not render at all until std/lc-bore@3 made
the LC bore keyed (#126): a 4.7 square has no orientation, so a mirrored row
drew identically to an unmirrored one.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
ROADMS = ("dcp-r-34d-cs", "dcp-r-9d-cs")


def dev(name):
    return yaml.safe_load((LIB / "devices" / "smartoptics" / name / "device.yaml").read_text())


def front(name):
    return dev(name)["views"]["front"]


def adapters(name):
    return [p for p in front(name)["components"]["placements"]
            if p["ref"].startswith("common/lc-duplex-adapter@")]


def test_the_bottom_row_is_mirrored_and_the_top_row_is_not():
    """A row is turned over as a unit, and only the lower one is.

    Stated by y rather than by port count, because Line shares the upper row's
    y on both faces and 1510 sits on a y of its own - so "the two biggest rows"
    is not the same set as "the channel block".
    """
    for name in ROADMS:
        rows = {}
        for p in adapters(name):
            rows.setdefault(p["at"][1], set()).add(p.get("rotate"))
        for y, rots in rows.items():
            assert len(rots) == 1, f"{name}: row at y={y} is half turned over: {rots}"
        turned = {y for y, r in rows.items() if r == {180}}
        upright = {y for y, r in rows.items() if r == {None}}
        assert turned and upright, f"{name}: expected one mirrored row and one not"
        assert min(turned) > max(upright), f"{name}: the MIRRORED row is the lower one"


def test_rotation_is_a_placement_key_and_not_an_attribute():
    """`attrs` is free-form, so `rotate` misfiled into it lints clean and does
    nothing at all. That is exactly how this was got wrong the first time."""
    for name in ROADMS:
        for p in front(name)["components"]["placements"]:
            assert "rotate" not in (p.get("attrs") or {}), f"{name}/{p['id']}: rotate inside attrs"


def test_the_two_management_jacks_share_one_x():
    # The stencil's own connection points disagree by 0.45mm on the 34D and
    # 0.14mm on the 9D - hand-placed Visio dots - while the art draws both
    # shells flush. Whatever value is chosen, the two must agree.
    for name in ROADMS:
        pl = {p["id"]: p for p in front(name)["components"]["placements"]}
        assert pl["eth0"]["at"][0] == pl["rs232"]["at"][0], name
        boxes = {e["id"]: e for e in front(name)["panel"]["cutouts"]}
        # the hit-boxes have to move with the art, or the port map lies
        assert boxes["eth0"]["at"][0] == pl["eth0"]["at"][0], name
        assert boxes["rs232"]["at"][0] == pl["rs232"]["at"][0], name


def labels(name):
    return front(name)["silkscreen"]


def test_the_osc_captions_sit_either_side_of_their_own_leds():
    for name in ROADMS:
        pl = {p["id"]: p for p in front(name)["components"]["placements"]}
        tx_led = pl["led-osc-tx"]["at"][0] + 1.0     # led-dot is 2.0 square
        rx_led = pl["led-osc-rx"]["at"][0] + 1.0
        cap = [l for l in labels(name) if l.get("for") == "port-osc" and l["text"] in ("Tx", "Rx")]
        tx = next(l for l in cap if l["text"] == "Tx")["at"][0]
        rx = next(l for l in cap if l["text"] == "Rx")["at"][0]
        # Tx caption left of its LED, Rx right of its own, and by the same margin
        assert tx < tx_led and rx > rx_led, name
        assert abs((tx_led - tx) - (rx - rx_led)) < 0.25, f"{name}: captions not symmetric"
        # and the pair is centred on the cage it labels
        osc = next(e for e in front(name)["panel"]["cutouts"] if e["id"] == "port-osc")
        cage_mid = osc["at"][0] + osc["size"][0] / 2
        assert abs((tx + rx) / 2 - cage_mid) < 0.5, f"{name}: caption pair off the cage centre"


def test_power_and_status_do_not_run_together():
    """They rendered as the single word "PowerStatus". The captions are centred
    on their own LEDs, so the collision was really the LED pitch: the stencil
    draws 6.1mm and the model carried 5.6."""
    for name in ROADMS:
        pl = {p["id"]: p for p in front(name)["components"]["placements"]}
        pitch = pl["led-status"]["at"][0] - pl["led-power"]["at"][0]
        assert pitch > 6.0, f"{name}: status LED pitch {pitch} too tight for the captions"
        cap = {l["text"]: l["at"][0] for l in labels(name) if l["text"] in ("Power", "Status")}
        # each caption over its own LED, within a quarter of a millimetre
        for text, led in (("Power", "led-power"), ("Status", "led-status")):
            assert abs(cap[text] - (pl[led]["at"][0] + 1.0)) < 0.25, f"{name}: {text} off its LED"


def test_both_roadms_took_a_major_bump_for_the_moved_ports():
    # Ports moved, so consumers keyed to positions break. devicelock asks for a
    # major and it is right to; this keeps the reason attached to the number.
    for name in ROADMS:
        assert dev(name)["version"].startswith("2."), name


def test_the_corrections_are_sourced_in_provenance():
    for name in ROADMS:
        prov = dev(name)["provenance"]
        for key in ("xc-orientation", "mgmt-jack-alignment", "osc-captions", "status-leds"):
            assert key in prov, f"{name}: {key} not recorded"
            assert "stencil" in prov[key], f"{name}: {key} does not name its source"
