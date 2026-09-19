"""Every fibre connector in the library states a capacity and its confidence.

Plan 1's optical rules read `optical.positions` off whatever a module composes,
and a connector missing it silently drops out of every coverage check - L80
iterates the parts it can find capacities for, so an absent capacity is not an
error, it is an omission that makes the rule quieter. This catches that.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"

FIBRE_CONNECTORS = [
    "common/lc-duplex-adapter/v3", "common/lc-duplex-v-adapter/v1",
    "common/mpo-adapter/v1", "common/mpo24-adapter/v1",
    "common/sc-duplex-adapter/v1",
    "common/st-simplex-adapter/v1", "common/fc-simplex-adapter/v1",
    "common/lsh-simplex-adapter/v1", "common/mdc-adapter/v1",
    "common/fibre-splice/v1",
    # generic/lc-plug@1 (pluggables B2, Task 4): the cable-end LC plug, not a
    # panel adapter - simplex, `optical.positions: 1`.
    "generic/lc-plug/v1",
]


def load(rel):
    p = LIB / rel / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def test_every_fibre_connector_declares_its_capacity():
    missing = []
    for rel in FIBRE_CONNECTORS:
        c = load(rel)
        if c is None:
            missing.append(f"{rel}: not built")
        elif not (c.get("optical") or {}).get("positions"):
            missing.append(f"{rel}: no optical.positions")
    assert not missing, (
        "a connector with no declared capacity drops out of every optical "
        "coverage check without erroring:\n  " + "\n  ".join(missing))


def test_the_sweep_covers_what_the_library_actually_has():
    """Guard against this list going stale while the library grows.

    Keyed on `attrs.media == "fiber"` and `class == "port"` - a component
    carrying fibres, not just naming fibre in some unrelated attrs field -
    rather than on whether it declares `optical.positions`: a new connector
    shipped with no capacity at all would otherwise satisfy this loop by
    omission and slip past silently, which is exactly the gap
    `test_every_fibre_connector_declares_its_capacity` cannot see either,
    since it only walks the hard-coded list above. `std/lc-bore/v3` and
    `std/mpo/v1` are excluded because they set `relief.cavity`: that is what
    makes a component a hole cut in a face rather than a part that carries
    fibres, so they are apertures, not connectors, and the exclusion is keyed
    on that structural fact rather than an allowlist - a future `std/sc`
    aperture is then exempt automatically, and a future
    `common/e2000-adapter` connector is not.
    """
    found = []
    for f in sorted(LIB.rglob("contract.yaml")):
        d = yaml.safe_load(f.read_text()) or {}
        if (d.get("attrs") or {}).get("media") != "fiber":
            continue
        if d.get("class") != "port":
            continue
        if (d.get("relief") or {}).get("cavity"):
            continue
        found.append("/".join(f.parts[-4:-1]))
    unlisted = sorted(set(found) - set(FIBRE_CONNECTORS))
    assert not unlisted, (
        "these are fibre connectors (class: port, attrs.media: fiber, no "
        "relief.cavity) and are not in FIBRE_CONNECTORS, so nothing above "
        f"sweeps them: {unlisted}")
