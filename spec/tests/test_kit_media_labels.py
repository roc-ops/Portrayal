"""Every coax medium, AC cord end, USB plug, D-sub plug and terminal plug medium has a label in the kit.

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


# D-sub and VGA cable plugs (#787). A plug states the key its core states
# (`db9`, `vga`, `da15`, `db25`); none of the four was in the table, and each
# is given the label the upper-casing fallback already read, so the row a
# plug adds reads as the connector row beside it always has.
DSUB_PLUGS = {
    "generic/db9-plug": ("std/db9", "db9", "DB9"),
    "generic/hd15-plug": ("std/vga", "vga", "VGA"),
    "generic/da15-plug": ("std/da15", "da15", "DA15"),
    "generic/db25-plug": ("std/db25", "db25", "DB25"),
}


def test_each_dsub_plug_medium_is_its_cores_and_has_its_label():
    table = media_table()
    for part, (core, key, label) in DSUB_PLUGS.items():
        for ref in (part, core):
            text = (LIBRARY / "components" / ref / "v1" / "contract.yaml").read_text()
            stated = re.search(r"^attrs:.*\bmedia:\s*([a-z0-9-]+)", text, re.M)
            assert stated and stated.group(1) == key, (ref, stated and stated.group(1))
        assert table.get(key) == label == key.upper(), (
            f"kit MEDIA[{key!r}] is {table.get(key)!r}, expected {label!r}")


# Terminal plugs (#789). All three state `terminal-block`, the connector word
# the two-position header states. The two flanged and six-position headers
# state `dc-terminal`, which a `class: port` plug cannot: lint L62 reads a
# port part's media as a connector word, and `dc` as one flags every `dc-in`
# placement id. Neither key was in the table; the fallback read
# TERMINAL-BLOCK and DC-TERMINAL.
TERMINAL_PLUGS = {
    "generic/terminal-508-2-plug": ("common/terminal-header-508-2", "terminal-block"),
    "generic/terminal-508-5-plug": ("common/terminal-header-508-5f", "dc-terminal"),
    "generic/terminal-508-6-plug": ("common/dc-terminal-header-6", "dc-terminal"),
}


def test_each_terminal_plug_and_header_medium_has_its_label():
    table = media_table()
    for part, (header, header_key) in TERMINAL_PLUGS.items():
        for ref, key in ((part, "terminal-block"), (header, header_key)):
            text = (LIBRARY / "components" / ref / "v1" / "contract.yaml").read_text()
            stated = re.search(r"^attrs:.*\bmedia:\s*([a-z0-9-]+)", text, re.M)
            assert stated and stated.group(1) == key, (ref, stated and stated.group(1))
    assert table.get("terminal-block") == "terminal block"
    assert table.get("dc-terminal") == "DC terminal"


def test_the_dc_barrel_plug_medium_has_its_label():
    """generic/dc-barrel-plug@1 states `barrel` (#789): `dc-barrel` would make
    `dc` a connector word for lint L62. The fallback would read BARREL."""
    text = (LIBRARY / "components/generic/dc-barrel-plug/v1/contract.yaml").read_text()
    stated = re.search(r"^attrs:.*\bmedia:\s*([a-z0-9-]+)", text, re.M)
    assert stated and stated.group(1) == "barrel"
    assert media_table().get("barrel") == "DC barrel"


def test_the_ring_lug_medium_has_its_label():
    """generic/ring-lug@1 states `ring-lug` (#789); the fallback would read
    RING-LUG."""
    text = (LIBRARY / "components/generic/ring-lug/v1/contract.yaml").read_text()
    stated = re.search(r"^attrs:.*\bmedia:\s*([a-z0-9-]+)", text, re.M)
    assert stated and stated.group(1) == "ring-lug"
    assert media_table().get("ring-lug") == "ring lug"
