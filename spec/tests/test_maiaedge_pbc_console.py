"""The MaiaEdge PBC-2000 records the console rate its data sheet states.

The data sheet's technical-specification table (page 3) lists the console port
as "RJ45 115.2 kbps". The device's provenance quotes the row; what a DCIM reads
is the exported device type, so the rate is checked there, as the `management`
attribute the library's other devices file their console under.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "library" / "exports"


def test_the_console_rate_reaches_both_exported_device_types():
    for dcim in ("netbox", "nautobot"):
        text = (EXPORTS / dcim / "device-types" / "MaiaEdge" / "PBC-2000.yaml").read_text()
        assert "management.console: RJ45 serial, 115.2 kbps" in text, dcim
