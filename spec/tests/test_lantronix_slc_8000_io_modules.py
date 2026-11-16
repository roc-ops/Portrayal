"""The Lantronix SLC 8000 I/O modules: the 16-port RJ45 module and the 16-port USB module.

The User Guide names the two modules by part number (Figure 3-7: FRRJ451601 and FRUSB1601), shows each face in
Figures 2-2 to 2-4 and says each carries sixteen ports. No document gives a module a size, so each takes the width and
height of the bay it seats in and says its depth is borrowed; the contracts say so. The three bays take them by the class
key the registry already holds. The chassis part numbers whose modules are fully stated are configurations.

These read the library and the registry and render nothing; they read no library/dist.
"""
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICE = LIB / "devices" / "lantronix" / "slc-8000" / "device.yaml"

RJ45 = "lantronix/frrj451601"
USB = "lantronix/frusb1601"
MODULES = {RJ45: "std/rj45-ganged@2", USB: "std/usb-a@1"}
# chassis part number -> modules in bays 1 to 3, as the maker's page names the port count and type
BUILDS = {
    "SLC80161201S": [RJ45],
    "SLC80321201S": [RJ45, RJ45],
    "SLC80481201S": [RJ45, RJ45, RJ45],
    "SLC81161201S": [USB],
}


def contract(ref):
    ns, part = ref.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / "v1" / "contract.yaml").read_text())


@pytest.fixture(scope="module")
def device():
    return yaml.safe_load(DEVICE.read_text())


@pytest.mark.parametrize("ref", MODULES)
def test_a_module_is_a_line_card_that_mates_the_bay_class(ref):
    c = contract(ref)
    assert c["kind"] == "module" and c["class"] == "line-card"
    assert c["mates"] == "slc-io-module"
    assert c["attrs"]["model"] == ref.split("/")[1].upper()


@pytest.mark.parametrize("ref", MODULES)
def test_a_module_has_the_size_of_the_bay_and_declares_it_estimated(ref, device):
    c = contract(ref)
    bay = device["views"]["rear"]["components"]["bays"][0]["size"]
    assert (c["size"]["w"], c["size"]["h"]) == (bay["w"], bay["h"])
    conf = c["size-confidence"]
    assert conf["d"] in ("borrowed", "estimated")
    assert conf["w"] != "datasheet" and conf["h"] != "datasheet"
    assert "size" in c["provenance"]


@pytest.mark.parametrize("ref,part", MODULES.items())
def test_a_module_carries_sixteen_ports_inside_its_face(ref, part):
    c = contract(ref)
    ports = [p for p in c["parts"] if p["ref"] == part]
    assert len(ports) == 16
    for p in ports:
        x, y = p["at"]
        assert 0 <= x < c["size"]["w"] and 0 <= y < c["size"]["h"]


@pytest.mark.parametrize("ref", MODULES)
def test_each_module_has_its_skin(ref):
    ns, part = ref.split("/")
    skin = LIB / "components" / ns / part / "v1" / "skins" / "default.svg"
    assert skin.is_file()
    assert contract(ref)["skins"] == ["default"]


def test_the_bays_stay_declared_and_the_default_build_stays_empty(device):
    bays = device["views"]["rear"]["components"]["bays"]
    assert [b["interface"] for b in bays] == ["slc-io-module"] * 3
    assert all(v == "" for v in device["configurations"]["base"]["bays"].values())


@pytest.mark.parametrize("number,modules", BUILDS.items())
def test_a_part_number_seats_the_modules_its_port_count_names(number, modules, device):
    # the builds carry no `part-numbers` (an example build exports no device type); each names its maker part number in its `source`
    cfgs = [c for c in device["configurations"].values() if number in c.get("source", "")]
    assert len(cfgs) == 1
    assert cfgs[0]["kind"] == "example" and "part-numbers" not in cfgs[0]
    seats = cfgs[0]["bays"]
    want = {f"io-bay-{i + 1}": f"{m}@1" for i, m in enumerate(modules)}
    want.update({f"io-bay-{i + 1}": "" for i in range(len(modules), 3)})
    assert seats == want


def test_the_bays_fill_in_order_in_every_build(device):
    for c in device["configurations"].values():
        seats = [c["bays"][f"io-bay-{i}"] for i in (1, 2, 3)]
        filled = [bool(s) for s in seats]
        assert filled == sorted(filled, reverse=True), "no empty bay before a filled one"


def test_the_gap_that_named_the_modules_now_names_what_is_left(device):
    gap = {g["what"]: g for g in device["gaps"]}["io-modules"]
    assert "FRETH1601" in gap["note"]
