"""A console server's serial lines export as console server ports.

A console port is the box's own management console (`role: console`). A console
server's RJ45 serial lines are the other end of one, and a device type has a
separate list for them, `console-server-ports`. Only a placement that says
`role: console-server` over `media: rj45-serial` is one: the same jack is a
PDU's configuration port or a routing engine's serial line elsewhere.
"""
import pytest

from portrayal import dcim_export as dx


def _dev(placements):
    return {"kind": "device", "name": "d", "model": "D", "manufacturer": "M",
            "version": "1.0.0",
            "chassis": {"width": 100, "height": 40, "depth": 30},
            "groups": {"serial": {"term": "Port"}},
            "views": {"front": {"size": {"w": 100, "h": 40},
                                "components": {"placements": placements}}}}


def _jack(pid, **attrs):
    return {"id": pid, "ref": "std/rj45@2", "at": [0, 0], "group": "serial",
            "attrs": {"media": "rj45-serial", **attrs}}


def _build(placements):
    dev = _dev(placements)
    return dx.build(dev, "default", {}, None)


def test_a_console_server_placement_is_a_console_server_port():
    out = _build([_jack("1", role="console-server"), _jack("2", role="console-server")])
    assert out["console-server-ports"] == [{"name": "1", "type": "rj-45"},
                                           {"name": "2", "type": "rj-45"}]
    assert "console-ports" not in out
    assert "interfaces" not in out


def test_a_console_server_port_is_not_also_an_interface():
    out = _build([_jack("1", role="console-server")])
    assert not [i for i in out.get("interfaces") or [] if i["name"] == "1"]


def test_a_console_placement_stays_a_console_port():
    out = _build([_jack("con", role="console")])
    assert out["console-ports"] == [{"name": "Console", "type": "rj-45"}]
    assert "console-server-ports" not in out


def test_a_serial_jack_with_no_role_is_not_a_console_server_port():
    out = _build([_jack("lx"), _jack("con", role="console")])
    assert "console-server-ports" not in out


def test_the_infrahub_export_names_a_console_server_port_it_leaves_out():
    from portrayal_dev import infrahub_export as ix
    assert ("console-server-ports", "console server port") in ix.UNHELD_PORTS


@pytest.mark.parametrize("media", ["rj45", "usb-a", None])
def test_the_role_needs_the_serial_media(media):
    pl = _jack("1", role="console-server")
    if media is None:
        del pl["attrs"]["media"]
    else:
        pl["attrs"]["media"] = media
    assert dx.device_console_server_row(pl, pl["attrs"]) is None
