"""kit/rack/cable-rules.js keeps the pairs of DC roles a feed may join and the
role list, for a page that cannot read YAML; each is spec/schemas/dc.yaml's."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "kit/rack/cable-rules.js").read_text()
DC = yaml.safe_load((ROOT / "spec/schemas/dc.yaml").read_text())


def _kit_roles():
    body = re.search(r"export const DC_ROLES = \[([^\]]*)\];", SRC).group(1)
    return re.findall(r"'(\w+)'", body)


def _kit_pairs():
    body = re.search(r"export const DC_MATCHES = \[(.*?)\n\];", SRC, re.S).group(1)
    return [(a, b, w or None) for a, b, w in re.findall(r"\{a: '(\w+)', b: '(\w+)'(?:, when: '([\w-]+)')?\}", body)]


def _key(a, b, when):
    return (tuple(sorted((a, b))), when)


def test_the_kits_roles_are_the_registrys():
    assert sorted(_kit_roles()) == sorted(DC["roles"])


def test_the_kits_pairs_are_the_registrys():
    want = sorted(_key(m["a"], m["b"], m.get("when")) for m in DC["matches"])
    got = sorted(_key(a, b, w) for a, b, w in _kit_pairs())
    assert got == want


def test_the_kit_reads_every_pair_it_holds():
    """the regular expression finds one entry for each line of the kit's table,
    so a pair written in another shape cannot slip past the comparison above"""
    body = re.search(r"export const DC_MATCHES = \[(.*?)\n\];", SRC, re.S).group(1)
    assert len(_kit_pairs()) == len([ln for ln in body.splitlines() if "{a:" in ln]) >= 6
