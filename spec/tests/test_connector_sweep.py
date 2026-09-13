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
    "common/lc-duplex-adapter/v3", "common/mpo-adapter/v1",
    "common/sc-duplex-adapter/v1", "common/st-simplex-adapter/v1",
    "common/fc-simplex-adapter/v1", "common/lsh-simplex-adapter/v1",
    "common/mdc-adapter/v1",
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

    Any component whose attrs name a fibre connector belongs in the list above.
    A new one that is not listed is not swept, and the sweep passes anyway.
    """
    found = []
    for f in sorted(LIB.rglob("contract.yaml")):
        d = yaml.safe_load(f.read_text()) or {}
        if (d.get("attrs") or {}).get("media") != "fiber":
            continue
        if not (d.get("optical") or {}).get("positions"):
            continue
        found.append("/".join(f.parts[-4:-1]))
    unlisted = sorted(set(found) - set(FIBRE_CONNECTORS))
    assert not unlisted, (
        "these declare a fibre capacity and are not in FIBRE_CONNECTORS, so "
        f"nothing above sweeps them: {unlisted}")
