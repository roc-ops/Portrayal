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


def _effective_lift(root, target_id):
    """The lift relief.js would resolve for a group: data-z-lift up the ancestors.

    relief.js's `liftOf` sums `data-z-lift` from a node up to the SVG root and
    reads nothing else, so this is the whole of what a consumer sees. A seated
    occupant is a TOP-LEVEL SIBLING of its host, not a child of it, which is
    precisely why the sum cannot recover a host's displacement on its own and
    why the renderer has to write the total onto the seat's own group.
    """
    parents = {c: p for p in root.iter() for c in p}
    node = next(el for el in root.iter() if el.get("id") == target_id)
    total = 0.0
    while node is not None:
        if node.get("data-z-lift") is not None:
            total += float(node.get("data-z-lift"))
        node = parents.get(node)
    return total


def test_a_chained_seat_inherits_the_whole_stack_of_lift(tmp_path):
    """The SECOND link's effective lift, against a host whose aperture is lifted.

    THIS IS THE ASSERTION THE OLD TEST WAS MISSING. `test_the_second_seat_lands_
    on_the_first` checks only that two transforms DIFFER - true of any two
    positions, including a wrong one - and the drawing is 2D, so a depth error
    moves nothing it compares. A boot on a plug on a 10 mm-proud bore drew at
    the panel plane, 10 mm too deep, and every test passed.

    `generic/sfp-lc-simplex@2` is the fixture because it is the only library
    part whose `presented_interface` forwards a NON-ZERO lift: it composes one
    `std/lc-bore@3` at `lift: 10.0`, and one bore is what lets
    `presented_interface` pick a single aperture to forward. `generic/sfp-lc@1`
    composes TWO bores, declines to pick, and forwards 0.0 - which is why the
    other tests here, written against it, could not have caught this.

    The failure mode was NOT that the second link got a wrong number: it got NO
    `data-z-lift` at all. `presented_interface` answers "how far off its own
    face is this host's aperture", and returns 0.0 for any host that declares
    its own `interface` + `mate` - which the plug does. The host's own seat
    lift was simply dropped, and being a sibling rather than a child, nothing
    downstream could put it back.
    """
    r, out = _render(
        tmp_path,
        [{"ref": "generic/lc-plug@2", "id": "plug1",
          "mate-to": "port-4-occupant"},
         {"ref": "common/lc-boot@1", "id": "boot1", "mate-to": "plug1"}],
        {"port-4": "generic/sfp-lc-simplex@2"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()

    module = _effective_lift(root, "port-4-occupant")
    plug = _effective_lift(root, "plug1")
    boot = _effective_lift(root, "boot1")

    # FIRST LINK: the module seats in the cage, and the cage's own presented
    # aperture is flush, so the module stands where the cage does.
    assert plug == module + 10.0, (
        f"the plug seats in the module's bore, which stands 10.0 proud of the "
        f"module face (std/lc-bore@3 at lift: 10.0); got {plug} against a "
        f"module at {module}")

    # SECOND LINK, the one that was broken: the boot mates the PLUG. The boot
    # inherits the plug's own seat lift - inheriting nothing put it 10 mm
    # inside the module - PLUS what the plug presents: since pluggables D the
    # plug presents `lc-plug` at its `boot` point, `on:` its body, so the boot
    # stands on the plug body's rear face, that feature's `out` further on.
    plug_c = yaml.safe_load((LIB / "components/generic/lc-plug/v2/contract.yaml").read_text())
    rear = next(f["out"] for f in plug_c["relief"]["features"] if f["node"] == "body")
    assert boot == plug + rear, (
        f"the boot's effective lift is {boot} but the plug it wraps stands at "
        f"{plug} with its body's rear {rear} further on. A chained seat inherits "
        f"its host's presented-aperture lift PLUS the host's own resolved seat "
        f"lift; dropping the second term buries the boot in the part it is "
        f"supposed to wrap")
    assert boot >= 10.0, (
        f"the fixture is not exercising anything: the chain's lift is {boot}. "
        f"An all-zero chain passes the equality above no matter what the "
        f"renderer does - check generic/sfp-lc-simplex@2 still composes a "
        f"lifted bore")


def test_a_cycle_is_refused(tmp_path):
    """Two placements mated to each other resolve nothing, forever."""
    r, _ = _render(
        tmp_path,
        [{"ref": "std/lc-bore@3", "id": "a", "mate-to": "b"},
         {"ref": "std/lc-bore@3", "id": "b", "mate-to": "a"}],
        {})
    assert r.returncode != 0, "a mate-to cycle rendered instead of erroring"
    assert "cycle" in r.stderr.lower(), (
        f"the error should name the cycle; got: {r.stderr[-300:]}")


def test_a_dangling_mate_to_still_errors(tmp_path):
    """The existing error must survive the rewrite."""
    r, _ = _render(
        tmp_path,
        [{"ref": "std/lc-bore@3", "id": "x", "mate-to": "nope"}],
        {})
    assert r.returncode != 0
    assert "nope" in r.stderr


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
        [{"ref": "generic/lc-plug@2", "id": "plug1",
          "mate-to": "port-4-occupant"},
         {"ref": "common/lc-boot@1", "id": "boot1", "mate-to": "plug1"}],
        {"port-4": "generic/sfp-lc-simplex@2"})
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
        [{"ref": "generic/lc-plug@2", "id": "plug1",
          "mate-to": "port-4-occupant", "for": "port-4"}],
        {"port-4": "generic/sfp-lc-simplex@2"})
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
        {"port-4": "generic/sfp-lc-simplex@2",
         "port-4-occupant": "generic/lc-plug@2",
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
        {"port-4": "generic/sfp-lc-simplex@2",
         "a-host-in-no-view-at-all": "generic/lc-plug@2"})
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    ids = {el.get("id") for el in root.iter() if el.get("id")}
    assert "port-4-occupant" in ids, "the resolvable occupant must still seat"
    assert "a-host-in-no-view-at-all-occupant" not in ids
