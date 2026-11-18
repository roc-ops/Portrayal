"""The Vertiv Geist VP7553 and VP7557, two basic vertical rack PDUs with IEC outlets.

What is true of the library once the devices are in it. Each is a 1683 mm strip, 51 mm wide and deep.
Its outlets are on the front, each fed by the fixed cord. The VP7553 runs them through two breakers.
The VP7557 spreads them over three phases. Each cord exports as a power port of type other.
"""
import pathlib
import xml.etree.ElementTree as ET

import yaml

from portrayal import dcim_export as dx
from portrayal import dcim_registers as dr

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICES = ROOT / "library" / "devices" / "vertiv"
COMPONENTS = ROOT / "library" / "components"

C13 = "std/c13-outlet"
C19 = "std/c19-outlet"
CORDS = {"vp7553": "vertiv/rpdu-cord-60309-2pe", "vp7557": "vertiv/rpdu-cord-60309-3pne"}
BREAKER = "vertiv/rpdu-magnetic-breaker"
COUNTS = {"vp7553": (20, 4), "vp7557": (36, 6)}


def _load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _device(name):
    return _load(DEVICES / name / "device.yaml")


def _contract(ref):
    ns, name = ref.split("/")
    return _load(COMPONENTS / ns / name / "v1" / "contract.yaml")


def _front(dev):
    return dev["views"]["front"]["components"]["placements"]


def _base(ref):
    return ref.split("@")[0]


def _of(dev, ref):
    return [p for p in _front(dev) if _base(p["ref"]) == ref]


def test_each_device_is_a_1683_mm_strip_with_all_six_faces():
    for name, model in (("vp7553", "VP7553"), ("vp7557", "VP7557")):
        dev = _device(name)
        assert dev["manufacturer"] == "Vertiv" and dev["model"] == model
        chassis = dev["chassis"]
        assert (chassis["width"], chassis["height"], chassis["depth"]) == (51.0, 1683.0, 51.0)
        assert set(dev["views"]) == {"front", "rear", "top", "bottom", "left", "right"}
        assert list(dev["configurations"]["base"]["part-numbers"]) == [model]


def test_the_front_carries_the_outlets_the_data_sheet_counts():
    for name, (n13, n19) in COUNTS.items():
        dev = _device(name)
        assert len(_of(dev, C13)) == n13, name
        assert len(_of(dev, C19)) == n19, name
        for p in _of(dev, C13) + _of(dev, C19):
            assert 0 <= p["at"][0] and p["at"][0] + 36 <= 51.0, (name, p["id"])
            assert 0 <= p["at"][1] and p["at"][1] + 28 <= 1683.0, (name, p["id"])


def test_the_c13_outlets_sit_in_pairs_or_banks_on_one_pitch():
    pairs = sorted(p["at"][1] for p in _of(_device("vp7553"), C13))
    assert {round(b - a, 1) for a, b in zip(pairs[0::2], pairs[1::2])} == {25.0}
    banks = sorted(p["at"][1] for p in _of(_device("vp7557"), C13))
    for i in range(0, 36, 6):
        steps = {round(b - a, 1) for a, b in zip(banks[i:i + 5], banks[i + 1:i + 6])}
        assert steps == {24.0}, i


def test_every_outlet_is_fed_by_the_fixed_cord():
    for name, cord in CORDS.items():
        dev = _device(name)
        inputs = _of(dev, cord)
        assert len(inputs) == 1
        for p in _of(dev, C13) + _of(dev, C19):
            assert p["fed-by"] == inputs[0]["id"], (name, p["id"])
            assert "states" not in p


def test_the_vp7553_runs_ten_c13_and_two_c19_through_each_breaker():
    dev = _device("vp7553")
    breakers = _of(dev, BREAKER)
    assert len(breakers) == 2
    for b in breakers:
        fed = [p for p in _of(dev, C13) + _of(dev, C19) if p["through"] == b["id"]]
        assert sum(_base(p["ref"]) == C13 for p in fed) == 10, b["id"]
        assert sum(_base(p["ref"]) == C19 for p in fed) == 2, b["id"]


def test_the_vp7557_has_no_breaker_and_twelve_c13_and_two_c19_per_phase():
    dev = _device("vp7557")
    assert _of(dev, BREAKER) == []
    assert dev["attrs"]["power"]["input-phase"] == "three"
    assert dev["attrs"]["power"]["input-wiring"] == "wye"
    for phase in ("L1", "L2", "L3"):
        mine = [p for p in _of(dev, C13) + _of(dev, C19) if p["lines"][0] == phase]
        assert sum(_base(p["ref"]) == C13 for p in mine) == 12, phase
        assert sum(_base(p["ref"]) == C19 for p in mine) == 2, phase


def test_the_cords_are_iec_60309_plugs_that_export_as_other():
    plugs = {"vp7553": "iec-60309-2p-e-32a", "vp7557": "iec-60309-3p-n-e-16a"}
    for name, cord in CORDS.items():
        contract = _contract(cord)
        assert contract["class"] == "inlet"
        assert contract["attrs"]["plug"] == plugs[name]
        assert dx.PART_POWER[cord] == "other"
        assert "IEC 60309" in dr.POWER_LABEL[cord]
        assert _device(name)["attrs"]["power"]["input-plug"] == "other"


def test_the_pdus_neither_meter_nor_switch_and_the_breaker_is_a_sixteen_amp_part():
    for name in COUNTS:
        management = _device(name)["attrs"]["management"]
        assert management["outlet-switching"] is False
        assert management["metering-scope"] == "none"
    contract = _contract(BREAKER)
    assert contract["class"] == "breaker"
    assert contract["elements"]["button"]["states"] == ["on", "off"]
    assert "16 A" in contract["provenance"]["rating"]


def test_the_breaker_states_have_their_own_provenance_entry():
    contract = _contract(BREAKER)
    for element in contract["elements"].values():
        if element.get("states"):
            assert "states" in contract["provenance"]
    states = contract["provenance"]["states"]
    assert states.startswith("estimated")
    assert "does not show" in states
    assert "`off`" in states


def _decor(dev):
    return dev["views"]["front"]["panel"]["decor"]


def _box(d):
    return (d["at"][0], d["at"][1], d["at"][0] + d["size"][0], d["at"][1] + d["size"][1])


def _overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _skin(ref):
    ns, name = ref.split("/")
    return (COMPONENTS / ns / name / "v1" / "skins" / "default.svg").read_text(encoding="utf-8")


def test_the_vp7553_plate_shows_eight_screws_in_the_figures_four_columns_and_none_is_covered():
    dev = _device("vp7553")
    decor = _decor(dev)
    plate = next(d for d in decor if d["id"] == "module-plate")
    screws = [d for d in decor if d["id"].startswith("module-screw-")]
    assert len(screws) == 8
    parts = []
    for p in _front(dev):
        size = _contract(_base(p["ref"]))["size"]
        parts.append((p["at"][0], p["at"][1], p["at"][0] + size["w"], p["at"][1] + size["h"]))
    px0, py0, px1, py1 = _box(plate)
    for i, s in enumerate(decor):
        if not s["id"].startswith("module-screw-"):
            continue
        box = _box(s)
        assert px0 <= box[0] and box[2] <= px1 and py0 <= box[1] and box[3] <= py1, s["id"]
        assert not any(_overlap(box, part) for part in parts), s["id"]
        assert not any(_overlap(box, _box(later)) for later in decor[i + 1:] if later.get("fill") and not later.get("stroke")), s["id"]
    columns = sorted({round(s["at"][1] + s["size"][1] / 2 - py0) for s in screws})
    # the figure at 1.99 mm per pixel: columns 16, 58, 103 and 143 mm from the plate start, good to about 3 mm
    assert len(columns) == 4
    assert all(abs(c - w) <= 4 for c, w in zip(columns, (16, 58, 103, 143))), columns
    for c in columns:
        assert sum(round(s["at"][1] + s["size"][1] / 2 - py0) == c for s in screws) == 2, c
    rows = sorted({round(s["at"][0] + s["size"][0] / 2, 1) for s in screws})
    assert len(rows) == 2 and abs((rows[1] - rows[0]) - 19.5) <= 3, rows
    assert abs((rows[0] + rows[1]) / 2 - 25.5) <= 2, rows


def test_each_vp7553_window_has_a_screw_column_on_either_side_of_it():
    dev = _device("vp7553")
    decor = _decor(dev)
    plate = next(d for d in decor if d["id"] == "module-plate")
    screw_y = sorted({s["at"][1] + s["size"][1] / 2 for s in decor if s["id"].startswith("module-screw-")})
    window = None
    for rect in ET.fromstring(_skin(BREAKER)).iter("{http://www.w3.org/2000/svg}rect"):
        if rect.get("stroke"):
            window = (float(rect.get("y")), float(rect.get("y")) + float(rect.get("height")))
    assert window is not None
    for b in _of(dev, BREAKER):
        start, end = b["at"][1] + window[0], b["at"][1] + window[1]
        before = [y for y in screw_y if start - 10 <= y <= start - 3]
        after = [y for y in screw_y if end + 0.5 <= y <= end + 6]
        assert len(before) == 1 and len(after) == 1, b["id"]
        assert plate["at"][1] <= before[0] and after[0] <= plate["at"][1] + plate["size"][1], b["id"]


def test_the_vp7553_module_note_says_what_is_drawn():
    dev = _device("vp7553")
    note = dev["provenance"]["module"]["note"]
    assert "Eight small screws" in note and "four columns" in note
    screws = [d for d in _decor(dev) if d.get("kind") == "screw"]
    assert len(screws) == 12, "eight on the plate, two just before it and one at each end of the strip"
    start = next(d for d in _decor(dev) if d["id"] == "module-plate")["at"][1]
    dots = [s for s in screws if s["id"].startswith("plate-dot-")]
    assert len(dots) == 2 and all(s["at"][1] + s["size"][1] < start for s in dots)


def test_the_vp7553_cord_draws_a_hex_sided_nut_and_the_vp7557_cord_a_round_gland():
    ns = "{http://www.w3.org/2000/svg}"
    nut = ET.fromstring(_skin(CORDS["vp7553"]))
    polygons = [e for e in nut.iter(ns + "polygon") if e.get("id") == "gland"]
    assert len(polygons) == 1
    points = [tuple(float(v) for v in pt.split(",")) for pt in polygons[0].get("points").split()]
    assert len(points) == 6
    assert min(p[1] for p in points) <= 0.5 and max(p[1] for p in points) >= 39.5
    assert not [e for e in nut.iter(ns + "circle") if e.get("id") == "gland"]
    assert "hex-sided" in _contract(CORDS["vp7553"])["description"]
    round_gland = ET.fromstring(_skin(CORDS["vp7557"]))
    assert [e for e in round_gland.iter(ns + "circle") if e.get("id") == "gland"]
    assert not list(round_gland.iter(ns + "polygon"))
    # the photograph cannot tell round from hex-sided, so the contract's description no longer says round
    assert "round" not in _contract(CORDS["vp7557"])["description"]


def test_every_slot_carries_a_light_rim_and_a_pale_bar_drawn_over_its_plate():
    for name, slots in (("vp7553", 2), ("vp7557", 3)):
        decor = _decor(_device(name))
        ids = [d["id"] for d in decor]
        for n in range(1, slots + 1):
            plate = decor[ids.index(f"label-window-{n}")]
            rim = decor[ids.index(f"label-window-{n}-rim")]
            bar = decor[ids.index(f"label-window-{n}-bar")]
            assert ids.index(f"label-window-{n}") < ids.index(f"label-window-{n}-rim") < ids.index(f"label-window-{n}-bar")
            assert rim["at"] == plate["at"] and rim["size"] == plate["size"], (name, n)
            assert rim["stroke"] == "#6f7072" and rim["stroke-width"] == 0.6, (name, n)
            inner = _box(bar)
            outer = _box(plate)
            assert outer[0] < inner[0] and inner[2] < outer[2] and outer[1] < inner[1] and inner[3] < outer[3], (name, n)
        assert f"label-window-{slots + 1}" not in ids
        gap = next(g for g in _device(name)["gaps"] if g["what"] == "label-windows")
        assert "rim" in gap["note"] and "plain plate" not in gap["note"], name


def test_the_vp7553_plate_has_the_figures_dark_band_along_its_start_edge_and_the_vp7557_has_none():
    dev = _device("vp7553")
    decor = _decor(dev)
    ids = [d["id"] for d in decor]
    plate = decor[ids.index("module-plate")]
    band = decor[ids.index("module-plate-band")]
    # the figure at 1.99 mm per pixel: the band reads about 3.9 px, 7.7 mm, good to 2 mm, across the whole plate
    assert band["at"][0] == plate["at"][0] and band["size"][0] == plate["size"][0]
    assert band["at"][1] == plate["at"][1], "on the plate's start edge, the edge nearer the far end"
    assert 5.5 <= band["size"][1] <= 9.5, band["size"]
    assert ids.index("module-plate") < ids.index("module-plate-band")
    assert band["fill"].lower() < plate["fill"].lower(), "darker than the plate"
    for screw in (d for d in decor if d.get("kind") == "screw"):
        assert not _overlap(_box(band), _box(screw)), screw["id"]
    assert all(ids.index("module-plate-band") < i for i, n in enumerate(ids) if n.startswith("module-screw-"))
    gap = next(g for g in dev["gaps"] if g["what"] == "module-detail")
    assert "band" in gap["note"] and "is drawn" in gap["note"] and "not drawn" in gap["note"]
    assert "which is not drawn" not in gap["note"]
    assert not [d for d in _decor(_device("vp7557")) if "band" in d["id"] and "bank" not in d["id"]]


def test_the_vp7557_gland_is_drawn_round_as_a_stated_stand_in_and_not_claimed_to_read_round():
    contract = _contract(CORDS["vp7557"])
    size = contract["provenance"]["size"]
    assert "too small to tell round from hex-sided" in size and "drawn round" in size
    assert "reads round" not in size
    assert "round" not in contract["description"] and "through a cable gland" in contract["description"]
    dev = _device("vp7557")
    assert "too small to tell round from hex-sided" in dev["provenance"]["input"]["note"]
    gap = next(g for g in dev["gaps"] if g["what"] == "gland-shape")
    for word in ("round", "hex", "18 px", "VP7553"):
        assert word in gap["note"], word
    assert [g for g in _device("vp7553")["gaps"] if g["what"] == "gland-shape"] == []
