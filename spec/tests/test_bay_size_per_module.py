"""L123: one module, one bay size.

The ASR 9000 seated the same cards in slots of 395.7, 403.1, 403.4 and 406.4 mm,
so an RSP drew 33 mm longer in one chassis than the line cards beside it. L33
reads one device at a time and a card fits every one of those slots, so only a
library-wide comparison can see it. These tests hold the comparison itself and
pin the family it was written for.
"""
import pathlib

from portrayal import lint, libwalk
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def l123(docs):
    got = []
    real = lint.warn
    lint.warn = lambda path, rule, msg: got.append((str(path), rule, msg))
    try:
        lint.lint_library_bay_size_per_module(docs, [str(LIB)])
    finally:
        lint.warn = real
    return [m for _, r, m in got if r == "L123"]


def device(name, *bays):
    return {"kind": "device", "name": name,
            "views": {"front": {"size": {"w": 500, "h": 500},
                                "components": {"bays": list(bays)}}}}


def bay(bid, w, h, accepts, rotate=None):
    b = {"id": bid, "at": [0, 0], "size": {"w": w, "h": h}, "accepts": list(accepts)}
    if rotate is not None:
        b["rotate"] = rotate
    return b


CARD = "acme/card@1"


def test_one_size_everywhere_is_quiet():
    docs = [("a.yaml", device("a", bay("s0", 41.4, 395.7, [CARD]))),
            ("b.yaml", device("b", bay("s0", 41.4, 395.7, [CARD])))]
    assert l123(docs) == []


def test_two_sizes_for_one_module_warn_once_and_name_both():
    docs = [("a.yaml", device("a", bay("s0", 41.4, 395.7, [CARD]), bay("s1", 41.4, 395.7, [CARD]))),
            ("b.yaml", device("b", bay("s0", 42.67, 403.4, [CARD])))]
    msgs = l123(docs)
    assert len(msgs) == 1
    assert "41.4 x 395.7 (a)" in msgs[0] and "42.67 x 403.4 (b)" in msgs[0]


def test_a_millimetre_of_drawing_noise_is_not_a_finding():
    docs = [("a.yaml", device("a", bay("s0", 80.0, 81.5, [CARD]))),
            ("b.yaml", device("b", bay("s0", 80.9, 81.0, [CARD])))]
    assert l123(docs) == []


def test_a_turned_bay_compares_in_the_module_frame():
    # a horizontal chassis lays the card flat and turns the bay 270; it is the
    # same slot as an upright one, not a different size
    docs = [("a.yaml", device("a", bay("s0", 395.7, 41.4, [CARD], rotate=270))),
            ("b.yaml", device("b", bay("s0", 41.4, 395.7, [CARD])))]
    assert l123(docs) == []
    docs[1] = ("b.yaml", device("b", bay("s0", 395.7, 41.4, [CARD])))
    assert len(l123(docs)) == 1


def test_a_carrier_component_is_a_host_too():
    carrier = {"kind": "module", "name": "carrier",
               "bays": {"bay-0": {"at": [0, 0], "size": [17.29, 165.47], "accepts": [CARD]},
                        "bay-1": {"at": [0, 170], "size": [17.29, 167.87], "accepts": [CARD]}}}
    assert len(l123([("c.yaml", carrier)])) == 1


def _library_docs():
    docs = []
    for f in libwalk.iter_devices([LIB]) + libwalk.iter_components([LIB]):
        d = load_yaml(f)
        if isinstance(d, dict):
            docs.append((f, d))
    return docs


def test_every_asr_9000_card_seats_in_one_size():
    # The family this rule was written for. Every full-size card - line cards,
    # RSPs, RPs, fabric cards, the blank - is 41.4 x 395.7, and so is every bay
    # that takes one; a card that drifts off it fails here before it can draw
    # larger in one chassis than another.
    sizes = lint.bay_sizes_by_module(_library_docs())
    asr = {ref: e for ref, e in sizes.items()
           if ref.startswith("cisco/") and any(o.startswith("asr-99") or o == "asr-9010"
                                               or o == "asr-9006" for _, o, _ in e)}
    full = {ref: e for ref, e in asr.items() if all(abs(h - 395.7) < 15 for (_, h), _, _ in e)}
    # 62 of the 71 full-size cards are seated somewhere; a walk that finds far
    # fewer has stopped reading the library rather than found it clean
    assert len(full) >= 60, f"measured only {len(full)} seated ASR cards - the walk found nothing"
    wrong = {ref: sorted({s for s, _, _ in e}) for ref, e in full.items()
             if {s for s, _, _ in e} != {(41.4, 395.7)}}
    assert wrong == {}
