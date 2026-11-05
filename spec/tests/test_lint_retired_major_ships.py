"""L89 tells a retired major that still ships from a dead one.

A component major that a newer live major supersedes, that no device reaches
and that nothing names is one of two things. If its contract says
`superseded-by: <ref>`, naming a major that exists, it is RETIRED AND STILL
SHIPPED: a manifest outside the library that pins it keeps resolving, and the
key says where to move. If it says nothing, it is DEAD, and the rule keeps
failing it: delete the directory, or mark it so it can stay.

The marker is the `superseded-by` key the schema already has. A marker whose
ref does not exist is not a marker: L101 reports the dangling ref, and L89 does
not accept the part on the strength of it.

Each case is a scratch library built for the one thing it exercises.
"""
import pathlib

import yaml

from portrayal import lint


def run(root):
    with lint.collecting() as found:
        lint.lint_unplaced_majors(root)
    return [e for e in found.errors if "[L89]" in e]


def write(root, ref, **keys):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    p = root / "components" / ns / name / f"v{major}" / "contract.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = {"format": 1, "kind": "module", "name": name, "version": "1.0.0",
           "class": "psu", "size": {"w": 10.0, "h": 10.0}}
    doc.update(keys)
    p.write_text(yaml.safe_dump(doc))
    return p


def device(root, name, *refs):
    p = root / "devices" / "acme" / name / "device.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = {"format": 1, "kind": "device", "name": name, "version": "1.0.0",
           "manufacturer": "Acme", "model": name, "maturity": "modelled",
           "chassis": {"width": 440.0, "height": 44.0, "depth": 300.0},
           "views": {"front": {"size": {"w": 440.0, "h": 44.0},
                               "panel": {"placements": [
                                   {"ref": r, "id": f"p{i}", "at": [float(i), 1.0]}
                                   for i, r in enumerate(refs)]}}}}
    p.write_text(yaml.safe_dump(doc))
    return p


def bulk(root, n):
    """Enough seated parts that the rule's own broken-walk guard stays quiet."""
    refs = [f"std/filler-{i}@1" for i in range(n)]
    for r in refs:
        write(root, r)
    device(root, "filler", *refs)


def l101(root, contract):
    with lint.collecting() as found:
        lint.lint_component_superseded_by(
            contract, yaml.safe_load(contract.read_text()), [pathlib.Path(root)])
    return [e for e in found.errors if "[L101]" in e]


def test_a_retired_major_that_says_superseded_by_ships(tmp_path):
    bulk(tmp_path, 8)
    write(tmp_path, "common/psu@1", **{"superseded-by": "common/psu@2"})
    write(tmp_path, "common/psu@2")
    device(tmp_path, "box", "common/psu@2")
    assert run(tmp_path) == []


def test_a_retired_major_that_says_nothing_still_fails(tmp_path):
    bulk(tmp_path, 8)
    write(tmp_path, "common/psu@1")
    write(tmp_path, "common/psu@2")
    device(tmp_path, "box", "common/psu@2")
    found = run(tmp_path)
    assert len(found) == 1 and "common/psu@1" in found[0], found
    assert "superseded-by: common/psu@2" in found[0], found
    assert "delete the directory" in found[0], found


def test_a_live_placed_major_is_not_reported(tmp_path):
    bulk(tmp_path, 8)
    write(tmp_path, "common/psu@1")
    write(tmp_path, "common/psu@2")
    device(tmp_path, "box", "common/psu@1", "common/psu@2")
    assert run(tmp_path) == []


def test_a_marker_naming_a_ref_that_is_not_there_is_not_accepted(tmp_path):
    """L101 reports the dangling ref; L89 does not take the key at its word, so
    the part is still reported as dead and neither finding hides the other."""
    bulk(tmp_path, 8)
    old = write(tmp_path, "common/psu@1", **{"superseded-by": "common/psu@9"})
    write(tmp_path, "common/psu@2")
    device(tmp_path, "box", "common/psu@2")
    found = run(tmp_path)
    assert len(found) == 1 and "common/psu@1" in found[0], found
    dangling = l101(tmp_path, old)
    assert len(dangling) == 1 and "not in the library" in dangling[0], dangling


def test_a_marker_naming_the_part_itself_is_not_accepted(tmp_path):
    bulk(tmp_path, 8)
    old = write(tmp_path, "common/psu@1", **{"superseded-by": "common/psu@1"})
    write(tmp_path, "common/psu@2")
    device(tmp_path, "box", "common/psu@2")
    assert len(run(tmp_path)) == 1
    assert len(l101(tmp_path, old)) == 1


def test_a_marked_major_that_is_seated_and_carries_unplaced_still_fails(tmp_path):
    """The second branch is unchanged: a waiver that outlived its gap fails
    whether or not the part is marked."""
    bulk(tmp_path, 8)
    write(tmp_path, "common/psu@1", **{"superseded-by": "common/psu@2"},
          unplaced="nothing seats this part yet, and here is a sentence long enough to pass")
    write(tmp_path, "common/psu@2")
    device(tmp_path, "box", "common/psu@1", "common/psu@2")
    found = run(tmp_path)
    assert len(found) == 1 and "has been closed" in found[0], found


def test_a_marked_major_with_no_live_successor_is_still_unplaced(tmp_path):
    """Marked, but the successor is not seated either: nothing here is retired
    in favour of anything in use, so the ordinary question is still asked."""
    bulk(tmp_path, 8)
    write(tmp_path, "common/psu@1", **{"superseded-by": "common/psu@2"})
    write(tmp_path, "common/psu@2")
    found = run(tmp_path)
    assert len(found) == 2 and all("is reachable from no device" in e for e in found), found
