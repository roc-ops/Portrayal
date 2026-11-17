"""The Vertiv Geist VP7553 and VP7557, two basic vertical rack PDUs with IEC outlets.

What is true of the library once the devices are in it. Each is a 1683 mm strip, 51 mm wide and deep.
Its outlets are on the front, each fed by the fixed cord. The VP7553 runs them through two breakers.
The VP7557 spreads them over three phases. Each cord exports as a power port of type other.
"""
import pathlib

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
