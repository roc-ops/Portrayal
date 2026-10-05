"""Every coax medium, AC cord end and USB plug medium has a label in the kit.

kit/shell.js labels a port row from its data-media through the `MEDIA` table
and falls back to upper-casing the key. For coax that fallback reads
`COAX-DIN-1-0-2-3` on a row that should say `1.0/2.3`, so each coax medium a
part or device states needs its own entry. The labels match
dcim_export.PART_RF's.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SHELL = ROOT / "kit" / "shell.js"
LIBRARY = ROOT / "library"

EXPECTED = {
    "coax-sma": "SMA",
    "coax-smb": "SMB",
    "coax-bnc": "BNC",
    "coax-din-1-0-2-3": "1.0/2.3",
    "coax-f": "F",
    "coax-mcx": "MCX",
}


def media_table():
    src = SHELL.read_text()
    m = re.search(r"const MEDIA = \{(.*?)\};", src, re.S)
    assert m, "kit/shell.js no longer has a `const MEDIA = {...}` table"
    return dict(re.findall(r"'([^']+)':\s*'([^']*)'", m.group(1)))


def stated_coax_media():
    got = set()
    for sub in ("components", "devices"):
        for f in (LIBRARY / sub).rglob("*.yaml"):
            got.update(re.findall(r"media:\s*['\"]?(coax-[a-z0-9-]+)",
                                  f.read_text()))
    return got


def test_each_coax_label_reads_as_its_connector():
    table = media_table()
    for key, label in EXPECTED.items():
        assert table.get(key) == label, (
            f"kit MEDIA[{key!r}] is {table.get(key)!r}, expected {label!r}")


def test_every_stated_coax_medium_has_a_label():
    stated = stated_coax_media()
    assert len(stated) >= 6, f"found only {sorted(stated)}; the scan measured nothing"
    missing = sorted(stated - set(media_table()))
    assert not missing, (
        f"library states {missing} but kit/shell.js MEDIA has no label; the "
        f"row would read the upper-cased key")


# AC cord ends (#785). A cord end states its connector as its media (`c13`,
# `c19`, `saf-d-grid`); the inlets themselves state `ac`. The fallback would
# read SAF-D-GRID on a row that should say Saf-D-Grid.
AC_CORD_ENDS = {
    "generic/c13-plug": ("c13", "C13"),
    "generic/c19-plug": ("c19", "C19"),
    "generic/saf-d-grid-plug": ("saf-d-grid", "Saf-D-Grid"),
}


def test_each_ac_cord_end_medium_has_its_label():
    table = media_table()
    for part, (key, label) in AC_CORD_ENDS.items():
        text = (LIBRARY / "components" / part / "v1" / "contract.yaml").read_text()
        stated = re.search(r"^attrs:.*\bmedia:\s*([a-z0-9-]+)", text, re.M)
        assert stated and stated.group(1) == key, (part, stated and stated.group(1))
        assert table.get(key) == label, (
            f"kit MEDIA[{key!r}] is {table.get(key)!r}, expected {label!r}")
    assert table.get("ac") == "AC"


# USB cable plugs (#786). A plug states the key its receptacle states
# (`usb-a`, `micro-usb-b`, `usb-c`), and the kit labelled all three before
# there was a plug. The fallback would read MICRO-USB-B on a row that should
# say micro-USB B.
USB_PLUGS = {
    "generic/usb-a-plug": ("std/usb-a", "usb-a", "USB-A"),
    "generic/micro-usb-b-plug": ("std/micro-usb", "micro-usb-b", "micro-USB B"),
    "generic/usb-c-plug": ("std/usb-c", "usb-c", "USB-C"),
}


def test_each_usb_plug_medium_is_its_receptacles_and_has_its_label():
    table = media_table()
    for part, (jack, key, label) in USB_PLUGS.items():
        for ref in (part, jack):
            text = (LIBRARY / "components" / ref / "v1" / "contract.yaml").read_text()
            stated = re.search(r"^attrs:.*\bmedia:\s*([a-z0-9-]+)", text, re.M)
            assert stated and stated.group(1) == key, (ref, stated and stated.group(1))
        assert table.get(key) == label, (
            f"kit MEDIA[{key!r}] is {table.get(key)!r}, expected {label!r}")
