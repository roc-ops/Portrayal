"""SFP cage -> generic/sfp-rj45 -> generic/rj45-plug -> common/rj45-boot: the
spec-B chain seats in the copper SFP's jack (docs/pluggables-heads-design.md
section 4.7 and section 6 item 3)."""
import pytest

from test_nested_occupants import (by_path, device_point, fitted_copy, own_mate,
                                   presented_interface, render, _contract)

CHAIN = {"front-6/xg0": "generic/sfp-rj45@1",
         "front-6/xg0-occupant": "generic/rj45-plug@1",
         "front-6/xg0-occupant-occupant": "common/rj45-boot@1"}


def test_the_plug_seats_on_the_copper_sfps_jack(tmp_path):
    dev = fitted_copy(tmp_path, "c100g", "base", {"front-6": "casa/smm-300gm@1"}, CHAIN)
    root, parents = render(dev, tmp_path / "o", "c100g", "base")
    sfp = by_path(root, "front-6/module/xg0-occupant")
    plug = by_path(root, "front-6/module/xg0-occupant-occupant")
    assert sfp.get("data-ref", "").startswith("generic/sfp-rj45@1")
    iface, hm, lift = presented_interface(_contract("generic/sfp-rj45@1"), _contract)
    assert iface == "rj45" and lift == pytest.approx(22.70)
    hx, hy = device_point(parents, sfp, hm)
    ox, oy = device_point(parents, plug, own_mate(plug))
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6
    assert float(plug.get("data-z-lift") or 0) == pytest.approx(22.70)
    boot = by_path(root, "front-6/module/xg0-occupant-occupant-occupant")
    assert boot is not None
