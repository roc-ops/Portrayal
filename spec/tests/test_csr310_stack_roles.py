"""The CSR310's stack control and stack sync jacks are not traffic ports.

A consumer that picks out the ports able to carry service traffic by `data-group-role="traffic"` counted the
STACK-CTRL RJ-45 as a 1G service port, and it is not one: the datasheet lists it as a control signal from the CPU,
apart from the QSFP28 data path. The group `role` vocabulary gains `stack-control` for the control and sync links
between the units of a stack, never user traffic, and:

  - `stack-ctrl` and `stack-sync` take it, and neither is `traffic` or `management`;
  - the two stacking QSFP28 carry the stack's data path and stay `traffic`;
  - the schema accepts the new value, and the exporter classes it as a port role.

These read the expanded device and the schema and render nothing.
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library/devices/edgecore/csr310/device.yaml"
SCHEMA = ROOT / "spec/schemas/device.schema.json"


def device():
    return yaml.safe_load(DEVICE.read_text())


def group_role_of(data, part_id):
    """The role of the group the placement `part_id` joins, on any face."""
    for view in data["views"].values():
        comps = view.get("components") or {}
        for item in (comps.get("placements") or []) + (comps.get("bays") or []):
            if item.get("id") == part_id:
                return item["group"], data["groups"][item["group"]]["role"]
    raise AssertionError(f"no placement {part_id!r}")


def test_stack_control_and_stack_sync_take_the_stack_control_role():
    data = device()
    for part in ("stack-ctrl", "stack-sync"):
        group, role = group_role_of(data, part)
        assert role == "stack-control", f"{part} is in {group!r}, whose role is {role!r}"
        assert role not in ("traffic", "management")


def test_the_stacking_qsfp28_stay_traffic():
    data = device()
    for part in ("stack-0", "stack-1"):
        assert group_role_of(data, part) == ("stacking", "traffic")


def test_the_schema_accepts_stack_control_as_a_group_role():
    schema = json.loads(SCHEMA.read_text())
    enum = schema["properties"]["groups"]["additionalProperties"]["properties"]["role"]["enum"]
    assert "stack-control" in enum
    assert {"traffic", "fabric", "management", "service", "indicator", "furniture"} <= set(enum)


def test_the_exporter_classes_stack_control_as_a_port_role():
    from portrayal import dcim_export as dx
    assert "stack-control" in dx.PORT_ROLES
