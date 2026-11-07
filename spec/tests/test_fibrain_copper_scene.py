"""What the Fibrain HD copper builds put in front of the explorer, and how each
module is told from the next (#1041, the preview of #1174).

THE BLANK 3D PREVIEW. The copper-mixed 3D shot came out a white canvas with no
model while the xps00 and xpu00 shots rendered. The scene is cut from the
compiled faces and added to the canvas only once every face texture has been
rasterised in turn - about sixty of them, a tenth of a second each on a
software renderer, so a first load takes six to eight seconds - and the shot had
been taken at a fixed six. No renderer error and no camera fault: nothing was
on the stage yet. A test cannot wait on a browser, and the pytest environment
holds none, so what it pins is what the scene is made of: if any of these
configurations compiled to faces with nothing in them, or lost a jack, the
scene would be blank for good and these fail. The shot is taken once the
explorer's "Download GLB" bar is up, which is when the model is.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal.artifacts import face_file

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"
COMPONENTS = LIB / "components" / "fibrain"
CONFIGS = ("copper-mixed", "xpu00-copper", "xps00-copper")
VIEWS = ("front", "rear", "top", "bottom", "left", "right")
JACK = re.compile(r"slot-[1-8]/module/pos-[1-6]/module/jack$")
SHELL_GREY = "#8d939a"       # the kit shell's --dim
HOLDER = "#17191b"           # the holder moulding the module strips sit against

# part -> (screened, keystone adapter)
MODULES = {
    f"x{cat}{s}{k}0": (s == 2, k == 1)
    for cat in "eqr" for s in (1, 2) for k in (0, 1)
}


def local(tag):
    return tag.rsplit("}", 1)[-1]


def painted(root):
    """Shapes that put colour on the drawing: a fill that is neither none nor
    transparent, or a stroke."""
    n = 0
    for e in root.iter():
        if local(e.tag) not in ("rect", "path", "circle", "ellipse", "polygon"):
            continue
        fill = (e.get("fill") or "").lower()
        if (fill and fill not in ("none", "transparent")) or e.get("stroke"):
            n += 1
    return n


@pytest.fixture(scope="module")
def built():
    if not (DIST / "xpu.configs.json").exists():
        pytest.fail("library/dist is not built: run ./build.sh --device xpu first")
    return DIST


@pytest.mark.parametrize("cfg", CONFIGS)
def test_a_copper_configuration_has_a_scene_to_draw(built, cfg):
    """All six faces the 3D scene is cut from exist and have colour in them, and
    the front carries a jack in every one of the 48 positions."""
    for view in VIEWS:
        path = face_file(built, "xpu", cfg, view)
        assert Path(path).exists(), (cfg, view)
        root = ET.parse(path).getroot()
        assert painted(root) >= 5, f"{cfg} {view}: a face with nothing on it is a blank scene"
    front = ET.parse(face_file(built, "xpu", cfg, "front")).getroot()
    jacks = [e for e in front.iter() if JACK.search(e.get("data-path") or "")]
    assert len(jacks) == 48, (cfg, len(jacks))
    assert painted(front) >= 400, (cfg, painted(front))


def srgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def luminance(h):
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def skin(name):
    path = COMPONENTS / name / "v1" / "skins" / "default.svg"
    return ET.parse(path).getroot()


def by_id(root, i):
    return next((e for e in root.iter() if e.get("id") == i), None)


@pytest.mark.parametrize("name", sorted(MODULES))
def test_a_module_face_says_what_the_module_is(name):
    """Screened modules draw a shield rim and keystone ones a collar and a
    latch; the others draw neither, so the four kinds of one category differ in
    shape and not only in colour."""
    screened, keystone = MODULES[name]
    root = skin(name)
    assert (by_id(root, "shield") is not None) == screened, name
    assert (by_id(root, "collar") is not None) == keystone, name
    assert (by_id(root, "latch") is not None) == keystone, name


@pytest.mark.parametrize("cat", "eqr")
def test_the_four_faces_of_a_category_are_four_drawings(cat):
    drawn = {ET.tostring(skin(f"x{cat}{s}{k}0")) for s in (1, 2) for k in (0, 1)}
    assert len(drawn) == 4


@pytest.mark.parametrize("name", sorted(n for n, (scr, _) in MODULES.items() if not scr))
def test_the_dark_shell_strips_read_against_the_holder(name):
    """The unscreened shell is near black on the maker's photograph and the
    holder is black: the strips above and below the frame are outlined in the
    kit's own dim grey, which reads against the holder (3:1 and over) on a light
    stage and a dark one."""
    root = skin(name)
    for i in ("housing-top", "housing-tab"):
        el = by_id(root, i)
        assert el.get("stroke") == SHELL_GREY, (name, i)
        assert contrast(el.get("stroke"), HOLDER) >= 3.0, (name, i)


def test_the_stand_ins_are_declared():
    """A figure no source gives is said to be a stand-in in the part's own
    sources, as the spec asks."""
    for name, (screened, keystone) in MODULES.items():
        c = yaml.safe_load((COMPONENTS / name / "v1" / "contract.yaml").read_text())
        prov = c["provenance"]
        if keystone or screened:
            assert "STAND-IN" in prov["art-stand-ins"], name
        else:
            assert "art-outline" in prov, name
        assert c["version"] == "1.0.1", name


def test_the_top_sheet_shows_what_the_sources_show(built):
    """The frame's top is not a flat slab: the five screw heads over the posts
    stand off the sheet in the compiled top face, and the eight slots are
    rimmed. The head height is the one estimated figure and is said so."""
    top = ET.parse(face_file(built, "xpu", "copper-mixed", "top")).getroot()
    heads = [e for e in top.iter() if (e.get("id") or "").startswith("top-sheet--screw-")]
    assert len(heads) == 5
    assert all(float(h.get("data-z-cyl")) > 0 for h in heads)
    assert all(float(h.get("data-z-lift")) + float(h.get("data-z-cyl")) < 43.96 for h in heads)
    rims = next(e for e in top.iter() if (e.get("id") or "").endswith("slot-rims"))
    assert len(re.findall(r"M ", next(iter(rims)).get("d"))) == 8
    c = yaml.safe_load((COMPONENTS / "xpu-top-sheet" / "v1" / "contract.yaml").read_text())
    assert "ESTIMATED" in c["provenance"]["top-features"]
