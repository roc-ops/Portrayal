"""docs/device-template.yaml is the file a contributor copies to start a device. It
is not a product and must not be indexed or exported, so it lives outside the
library - and the only way a file outside the library stays valid is a test that
runs it through the same gates a real device meets.

The template is linted inside a throwaway library that holds only it: the real
components (linked, not copied), and a copy of the schemas whose vendor registry
gains the fictional vendor `example`, because L55 rightly refuses a namespace the
registry does not know.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs" / "device-template.yaml"
TOOLS = ROOT / "spec" / "tools" / "portrayal"

# Two warnings come from the fan module the template seats, not from the template:
# common/fan-module@1 declares lamp states it never draws (L47) and states no draw
# figure (L29). Tracked as roc-ops/Portrayal#212; the template is not the place to fix it.
ALLOWED_WARNINGS = {"L29", "L47"}


def test_template_validates_against_the_device_schema():
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    doc = yaml.safe_load(TEMPLATE.read_text())
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(doc))
    assert not errors, [f"{'/'.join(map(str, e.path))}: {e.message}" for e in errors]


@pytest.fixture(scope="module")
def template_library(tmp_path_factory):
    base = tmp_path_factory.mktemp("template")
    lib = base / "library"
    (lib / "devices" / "example" / "ex-1u").mkdir(parents=True)
    shutil.copy(TEMPLATE, lib / "devices" / "example" / "ex-1u" / "device.yaml")
    (lib / "components").symlink_to(ROOT / "library" / "components", target_is_directory=True)
    schemas = base / "schemas"
    shutil.copytree(ROOT / "spec" / "schemas", schemas)
    vendors = schemas / "vendors.yaml"
    text = vendors.read_text()
    assert "\nvendors:\n" in text
    vendors.write_text(text.replace(
        "\nvendors:\n",
        "\nvendors:\n\n  example:\n    display: Example\n    role: hardware\n"
        "    source: 'a fictional vendor that exists only so docs/device-template.yaml can be linted'\n", 1))
    return lib, schemas


def test_template_lints_with_no_errors_and_only_the_fan_modules_warnings(template_library):
    lib, schemas = template_library
    r = subprocess.run([sys.executable, str(TOOLS / "lint.py"), "--schemas", str(schemas),
                        "--library", str(lib), "--device", "ex-1u"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    codes = {line.split("[")[1].split("]")[0]
             for line in r.stdout.splitlines() if "device.yaml: [L" in line}
    assert codes <= ALLOWED_WARNINGS, (
        f"the template warns on {sorted(codes - ALLOWED_WARNINGS)}; a starting point lints silent\n"
        + r.stdout)


def test_template_renders_all_six_faces(template_library, tmp_path):
    lib, _ = template_library
    out = tmp_path / "dist"
    r = subprocess.run([sys.executable, str(TOOLS / "render.py"),
                        str(lib / "devices" / "example" / "ex-1u" / "device.yaml"),
                        "--library", str(lib), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    faces = {p.name for p in out.glob("ex-1u.base.*.svg")}
    assert faces == {f"ex-1u.base.{f}.svg" for f in ("front", "rear", "top", "bottom", "left", "right")}
