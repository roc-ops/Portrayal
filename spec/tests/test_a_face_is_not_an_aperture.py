"""A component drawn as another part's FACE must not compile to a hole.

`render.py` treats `size.d` on a fixed component as an APERTURE: the instance
group gets `data-depth`, and the kit punches a recess that deep behind the whole
bounding box. That is right for a cage or a port opening and wrong for a face,
which is the drawing of a surface - the back of a cassette, the plan of a card -
and has no depth of its own. The body it closes carries the depth, and says so
in `body.depth`.

WHAT IT COST. Ten FHD rear faces carried an estimated `d: 2.0`, so every cassette
back was a 2 mm pit the size of the face. Nobody saw it while the backs were
flat. The moment a flanged MTP on one of them declared a recessed `opening`,
that pocket landed INSIDE the face-wide cavity - and `cavities` in relief.js
takes only the innermost recess of a nest:

    [...q('[data-depth]')].filter(el => !el.querySelector('[data-depth]'))

so the pocket deleted the pit rather than nesting in it, and neither was built
the way its contract asked. `test_a_pocket_does_not_swallow_the_cavity_it_sits_in`
caught the collision; this catches the cause, which is the face claiming to be a
hole in the first place.

Read off the COMPILED drawing, not the contract, because `size.d` is only one way
in - an explicit `relief.cavity` is another, and a face has no use for either.
"""
import json
import pathlib
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"


def test_no_component_used_as_a_face_compiles_to_an_aperture():
    index = DIST / "components.json"
    if not index.exists():
        pytest.skip("library/dist not built")
    entries = json.loads(index.read_text())
    entries = entries["components"] if isinstance(entries, dict) else entries
    by_ref = {f"{e['ns']}/{e['name']}@{e['version'].split('.')[0]}": e for e in entries}

    faces, bad = 0, []
    for e in entries:
        here = f"{e['ns']}/{e['name']}@{e['version'].split('.')[0]}"
        for direction, ref in (e.get("faces") or {}).items():
            target = by_ref.get(ref)
            assert target, f"{here} names {ref} as its {direction} face and it is not in the index"
            drawing = (target.get("files") or {}).get("default")
            if not drawing:
                continue
            faces += 1
            root = ET.parse(DIST / drawing).getroot()
            top = next((g for g in root.iter() if g.get("data-path") == target["name"]), None)
            if top is not None and top.get("data-depth") is not None:
                bad.append(f"{ref} is the {direction} face of {here} and compiles to a "
                           f"{top.get('data-depth')} mm aperture over its whole area "
                           "(drop `size.d` - the body it closes carries the depth)")

    assert faces >= 10, (
        f"only {faces} face drawings were reached, so this sweep is not measuring "
        "the library it was written for - has `faces:` been renamed?")
    assert not bad, "a face that is a hole:\n  " + "\n  ".join(sorted(bad))
