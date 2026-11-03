"""`audience`: an optional label on a device or component contract.

A project that keeps private entries beside Portrayal's public library writes
them in the same format, and says who each one is for. The field is optional
and absent means `public`. Portrayal's own library only ever uses `public`, so
a lint rule holds it to that, and the two indexes carry the field when it is
set so a consumer can filter on it without opening a contract.
"""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest
from jsonschema import Draft202012Validator

from portrayal import lint
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "spec" / "schemas"
TOOLS = ROOT / "spec" / "tools" / "portrayal"
LIB = ROOT / "library"

DEVICE = "fs/fhu-bpa-1u-10"
COMPONENT = "common/qsfp-pull-tab/v2"

ALLOWED = ["public", "internal", "nda", "customer:acme", "customer:acme-2"]
REFUSED = ["customer:Acme Corp", "secret", "customer:", "customer:acme corp",
           "Public", "customer:acme_corp", "", None, 3, ["public"]]


def _property(schema_name):
    schema = json.loads((SCHEMAS / f"{schema_name}.schema.json").read_text())
    return Draft202012Validator(schema["properties"]["audience"])


# ---- the schema --------------------------------------------------------------

@pytest.mark.parametrize("schema", ["device", "component"])
@pytest.mark.parametrize("value", ALLOWED)
def test_each_allowed_value_validates(schema, value):
    assert list(_property(schema).iter_errors(value)) == []


@pytest.mark.parametrize("schema", ["device", "component"])
@pytest.mark.parametrize("value", REFUSED, ids=repr)
def test_a_value_outside_the_set_does_not(schema, value):
    assert list(_property(schema).iter_errors(value)) != []


def _contract_errors(schema_name, doc):
    schema = json.loads((SCHEMAS / f"{schema_name}.schema.json").read_text())
    return list(Draft202012Validator(schema).iter_errors(doc))


def _with(path, **extra):
    return {**load_yaml(path), **extra}


@pytest.mark.parametrize("value", ALLOWED)
def test_a_whole_device_with_the_field_validates(value):
    doc = _with(LIB / "devices" / DEVICE / "device.yaml", audience=value)
    assert _contract_errors("device", doc) == []


@pytest.mark.parametrize("value", ALLOWED)
def test_a_whole_component_with_the_field_validates(value):
    doc = _with(LIB / "components" / COMPONENT / "contract.yaml", audience=value)
    assert _contract_errors("component", doc) == []


def test_a_whole_contract_with_a_bad_value_fails():
    dev = _with(LIB / "devices" / DEVICE / "device.yaml", audience="customer:Acme Corp")
    comp = _with(LIB / "components" / COMPONENT / "contract.yaml", audience="secret")
    assert _contract_errors("device", dev) and _contract_errors("component", comp)


@pytest.mark.parametrize("schema", ["device", "component"])
def test_the_description_says_absent_means_public(schema):
    desc = json.loads((SCHEMAS / f"{schema}.schema.json").read_text())["properties"]["audience"]["description"]
    assert "absent" in desc and "public" in desc


# ---- the lint rule -----------------------------------------------------------

DEV_PATH = pathlib.Path("library/devices/acme/box/device.yaml")
COMP_PATH = pathlib.Path("library/components/acme/part/v1/contract.yaml")


def run(doc, path=DEV_PATH):
    with lint.collecting() as got:
        lint.lint_public_audience(path, doc)
        return [e for e in got.errors if "[L192]" in e]


@pytest.mark.parametrize("path", [DEV_PATH, COMP_PATH], ids=["device", "component"])
@pytest.mark.parametrize("value", ["internal", "nda", "customer:acme"])
def test_a_public_library_entry_that_is_not_public_fails(path, value):
    errs = run({"kind": "device", "audience": value}, path)
    assert len(errs) == 1 and value in errs[0]


@pytest.mark.parametrize("doc", [{"kind": "device"}, {"kind": "device", "audience": "public"}])
def test_absent_or_public_passes(doc):
    assert run(doc) == []


@pytest.mark.heavy
def test_the_rule_is_in_the_table_and_the_library_passes_it():
    assert "L192" in lint.RULES
    bad = []
    for f in sorted(LIB.glob("devices/**/device.yaml")) + sorted(LIB.glob("components/**/contract.yaml")):
        d = load_yaml(f)
        if isinstance(d, dict) and d.get("audience") not in (None, "public"):
            bad.append(str(f))
    assert bad == []


def test_a_private_library_can_turn_the_rule_off(tmp_path):
    out = subprocess.run([sys.executable, str(TOOLS / "lint.py"), "--help"],
                         capture_output=True, text=True, check=True).stdout
    assert "--allow-audience" in out


# ---- the indexes -------------------------------------------------------------

def _library(tmp_path, audience):
    """A one-device, one-component library, the contracts copied from the
    real one with `audience` written first when it is set."""
    lib = tmp_path / ("lib-" + str(audience).replace(":", "-"))
    for rel, name in ((f"devices/{DEVICE}", "device.yaml"),
                      (f"components/{COMPONENT}", "contract.yaml")):
        shutil.copytree(LIB / rel, lib / rel)
        if audience is not None:
            p = lib / rel / name
            p.write_text(f"audience: {audience}\n" + p.read_text())
    return lib


def _index(lib, tool, key, tmp_path):
    out = tmp_path / ("out-" + lib.name + "-" + tool)
    out.mkdir()
    subprocess.run([sys.executable, str(TOOLS / f"{tool}_index.py"),
                    "--library", str(lib), "--out", str(out)],
                   check=True, capture_output=True, text=True)
    return json.loads((out / f"{tool}.json").read_text())[key]


@pytest.mark.parametrize("audience", ["internal", "customer:acme"])
def test_an_index_entry_carries_the_field_when_set(tmp_path, audience):
    lib = _library(tmp_path, audience)
    (dev,) = _index(lib, "devices", "devices", tmp_path)
    (comp,) = _index(lib, "components", "components", tmp_path)
    assert dev["audience"] == audience and comp["audience"] == audience


def test_an_index_entry_has_none_when_absent(tmp_path):
    lib = _library(tmp_path, None)
    (dev,) = _index(lib, "devices", "devices", tmp_path)
    (comp,) = _index(lib, "components", "components", tmp_path)
    assert "audience" not in dev and "audience" not in comp
