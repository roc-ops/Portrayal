"""Every optical contract in the library resolves, and the sweep is not vacuous.

The lint rules run over the library on every build, so in principle this adds
nothing. In practice a rule that stops being dispatched goes quiet and the build
stays green - which is exactly how a fixture that could not tell `!seen` from
`!seen && named` shipped here. A sweep that asserts it FOUND something is the
cheap guard against that.
"""
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"
from portrayal import optical


def contracts():
    for f in sorted(LIB.rglob("contract.yaml")):
        d = yaml.safe_load(f.read_text()) or {}
        if d.get("optical", {}).get("paths"):
            yield f, d


def load_ref(ref):
    name, major = ref.split("@")
    p = LIB / name / f"v{major}" / "contract.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else {}


def test_the_sweep_finds_optical_contracts_at_all():
    found = list(contracts())
    assert len(found) >= 6, (
        f"only {len(found)} contracts declare optical paths. Six were added by "
        "this plan (2 OCU couplers, 4 DCMs); fewer means one lost its block or "
        "this sweep stopped finding them")


def test_every_optical_endpoint_resolves_to_a_real_position():
    bad = []
    for f, d in contracts():
        caps = optical.capacities(d, load_ref)
        for ep in optical.reached(d):
            face, part, pos = optical.split_endpoint(ep)
            key = optical.part_key(face, part)
            if key not in caps:
                bad.append(f"{f.parent.parent.name}: {ep} names no connector")
            elif pos > caps[key]:
                bad.append(f"{f.parent.parent.name}: {ep} exceeds {caps[key]}")
    assert not bad, "unresolvable optical endpoints:\n  " + "\n  ".join(bad)


def test_every_declared_position_is_reached_or_declared_unused():
    bad = []
    for f, d in contracts():
        caps = optical.capacities(d, load_ref)
        hit = optical.reached(d)
        unused = (d.get("optical") or {}).get("unused") or {}
        for part, n in caps.items():
            for pos in range(1, n + 1):
                ep = f"{part}.{pos}"
                if ep not in hit and ep not in unused:
                    bad.append(f"{f.parent.parent.name}: {ep} unaccounted for")
    assert not bad, "fibre positions nothing accounts for:\n  " + "\n  ".join(bad)
