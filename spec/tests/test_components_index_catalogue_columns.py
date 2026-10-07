"""components.json carries the catalogue's derived columns, per component major.

library/components/CATALOGUE.md shows, for each component major, how many
devices seat it, how many other component majors compose it, and what it
conforms to or the interface it presents or mates. A reader that renders the
catalogue from data (portrayal.dev's catalog page) holds components.json and
not the library, so each entry carries the same three facts: `seats`,
`composed-by`, and `interface` / `mates` beside the existing `conforms`.

One entry is one component major, as one catalogue row is. Both are counted by
components_catalogue's own functions; this checks the two outputs agree row by
row, and that the comparison measured something.
"""
import json
import pathlib

import onebuild
from portrayal import components_catalogue as cat

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def _rows():
    """ref -> (fits, devices, in parts), read off the generated page."""
    rows = {}
    for line in cat.build(LIB).splitlines():
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in line.strip("|").split(" | ")]
        rows[cells[0].strip("`")] = (cells[4], int(cells[5]), int(cells[6]))
    return rows


def _index():
    out = onebuild.components_index()   # built once per session
    return {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
            for e in json.loads((out / "components.json").read_text())["components"]}


def test_every_entry_matches_its_catalogue_row():
    rows, idx = _rows(), _index()
    # NOT VACUOUS: the page and the index list the same majors, and there are
    # hundreds of them, so an empty walk on either side fails here.
    assert len(rows) > 500, len(rows)
    assert set(idx) == set(rows)
    wrong = []
    for ref, (fits, devices, composers) in sorted(rows.items()):
        e = idx[ref]
        got = (str(cat.fits(e)), e["seats"], e["composed-by"])
        if got != (fits, devices, composers):
            wrong.append(f"{ref}: index {got} != page {(fits, devices, composers)}")
    assert not wrong, "\n".join(wrong[:20])


def test_widely_used_parts_are_counted():
    """A count of 0 everywhere would also agree with a page that counted 0
    everywhere; these parts are seated and composed across the library."""
    idx = _index()
    for ref in ("std/usb-a@1", "std/rj45@2"):
        assert idx[ref]["seats"] > 0, ref
        assert idx[ref]["composed-by"] > 0, ref
    assert sum(e["seats"] for e in idx.values()) > 1000
    # `interface` / `mates` are carried when the contract states them
    assert any(e.get("interface") for e in idx.values())
    assert any(e.get("mates") for e in idx.values())
