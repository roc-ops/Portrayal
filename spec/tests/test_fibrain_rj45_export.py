"""The Fibrain RJ45 modules export as Ethernet interfaces (#1041).

A module's jack used to compose the bare `std/rj45-ganged@2`, which the DCIM exporter
types as a console port. The modules compose `common/rj45-ganged-eth-plain@1`, the
family's Ethernet cell without lamps, so the same jack is an interface.

These tests read the GENERATED export files, not the exporter's tables: a table that says
interface proves nothing about the file a NetBox or Nautobot user imports.
"""
import json
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
MODULES = ["xe100", "xe110", "xe200", "xe210", "xq100", "xq110",
           "xq200", "xq210", "xr100", "xr110", "xr200", "xr210"]
TARGETS = ("netbox", "nautobot")
# Nautobot names a module's interface by its parent module as well
JACK = {"netbox": "{module}/jack", "nautobot": "{module.parent}/{module}/jack"}


def export(target, model):
    p = LIB / "exports" / target / "module-types" / "Fibrain" / f"{model}.yaml"
    assert p.is_file(), p
    return yaml.safe_load(p.read_text())


EXAMPLES = ("copper-mixed", "xpu00-copper", "xps00-copper")


def seats(example):
    d = yaml.safe_load((LIB / "devices/fibrain/xpu/device.yaml").read_text())
    return [v for k, v in d["configurations"][example]["bays"].items() if "/pos-" in k]


@pytest.mark.parametrize("example", EXAMPLES)
def test_a_copper_example_seats_modules_whose_exports_are_all_in_the_set(example):
    seated = seats(example)
    assert len(seated) == 48
    assert {r.split("/")[1].split("@")[0] for r in seated} <= set(MODULES)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("example", EXAMPLES)
def test_a_copper_example_lists_48_copper_interfaces_and_no_console_port(target, example):
    """An example is no device type (the exporter files only the orderable frames), so the
    48 ports of a full frame are counted through the module types its 48 seats export."""
    n = 0
    for ref in seats(example):
        doc = export(target, ref.split("/")[1].split("@")[0].upper())
        assert "console-ports" not in doc
        n += len(doc["interfaces"])
    assert n == 48


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("m", MODULES)
def test_a_module_jack_is_an_interface_in_the_export_not_a_console_port(target, m):
    doc = export(target, m.upper())
    assert doc.get("interfaces") == [{"name": JACK[target], "type": "1000base-t"}], doc
    assert "console-ports" not in doc


@pytest.mark.parametrize("target", TARGETS)
def test_every_module_seated_in_the_copper_mixed_build_exports_an_interface(target):
    d = yaml.safe_load((LIB / "devices/fibrain/xpu/device.yaml").read_text())
    seated = {v.split("/")[1].split("@")[0]
              for k, v in d["configurations"]["copper-mixed"]["bays"].items() if "/pos-" in k}
    assert len(seated) > 4
    for m in sorted(seated):
        doc = export(target, m.upper())
        assert [i["name"] for i in doc["interfaces"]] == [JACK[target]], m


def test_the_exporter_itself_types_the_module_jack_as_an_interface():
    """The same answer from the exporter as from the files, so a stale file is caught
    here and not only by preflight."""
    from portrayal import dcim_export as dx
    for m in MODULES:
        c = yaml.safe_load((LIB / f"components/fibrain/{m}/v1/contract.yaml").read_text())
        out = dx.build_module(c, "Fibrain")
        assert out["interfaces"] == [{"name": "jack", "type": "1000base-t"}], m
        assert "console-ports" not in out


def test_the_lint_baseline_holds_no_fibrain_entry():
    base = json.loads((LIB / "lint-baseline.json").read_text())
    assert [k for k in base if "fibrain" in k] == []


def test_nothing_in_the_fibrain_holders_or_the_frame_names_the_bare_rj45_cell():
    for rel in ("components/fibrain/xmu00/v1/contract.yaml", "components/fibrain/xms00/v1/contract.yaml",
                "devices/fibrain/xpu/device.yaml"):
        assert "std/rj45-ganged" not in (LIB / rel).read_text(), rel
