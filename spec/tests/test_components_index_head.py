"""components.json carries a pluggable's `head`, verbatim from its contract.

A downstream tool that never builds 3D still needs the box a pluggable
occupies outside its cage (docs/pluggables-heads-design.md 4.2), and it reads
this index, not the contract."""
import json
import os
import pathlib
import subprocess
import sys

import yaml

import onebuild

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library" / "components"


def _index(tmp_path):
    tmp_path = onebuild.components_index()   # built once per session
    return {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
            for e in json.loads((tmp_path / "components.json").read_text())["components"]}


def test_the_index_carries_each_declared_head_verbatim(tmp_path):
    idx = _index(tmp_path)
    for ref, path in (("generic/sfp-rj45@1", "generic/sfp-rj45/v1"),
                      ("generic/qsfp-lc@2", "generic/qsfp-lc/v2")):
        head = yaml.safe_load((LIB / path / "contract.yaml").read_text())["head"]
        assert idx[ref]["head"] == head, ref


def test_a_part_without_a_head_carries_none(tmp_path):
    idx = _index(tmp_path)
    assert "head" not in idx["common/qsfp-pull-tab@2"]
