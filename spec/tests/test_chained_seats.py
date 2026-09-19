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
import tempfile
import xml.etree.ElementTree as ET

import pytest
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
