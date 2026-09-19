"""A boot seats on a plug that is itself seated. Spec B's two-part fit needs this.

`hosts` was built once, from placements carrying an explicit `at`, so a `mate-to`
occupant could never host another. The renderer said so outright:

    boot: mate-to 'port-4-occupant' is not a placement with an explicit position

Composition is not a way round it - `parts:` entries have no `optional` and are
compile-time flattened, so a composed boot could not be chosen per connector, which
is what the spec asks for.

Resolution is now iterative: each pass resolves the placements whose hosts are known
and adds them to `hosts`, until a pass resolves nothing. A pass that resolves nothing
while placements remain unresolved is either a dangling `mate-to` (already an error)
or a cycle (a new one).
"""
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC, LIB = ROOT / "spec", ROOT / "library"
SRC = LIB / "devices/ufispace/s9510-28dc"


def _render(tmp_path, extra_placements, occupants):
    d = yaml.safe_load((SRC / "device.yaml").read_text())
    # render.py's CLI renders every configuration in one pass (main() has no
    # --config flag to scope one), and the extra placement above is added to
    # the view unconditionally, not per-config. s9510-28dc has two configs,
    # `dc` and `ac`, and only `dc` is `default: true` - `ac` ships bare, with
    # no `occupants:` of its own. Setting occupants on `dc` alone leaves a
    # mate-to placement dangling when the `ac` pass renders the same view,
    # which is a fixture gap unrelated to what this test checks (chained
    # mate-to resolution), so occupants go on every config.
    for cfg in d["configurations"].values():
        cfg["occupants"] = occupants
    d["views"]["front"]["components"]["placements"].extend(extra_placements)
    dev = tmp_path / "device.yaml"
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "o"
    out.mkdir()
    return subprocess.run(
        [sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
         "--library", str(LIB), "--out", str(out)],
        capture_output=True, text=True), out


def test_a_boot_seats_on_a_seated_plug(tmp_path):
    r, out = _render(
        tmp_path,
        [{"ref": "std/lc-bore@3", "id": "boot", "mate-to": "port-4-occupant"}],
        {"port-4": "generic/sfp-lc@1"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    assert "boot" in ids, (
        "the second seat did not render. A boot seated on a seated plug is the whole "
        "of spec B's two-part fit.")


def test_the_second_seat_lands_on_the_first(tmp_path):
    """Not merely present - positioned by the mate points, like any other seat."""
    r, out = _render(
        tmp_path,
        [{"ref": "std/lc-bore@3", "id": "boot", "mate-to": "port-4-occupant"}],
        {"port-4": "generic/sfp-lc@1"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}
    boot, host = by_id["boot"], by_id["port-4-occupant"]
    assert boot.get("transform") and host.get("transform"), (
        "one of the two carries no transform, so nothing can be compared")
    assert boot.get("transform") != host.get("transform"), (
        "the boot landed exactly on its host's origin, which means it was placed "
        "rather than mated")


def test_a_hand_written_mate_to_records_its_host(tmp_path):
    """`data-for` on the seat, whichever way the seat was authored.

    The spec offers two authorings in one breath - "through `occupants:` or
    `mate-to`" - but only the `occupants:` expansion wrote `for: host`. A
    hand-written `mate-to` placement got nothing, so relief.js's `cablePoints`
    had no `data-for` to walk, its seat-chain grouping never fired, and a plug
    with a boot on it came back as TWO cable points for ONE connector. Path
    ancestry cannot stand in: a seated occupant is a top-level SIBLING of its
    host, so the three groups here carry three unrelated paths by construction.
    """
    r, out = _render(
        tmp_path,
        [{"ref": "generic/lc-plug@1", "id": "plug1",
          "mate-to": "port-4-occupant"},
         {"ref": "common/lc-boot@1", "id": "boot1", "mate-to": "plug1"}],
        {"port-4": "generic/sfp-lc-simplex@1"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}

    assert by_id["plug1"].get("data-for") == "port-4-occupant", (
        "a hand-written mate-to must record its host the same way an "
        "occupants:-authored one does")
    assert by_id["boot1"].get("data-for") == "plug1"
    # the occupants: authoring is unchanged - it already did this
    assert by_id["port-4-occupant"].get("data-for") == "port-4"


def test_an_authors_own_for_wins_over_the_mate_to_default(tmp_path):
    """The default fills a gap; it does not overwrite a declaration.

    `for:` is older than seating and means "what this part belongs to" - an LED
    to its port. A placement that both mates something and says what it belongs
    to is stating two different facts, and the seat must not clobber the one
    the author wrote.
    """
    r, out = _render(
        tmp_path,
        [{"ref": "generic/lc-plug@1", "id": "plug1",
          "mate-to": "port-4-occupant", "for": "port-4"}],
        {"port-4": "generic/sfp-lc-simplex@1"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}
    assert by_id["plug1"].get("data-for") == "port-4"


def test_occupants_can_chain(tmp_path):
    """A second tier seats, rather than being dropped without a word.

    `here` - the set of placement ids an occupant's host must be in - was
    sampled ONCE, before the expansion loop appended anything. So
    `occupants: {port-4: module, port-4-occupant: plug}` looked for
    `port-4-occupant` in a snapshot taken before it existed, failed to find it,
    and hit the `continue` meant for a host in ANOTHER VIEW. The plug was
    dropped silently: no error, no warning, a drawing simply missing a part the
    configuration asked for.
    """
    r, out = _render(
        tmp_path, [],
        {"port-4": "generic/sfp-lc-simplex@1",
         "port-4-occupant": "generic/lc-plug@1",
         "port-4-occupant-occupant": "common/lc-boot@1"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    by_id = {el.get("id"): el for el in root.iter() if el.get("id")}
    for tier in ("port-4-occupant", "port-4-occupant-occupant",
                 "port-4-occupant-occupant-occupant"):
        assert tier in by_id, (
            f"{tier} was dropped. occupants: must seat a tier on a tier, not "
            f"only on a placement that existed before the loop began")
    # and the chain is a chain: each tier records the one below it
    assert by_id["port-4-occupant-occupant"].get("data-for") == "port-4-occupant"
    assert (by_id["port-4-occupant-occupant-occupant"].get("data-for")
            == "port-4-occupant-occupant")


def test_an_occupant_for_a_host_in_another_view_is_still_skipped(tmp_path):
    """The fixed point must not turn a documented skip into an error.

    A configuration describes the WHOLE device, so the front view legitimately
    carries `occupants:` entries whose hosts live on the rear. Those are
    skipped, not refused - and the iteration must tell "cannot progress yet"
    apart from "cannot progress ever" by whether a pass seated anything, not by
    when the id set was sampled.
    """
    r, out = _render(
        tmp_path, [],
        {"port-4": "generic/sfp-lc-simplex@1",
         "a-host-in-no-view-at-all": "generic/lc-plug@1"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    assert "port-4-occupant" in ids, "the resolvable occupant must still seat"
    assert "a-host-in-no-view-at-all-occupant" not in ids
