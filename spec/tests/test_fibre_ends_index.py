"""components.json carries each fibre end's far end and front number.

The explorer labels a fibre `1 -> rear mtp2 . 2` and an MTP `front 1-12`.
Front numbers are optical_ports.front_label's, and must not be re-derived in
JavaScript, so the build writes them next to the paths they come from.
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _index(tmp_path):
    env = {**os.environ, "PYTHONPATH": "spec/tools"}
    subprocess.run([sys.executable, "spec/tools/portrayal/components_index.py",
                    "--library", "library", "--out", str(tmp_path)],
                   cwd=ROOT, check=True, env=env)
    return {f"{e['ns']}/{e['name']}": e for e in json.loads((tmp_path / "components.json").read_text())["components"]}


def test_an_af_cassette_names_both_ends_of_every_fibre(tmp_path):
    idx = _index(tmp_path)
    af = idx["fs/fhd-2mtp12-lc-os2-af"]["optical"]["ends"]
    assert af["lc01.1"] == {"to": "rear:mtp2.2", "label": "1"}
    assert af["lc01.2"] == {"to": "rear:mtp2.1", "label": "2"}
    assert af["rear:mtp2.2"] == {"to": "lc01.1", "label": "1"}
    assert len([k for k in af if not k.startswith("rear:")]) == 24


def test_a_front_to_front_path_numbers_each_end(tmp_path):
    ends = _index(tmp_path)["smartoptics/ppm-dcm-10"]["optical"]["ends"]
    assert ends["dcm.2"]["to"] == "dcm.1" and ends["dcm.1"]["to"] == "dcm.2"
    assert ends["dcm.1"]["label"] and ends["dcm.2"]["label"]
