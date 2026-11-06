"""A bay states the class of module it takes, with no module to seat yet.

A chassis with an opening for a module the library does not hold (an I/O
window, a cellular socket) has a real fact to state: what kind of module the
opening takes. The bay states it as its `interface`, a key registered in
spec/schemas/connectors.yaml, and carries neither `accepts` nor `default`
because no part exists to name. What follows from that is held here:

- lint L6 does not ask such a bay for a default, and still asks one a part could
  fill;
- the device type's export lists the bay, with a name, a position and a
  description saying what it takes, and no port;
- every interface a bay states is a registered key, so the description is the
  registry's sentence and never the bare key.
"""
import json
import pathlib

import jsonschema
import pytest
import yaml

from portrayal import dcim_export as dcim
from portrayal import libwalk
from portrayal import lint
from portrayal import manifest
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "spec/schemas"
LIB = ROOT / "library"
DEVICE_VALIDATOR = jsonschema.Draft202012Validator(
    json.loads((SCHEMAS / "device.schema.json").read_text()))

CLASS = "acme-io-module"
NIC = "acme/nic@1"


def _write(lib, ref, doc):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    d = lib / "components" / ns / name / f"v{major}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "contract.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))


@pytest.fixture
def lib(tmp_path):
    root = tmp_path / "library"
    _write(root, NIC, {"format": 1, "kind": "component", "name": "nic", "version": "1.0.0",
                       "class": "card", "behaviour": "fills", "mates": "pcie-fh",
                       "size": {"w": 120.02, "h": 21.59}, "description": "A test card."})
    (root / "devices").mkdir(parents=True)
    return root


def _device(bays):
    return {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
            "manufacturer": "Acme", "model": "D", "maturity": "modelled",
            "profile": "networking",
            "groups": {"io": {"term": "Bay", "role": "traffic", "index-origin": 1}},
            "chassis": {"width": 440.0, "height": 44.45, "depth": 500.0, "ru": 1},
            "views": {"front": {"size": {"w": 440.0, "h": 44.45},
                               "components": {"bays": list(bays)}}}}


def _bay(i, **extra):
    return {"id": f"io-bay-{i}", "at": [10.0 + 120.0 * (i - 1), 2.0],
            "size": {"w": 112.5, "h": 40.0}, "group": "io", "rel-pos": i, **extra}


def _l6(lib, bays):
    path = lib / "devices" / "acme" / "d" / "device.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(_device(bays), sort_keys=False))
    with lint.collecting() as found:
        lint.lint_device(path, DEVICE_VALIDATOR, [str(lib)])
    assert not [e for e in found.errors if "[L1]" in e], found.errors
    return [f for f in found.errors + found.warnings if "[L6]" in f]


def test_l6_a_bay_naming_a_class_no_part_mates_needs_no_default(lib):
    assert _l6(lib, [_bay(1, interface=CLASS), _bay(2, interface=CLASS)]) == []


def test_l6_a_bay_a_part_could_fill_still_needs_a_default(lib):
    got = _l6(lib, [_bay(1, interface="pcie-fh")])
    assert len(got) == 1 and "io-bay-1 names no default" in got[0]


def test_l6_a_bay_with_neither_a_class_nor_a_part_still_needs_a_default(lib):
    got = _l6(lib, [_bay(1, accepts=[NIC])])
    assert len(got) == 1 and "io-bay-1 names no default" in got[0]


def test_the_device_type_lists_each_bay_with_what_it_takes_and_no_port():
    out = dcim.build(_device([_bay(1, interface=CLASS), _bay(2, interface=CLASS)]),
                     "default", {}, None)
    assert out["module-bays"] == [
        {"name": f"io-bay-{i}", "position": f"io-bay-{i}",
         "description": f"Takes {CLASS}."} for i in (1, 2)]
    assert not {"interfaces", "console-ports", "power-ports"} & set(out)


def test_a_bay_with_a_list_and_a_class_says_both():
    out = dcim.build(_device([_bay(1, interface=CLASS, accepts=[NIC])]), "default", {}, None)
    assert out["module-bays"][0]["description"] == f"Takes {CLASS}. Also accepts: nic"


@pytest.mark.heavy
def test_every_interface_a_bay_states_is_a_registered_key():
    from portrayal.render import _connector_registry
    registry = set(_connector_registry())
    unregistered = []
    for df in libwalk.iter_devices([LIB]):
        for view in ((load_yaml(df) or {}).get("views") or {}).values():
            for b in manifest.view_parts(view or {})["bays"]:
                if b.get("interface") and b["interface"] not in registry:
                    unregistered.append(f"{df.parent.name}:{b['id']}={b['interface']}")
    for cf in libwalk.iter_components([LIB]):
        for bid, b in ((load_yaml(cf) or {}).get("bays") or {}).items():
            if isinstance(b, dict) and b.get("interface") and b["interface"] not in registry:
                unregistered.append(f"{cf.parent.parent.name}/{cf.parent.name}:{bid}={b['interface']}")
    assert unregistered == [], unregistered
