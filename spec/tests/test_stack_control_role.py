"""`stack-control`: the group role of a stacking pair's control and sync jacks (#1042).

A consumer that picks the ports able to carry service traffic by
`data-group-role="traffic"` counted the CSR310's STACK-CTRL as a 1G service port.
It is a control signal from the CPU. STACK-SYNC sat under `management` beside the
BITS and PPS/ToD jacks. Both now sit in one group with a role of their own, and
the two stacking QSFP28 cages stay `traffic`: they carry traffic unless the unit
is stacked.

What these hold:

  - the schemas accept the role on a device group and a component group;
  - the built CSR310 front marks the two jacks with it and the cages `traffic`;
  - the export still cables the control jack and still lists nothing for the
    sync jack, and no port with the role is typed as a traffic port.
"""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import libdata
from portrayal import dcim_export as dx
from portrayal.manifest import view_parts

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
RENDER = SPEC / "tools/portrayal/render.py"
ROLE = "stack-control"


def _schema_roles():
    dev = json.loads((SPEC / "schemas/device.schema.json").read_text())
    comp = json.loads((SPEC / "schemas/component.schema.json").read_text())
    return (dev["properties"]["groups"]["additionalProperties"]["properties"]["role"],
            comp["$defs"]["group"]["properties"]["role"])


@pytest.mark.parametrize("which", [0, 1], ids=["device", "component"])
def test_the_schema_accepts_the_role_on_a_group(which):
    role = _schema_roles()[which]
    assert ROLE in role["enum"]
    assert f"`{ROLE}`" in role["description"], "the role is in the enum and nowhere explained"


@pytest.fixture(scope="module")
def front(tmp_path_factory):
    out = tmp_path_factory.mktemp("stack-control")
    manifest = LIB / "devices/edgecore/csr310/device.yaml"
    r = subprocess.run([sys.executable, str(RENDER), str(manifest), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    root = ET.parse(sorted(out.glob("*.front.svg"))[0]).getroot()
    return {e.get("data-path"): e for e in root.iter() if e.get("data-class") == "port"}


def test_the_csr310_marks_its_stack_jacks_and_leaves_the_cages_traffic(front):
    got = {p: (front[p].get("data-group"), front[p].get("data-group-role"))
           for p in ("stack-ctrl", "stack-sync", "stack-0", "stack-1")}
    assert got["stack-ctrl"][1] == ROLE, got
    assert got["stack-sync"][1] == ROLE, got
    assert got["stack-ctrl"][0] == got["stack-sync"][0], got
    assert got["stack-0"] == got["stack-1"] == ("stacking", "traffic"), got
    # the group name is not the role's, so a consumer can tell which it is reading
    assert got["stack-ctrl"][0] != ROLE, got


def _role_ports():
    for slug, doc in libdata.devices():
        groups = doc.get("groups") or {}
        for view in (doc.get("views") or {}).values():
            for p in view_parts(view)["placements"]:
                g = groups.get(p.get("group")) or {}
                if g.get("role") == ROLE:
                    yield slug, p, {**(g.get("attrs") or {}), **(p.get("attrs") or {})}


def test_no_port_with_the_role_is_exported_as_a_traffic_port():
    ports = list(_role_ports())
    assert ports, f"no group in the library has role {ROLE!r}"
    assert ROLE in dx.PORT_ROLES, "the role is not classified by the export"
    for slug, p, a in ports:
        assert not dx.mgmt_only(a, ROLE), (slug, p["id"], "a stack link is not how you reach the box")
        # a bare jack that states no speed is not rescued by the role, which is how
        # the sync jack stays out of the interface list; `traffic` would not type it
        # either, but it would have typed a jack that states a speed as a service port
        if not a.get("speed"):
            t, _, _ = dx.device_port_type(p, a, ROLE)
            assert t is None, (slug, p["id"], t)


def test_the_csr310_exports_the_control_jack_and_not_the_sync_jack():
    by_id = {p["id"]: (p, a) for slug, p, a in _role_ports() if slug == "edgecore/csr310"}
    assert set(by_id) == {"stack-ctrl", "stack-sync"}, sorted(by_id)
    ctrl = dx.device_port_type(*by_id["stack-ctrl"], ROLE)
    sync = dx.device_port_type(*by_id["stack-sync"], ROLE)
    assert ctrl == ("1000base-t", None, None), ctrl
    assert sync[0] is None, sync
