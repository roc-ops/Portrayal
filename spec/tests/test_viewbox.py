"""A drawing's viewBox must cover the panel it draws.

The bug this locks: the region-extent code unpacked its box as `x, y, w, h`,
shadowing the VIEW's own w and h for the remainder of render_view. Everything
downstream that asked "how big is this panel" got the last region's box instead.
The C100G rear came out 420.8 x 471.5 against a 432.95 x 571.0 panel - one line
card clipped off the right edge and BOTH PEMs outside the drawing entirely,
present in the tree and invisible in the image.

Why nothing caught it: every element was still emitted at the correct
coordinate, so no rule about positions or sizes could see anything wrong. The
data was right and the window onto it was too small. A test that reads the
manifest and the output and compares the two is the only thing that can tell.

It also silently corrupts 3D, because the face texture is rasterised from this
SVG - which is how it was found: the owner reported cards apparently 30% too
wide and PEMs missing from a view whose YAML places them correctly.
"""
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
DEVICES = ROOT / "library" / "devices"
VB = re.compile(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"')


def rendered_as(d, vname, view):
    """The files the renderer actually writes for one view.

    A VIEW IS NOT ALWAYS ITS OWN FILENAME. A view may declare `face: front`,
    which makes it a VARIANT of the front - a different drawing of the same
    face, chosen by configuration:

        views:            front-lff-12: {face: front, ...}
        configurations:   lff-12: {views: {front: front-lff-12}}

    and the renderer names the output by the FACE, not by the view - so that
    variant comes out as `r740xd.lff-12.front.svg`. Globbing `*{view}.svg`
    finds nothing for it.

    That cost the r740xd's twelve-bay front its only check: the drawing was
    built, the test skipped with "not built", and the skip sat one under the CI
    guard's threshold so nothing said so. It also worked the other way - the
    plain `front` glob swept up all three variant files and measured them
    against the BASE view's size. Both views happen to declare 482.6 x 86.8
    today, so it passed by coincidence; a variant with its own size would have
    been compared against the wrong number.

    A VARIANT IS RESOLVED PRECISELY and a base face by SUBTRACTION, which is
    deliberate. A variant's configurations are named in the manifest, so they
    can be listed. The base face's are not exhaustively knowable from the
    manifest: a device that declares no configurations at all still renders a
    synthetic `mx150.default.front.svg`, and modelling that here would mean
    tracking every naming rule the renderer has. Taking everything on disk for
    the face and removing what the variants claim needs to know only what IS a
    variant, which the manifest does say.
    """
    face = (view or {}).get("face") or vname
    cfgs = d.get("configurations") or {}

    def selected_by(target):
        return [cn for cn, c in cfgs.items()
                if ((c or {}).get("views") or {}).get(face) == target]

    if (view or {}).get("face"):
        return [DIST / f"{d['name']}.{cn}.{face}.svg" for cn in selected_by(vname)]

    # the base drawing of this face: everything rendered for it, less every
    # file a variant of the same face claims
    variants = [n for n, v in (d.get("views") or {}).items()
                if (v or {}).get("face") == face]
    taken = {DIST / f"{d['name']}.{cn}.{face}.svg"
             for var in variants for cn in selected_by(var)}
    on_disk = {p for p in DIST.glob(f"{d['name']}.*{face}.svg")
               if p.name.endswith(f".{face}.svg")}
    return sorted(on_disk - taken)


def cases():
    out = []
    for dev in sorted(DEVICES.glob("*/*/device.yaml")):
        d = yaml.safe_load(dev.read_text()) or {}
        for vname, view in (d.get("views") or {}).items():
            size = (view or {}).get("size")
            if size:
                out.append((d["name"], vname, size["w"], size["h"],
                            [str(f) for f in rendered_as(d, vname, view)]))
    return out


@pytest.mark.parametrize("name,view,w,h,expected", cases())
def test_viewbox_covers_the_declared_panel(name, view, w, h, expected):
    files = [pathlib.Path(f) for f in expected]
    files = [f for f in files if f.exists()]
    if not files:
        pytest.skip(f"{name}.{view} not built")
    for f in files:
        m = VB.search(f.read_text()[:4096])
        assert m, f"{f.name}: no viewBox"
        x, y, vw, vh = (float(g) for g in m.groups())
        # the window may be LARGER than the panel - a placement can legitimately
        # hang off the edge, and that is what the extents pass is for - but it
        # may never be smaller, and it must include the panel's own origin.
        assert x <= 0 and y <= 0, f"{f.name}: viewBox origin {x},{y} excludes the panel"
        assert vw + x >= w - 0.01, (
            f"{f.name}: viewBox is {vw:g} wide from {x:g} but the panel is {w:g} - "
            f"{w - (vw + x):.2f} mm of it is outside the drawing")
        assert vh + y >= h - 0.01, (
            f"{f.name}: viewBox is {vh:g} tall from {y:g} but the panel is {h:g} - "
            f"{h - (vh + y):.2f} mm of it is outside the drawing")


# ---- the mapping itself ------------------------------------------------------
#
# `rendered_as` is the part that was wrong, so it gets its own tests rather than
# being covered only through the parametrised sweep above. A resolution bug is
# invisible there: a view that resolves to NO files skips, and a skip reads as
# "not built" rather than as a fault.

def _r740xd():
    return yaml.safe_load((DEVICES / "dell" / "r740xd" / "device.yaml").read_text())


def test_a_variant_view_resolves_to_the_configurations_that_select_it():
    """`front-lff-12` is drawn only when a configuration redirects the front to
    it. Before this, nothing matched `*front-lff-12.svg` and the twelve-bay
    front - the whole point of the change that added it - went unchecked."""
    d = _r740xd()
    got = {f.name for f in rendered_as(d, "front-lff-12", d["views"]["front-lff-12"])}
    # THE PROPERTY, NOT THE ROLL-CALL. This asserted three configuration names
    # and broke the moment the device was renamed onto Dell's own scheme - a
    # test measuring the spelling of its fixture rather than the resolver. What
    # has to hold is that the variant resolves to EXACTLY the configurations
    # that bind it, whatever those are called and however many there are.
    bound = {n for n, c in d["configurations"].items()
             if (c.get("views") or {}).get("front") == "front-lff-12"}
    assert bound, "no configuration binds the variant - the fixture changed"
    assert got == {f"r740xd.{n}.front.svg" for n in bound}, got


def test_a_base_face_does_not_sweep_up_its_own_variants():
    """The other half of the bug, and the quieter one. The old glob measured
    all three variant drawings against the BASE front's declared size. Both
    happen to be 482.6 x 86.8 today, so it passed for the wrong reason."""
    d = _r740xd()
    got = {f.name for f in rendered_as(d, "front", d["views"]["front"])}
    bound = {n for n, c in d["configurations"].items()
             if (c.get("views") or {}).get("front") == "front-lff-12"}
    assert not (got & {f"r740xd.{n}.front.svg" for n in bound}), got
    # the unconfigured drawing belongs to the base face and is always present
    assert "r740xd.front.svg" in got
    assert got, "the base front resolved to nothing at all"


def test_every_rendered_file_is_claimed_by_exactly_one_view():
    """The completeness property, which is what makes the two above more than
    spot checks: for a face whose view declares a size, the views' resolved
    files must partition what is on disk - none checked twice against two
    different declared sizes, and none left unchecked.

    Scoped to faces that DECLARE a size, because `cases()` is. A view with no
    `size:` has no declared panel to cover, so it yields no case and claims no
    file - the as5912-54x draws a front and a rear it never dimensions. That is
    a real hole in this test's reach, but it is a different one, and pretending
    those files should be claimed here would only hide it behind a failure
    about variants.
    """
    for dev in sorted(DEVICES.glob("*/*/device.yaml")):
        d = yaml.safe_load(dev.read_text()) or {}
        if d.get("kind") != "device":
            continue
        claimed, sized_faces = [], set()
        for vname, view in (d.get("views") or {}).items():
            if not (view or {}).get("size"):
                continue
            sized_faces.add((view or {}).get("face") or vname)
            claimed += [f for f in rendered_as(d, vname, view) if f.exists()]

        dupes = sorted({p.name for p in claimed if claimed.count(p) > 1})
        assert not dupes, f"{d['name']}: claimed by two views: {dupes}"

        for face in sized_faces:
            on_disk = {p for p in DIST.glob(f"{d['name']}.*{face}.svg")
                       if p.name.endswith(f".{face}.svg")}
            missed = sorted(p.name for p in on_disk - set(claimed))
            assert not missed, \
                f"{d['name']}: rendered but checked by no view: {missed}"
