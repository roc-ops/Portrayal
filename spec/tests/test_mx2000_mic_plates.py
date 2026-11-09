"""The multirate MICs of the MX2000 cards are drawn at the MIC's plate, not at a window.

The MPC8E and MPC9E seat the 12-port multirate MICs and the MIC blank in two
bays each. Those bays and the parts that fill them were sized from the layout
("registry + layout", 27.0 x 168.0), so the same MIC form was drawn smaller
than the 168.8 x 29.2 plate every other Juniper MIC is drawn at, and the
estimate read exactly like a measurement to anything that only had the number.

The plate is the figure the horizontal MICs state, measured off the MX104 and MX80
front photographs. These parts borrow it and say so: nothing in the held guides
dimensions a MIC to better than a tenth of an inch.
"""
import re

import pytest

import libdata

PLATE = (29.2, 168.8)
MICS = ("mic-mrate", "mic-macsec-mrate", "mx-mic-blank-v")
CARRIERS = ("mx2k-mpc8e-v2k", "mx2k-mpc9e-v2k")


def _by_name():
    """{name: {major: (path, doc)}} for the juniper namespace."""
    out = {}
    for ref, path, doc in libdata.components():
        ns, name = ref.split("/")
        if ns != "juniper":
            continue
        out.setdefault(name, {})[int(path.parent.name[1:])] = (path, doc)
    return out


def _current(name):
    majors = _by_name()[name]
    return majors[max(majors)][1]


def _resolve(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return _by_name()[name][int(major)][1]


@pytest.mark.parametrize("name", MICS)
@pytest.mark.heavy
def test_the_current_mic_is_the_plate_and_says_how_it_got_there(name):
    doc = _current(name)
    assert (doc["size"]["w"], doc["size"]["h"]) == PLATE
    conf = doc["size-confidence"]
    assert conf["w"] != "estimated" and conf["h"] != "estimated"
    assert not str(doc["provenance"].get("size", "")).startswith("registry + layout")
    assert re.search(r"168\.8 x 29\.2", doc["size-notes"])


@pytest.mark.parametrize("name", CARRIERS)
def test_each_bay_is_the_plate_and_takes_only_what_fits_it(name):
    doc = _current(name)
    assert doc["bays"]
    for bay_id, bay in doc["bays"].items():
        assert tuple(bay["size"]) == PLATE, bay_id
        for ref in bay["accepts"]:
            part = _resolve(ref)
            assert (part["size"]["w"], part["size"]["h"]) == PLATE, (bay_id, ref)


@pytest.mark.parametrize("name", CARRIERS)
def test_the_bays_do_not_overlap(name):
    bays = list(_current(name)["bays"].values())
    for i, a in enumerate(bays):
        for b in bays[i + 1:]:
            ax, ay = a["at"]
            bx, by = b["at"]
            separate = (ax + a["size"][0] <= bx or bx + b["size"][0] <= ax
                        or ay + a["size"][1] <= by or by + b["size"][1] <= ay)
            assert separate
