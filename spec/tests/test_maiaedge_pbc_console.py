"""The MaiaEdge PBC-2000 records the console rate its data sheet states.

The data sheet's technical-specification table (page 3) lists the console port
as "RJ45 115.2 kbps". The device's provenance quotes the row; the device's
attributes are what a DCIM reads, so the rate is recorded there too, in the
`management` section the library's other devices file their console under.
"""
import pathlib

from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE = ROOT / "library" / "devices" / "maiaedge" / "pbc-2000" / "device.yaml"


def test_the_console_rate_is_an_attribute_of_the_device():
    attrs = load_yaml(DEVICE)["attrs"]
    assert attrs["management"]["console"] == "RJ45 serial, 115.2 kbps"


def test_the_console_is_still_a_serial_jack_and_not_an_interface():
    placements = load_yaml(DEVICE)["views"]["front"]["components"]["placements"]
    con = next(p for p in placements if p["id"] == "con")
    assert con["attrs"]["media"] == "rj45-serial"
    assert "speed" not in con["attrs"]
