"""A seated part turns with the aperture it is in, forwarded or not (#548).

render.solve_seat turned an occupant by its HOST's rotate (plus a spanning
pair's axis). A host that FORWARDS a composed part's aperture
(manifest.forwarded_part) seats the occupant in that part, and the part's own
`rotate` was left out:
  - an optic `mate-to` a card whose cage is a part at `rotate: 90` was drawn
    crosswise over its cage - the issue's report, on an untilted card;
  - a plug seated in generic/sfp-lc-simplex@2 or generic/sfp-rj45@1, which
    compose their one aperture at 180, was drawn 180 out: latch off the side
    opposite the keyway, where a plug in a composed bore seated DIRECTLY
    (qsfp-lc's tx/rx) faces it (test_lc_seated_orientation's rule).
manifest.presented_turn is the one answer for both the drawing (solve_seat)
and the published entries (render._slot_dict, so components.json `presents`
and the kit's chained slots), so the kit and the build turn alike.
"""
from pathlib import Path

import pytest
import yaml

from portrayal import render as R
from portrayal.manifest import presented_turn

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def _resolver(lib):
    def res(ref):
        try:
            return lib.resolve(ref)[0]
        except Exception:
            return None
    return res


@pytest.fixture(scope="module")
def lib():
    return R.Library([str(LIB)])


@pytest.mark.parametrize("ref,want", [
    # port wrappers compose their aperture upright: no turn, and None not 0,
    # so no published `rotate` changes from None
    ("common/rj45-eth@1", None),
    ("common/qsfp-cage@3", None),
    ("common/mpo-adapter@2", None),
    # the two parts that compose their one aperture turned
    ("generic/sfp-lc-simplex@2", 180),
    ("generic/sfp-rj45@1", 180),
    # a host presenting its own interface: the spanning axis, as before
    ("common/lc-duplex-v-adapter@6", 270),
])
def test_the_turn_a_host_gives_its_occupant(lib, ref, want):
    res = _resolver(lib)
    got = presented_turn(res(ref), res, R._connector_registry())
    assert got == want, (ref, got)


def test_an_optic_seated_through_a_card_turns_with_the_cage_part(tmp_path):
    """The issue's report. A card whose one QSFP aperture is a part at
    rotate 90, placed unturned; an optic `mate-to` the card is drawn at 90,
    the cage part's turn, and lands its mate on the cage's."""
    comp = tmp_path / "components" / "test" / "vcard" / "v1"
    comp.mkdir(parents=True)
    (comp / "contract.yaml").write_text(yaml.safe_dump({
        "format": 1, "kind": "component", "name": "vcard", "version": "1.0.0",
        "class": "line-card", "profile": "networking",
        "description": "a vertical card: one QSFP28 aperture composed at 90",
        "size": {"w": 30.0, "h": 60.0},
        "parts": [{"ref": "std/qsfp28@1", "id": "cage", "at": [5.0, 20.0], "rotate": 90}],
    }, sort_keys=False))
    lib = R.Library([str(tmp_path), str(LIB)])
    host = {"ref": "test/vcard@1", "at": [100.0, 0.0]}
    at, orot, _lift = R.solve_seat(lib, "optic", "generic/qsfp-lc@1", "card", host)
    assert float(orot or 0) % 360 == 90, orot
    # and its mate is on the cage's turned mate point
    res = _resolver(lib)
    from portrayal.manifest import presented_interface, seat_point
    _i, host_mate, _l = presented_interface(res("test/vcard@1"), res)
    want = seat_point(host["at"], {"w": 30.0, "h": 60.0}, None, host_mate)
    oc = res("generic/qsfp-lc@1")
    got = seat_point(at, oc["size"], orot, oc["connection-points"]["mate"]["at"])
    assert got == pytest.approx(want, abs=1e-3), (got, want)


def test_what_the_kit_reads_is_the_turn_the_build_draws(lib):
    """components.json `presents` carries the same turn, so the kit's chained
    slot on a seated simplex optic turns its plug as solve_seat does."""
    res = _resolver(lib)
    families = R._pluggable_families()
    candidates = R._pluggable_candidates([str(LIB)])
    for ref in ("generic/sfp-lc-simplex@2", "generic/sfp-rj45@1"):
        p = R.component_presents(ref, lib, families, candidates)
        assert p["rotate"] == presented_turn(res(ref), res, R._connector_registry()) == 180
