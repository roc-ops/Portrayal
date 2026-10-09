"""A distribution panel's outputs export as power outlets (#806).

docs/power-outlets-design.md. An output circuit is a `power-outlets` row on the
DEVICE type, named by its placement id, typed from PART_OUTLET, its
`power_port` the input its `fed-by` names. The breaker position it runs
through is a sentence on the outlet and on the bay, because neither target
relates an outlet to a module bay.
"""
import copy

import pytest

from portrayal import dcim_export as dx

OUT = "amphenol-ns/output-terminal@1"
P40 = "amphenol-ns/output-p40@1"
FEED = "amphenol-ns/input-feed-studs@1"
ACCEPTS = ["amphenol-ns/breaker-1ru@1"]


def panel(ref=OUT, **outputs):
    rear = [{"id": "input-a", "ref": FEED, "at": [0, 0]},
            {"id": "input-b", "ref": FEED, "at": [10, 0]}]
    for i, (oid, keys) in enumerate(sorted(outputs.items())):
        rear.append({"id": oid, "ref": ref, "at": [100 + 15 * i, 0], **keys})
    bays = [{"id": f"breaker-a{n}", "at": [20 * n, 0], "size": {"w": 10, "h": 10},
             "accepts": ACCEPTS} for n in (1, 2, 10)]
    return {"format": 1, "kind": "device", "name": "p", "version": "1.0.0",
            "manufacturer": "Acme", "model": "P1",
            "chassis": {"width": 440, "height": 44, "depth": 300, "ru": 1},
            "views": {"front": {"components": {"bays": bays}},
                      "rear": {"components": {"placements": rear}}}}


def build(dev):
    return dx.build(dev, "default", {}, None)


FED = {"output-a10": {"fed-by": "input-a", "through": "breaker-a10"},
       "output-a2": {"fed-by": "input-a", "through": "breaker-a2"},
       "output-a1": {"fed-by": "input-b"}}


def test_each_output_is_an_outlet_named_by_its_id_in_natural_order():
    d = build(panel(**FED))
    assert d["power-outlets"] == [
        {"name": "output-a1", "type": "dc-terminal", "power_port": "input-b"},
        {"name": "output-a2", "type": "dc-terminal", "power_port": "input-a",
         "description": "Through breaker position breaker-a2"},
        {"name": "output-a10", "type": "dc-terminal", "power_port": "input-a",
         "description": "Through breaker position breaker-a10"},
    ]
    keys = list(d)
    assert keys.index("power-outlets") == keys.index("power-ports") + 1


def test_no_feed_leg_is_written():
    """`feed_leg` is a phase of three; a DC panel's sides are two feeds."""
    assert not any("feed_leg" in o for o in build(panel(**FED))["power-outlets"])


def test_the_bay_says_which_output_it_protects():
    bays = {b["position"]: b for b in build(panel(**FED))["module-bays"]}
    assert bays["breaker-a2"]["description"] == \
        "Accepts: breaker-1ru; protects output-a2"
    assert bays["breaker-a10"]["description"] == \
        "Accepts: breaker-1ru; protects output-a10"
    assert bays["breaker-a1"]["description"] == "Accepts: breaker-1ru"


def test_a_bay_with_no_accepts_sentence_still_says_it():
    dev = panel(**FED)
    for b in dev["views"]["front"]["components"]["bays"]:
        b.pop("accepts")
        b["interface"] = "breaker"
    bays = {b["position"]: b for b in build(dev)["module-bays"]}
    assert bays["breaker-a2"]["description"] == "Protects output-a2"


def test_an_outlet_with_no_feed_is_written_without_one():
    d = build(panel(**{"output-a1": {}}))
    assert d["power-outlets"] == [{"name": "output-a1", "type": "dc-terminal"}]


@pytest.mark.parametrize("fed", ["input-z", "breaker-a1", "output-a2"])
def test_a_feed_that_names_no_power_port_stops_the_export(fed):
    """Both targets refuse a dangling `power_port` at import; a file that is
    committed, looks right and fails there is what NotExpressible prevents."""
    with pytest.raises(dx.NotExpressible, match="exports no power port"):
        build(panel(**{"output-a1": {"fed-by": fed}, "output-a2": {}}))


def test_a_p40_outlet_is_other_with_its_connector_as_label():
    d = build(panel(ref=P40, **{"output-a1": {"fed-by": "input-a"}}))
    assert d["power-outlets"] == [{"name": "output-a1", "type": "other", "label": "P40",
                                   "power_port": "input-a"}]


def test_every_outlet_type_is_one_both_targets_list():
    """Nautobot turns an unknown outlet type into `other` without a word, so
    the table is checked against the list read from both choices.py files. A
    new type joins OUTLET_TYPES - and this set - only with both SHAs cited."""
    assert dx.PART_OUTLET
    assert set(dx.PART_OUTLET.values()) <= dx.OUTLET_TYPES
    # iec-60320-c13 and eaton-c39: NetBox choices.py at 2b3f4b48, Nautobot at
    # c77e4255 (the Eaton EVMI2130X, the first rack PDU).
    assert dx.OUTLET_TYPES == {"dc-terminal", "other", "iec-60320-c13", "eaton-c39"}
    # the C13 is the standard's face, a std/ part; the C39 is Eaton's own
    assert dx.PART_OUTLET["std/c13-outlet"] == "iec-60320-c13"
    assert dx.PART_OUTLET["eaton/c39-outlet"] == "eaton-c39"
    assert all(dx.PART_OUTLET.get(r) == "other" for r in dx.OUTLET_LABEL), \
        "OUTLET_LABEL labels an outlet that is not `other`"


@pytest.mark.parametrize("target", dx.TARGETS)
def test_both_targets_get_the_same_outlets(target):
    """Both import `power_port` by name, so for_target leaves the block alone."""
    d = build(panel(**FED))
    assert dx.for_target(copy.deepcopy(d), target)["power-outlets"] == d["power-outlets"]


def test_a_device_with_no_outlet_part_writes_no_block():
    assert "power-outlets" not in build(panel())


def test_bay_descriptions_do_not_move_the_collision_check():
    """dcim_significant reads a bay's description as a sentence about the
    drawing, so the `protects` suffix is not a difference in the hardware."""
    with_suffix = build(panel(**FED))
    without = copy.deepcopy(with_suffix)
    for b in without["module-bays"]:
        b["description"] = "Accepts: breaker-1ru"
    assert dx.dcim_significant(with_suffix)["module-bays"] == \
        dx.dcim_significant(without)["module-bays"]
