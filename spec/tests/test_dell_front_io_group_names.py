"""The front I/O and lamp groups of six Dell servers are named for what they hold.

A group called `ports` or `leds` names nothing. On the R740xd the front I/O group is
`local-access` and the lamp under the iDRAC Direct port is `port-leds`; these six servers
carry the same front panel and take the same names.

Each device declares `local-access` and `port-leds` and neither old name, and the compiled
front face carries those two names in `data-group` and neither old one. Without the rename
the device files declare `ports` and `leds`, so the declaration tests fail, and the built
face still carries them, so the face tests fail too. The face tests read the build, so run
./build.sh first.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "devices"
DIST = ROOT / "library" / "dist"

DEVICES = ("dell/r660", "dell/r660xs", "dell/r6615", "dell/r6625", "dell/r760", "dell/r960")


@pytest.mark.parametrize("key", DEVICES)
def test_the_device_declares_the_new_group_names_and_not_the_old(key):
    with open(LIB / key / "device.yaml") as fh:
        groups = set(yaml.safe_load(fh)["groups"])
    assert {"local-access", "port-leds"} <= groups, f"{key} declares {sorted(groups)}"
    assert not {"ports", "leds"} & groups, f"{key} still declares a vague group"


@pytest.mark.parametrize("key", DEVICES)
def test_the_compiled_front_face_carries_the_new_group_names_and_not_the_old(key):
    path = DIST / f"{key.split('/')[1]}.front.svg"
    assert path.exists(), f"library/dist has no {path.name}: these read the build, so run ./build.sh first"
    names = set(re.findall(r'data-group="([^"]*)"', path.read_text()))
    assert {"local-access", "port-leds"} <= names, f"{key} face carries {sorted(names)}"
    assert not {"ports", "leds"} & names, f"{key} face still carries a vague group"
