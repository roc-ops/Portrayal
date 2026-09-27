"""Every coax medium the library states has a label in the kit.

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
