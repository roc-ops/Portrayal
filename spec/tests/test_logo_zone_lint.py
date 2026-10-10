"""L172: what is named for a logo is a reserved place, and paints nothing.

A vendor mark is never reproduced; its place is reserved as `logo-zone` - an
empty rect in a part's skin, a region on a device. The rule reads NAMES, so
these cases pin both halves: each way a named logo has been drawn is caught,
and every shape that reserves without painting stays quiet. The sweep at the
end says today's library is clean and that the rule had something to read.
"""
import pathlib

import yaml

from portrayal import libwalk
from portrayal import lint as L

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "library"
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 57">{}</svg>'


def part(tmp_path, body, elements=None):
    """A contract with one skin, on disk, because the rule opens the skin."""
    d = tmp_path / "components" / "acme" / "label" / "v1"
    (d / "skins").mkdir(parents=True)
    (d / "skins" / "default.svg").write_text(SVG.format(body))
    doc = {"kind": "component", "name": "label", "size": {"w": 120.0, "h": 57.0},
           "skins": ["default"]}
    if elements is not None:
        doc["elements"] = elements
    path = d / "contract.yaml"
    path.write_text(yaml.safe_dump(doc))
    with L.collecting() as found:
        L.lint_component_logo_zone(path, doc)
    assert not [w for w in found.warnings if "L172" in w], "L172 is an error, never a warning"
    return [e for e in found.errors if "L172" in e]


def device(front):
    with L.collecting() as found:
        L.lint_device_logo_zone("t", {"kind": "device", "views": {"front": front}})
    return [e for e in found.errors if "L172" in e]


ZONE = {"logo-zone": {"at": [18.8, 7.9], "size": [11.6, 9.8], "class": "logo-zone"}}


# ---- a part -----------------------------------------------------------------

def test_a_reserved_box_is_silent(tmp_path):
    assert part(tmp_path, '<rect id="logo-zone" x="18.8" y="7.9" width="11.6" '
                          'height="9.8" fill="none"/>', ZONE) == []


def test_a_reserved_box_may_say_stroke_none_and_be_numbered(tmp_path):
    assert part(tmp_path, '<rect id="logo-zone-2" x="1" y="1" width="5" height="5" '
                          'fill="none" stroke="none"/>',
                {"logo-zone-2": {"at": [1, 1], "size": [5, 5]}}) == []


def test_a_drawn_mark_named_logo_is_caught(tmp_path):
    """The stand-in this rule was written after: a black triangle with the id
    `logo` where a vendor's triangle mark sits."""
    hits = part(tmp_path, '<path id="logo" d="M 14 8 L 22 20 L 6 20 Z" fill="#231f20"/>')
    assert len(hits) == 1 and "'logo'" in hits[0] and "logo-zone" in hits[0], hits


def test_a_filled_reserved_box_is_caught(tmp_path):
    hits = part(tmp_path, '<rect id="logo-zone" x="1" y="1" width="5" height="5" '
                          'fill="#d7dbdf"/>', ZONE)
    assert len(hits) == 1 and "fill='#d7dbdf'" in hits[0], hits


def test_a_reserved_box_with_no_fill_stated_is_caught(tmp_path):
    """SVG paints a rect black when it states no fill."""
    hits = part(tmp_path, '<rect id="logo-zone" x="1" y="1" width="5" height="5"/>', ZONE)
    assert len(hits) == 1 and "fill=None" in hits[0], hits


def test_a_stroked_or_styled_reserved_box_is_caught(tmp_path):
    hits = part(tmp_path, '<rect id="logo-zone" x="1" y="1" width="5" height="5" '
                          'fill="none" stroke="#fff" style="fill:#000"/>', ZONE)
    assert len(hits) == 1 and "stroke" in hits[0] and "style" in hits[0], hits


def test_a_group_of_shapes_under_the_reserved_name_is_caught(tmp_path):
    hits = part(tmp_path, '<g id="logo-zone" fill="none"><circle r="3"/></g>', ZONE)
    assert len(hits) == 1 and "<g>" in hits[0] and "child" in hits[0], hits


def test_an_element_named_for_a_logo_is_logo_zone(tmp_path):
    hits = part(tmp_path, '', {"front-logo": {"at": [1, 1], "size": [5, 5]}})
    assert len(hits) == 1 and "elements/front-logo" in hits[0], hits


def test_the_letters_alone_are_not_the_word(tmp_path):
    """`catalogo` and `analogous` have the letters and name no logo."""
    assert part(tmp_path, '<rect id="catalogo" x="1" y="1" width="5" height="5" '
                          'fill="#000"/><path id="analogous-input" d="M0 0 L1 1"/>') == []


def test_a_skin_the_contract_does_not_list_is_read_too(tmp_path):
    d = tmp_path / "components" / "acme" / "label" / "v1" / "skins"
    d.mkdir(parents=True)
    (d / "body-top.svg").write_text(SVG.format('<path id="logo" d="M0 0 L1 1 Z"/>'))
    (d / "default.svg").write_text(SVG.format(''))
    path = d.parent / "contract.yaml"
    with L.collecting() as found:
        L.lint_component_logo_zone(path, {"kind": "component", "skins": ["default"]})
    hits = [e for e in found.errors if "L172" in e]
    assert len(hits) == 1 and "body-top.svg" in hits[0], hits


# ---- a device ---------------------------------------------------------------

def test_a_region_with_its_box_is_silent():
    assert device({"regions": [{"id": "logo-zone", "at": [406.9, 6.1],
                                "size": {"w": 25.2, "h": 4.4}}]}) == []
    assert device({"regions": [{"id": "logo-zone-1", "at": [1, 1], "size": {"w": 2, "h": 2}},
                               {"id": "logo-zone-2", "at": [1, 9], "size": {"w": 2, "h": 2}}]}) == []


def test_a_region_with_no_box_reserves_nothing():
    hits = device({"regions": [{"id": "logo-zone", "label": "Branding area"}]})
    assert len(hits) == 1 and "`at` and `size`" in hits[0], hits


def test_a_region_named_for_a_logo_is_logo_zone():
    hits = device({"regions": [{"id": "vendor-logo", "at": [1, 1], "size": {"w": 2, "h": 2}}]})
    assert len(hits) == 1 and "vendor-logo" in hits[0], hits


def test_nothing_a_view_draws_is_named_for_a_logo():
    box = {"id": "logo-box", "at": [409.0, 5.0], "size": [22.0, 9.0], "fill": "#d7dbdf"}
    for front, kind in [({"panel": {"decor": [box]}}, "decor"),
                        ({"panel": {"cutouts": [box]}}, "cutout"),
                        ({"silkscreen": [{"id": "logo", "at": [1, 1], "mark": "arrow"}]},
                         "silkscreen"),
                        ({"components": {"bays": [dict(box, id="logo-bay")]}}, "bay"),
                        ({"components": {"placements": [{"id": "logo", "ref": "acme/mark@1",
                                                         "at": [1, 1]}]}}, "placement")]:
        hits = device(front)
        assert len(hits) == 1 and kind in hits[0], (kind, hits)


def test_real_metal_under_another_name_is_not_guessed_at():
    """A recessed badge and a label plate are parts of the face; the rule reads
    the word logo and nothing wider."""
    assert device({"panel": {"decor": [
        {"id": "badge-1", "at": [19.7, 5.1], "size": [34.8, 9.2], "fill": "#17191b"},
        {"id": "brand-plate", "at": [26.0, 1.0], "size": [56.0, 8.6], "fill": "#17191c"}]},
        "regions": [{"id": "status-leds"}]}) == []


# ---- today's library --------------------------------------------------------

def test_the_library_is_clean_and_the_rule_read_something():
    zones = regions = 0
    with L.collecting() as found:
        for f in libwalk.iter_components(LIBRARY):
            doc = yaml.safe_load(f.read_text())
            if (doc or {}).get("kind") == "kit":
                continue
            zones += sum(1 for el in (doc.get("elements") or {}) if L._names_a_logo(el))
            L.lint_component_logo_zone(f, doc)
        for f in libwalk.iter_devices(LIBRARY):
            doc = yaml.safe_load(f.read_text())
            regions += sum(1 for v in (doc.get("views") or {}).values() if isinstance(v, dict)
                           for r in v.get("regions") or [] if L._names_a_logo(r.get("id")))
            L.lint_device_logo_zone(f, doc)
    hits = [e for e in found.errors if "L172" in e]
    assert not hits, "\n".join(hits)
    # not vacuous: the rule had reserved places to read on both sides
    assert zones >= 100 and regions >= 25, (zones, regions)
