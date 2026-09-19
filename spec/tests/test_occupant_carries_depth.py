"""What a bore is off the panel, the plug seated in it is too.

The bay case is already held by test_bay_occupant_lift.py. This is the MATE-TO
case, which had no z at all: only `parts:` composition carried `lift`, so an
occupant positioned by mate points sat at the panel plane no matter how far
forward the thing it seats into stands.

Asserted on the UNIT rather than on a shipped drawing, because no device in the
library seats an optic any more - spec A made them all bare on purpose - so
there is no compiled fixture to read. The invariant is about the function.
"""
from portrayal.manifest import presented_interface


def _res(table):
    return lambda ref: table.get(ref)


def test_a_host_that_presents_its_own_point_lifts_nothing():
    host = {"interface": "sfp", "connection-points": {"mate": {"at": [8.0, 5.0]}}}
    iface, at, lift = presented_interface(host, _res({}))
    assert (iface, at) == ("sfp", [8.0, 5.0])
    assert lift == 0.0, "a host mating on its own face displaces nothing"


def test_a_forwarded_point_carries_the_composed_parts_lift():
    """The whole point: the aperture is the thing that stands forward."""
    bore = {"interface": "lc", "connection-points": {"mate": {"at": [2.35, 2.35]}}}
    host = {"parts": [{"ref": "std/lc-bore@3", "id": "tx",
                       "at": [1.25, 1.75], "lift": 10.0}]}
    iface, at, lift = presented_interface(host, _res({"std/lc-bore@3": bore}))
    assert iface == "lc"
    assert at == [3.6, 4.1]
    assert lift == 10.0, (
        "the bore stands 10.0 off the module face; a plug seated in it that "
        "ignores that is buried in the transceiver body")


def test_a_composed_part_with_no_lift_forwards_zero():
    bore = {"interface": "lc", "connection-points": {"mate": {"at": [2.35, 2.35]}}}
    host = {"parts": [{"ref": "std/lc-bore@3", "id": "tx", "at": [1.25, 1.75]}]}
    _, _, lift = presented_interface(host, _res({"std/lc-bore@3": bore}))
    assert lift == 0.0
