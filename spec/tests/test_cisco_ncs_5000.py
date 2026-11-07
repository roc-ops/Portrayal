"""The Cisco NCS 5001 and NCS 5002 match the Hardware Installation Guide for Cisco NCS 5000 Series Routers.

The guide (first published 2015-12-23, last modified 2019-01-31) gives each router's size and weight
(Appendix C, Tables 11 and 12), its port counts (Chapter 1), the supplies and fan modules it takes with
their airflow (Tables 2 to 5), and the rack height. Its face figures are three-quarter views, so what is
held to the guide here is counts, sizes and part numbers, not positions.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

INCH = 25.4

# Table 11 and Table 12, in inches as printed: H x W x D.
ENVELOPE = {
    "ncs-5001": {"h": 1.72, "w": 17.42, "d": 19.3, "ru": 1},
    "ncs-5002": {"h": 3.5, "w": 17.42, "d": 19.28, "ru": 2},
}

# Chapter 1, Ports: SFP+ and QSFP28 counts.
PORTS = {"ncs-5001": {"sfp-ganged": 40, "qsfp28": 4},
         "ncs-5002": {"sfp-ganged": 80, "qsfp28": 4}}

# Tables 2 to 5: the supply and fan part numbers, by airflow, as the component names them.
PSU = {("ac", "front-to-back"): "nc5k-pac-650w-fr", ("ac", "back-to-front"): "nc5k-pac-650w-bk",
       ("dc", "front-to-back"): "nc5k-pdc-930w-fr", ("dc", "back-to-front"): "nc5k-pdc-930w-bk"}
FAN = {"ncs-5001": {"front-to-back": "ncs-5001-fn-fr", "back-to-front": "ncs-5001-fn-bk"},
       "ncs-5002": {"front-to-back": "ncs-5002-fn-fr", "back-to-front": "ncs-5002-fn-bk"}}


def device(name):
    return yaml.safe_load((LIB / "devices/cisco" / name / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((LIB / "components/cisco" / name / "v1/contract.yaml").read_text())


def ref_name(ref):
    return ref.split("/", 1)[1].split("@", 1)[0]


@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_envelope_is_the_guides_table(name):
    want, ch = ENVELOPE[name], device(name)["chassis"]
    assert ch["height"] == pytest.approx(want["h"] * INCH, abs=0.1)
    assert ch["width"] == pytest.approx(want["w"] * INCH, abs=0.1)
    assert ch["depth"] == pytest.approx(want["d"] * INCH, abs=0.1)
    assert ch["ru"] == want["ru"]
    assert ch.get("mount", "rack") == "rack"


@pytest.mark.parametrize("name", sorted(PORTS))
def test_front_ports_are_counted_by_cage_and_numbered_from_one(name):
    placements = device(name)["views"]["front"]["components"]["placements"]
    ports = [p for p in placements if str(p["id"]).startswith("port-")]
    by_cage = {}
    for p in ports:
        cage = ref_name(p["ref"])
        by_cage[cage] = by_cage.get(cage, 0) + 1
    assert by_cage == PORTS[name]
    numbers = sorted(int(p["id"].split("-")[1]) for p in ports)
    assert numbers == list(range(1, sum(PORTS[name].values()) + 1))


@pytest.mark.parametrize("name", sorted(PORTS))
def test_front_carries_console_and_management_and_the_rear_does_not_duplicate_them(name):
    d = device(name)
    front = {p["id"] for p in d["views"]["front"]["components"]["placements"]}
    rear = {p["id"] for p in d["views"]["rear"]["components"].get("placements", [])}
    assert {"console", "mgmt"} <= front
    assert not ({"console", "mgmt"} & rear)


def test_usb_is_on_the_fan_side_of_the_5001_and_the_port_side_of_the_5002():
    rear5001 = {p["id"] for p in device("ncs-5001")["views"]["rear"]["components"]["placements"]}
    front5002 = {p["id"] for p in device("ncs-5002")["views"]["front"]["components"]["placements"]}
    front5001 = {p["id"] for p in device("ncs-5001")["views"]["front"]["components"]["placements"]}
    assert "usb" in rear5001 and "usb" not in front5001
    assert "usb" in front5002


@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_two_supply_bays_and_two_fan_bays_each_accept_the_guides_parts(name):
    bays = {b["id"]: b for b in device(name)["views"]["rear"]["components"]["bays"]}
    assert sorted(bays) == ["fan-1", "fan-2", "psu-1", "psu-2"]
    psus = sorted(f"cisco/{n}@1" for n in PSU.values())
    fans = sorted(f"cisco/{n}@1" for n in FAN[name].values())
    for b in ("psu-1", "psu-2"):
        assert sorted(bays[b]["accepts"]) == psus
    for b in ("fan-1", "fan-2"):
        assert sorted(bays[b]["accepts"]) == fans


@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_each_configuration_seats_matching_parts_with_matching_airflow(name):
    d = device(name)
    cfgs = d["configurations"]
    assert sorted(cfgs) == ["ac-port-side-exhaust", "ac-port-side-intake",
                            "dc-port-side-exhaust", "dc-port-side-intake"]
    bays = {b["id"]: b for b in d["views"]["rear"]["components"]["bays"]}
    seen = set()
    for cname, cfg in cfgs.items():
        assert cfg["kind"] == ("base" if cfg.get("default") else "example")
        assert not cfg.get("part-numbers"), cname
        psu, fan = PSU[(cfg["power"], cfg["airflow"])], FAN[name][cfg["airflow"]]
        seated = {}
        for bay in bays:
            seated[bay] = ref_name((cfg.get("bays") or {}).get(bay) or bays[bay]["default"])
        assert seated == {"psu-1": psu, "psu-2": psu, "fan-1": fan, "fan-2": fan}, cname
        for part in (psu, fan):
            assert contract(part)["attrs"]["airflow"] == cfg["airflow"], (cname, part)
        assert contract(psu)["attrs"]["input"] == cfg["power"]
        seen.add((cfg["power"], cfg["airflow"]))
    assert seen == set(PSU)
    assert sum(1 for c in cfgs.values() if c.get("default")) == 1


def test_the_supplies_are_the_guides_ratings():
    assert contract("nc5k-pac-650w-fr")["attrs"]["power-output-w"] == 650
    assert contract("nc5k-pac-650w-bk")["attrs"]["power-output-w"] == 650
    assert contract("nc5k-pdc-930w-fr")["attrs"]["power-output-w"] == 930
    assert contract("nc5k-pdc-930w-bk")["attrs"]["power-output-w"] == 930


@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_sale_status_is_not_guessed(name):
    d = device(name)
    assert "eol" not in ((d.get("attrs") or {}).get("lifecycle") or {})
    assert any(g.get("what") == "sale-status" for g in d["gaps"])


@pytest.mark.parametrize("name", sorted(ENVELOPE))
def test_dcim_device_type_is_one_per_chassis_at_the_guides_u_height(name):
    # the builds are examples with no SKU, so no build-named device type is exported
    model = device(name)["model"]
    files = sorted((LIB / "exports/netbox/device-types/Cisco").glob(f"{model}*.yaml"))
    types = [yaml.safe_load(f.read_text()) for f in files]
    assert [t["model"] for t in types] == [model], [f.name for f in files]
    assert types[0]["u_height"] == ENVELOPE[name]["ru"]
