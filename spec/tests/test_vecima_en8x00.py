"""The Vecima EN8100 and EN8400 nodes: a strand-mounted housing that opens in two halves.

What is true of the two devices and their parts: the mount and the halves they state, where
each module sits, what the open drawing shows of the housing, and how the EN8400 differs
from the EN8100. Reads the library files only; nothing here needs a build.
"""
import pathlib
import re

import pytest
import yaml

import libdata
from portrayal import halves

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPONENTS = ROOT / "library/components/vecima"
NODES = ("vecima/en8100", "vecima/en8400")
BASE_BAYS = {"pem-1", "pem-2", "pem-3", "pem-4", "pem-5", "pem-6", "rfam-1", "rfam-2",
             "psm-1", "psm-2", "pdm"}
LID_BAYS = {"am-1", "am-2", "fim", "ldm", "tray"}


def node(slug):
    return dict(libdata.devices())[slug]


def open_view(slug):
    return node(slug)["views"]["lid-open"]


@pytest.mark.parametrize("slug", NODES)
def test_the_node_hangs_from_a_strand_and_opens_in_two_halves(slug):
    doc = node(slug)
    chassis = doc["chassis"]
    assert chassis["mount"] == "strand"
    assert chassis["halves"]["base"]["outer"] == "top"
    assert chassis["halves"]["lid"]["hinge"] == "rear"
    assert halves.seam_axis(doc) == "y"
    total = chassis["halves"]["base"]["stands"] + chassis["halves"]["lid"]["stands"]
    assert abs(total - chassis["height"]) <= halves.STANDS_TOLERANCE * chassis["height"]


@pytest.mark.parametrize("slug", NODES)
def test_every_number_of_the_halves_says_where_it_came_from(slug):
    provenance = node(slug)["provenance"]
    for key in ("halves.base.outer", "halves.base.stands", "halves.lid.hinge",
                "halves.lid.angle", "halves.lid.stands"):
        assert provenance[key]["confidence"] in {"estimated", "photo-measured", "drawing", "datasheet"}
        assert len(provenance[key]["note"]) > 40, key
    assert provenance["halves.lid.angle"]["confidence"] == "estimated"


@pytest.mark.parametrize("slug", NODES)
def test_each_module_is_on_the_half_the_figure_shows(slug):
    by_bay = halves.bay_halves(node(slug))["lid-open"]
    assert {b for b, h in by_bay.items() if h == "base"} == BASE_BAYS
    assert {b for b, h in by_bay.items() if h == "lid"} == LID_BAYS


@pytest.mark.parametrize("slug", NODES)
def test_the_open_drawing_shows_ten_bolts_a_gasket_and_two_hinges_on_each_half(slug):
    decor = open_view(slug)["panel"]["decor"]
    for half in ("base", "lid"):
        bolts = [d for d in decor if d.get("kind") == "bolt-head" and d["id"].startswith(f"{half}-bolt-")]
        assert len(bolts) == 10, half
        assert any(d.get("kind") == "gasket" and d["id"] == f"{half}-gasket" for d in decor)
    assert len([d for d in decor if d.get("kind") == "hinge-pin"]) == 2
    assert any(d.get("kind") == "finned-strip" for d in decor)


@pytest.mark.parametrize("slug", NODES)
def test_the_closed_faces_show_the_closure_bolts_the_hinge_and_the_strand_clamps(slug):
    views = node(slug)["views"]
    kinds = lambda face: [d.get("kind") for d in views[face]["panel"]["decor"]]  # noqa: E731
    assert kinds("front").count("bolt-head") == 3
    assert kinds("rear").count("hinge") == 6
    assert kinds("top").count("strand-clamp") == 2
    # the three bolts the guide numbers on the front are numbered on the drawing
    numbers = [m["text"] for m in views["front"]["silkscreen"] if m["text"].isdigit()]
    assert sorted(numbers) == ["1", "3", "5"]


def test_the_en8400_is_the_en8100_housing_with_its_own_port_entry_modules():
    a, b = node("vecima/en8100"), node("vecima/en8400")
    assert a["chassis"] == b["chassis"]
    bays_a = {x["id"]: x for x in open_view("vecima/en8100")["components"]["bays"]}
    bays_b = {x["id"]: x for x in open_view("vecima/en8400")["components"]["bays"]}
    assert bays_a.keys() == bays_b.keys()
    for bay_id, bay_a in bays_a.items():
        bay_b = bays_b[bay_id]
        assert (bay_a["at"], bay_a["size"]) == (bay_b["at"], bay_b["size"]), bay_id
        if bay_id.startswith("pem-"):
            assert bay_a["accepts"][0].startswith("vecima/en8100-pem-")
            assert bay_b["accepts"][0] == bay_a["accepts"][0].replace("en8100", "en8400")
        else:
            assert bay_a["accepts"] == bay_b["accepts"], bay_id


def test_the_en8400_front_carries_the_orange_label_the_en8100_does_not():
    def labels(slug):
        return [d["id"] for d in node(slug)["views"]["front"]["panel"]["decor"]
                if d.get("kind") == "label-plate"]
    assert "label-1800" in labels("vecima/en8400")
    assert "label-1800" not in labels("vecima/en8100")


@pytest.mark.parametrize("slug", NODES)
def test_the_faces_are_drawn_as_installed_with_the_lid_below(slug):
    views = node(slug)["views"]
    seam_top, seam_bottom = 136, 152  # the flange band on every closed face
    for face in ("left", "right"):
        plugs = {p["id"]: p for p in views[face]["components"]["placements"]}
        assert plugs["fibre-plug"]["at"][1] >= seam_bottom, face  # the lid, the lower half
        for name, plug in plugs.items():
            if name != "fibre-plug":  # the RF/AC, AC-only and test plugs are the base's
                assert plug["at"][1] + 30 <= seam_top, (face, name)
    # the two ends are a pair: the same plugs, mirrored left to right
    left = {p["id"]: p["at"] for p in views["left"]["components"]["placements"]}
    right = {p["id"]: p["at"] for p in views["right"]["components"]["placements"]}
    assert left["fibre-plug"][0] < 281 / 2 < right["fibre-plug"][0]
    for face in ("front", "rear"):
        fins = {d["id"]: d for d in views[face]["panel"]["decor"] if d.get("kind") == "heat-sink-fins"}
        tall = [d for i, d in fins.items() if i.startswith("fins-tall")]
        short = [d for i, d in fins.items() if i.startswith("fins-short")]
        assert tall and short, face
        assert all(d["at"][1] >= seam_bottom for d in tall), face  # the lid's tall fins, below
        assert all(d["at"][1] + d["size"][1] <= seam_top for d in short), face


@pytest.mark.parametrize("slug", NODES)
def test_the_three_arrangements_the_makers_drawing_shows_are_configurations(slug):
    configs = node(slug)["configurations"]
    assert configs["2am-2x4"].get("default") is True
    assert configs["2am-no-fim"]["bays"] == {"fim": ""}
    assert configs["fiber-deep-1x2"]["bays"] == {"fim": "", "am-2": ""}


def test_the_amplifier_module_draws_its_connectors_and_circuit_lines():
    """Reads the skin's source text because no library interface returns a skin's contents.

    What it asks about, the ids of the drawn groups and two connector colours, is a property
    of the drawing in the file; a build is not run here (this module reads library files only)
    and the built drawing is not the place to look for what a skin file drew. The file is read
    as text, never parsed, so it adds milliseconds; the 21 seconds of this module is the one
    library load the other tests share through `libdata`, not a cost of this test.
    """
    skin = (COMPONENTS / "en8100-rfam/v1/skins/default.svg").read_text()
    for group in ("shunts", "test-leads", "rf-circuit"):
        assert f'id="{group}"' in skin
    assert "#e0782c" in skin  # the orange AC shunt connector
    assert "#1a1b1d" in skin  # the black connector block


def test_no_maker_lettering_and_no_document_hash_is_published():
    """Reads each skin's source text because no library interface returns a skin's lettering.

    The device views' lettering comes through `libdata`; the skins' text is only in the files,
    and a check of what the maker's logo would look like must see every file, built or not.
    They are read as text, not parsed, so the cost is milliseconds; the 21 seconds of this
    module is the shared library load, not this test.
    """
    texts = []
    for slug in NODES:
        doc = node(slug)
        assert "sha256" not in yaml.safe_dump(doc), slug
        for view in doc["views"].values():
            texts += [m.get("text", "") for m in view.get("silkscreen") or []]
    for skin in COMPONENTS.glob("*/v1/skins/*.svg"):
        texts += re.findall(r">([^<]+)<", skin.read_text())
    assert not [t for t in texts if "vecima" in t.lower()]
