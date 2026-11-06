"""The MX304 LMIC16 states each cage's native rates, and its module type follows them.

The hardware guide's port-speed table gives ports 0, 6, 8 and 14 as 100GbE or
400GbE; ports 1, 3, 5, 7, 9, 11, 13 and 15 as 100GbE or 40G (breakout is not
recorded); ports 2, 4, 10 and 12 as 100GbE only. A QSFP-DD cage placed at 100G
takes a QSFP28 optic, so it exports as `100gbase-x-qsfp28`, as the library
already types a QSFP-DD cage placed at 100G elsewhere.
"""
import pathlib

import yaml

from portrayal.dcim_export import PART_MEDIA
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "library" / "components" / "juniper" / "mx304-lmic16" / "v1" / "contract.yaml"
EXPORTS = [
    ROOT / "library" / "exports" / vendor / "module-types" / "Juniper" / "MX304-LMIC16-BASE.yaml"
    for vendor in ("netbox", "nautobot")
]

PORTS_400G = {0, 6, 8, 14}
PORTS_MULTI_100G = {1, 3, 5, 7, 9, 11, 13, 15}
PORTS_100G_ONLY = {2, 4, 10, 12}


def _placements():
    parts = load_yaml(CONTRACT)["parts"]
    return {int(p["id"].split("-")[1]): p for p in parts}


def test_every_cage_states_its_native_rates():
    placed = _placements()
    assert set(placed) == set(range(16))
    for n in PORTS_400G:
        a = placed[n]["attrs"]
        assert (a["speed"], a.get("speeds")) == ("400g", ["100g", "400g"]), n
    for n in PORTS_MULTI_100G:
        a = placed[n]["attrs"]
        assert (a["speed"], a.get("speeds")) == ("100g", ["40g", "100g"]), n
    for n in PORTS_100G_ONLY:
        a = placed[n]["attrs"]
        assert (a["speed"], a.get("speeds")) == ("100g", None), n


def test_the_module_type_types_each_port_by_its_rate():
    for path in EXPORTS:
        got = {i["name"]: i["type"] for i in yaml.safe_load(path.read_text())["interfaces"]}
        for n in range(16):
            want = "400gbase-x-qsfpdd" if n in PORTS_400G else "100gbase-x-qsfp28"
            assert got[f"{{module}}/port-{n}"] == want, (path.parent.parent.name, n)


def test_the_two_exports_name_the_contracts_ports():
    want = [f"{{module}}/port-{n}" for n in range(16)]
    for path in EXPORTS:
        names = [i["name"] for i in yaml.safe_load(path.read_text())["interfaces"]]
        assert names == want, path.parent.parent.name


def test_each_placement_states_its_media_beside_its_speed():
    # the exporter types a placement from its `media` and `speed`; with no media it
    # falls back to the card's one type for every QSFP-DD cage
    for n, p in _placements().items():
        assert p["attrs"].get("media") == "qsfp-dd", n
    assert PART_MEDIA[("qsfp-dd", "100g")] == "100gbase-x-qsfp28"
