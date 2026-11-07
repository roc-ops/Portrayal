"""`layout_fit.py` says which blocks `expand.py` could write, and why not.

The measure is only worth having if it agrees with the generator it asks about, so
the first test round-trips: a block `expand.py` writes is a block the measure calls
regular. The rest hold one reason each, on a small grid built here, so a reason
that stops firing (or fires on everything) fails on its own line.
"""
import pathlib

from portrayal import expand as E
from portrayal_dev import layout_fit as F

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
STD = E.load_standards(ROOT / "spec/schemas")

BLOCK = {"id": "p", "ref": "std/sfp-ganged@1", "at": [10.0, 5.0], "count": 16, "rows": 2,
         "pitch": 14.5, "row-pitch": 12.0, "gang": 4, "gutter": 3.0,
         "number-from": 1, "rotate": {"bottom": 180}}


def device(placements):
    return {"views": {"front": {"components": {"placements": placements}}}}


def measured(block=BLOCK, mutate=None):
    ports, _, _ = E.block_items(block, LIB, STD)
    ports = [dict(p) for p in ports]
    if mutate:
        mutate(ports)
    return F.measure_device(device(ports))


def reasons(recs):
    return {r for rec in recs for r in rec["reasons"]}


def test_a_block_expand_writes_is_a_block_the_measure_calls_regular():
    recs = measured()
    assert [r["count"] for r in recs] == [16]
    assert recs[0]["reasons"] == []
    assert recs[0]["facts"]["cols"] == 8 and recs[0]["facts"]["rows"] == 2


def test_fewer_than_eight_placements_are_not_a_block():
    assert measured(dict(BLOCK, count=6)) == []


def test_a_rel_pos_that_is_not_the_number_in_the_id_is_named():
    def shift(ports):
        for p in ports:
            p["rel-pos"] += 1
    assert reasons(measured(mutate=shift)) == {"relpos-offset"}


def test_a_rel_pos_that_restarts_is_not_a_constant_offset():
    def restart(ports):
        for p in ports:
            p["rel-pos"] = p["rel-pos"] % 8
    assert reasons(measured(mutate=restart)) == {"relpos-other"}


def test_row_major_numbering_is_named():
    def renumber(ports):
        for i, p in enumerate(ports):
            col, row = divmod(i, 2)
            p["id"] = f"port-{1 + row * 8 + col}"
            p["rel-pos"] = 1 + row * 8 + col
    assert reasons(measured(mutate=renumber)) == {"row-major"}


def test_a_third_x_gap_is_named():
    def squeeze(ports):
        for p in ports:
            if abs(p["at"][0] - 85.5) < 0.1:      # the sixth column only
                p["at"][0] += 1.0
    assert "x-gaps" in reasons(measured(mutate=squeeze))


def test_ids_with_no_number_are_named():
    def rename(ports):
        for i, p in enumerate(ports):
            p["id"] = "port-" + "abcdefghijklmnop"[i]
    assert "no-number" in reasons(measured(mutate=rename))


def test_a_rotation_that_is_not_top_and_bottom_is_named():
    block = dict(BLOCK, rows=3, count=24, rotate={"top": 180})

    def third(ports):
        for p in ports:
            if p["at"][1] > 25:
                p["rotate"] = 90
    assert "rotation" in reasons(measured(block, third))


def test_a_lamp_block_folds_into_the_port_block_it_names():
    block = dict(BLOCK, led={"ref": "common/led-dot@1", "id-format": "led-{n}",
                             "dx-by-col": [-2.0, 2.0], "dy-top": -1.0, "dy-bottom": 13.0})
    recs = measured(block)
    kinds = {r["kind"]: r for r in recs}
    assert set(kinds) == {"port", "lamp"}
    assert kinds["lamp"]["folds-into"] == ["std/sfp-ganged@1", "p"]
    assert kinds["lamp"]["reasons"] == [] and kinds["port"]["reasons"] == []


def test_lamps_written_before_their_ports_cannot_be_one_run():
    block = dict(BLOCK, led={"ref": "common/led-dot@1", "id-format": "led-{n}",
                             "dx": -2.0, "dy": -1.0})
    ports, _, _ = E.block_items(block, LIB, STD)
    flipped = [p for p in ports if "for" in p] + [p for p in ports if "for" not in p]
    recs = F.measure_device(device(flipped))
    assert reasons(recs) == {"lamp-after-port"}


def test_a_lamp_with_a_key_led_does_not_write_is_named():
    block = dict(BLOCK, led={"ref": "common/led-dot@1", "id-format": "led-{n}", "dx": -2.0})

    def label(ports):
        for p in ports:
            if "for" in p:
                p["attrs"] = {"port": p["for"]}
    assert reasons(measured(block, label)) == {"lamp-extra-keys"}
