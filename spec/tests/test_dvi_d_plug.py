"""The DVI-D jack has a cable end: `generic/dvi-d-plug@1` mates the `dvi-d` key.

What is true of the library once it is in it: the plug mates the key the jack presents, it states the
figures the Digital Display Working Group's Digital Visual Interface specification, Revision 1.0, prints
for a digital plug (Figure 5-5, page 47) as numbers in the contract and the skin, it declares which figures
it estimates, and its skin is the plug seen from the cable end.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"

KEY = "dvi-d"
PLUG_DIR = LIB / "components/generic/dvi-d-plug/v1"


def contract():
    return yaml.safe_load((PLUG_DIR / "contract.yaml").read_text())


def skin():
    root = ET.parse(PLUG_DIR / "skins/default.svg").getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def standards():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def features():
    return {f["node"]: f for f in contract()["relief"]["features"]}


def test_the_plug_mates_the_key_the_jack_presents():
    c = contract()
    jack = yaml.safe_load((LIB / "components/std/dvi-d-jack/v1/contract.yaml").read_text())
    assert c["class"] == "port" and c["mates"] == KEY and jack["interface"] == KEY
    assert c["attrs"]["media"] == jack["attrs"]["media"] == KEY
    assert c["attrs"]["gender"] == "male"
    assert c["connection-points"]["mate"]["direction"] == "front"


def shell_box():
    """The bounding box of the shell path: the end point of every M, L and A segment."""
    tokens = re.findall(r"[MLAZ]|-?\d+\.?\d*", skin()["shell"].get("d"))
    xs, ys, i = [], [], 0
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd == "Z":
            continue
        n = 7 if cmd == "A" else 2
        args = [float(t) for t in tokens[i:i + n]]
        i += n
        xs.append(args[-2])
        ys.append(args[-1])
    return min(xs), min(ys), max(xs), max(ys)


def test_the_plug_conforms_to_its_standards_entry_at_the_outline_the_figure_prints():
    c = contract()
    entry = standards()[c["conforms"]]
    assert (c["size"]["w"], c["size"]["h"]) == (entry["w"], entry["h"]) == (39.5, 15.13)
    assert c["size-confidence"] == {"w": "drawing", "h": "drawing"}
    assert entry["confidence"] == "drawing"


def test_the_skin_draws_the_outline_the_contract_states():
    ids = skin()
    hood = ids["hood"]
    assert (float(hood.get("width")), float(hood.get("height"))) == (39.5, 15.13)
    assert (float(hood.get("x")), float(hood.get("y"))) == (0, 0)
    size = contract()["size"]
    assert (size["w"], size["h"]) == (39.5, 15.13)


def test_the_shell_is_24_16_by_7_90_and_centred_on_the_mate_point():
    x0, y0, x1, y1 = shell_box()
    assert abs((x1 - x0) - 24.16) < 0.005 and abs((y1 - y0) - 7.90) < 0.005
    mate = contract()["connection-points"]["mate"]["at"]
    assert mate == [19.75, 7.565]
    assert abs((x0 + x1) / 2 - mate[0]) < 0.005 and abs((y0 + y1) / 2 - mate[1]) < 0.005
    assert features()["shell"]["out"] == 6.5


def test_the_jackscrews_are_32_51_apart_level_and_centred_on_the_mate_point():
    ids = skin()
    left, right = ids["screw-l"], ids["screw-r"]
    assert abs(float(right.get("cx")) - float(left.get("cx")) - 32.51) < 0.005
    assert float(left.get("cy")) == float(right.get("cy")) == 7.565
    mate = contract()["connection-points"]["mate"]["at"]
    assert abs((float(left.get("cx")) + float(right.get("cx"))) / 2 - mate[0]) < 0.005
    assert float(left.get("r")) == float(right.get("r")) == 1.7


def test_the_stub_leaves_from_the_mate_point():
    ids = skin()
    mate = contract()["connection-points"]["mate"]["at"]
    stub = ids["stub"]
    assert [float(stub.get("cx")), float(stub.get("cy"))] == mate
    assert float(stub.get("r")) * 2 == contract()["fields"]["cable-od"]["default"]
    assert features()["stub"]["cyl"] == 30
    cable = contract()["connection-points"]["cable"]
    assert cable["at"] == mate and cable["on"] == "stub"


def test_the_contacts_are_recorded_and_not_drawn():
    c = contract()
    assert "contacts" in c["provenance"]
    assert not [i for i in skin() if i.startswith(("pin-", "cell-"))]


def test_every_estimate_of_the_plug_is_declared():
    prov = contract()["provenance"]
    for key in ("size", "contacts", "shell", "depth", "hood", "stub", "cable-od", "colour"):
        assert key in prov, key
    assert features()["stub"]["confidence"] == "estimated"
    assert features()["shell"]["confidence"] == "estimated"


def test_the_registry_entry_of_the_key_is_mated_by_the_plug():
    entry = render_mod._connector_registry()[KEY]
    assert "unmated" not in entry
    assert contract()["mates"] == KEY
