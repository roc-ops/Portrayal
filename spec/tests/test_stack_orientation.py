"""Belly-to-belly cage stacks face one way (L108).

A pluggable cage's `rotate: 0` is a module seated upright - bail at the top,
belly and cage latch at the bottom - and a seated optic takes its cage's turn.
So a stack's two cages are upper 0 over lower 180 (or left 270 beside right 90
on a card drawn on its side), which puts both bails outward, where a thumb
reaches them. docs/pluggables-3d-design.md records the decisions.

THE PAIRING IS spec/tools/portrayal/stacks.py, and this file reads it rather
than restating it: lint L108 and the census below cannot disagree about what a
pair is, because there is only one answer to ask.
"""
import functools
import pathlib

import jsonschema
import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

from portrayal import libwalk, lint, stacks          # noqa: E402
from portrayal.manifest import view_parts           # noqa: E402


@functools.lru_cache(maxsize=None)
def _resolve(ref):
    if not ref:
        return None
    try:
        return libwalk.load_contract(ref.split(":")[0], [str(LIB)])
    except Exception:
        return None


def _cage(id_, at, rotate=0, ref="std/sfp-ganged@1"):
    p = {"ref": ref, "id": id_, "at": list(at)}
    if rotate:
        p["rotate"] = rotate
    return p


def _pairs(items):
    return [(p["kind"], p["first"]["id"], p["second"]["id"])
            for p in stacks.pairs(stacks.cages(items, _resolve))]


# --- the pairing ------------------------------------------------------------

def test_a_two_high_block_pairs_down_each_column_not_across_it():
    items = [_cage("a", (0, 0)), _cage("b", (0, 15)),
             _cage("c", (14.25, 0)), _cage("d", (14.25, 15))]
    assert sorted(_pairs(items)) == [("row", "a", "b"), ("row", "c", "d")]


def test_four_rows_pair_as_two_stacks_from_the_top():
    items = [_cage(f"r{i}", (0, y)) for i, y in enumerate((0, 15, 32, 47))]
    assert _pairs(items) == [("row", "r0", "r1"), ("row", "r2", "r3")]


def test_touching_columns_are_not_a_partial_overlap():
    """Adjacent ganged columns abut to within float noise; that is not a stack."""
    items = [_cage("a", (0, 0)), _cage("b", (14.2500001, 15.0))]
    assert _pairs(items) == []


def test_a_card_on_its_side_pairs_across_the_belly_not_down_the_column():
    # cisco/a9k-40ge-b's geometry: two columns of 90-turned cages, 2.4 mm apart
    items = [_cage("p0", (10.27, 43.17), 90), _cage("p1", (23.09, 43.17), 90),
             _cage("p2", (10.27, 57.78), 90), _cage("p3", (23.09, 57.78), 90)]
    assert sorted(_pairs(items)) == [("column", "p0", "p1"), ("column", "p2", "p3")]


def test_a_single_column_on_its_side_is_not_a_stack():
    items = [_cage(f"x{i}", (7.4, 60 + 14.25 * i), 90) for i in range(6)]
    assert _pairs(items) == []


def test_a_turned_cage_beside_an_upright_one_is_not_forced_into_a_pair():
    assert _pairs([_cage("a", (0, 0)), _cage("b", (0, 15), 90)]) == []


def test_qsfp_over_qsfp_dd_is_one_face_family():
    items = [_cage("a", (0, 0), ref="std/qsfp-ganged@1"),
             _cage("b", (0, 13), ref="std/qsfp-dd@1")]
    assert _pairs(items) == [("row", "a", "b")]


def test_sfp_over_qsfp_is_not_a_pair():
    items = [_cage("a", (0, 0)), _cage("b", (0, 13), ref="std/qsfp-ganged@1")]
    assert _pairs(items) == []


def test_osfp_pairs_and_is_checked():
    items = [_cage("a", (0, 0), ref="std/osfp@1"), _cage("b", (0, 15), ref="std/osfp@1")]
    (pr,) = stacks.pairs(stacks.cages(items, _resolve))
    assert stacks.checked(pr) and pr["first"]["family"] == "osfp"


def test_osfp_over_sfp_is_not_a_pair():
    items = [_cage("a", (0, 0), ref="std/osfp@1"), _cage("b", (0, 15))]
    assert _pairs(items) == []


# --- OSFP: the same way up (#799) ----------------------------------------------
# A stacked OSFP cage is one connector seating both modules heat sink up (OSFP
# MSA rev 5.22 section 7.1, Table 7-1, Figures 7-1 and 7-2); the whole cage may
# sit under the board, which turns both alike.

def _osfp(id_, at, rotate=0):
    return _cage(id_, at, rotate, ref="std/osfp@1")


@pytest.mark.parametrize("rots", [(0, 0), (180, 180)])
def test_an_osfp_row_pair_turned_alike_is_the_convention(rots):
    assert _findings({"parts": [_osfp("a", (0, 0), rots[0]), _osfp("b", (0, 14.9), rots[1])]}) == []


@pytest.mark.parametrize("rots", [(0, 180), (180, 0)])
def test_an_osfp_row_pair_turned_belly_to_belly_is_a_finding(rots):
    (msg,) = _findings({"parts": [_osfp("a", (0, 0), rots[0]), _osfp("b", (0, 14.9), rots[1])]})
    assert "same-way-up OSFP row pair" in msg and "0/0" in msg and "OSFP MSA" in msg
    assert "upper 0, lower 180" not in msg


def test_an_osfp_column_pair_on_its_side_is_turned_alike():
    for rots in ((90, 90), (270, 270)):
        assert _findings({"parts": [_osfp("l", (0, 0), rots[0]), _osfp("r", (14.9, 0), rots[1])]}) == []
    (msg,) = _findings({"parts": [_osfp("l", (0, 0), 270), _osfp("r", (14.9, 0), 90)]})
    assert "OSFP column pair" in msg


def test_the_sfp_convention_did_not_move_with_osfp():
    """(0, 0) is right for an OSFP stack and still wrong for an SFP one."""
    (msg,) = _findings({"parts": [_cage("a", (0, 0)), _cage("b", (0, 15))]})
    assert "belly-to-belly SFP row pair" in msg and "upper 0, lower 180" in msg


def test_an_osfp_pair_built_belly_to_belly_takes_an_exception_and_a_turned_alike_one_refuses_it():
    belly = [_osfp("a", (0, 0)), _osfp("b", (0, 18.86), 180)]
    doc = {"parts": belly, "stack-exceptions": [{"pair": ["a", "b"], "reason": "x" * 40}]}
    assert _findings(doc) == []
    doc["parts"] = [_osfp("a", (0, 0)), _osfp("b", (0, 18.86))]
    (msg,) = _findings(doc)
    assert "already follows the convention" in msg


def test_every_osfp_stack_in_the_library_is_turned_alike_or_excepted():
    """The census for the family L108 began checking in #799, so a vacuous
    walk cannot pass it: it has to find the OSFP stacks the library draws."""
    osfp = [(p, pr, e) for p, _v, pr, e in _census() if pr["first"]["family"] == "osfp"]
    assert len(osfp) >= 200
    turned_alike = [r for r in osfp if stacks.conforms(r[1])]
    assert len(turned_alike) >= 50          # ais800-32o, exp800-16o, s9321-64eo
    assert all(e or stacks.conforms(pr) for _p, pr, e in osfp)


# --- the rule ---------------------------------------------------------------

def _findings(doc, device=False):
    return stacks.findings(doc, _resolve, device)


def test_upper_upright_over_lower_turned_is_the_convention():
    assert _findings({"parts": [_cage("a", (0, 0)), _cage("b", (0, 15), 180)]}) == []


@pytest.mark.parametrize("rots", [(0, 0), (180, 0), (180, 180)])
def test_every_other_row_turn_is_a_finding(rots):
    (msg,) = _findings({"parts": [_cage("a", (0, 0), rots[0]), _cage("b", (0, 15), rots[1])]})
    assert "upper 0, lower 180" in msg


def test_left_270_beside_right_90_is_the_convention_on_its_side():
    good = [_cage("l", (0, 0), 270), _cage("r", (12.8, 0), 90)]
    bad = [_cage("l", (0, 0), 90), _cage("r", (12.8, 0), 90)]
    assert _findings({"parts": good}) == []
    (msg,) = _findings({"parts": bad})
    assert "left 270, right 90" in msg


def test_a_declared_exception_silences_its_pair_and_only_its_pair():
    parts = [_cage("a", (0, 0)), _cage("b", (0, 15)), _cage("c", (20, 0)), _cage("d", (20, 15))]
    doc = {"parts": parts, "stack-exceptions": [
        {"pair": ["a", "b"], "reason": "x" * 40}]}
    (msg,) = _findings(doc)
    assert msg.startswith("c over d")
    doc["stack-exceptions"] = [{"pairs": [["a", "b"], ["c", "d"]], "reason": "x" * 40}]
    assert _findings(doc) == []


def test_an_exception_that_names_no_pair_is_itself_a_finding():
    doc = {"parts": [_cage("a", (0, 0)), _cage("b", (0, 15), 180)],
           "stack-exceptions": [{"pair": ["a", "zz"], "reason": "x" * 40}]}
    (msg,) = _findings(doc)
    assert "not a checked stacked pair" in msg


def test_an_exception_on_a_pair_that_already_conforms_is_a_finding():
    """An exception says the stack is built otherwise; a pair drawn upper 0 over
    lower 180 contradicts that, whatever the reason says."""
    doc = {"parts": [_cage("a", (0, 0)), _cage("b", (0, 15), 180)],
           "stack-exceptions": [{"pair": ["a", "b"], "reason": "x" * 40}]}
    (msg,) = _findings(doc)
    assert "already follows the convention" in msg
    doc["parts"][1] = _cage("b", (0, 15))
    assert _findings(doc) == []


def test_the_device_form_reads_views_and_a_view_scoped_exception():
    view = {"components": {"placements": [_cage("a", (0, 0)), _cage("b", (0, 15))]}}
    doc = {"views": {"front": view}}
    assert len(_findings(doc, True)) == 1
    doc["stack-exceptions"] = [{"pair": ["a", "b"], "view": "front", "reason": "x" * 40}]
    assert _findings(doc, True) == []


@pytest.mark.parametrize("schema", ["device", "component"])
def test_the_schema_takes_a_pair_or_pairs_and_requires_a_reason(schema):
    s = yaml.safe_load((ROOT / f"spec/schemas/{schema}.schema.json").read_text())
    sub = {**s["properties"]["stack-exceptions"], "$defs": s.get("$defs", {})}
    ok = jsonschema.Draft202012Validator(sub)
    assert not list(ok.iter_errors([{"pair": ["a", "b"], "reason": "r" * 40}]))
    assert not list(ok.iter_errors([{"pairs": [["a", "b"]], "reason": "r" * 40}]))
    assert list(ok.iter_errors([{"pair": ["a", "b"]}]))
    assert list(ok.iter_errors([{"pair": ["a", "b"], "reason": "short"}]))
    assert list(ok.iter_errors([{"pair": ["a"], "reason": "r" * 40}]))


def test_lint_reports_it_as_l108(tmp_path):
    doc = {"parts": [_cage("a", (0, 0), 180), _cage("b", (0, 15))]}
    with lint.collecting() as found:
        lint.lint_component_stack_orientation(tmp_path / "c.yaml", doc, [str(LIB)])
    assert any("[L108]" in f for f in found.errors)


# --- the library ------------------------------------------------------------

def _owners():
    for dev in libwalk.iter_devices([LIB]):
        doc = yaml.safe_load(dev.read_text())
        yield dev, doc, True
    for ct in sorted(LIB.glob("components/*/*/v*/contract.yaml")):
        yield ct, yaml.safe_load(ct.read_text()), False


@functools.lru_cache(maxsize=None)
def _census():
    rows = []
    for path, doc, is_device in _owners():
        walk = stacks.device_pairs if is_device else stacks.component_pairs
        exc = stacks.exceptions(doc)
        for vname, pr in walk(doc, _resolve):
            rows.append((path, vname, pr, stacks.excepted(exc, pr, vname)))
    return rows


def test_the_census_measured_something():
    """A walk that found nothing would pass every assertion below."""
    rows = _census()
    assert sum(1 for r in rows if r[1] is not None) > 1500
    # component-owned pairs and columns count every contract, the majors #261
    # part 2 retired but kept (`superseded-by`, #448) included: 896 pairs and 504
    # columns measured.
    assert sum(1 for r in rows if r[1] is None) > 800
    assert sum(1 for r in rows if r[2]["kind"] == "column") > 500


def test_every_checked_stack_in_the_library_faces_the_convention_or_says_why():
    bad = [f"{p.relative_to(ROOT)}: {pr['first']['id']}/{pr['second']['id']} {stacks.state(pr)}"
           for p, _v, pr, e in _census()
           if stacks.checked(pr) and not e and not stacks.conforms(pr)]
    assert not bad, f"{len(bad)} stacks off the convention:\n" + "\n".join(bad[:40])


def test_every_exception_has_a_reason_worth_reading():
    for path, doc, _d in _owners():
        for e in doc.get("stack-exceptions") or []:
            assert len((e.get("reason") or "").split()) >= 12, path


# THE THREE-HIGH FACES, each a two-high stack with a separate single row under
# it, and each device's own provenance says which two rows are the stack. The
# pairing takes them from the top, and on every one of these that is right even
# though the separate row sits CLOSER to the stack's lower row than the stack's
# two rows sit to each other (agr110: 16.2 apart within the stack, 13.1 to the
# third) - which is why pairing by nearest gap was tried and rejected. A new
# face joins this table only after someone has read which rows are the stack.
THREE_HIGH = {
    "edgecore/agr110": {"uplink-2", "uplink-5"},        # qsfp-block: "NOT one block"
    "edgecore/agr130": {"uplink-2", "uplink-5"},        # the same face as the AGR110
    "edgecore/as5912-54x": {"port-51", "port-54"},      # QSFP28: a 2x2 stack and a row below
    "edgecore/as7326-56x": {f"port-{n}" for n in range(3, 49, 3)},  # "top two SFP rows are 2x4 ganged"
    "edgecore/dcs201": {"port-51", "port-54"},          # "third row is a separate block below"
    "edgecore/dcs202": {"port-51", "port-54"},          # the DCS201's face
    # NOT A THIRD COLUMN: the AIS2004s' right-hand SFP column (13-20, its own gold
    # strip and numbering) runs down beside the 2x2 block (9-12) with 2 mm between
    # them, so its lowest two cages read as a neighbour of the block's right-hand
    # pair. The 2x2 block is the stack; the column is single (#738).
    "aurcore/ais2004": {"port-19", "port-20"},
    "aurcore/ais2004p": {"port-19", "port-20"},
}


def test_a_stack_is_two_high_or_its_face_is_in_the_three_high_table():
    """Greedy pairing from the top is only right where the stack is the top
    two rows. A cage left over that would pair with a neighbour already taken
    is a third cage in line, and the pairing is then a claim someone has to
    have read off the device."""
    seen = {}
    for path, doc, is_device in _owners():
        views = ([view_parts(v)["placements"] for v in (doc.get("views") or {}).values()]
                 if is_device else [doc.get("parts") or []])
        for items in views:
            found = stacks.cages(items, _resolve)
            paired = {c["id"] for pr in stacks.pairs(found) for c in (pr["first"], pr["second"])}
            for c in found:
                if c["id"] not in paired and any(
                        o is not c and stacks.pairs([c, o]) for o in found):
                    key = f"{path.parent.parent.name}/{path.parent.name}"
                    seen.setdefault(key, set()).add(c["id"])
    assert seen == THREE_HIGH


def test_two_real_cards_pair_the_way_the_hardware_stacks():
    """The proof the pairing was checked against before the sweep: an ASR 9000
    card on its side pairs its two columns across the band between them, and a
    Casa card's single column of cages is not a stack at all."""
    a9k = stacks.cages(_resolve("cisco/a9k-40ge-b@2")["parts"], _resolve)
    got = {(p["first"]["id"], p["second"]["id"]) for p in stacks.pairs(a9k)}
    assert got == {(f"p{i}", f"p{i + 1}") for i in range(0, 40, 2)}
    casa = stacks.cages(_resolve("casa/smm-300g@1")["parts"], _resolve)
    assert len(casa) == 12 and stacks.pairs(casa) == []
