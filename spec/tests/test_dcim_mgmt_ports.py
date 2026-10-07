"""Every management-cluster port reaches a DCIM, or a register says why not (#384).

The DCS511's datasheet lists six "Management Ports on Port Side" and its model
carries all six. Its export carried four: the RJ45 console and three Ethernet
or SFP management interfaces (when #384 was filed it carried two; adeedf74
restored `mgmt-eth` and `mgmt-cpu`, the `role: mgmt` skip). The micro-USB console was dropped because the
device path knew RJ45, USB-A and USB-C consoles and not micro-USB, and
`std/micro-usb` sat in NOT_A_DCIM_PORT as an iDRAC Direct port - a register
keyed on the PART, which cannot see a part that is a console on 31 devices and
a BMC link on two servers. The USB storage port is dropped on purpose, by the
line NOT_A_DCIM_PORT's USB block already draws.

So this census is PER PLACEMENT and it asks `build` itself, through its `trace`,
rather than a mirror of `build` - test_silent_drops' mirror did not know the
console exit, and that is how `std/usb-c` sat in NOT_A_DCIM_PORT while three
devices exported a USB-C console.
"""
import collections
import functools
import pathlib

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import libwalk
from portrayal.manifest import load_yaml, view_parts

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


@functools.lru_cache(maxsize=1)
def _classes():
    out = {}
    for cf in libwalk.iter_components([LIB]):
        d = yaml.safe_load(cf.read_text()) or {}
        out[f"{cf.parent.parent.parent.name}/{cf.parent.parent.name}"] = d.get("class")
    return out


def _is_mgmt(a, group_role):
    return a.get("role") in dx.MGMT_EXPORTED_ROLES or group_role == "management"


@functools.lru_cache(maxsize=1)
def _census():
    """(heard, dropped, devices): every port-class management placement, per
    configuration, and whether `build` put it in the document.

    dropped maps (part, role) -> the "vendor/model:id" placements it covers.
    """
    cls = _classes()
    heard, devices = 0, set()
    dropped = collections.defaultdict(set)
    for p in sorted((LIB / "devices").glob("*/*/device.yaml")):
        dev = load_yaml(p) or {}
        groups = dev.get("groups") or {}
        where = f"{p.parent.parent.name}/{p.parent.name}"
        for cfg_name, cfg in (dev.get("configurations") or {"default": {}}).items():
            trace = set()
            dx.build(dev, cfg_name, cfg, None, trace=trace)
            for view in dx.views_for(dev, cfg_name):
                for pl in dx.scoped(view_parts(view)["placements"], cfg_name):
                    ref = pl["ref"].split("@")[0]
                    if cls.get(ref) != "port":
                        continue
                    g = groups.get(pl.get("group")) or {}
                    a = {**(g.get("attrs") or {}), **(pl.get("attrs") or {})}
                    if not _is_mgmt(a, g.get("role")):
                        continue
                    devices.add(where)
                    if pl.get("id") in trace:
                        heard += 1
                    else:
                        dropped[(ref, a.get("role"))].add(f"{where}:{pl.get('id')}")
    return heard, dropped, devices


def test_no_management_port_is_silently_dropped():
    """THE GUARD. A management-cluster port that exports nothing is either a
    part NOT_A_DCIM_PORT already explains, or a (part, role) the management
    register explains. Anything else is the #384 shape arriving again."""
    _heard, dropped, _devices = _census()
    unexplained = {k: v for k, v in dropped.items()
                   if k[0] not in dx.NOT_A_DCIM_PORT and k not in dx.MGMT_NOT_A_DCIM_PORT}
    assert not unexplained, "management ports that export nothing, unexplained:\n" + "\n".join(
        f"  {k}: {sorted(v)[:4]}" for k, v in sorted(unexplained.items(), key=str))


def test_a_mgmt_or_console_port_is_never_exempt():
    """The ports a DCIM exists to know about may not be registered away: a
    management jack, a management SFP, a console or an AUX line that does not
    export is a defect to fix, not an entry to write."""
    bad = [k for k in dx.MGMT_NOT_A_DCIM_PORT if k[1] in dx.MGMT_EXPORTED_ROLES]
    assert not bad, bad
    _heard, dropped, _devices = _census()
    leaked = {k: sorted(v)[:4] for k, v in dropped.items() if k[1] in dx.MGMT_EXPORTED_ROLES}
    assert not leaked, f"role mgmt/console/aux placements that export nothing: {leaked}"


def test_the_management_register_carries_no_stale_entries():
    _heard, dropped, _devices = _census()
    stale = sorted((k for k in dx.MGMT_NOT_A_DCIM_PORT if k not in dropped), key=str)
    assert not stale, f"MGMT_NOT_A_DCIM_PORT entries that match no dropped placement: {stale}"
    shadowed = sorted((k for k in dx.MGMT_NOT_A_DCIM_PORT if k[0] in dx.NOT_A_DCIM_PORT), key=str)
    assert not shadowed, f"already explained by NOT_A_DCIM_PORT: {shadowed}"


def test_every_management_register_entry_gives_a_reason():
    thin = {k: why for k, why in dx.MGMT_NOT_A_DCIM_PORT.items() if len(why) < 40}
    assert not thin, thin


def test_the_census_is_not_vacuous():
    """An empty walk passes as quietly as the bug. Measured on #384: 1,795
    management placements heard across every configuration, on 154 devices, and
    168 dropped placements each explained by a register."""
    heard, dropped, devices = _census()
    assert heard >= 1500, f"only {heard} management placements reached an export"
    assert len(devices) >= 120, f"only {len(devices)} devices have a management cluster"
    assert sum(len(v) for v in dropped.values()) >= 100, "the dropped side collapsed"


# --- each kind of management port, on the device the issue names -------------

@functools.lru_cache(maxsize=1)
def _dcs511():
    dev = load_yaml(LIB / "devices/edgecore/dcs511/device.yaml")
    trace = set()
    return dx.build(dev, "ac-f2b", dev["configurations"]["ac-f2b"], None, trace=trace), trace


def test_an_ethernet_management_jack_is_a_mgmt_only_interface():
    doc, _ = _dcs511()
    rows = {i["name"]: i for i in doc["interfaces"]}
    assert rows["mgmt-eth"] == {"name": "mgmt-eth", "type": "1000base-t", "mgmt_only": True}


@pytest.mark.parametrize("pid,kind", [("mgmt-asic", "10gbase-x-sfpp"),
                                      ("mgmt-cpu", "1000base-x-sfp")])
def test_an_sfp_management_port_is_a_mgmt_only_interface(pid, kind):
    doc, _ = _dcs511()
    rows = {i["name"]: i for i in doc["interfaces"]}
    assert rows[pid]["type"] == kind and rows[pid]["mgmt_only"] is True, rows[pid]


def test_two_consoles_the_panel_labels_apart_export_apart():
    """"RJ45 Console" and "Micro-USB Console" are printed over two jacks, and
    both libraries key console ports by name."""
    doc, _ = _dcs511()
    assert doc["console-ports"] == [{"name": "Console", "type": "rj-45"},
                                    {"name": "Console (Micro-USB)", "type": "usb-micro-b"}]


def test_a_usb_storage_port_stays_out():
    doc, trace = _dcs511()
    assert "usb-a" not in trace
    assert ("std/usb-a", "storage") in dx.MGMT_NOT_A_DCIM_PORT


@pytest.mark.parametrize("target", dx.TARGETS)
def test_the_published_dcs511_carries_both_consoles(target):
    f = LIB / "exports" / target / "device-types" / "Edgecore" / "AS9737-32DB-O-AC-F.yaml"
    d = yaml.safe_load(f.read_text())
    assert [(c["name"], c["type"]) for c in d["console-ports"]] == [
        ("Console", "rj-45"), ("Console (Micro-USB)", "usb-micro-b")]
    mgmt = [i["name"] for i in d["interfaces"] if i.get("mgmt_only")]
    assert sorted(mgmt) == ["mgmt-asic", "mgmt-cpu", "mgmt-eth"]


# --- device_console_row, one placement at a time ------------------------------

@pytest.mark.parametrize("pl,a,row", [
    ({"ref": "std/rj45@2", "id": "console"}, {"media": "rj45-serial", "role": "console"},
     {"name": "Console", "type": "rj-45"}),
    ({"ref": "std/usb-c@1", "id": "usb-c"}, {"media": "usb-c", "role": "console"},
     {"name": "Console (USB-C)", "type": "usb-c"}),
    ({"ref": "std/usb-a@1", "id": "usb"}, {"media": "usb-a", "role": "console"},
     {"name": "Console (USB-A)", "type": "usb-a"}),
    # a micro-USB console says so by role (DCS511), by id (S9701-82DC) or by
    # function (MX150's `con`)
    ({"ref": "std/micro-usb@1", "id": "console-usb"}, {"media": "micro-usb-b", "role": "console"},
     {"name": "Console (Micro-USB)", "type": "usb-micro-b"}),
    ({"ref": "std/micro-usb@1", "id": "console-usb"}, {},
     {"name": "Console (Micro-USB)", "type": "usb-micro-b"}),
    ({"ref": "std/micro-usb@1", "id": "con"}, {"function": "console"},
     {"name": "Console (Micro-USB)", "type": "usb-micro-b"}),
    # an AUX serial line is a console port, as route_part files a card's
    ({"ref": "std/rj45-ganged@2", "id": "aux"}, {"media": "rj45-serial", "role": "aux"},
     {"name": "AUX", "type": "rj-45"}),
    # and these are not consoles
    ({"ref": "std/micro-usb@1", "id": "idrac-direct"}, {}, None),
    ({"ref": "std/micro-usb@1", "id": "usb"}, {"media": "micro-usb", "role": "storage"}, None),
    ({"ref": "std/usb-a@1", "id": "usb-a"}, {"media": "usb-a", "role": "storage"}, None),
    ({"ref": "std/usb-a@1", "id": "usb"}, {"function": "USB service port"}, None),
])
def test_device_console_row(pl, a, row):
    assert dx.device_console_row(pl, a) == row


def test_usb_micro_b_is_a_console_type_in_both_targets():
    """Checked by hand against ConsolePortTypeChoices at the SHAs the exporter
    cites (netbox 64ce9e2d, nautobot 3edb1fca); this pins the spelling."""
    assert dx.device_console_row({"ref": "std/micro-usb@1", "id": "console"}, {})["type"] \
        == "usb-micro-b"
