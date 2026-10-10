"""components.json carries each fibre end's far end and front number.

The explorer labels a fibre `1 -> rear mtp2 . 2` and an MTP `front 1-12`.
Front numbers are optical_ports.front_label's, and must not be re-derived in
JavaScript, so the build writes them next to the paths they come from.
"""
import json
import os
import pathlib
import subprocess
import sys

import onebuild

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _index(tmp_path):
    tmp_path = onebuild.components_index()   # built once per session
    return {f"{e['ns']}/{e['name']}": e for e in json.loads((tmp_path / "components.json").read_text())["components"]}


def test_an_af_cassette_names_both_ends_of_every_fibre(tmp_path):
    idx = _index(tmp_path)
    af = idx["fs/fhd-2mtp12-lc-os2-af"]["optical"]["ends"]
    assert af["lc01.1"] == {"to": "rear:mtp2.2", "label": "1"}
    assert af["lc01.2"] == {"to": "rear:mtp2.1", "label": "2"}
    assert af["rear:mtp2.2"] == {"to": "lc01.1", "label": "1"}
    assert len([k for k in af if not k.startswith("rear:")]) == 24


def test_a_front_to_front_path_numbers_each_end(tmp_path):
    ends = _index(tmp_path)["smartoptics/ppm-dcm-10"]["optical"]["ends"]
    assert ends["dcm.2"]["to"] == "dcm.1" and ends["dcm.1"]["to"] == "dcm.2"
    assert ends["dcm.1"]["label"] and ends["dcm.2"]["label"]


def test_a_splitter_fans_out_instead_of_being_dropped(tmp_path):
    ends = _index(tmp_path)["smartoptics/ppm-ocu-50-50"]["optical"]["ends"]
    # the common end names BOTH branches, not one, and not `{}` (a crash or a
    # dropped path would leave `common.1` missing entirely - see fibre_ends'
    # guard against a list-shaped endpoint it cannot resolve).
    assert isinstance(ends["common.1"]["to"], list)
    assert set(ends["common.1"]["to"]) == {"split.1", "split.2"}
    assert ends["common.1"]["label"]
    # each branch points back at the one common end, not at each other
    assert ends["split.1"]["to"] == "common.1"
    assert ends["split.2"]["to"] == "common.1"
    assert ends["split.1"]["label"] and ends["split.2"]["label"]


def test_a_rear_cutout_carries_its_slot_and_occupant():
    import yaml
    from portrayal import render
    lib = render.Library([str(ROOT / "library")])
    dev = yaml.safe_load((ROOT / "library/devices/fs/fhd-1ufce/device.yaml").read_text())
    # bay-1 declares no `default`, so an occupant is only on the cutout when
    # the config seats one - a bay-less config gets no data-rear-ref at all.
    occ = dev["views"]["front"]["components"]["bays"][0]["accepts"][0]
    out = render.render_view(dev, "rear", dev["views"]["rear"], lib, config_name="t",
                             config={"bays": {"bay-1": occ}})
    root = render.ET.fromstring(out) if isinstance(out, str) else out
    cut = next(e for e in root.iter() if e.get("data-rear-of") == "bay-1")
    assert cut.get("data-group") == "slots" and cut.get("data-rel-pos") == "1"
    assert cut.get("data-rear-ref") == occ
    # The cutout carries the bay's group and role (fs/fhd-1ufce's `slots`
    # group reads role: service in device.yaml), but never `data-media` - a
    # hole is not itself a port, and a `data-media` here would make the
    # explorer misread the cutout as one.
    assert cut.get("data-media") is None
    assert cut.get("data-group-role") == "service"


def test_a_combine_fans_in_instead_of_being_dropped(tmp_path):
    """The add side of an add/drop filter is a declared combine: its
    destination names BOTH sources and each source names the destination."""
    ends = _index(tmp_path)["smartoptics/ppm-ad1-1510"]["optical"]["ends"]
    assert set(ends["line.1"]["to"]) == {"osc.2", "edfa.2"}
    assert ends["osc.2"]["to"] == "line.1" and ends["edfa.2"]["to"] == "line.1"
    assert ends["line.1"]["label"] and ends["osc.2"]["label"] and ends["edfa.2"]["label"]


def test_fibre_ends_reads_a_combine_as_a_fan():
    """Unit form, so it does not lean on the library keeping the shape."""
    from portrayal import components_index as C
    known = {"common/lc-duplex-adapter@6": {"optical": {"positions": 2}}}
    doc = {"parts": [{"id": "a", "ref": "common/lc-duplex-adapter@6", "at": [0, 0]},
                     {"id": "b", "ref": "common/lc-duplex-adapter@6", "at": [13, 0]}],
           "optical": {"trunk": ["b"], "paths": [
               {"combine": [{"at": "a.1", "ratio": 50}, {"at": "a.2", "ratio": 50}],
                "to": "b.1"}]}}
    ends = C.fibre_ends(doc, known.get)
    assert ends["b.1"]["to"] == ["a.1", "a.2"]
    assert ends["a.1"] == {"to": "b.1", "label": "1"}
    assert ends["a.2"] == {"to": "b.1", "label": "2"}
