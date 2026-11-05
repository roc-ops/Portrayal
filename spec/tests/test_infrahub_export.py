"""The Infrahub object files for device types and module types.

`infrahub_export.py` reads the committed NetBox trees and writes Infrahub object
files into the folder `--out` names. Nothing it writes is committed, so these
tests regenerate into a temporary folder and compare structure against the
NetBox tree: the same makers and models, one to one, with the key rule, the
rounding rules and the weights as the README says. No test pins a row count or
a version, so a later device change does not break them.

The schema the files are checked against is `fixtures/infrahub_schema_from_note.json`.
It is taken from the tables of `docs/infrahub-export-design.md` (sections 3.1,
3.2, 3.6 and 3.9), not from OpsMill's schema library, and it is unchecked
against the library commit the note names. A pass here is not a load into an
Infrahub instance; no load was done.
"""
import functools
import json
import math
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
NETBOX = ROOT / "library" / "exports" / "netbox"
SCHEMA = json.loads((pathlib.Path(__file__).parent / "fixtures" / "infrahub_schema_from_note.json").read_text())

_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
GRAMS = {"kg": 1000, "g": 1, "lb": 453.59237, "oz": 28.349523125}
MANUFACTURERS_FILE = "00-manufacturers.yml"


def load(path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER)


@functools.cache
def netbox(folder):
    """The committed NetBox documents of `device-types` or `module-types`, as a list."""
    return [load(p) for p in sorted((NETBOX / folder).glob("*/*.yaml"))]


def whole_kg(value, unit="kg"):
    return math.floor(value * GRAMS[unit] / 1000 + 0.5)


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    from portrayal_dev import infrahub_export as ix
    dest = tmp_path_factory.mktemp("infrahub")
    assert ix.main(["--netbox", str(NETBOX), "--out", str(dest)]) == 0
    return dest


@functools.cache
def _read(dest):
    """Every object file as {relative name: [document, ...]}."""
    files = {}
    for p in sorted((dest / "objects").glob("*.yml")):
        files[p.name] = list(yaml.load_all(p.read_text(encoding="utf-8"), Loader=_LOADER))
    return files


def entries(dest, kind):
    """The data entries of one kind, every maker's file, as (file name, entry)."""
    rows = []
    for name, docs in _read(dest).items():
        for doc in docs:
            if doc["spec"]["kind"] == kind:
                rows.extend((name, e) for e in doc["spec"]["data"])
    return rows


def test_every_object_file_has_the_note_file_shape(out):
    files = _read(out)
    assert MANUFACTURERS_FILE in files
    for name, docs in files.items():
        assert docs, name
        for doc in docs:
            assert doc["apiVersion"] == "infrahub.app/v1", name
            assert doc["kind"] == "Object", name
            assert set(doc["spec"]) == {"kind", "data"}, name
            assert isinstance(doc["spec"]["data"], list) and doc["spec"]["data"], name


@pytest.mark.parametrize("kind,folder", [("DcimDeviceType", "device-types"), ("DcimModuleType", "module-types")])
def test_a_type_has_its_fields_and_the_key_rule(out, kind, folder):
    rows = entries(out, kind)
    assert rows
    names = [e["name"] for _, e in rows]
    assert len(names) == len(set(names)), "a type name is not unique"
    for _, e in rows:
        assert e["manufacturer"] and e["name"].startswith(e["manufacturer"] + " ")
        if kind == "DcimDeviceType":
            assert isinstance(e["full_depth"], bool)
            assert "height" in e or e["name"] in zero_u_names()


def zero_u_names():
    return {f"{d['manufacturer']} {d['model']}" for d in netbox("device-types") if not d.get("u_height")}


def test_a_bare_model_collides_across_makers_and_the_name_does_not(out):
    seen = {}
    for d in netbox("device-types"):
        seen.setdefault(d["model"], set()).add(d["manufacturer"])
    shared = {m: makers for m, makers in seen.items() if len(makers) > 1}
    assert shared, "no model is listed by more than one maker"
    names = {e["name"] for _, e in entries(out, "DcimDeviceType")}
    for model, makers in shared.items():
        assert {f"{mk} {model}" for mk in makers} <= names


@pytest.mark.parametrize("kind,folder", [("DcimDeviceType", "device-types"), ("DcimModuleType", "module-types")])
def test_the_types_agree_with_the_netbox_tree_one_to_one(out, kind, folder):
    docs = netbox(folder)
    expected = [f"{d['manufacturer']} {d['model']}" for d in docs]
    assert len(expected) == len(set(expected))
    rows = entries(out, kind)
    assert sorted(e["name"] for _, e in rows) == sorted(expected)
    per_maker = {}
    for d in docs:
        per_maker[d["manufacturer"]] = per_maker.get(d["manufacturer"], 0) + 1
    written = {}
    for _, e in rows:
        written[e["manufacturer"]] = written.get(e["manufacturer"], 0) + 1
    assert written == per_maker


def test_the_manufacturers_file_lists_every_maker_once(out):
    makers = {d["manufacturer"] for folder in ("device-types", "module-types") for d in netbox(folder)}
    docs = _read(out)[MANUFACTURERS_FILE]
    assert [d["spec"]["kind"] for d in docs] == ["OrganizationManufacturer"]
    names = [e["name"] for e in docs[0]["spec"]["data"]]
    assert names == sorted(makers)
    stems = {n[:-4] for n in _read(out) if n != MANUFACTURERS_FILE}
    assert len(stems) == len([n for n in _read(out) if n != MANUFACTURERS_FILE])
    assert len(stems) == len(makers)


def test_height_is_the_u_height_rounded_up_and_half_units_say_so(out):
    rows = {e["name"]: e for _, e in entries(out, "DcimDeviceType")}
    halves = 0
    for d in netbox("device-types"):
        e = rows[f"{d['manufacturer']} {d['model']}"]
        u = d.get("u_height") or 0
        assert e["full_depth"] == bool(d.get("is_full_depth", True))
        if not u:
            assert "height" not in e
            continue
        assert e["height"] == math.ceil(u) and isinstance(e["height"], int)
        if u != int(u):
            halves += 1
            assert f"{u:g} U nominal" in e["description"]
        else:
            assert "U nominal" not in e.get("description", "")
    assert halves, "no half-unit type to check the rounding on"


def test_device_weight_is_whole_kilograms_and_weight_grams_is_exact(out):
    rows = {e["name"]: e for _, e in entries(out, "DcimDeviceType")}
    fractional = 0
    for d in netbox("device-types"):
        e = rows[f"{d['manufacturer']} {d['model']}"]
        if d.get("weight") is None:
            assert "weight" not in e and "weight_grams" not in e
            continue
        unit = d.get("weight_unit", "kg")
        assert e["weight"] == whole_kg(d["weight"], unit)
        assert e["weight_grams"] == round(d["weight"] * GRAMS[unit])
        assert isinstance(e["weight"], int) and isinstance(e["weight_grams"], int)
        fractional += d["weight"] != int(d["weight"])
    assert fractional, "no fractional weight to check the rounding on"


def test_module_weight_is_grams_only(out):
    rows = {e["name"]: e for _, e in entries(out, "DcimModuleType")}
    for d in netbox("module-types"):
        e = rows[f"{d['manufacturer']} {d['model']}"]
        assert "weight" not in e
        if d.get("weight") is None:
            assert "weight_grams" not in e
        else:
            assert e["weight_grams"] == round(d["weight"] * GRAMS[d.get("weight_unit", "kg")])
        assert e.get("part_number") == d.get("part_number")


def test_the_console_and_power_ports_are_named_in_the_description(out):
    rows = {e["name"]: e for _, e in entries(out, "DcimDeviceType")}
    named = 0
    for d in netbox("device-types"):
        if d.get("console-ports") or d.get("power-ports"):
            named += 1
            assert "not exported" in rows[f"{d['manufacturer']} {d['model']}"]["description"]
    assert named


def test_every_kind_attribute_and_value_exists_in_the_schema_fixture(out):
    nodes = SCHEMA["nodes"]
    checks = {"Text": str, "Number": int, "Boolean": bool}
    seen_kinds = set()
    for name, docs in _read(out).items():
        for doc in docs:
            kind = doc["spec"]["kind"]
            seen_kinds.add(kind)
            node = nodes[kind]
            for entry in doc["spec"]["data"]:
                for key, value in entry.items():
                    if key in node["relationships"]:
                        assert node["relationships"][key]["peer"] == "OrganizationManufacturer"
                        assert isinstance(value, str)
                        continue
                    attr = node["attributes"][key]
                    if attr["kind"] == "Dropdown":
                        assert value in SCHEMA["dropdowns"][f"{kind}.{key}"]
                    else:
                        assert type(value) is checks[attr["kind"]], (name, key)
                required = [k for k, a in node["attributes"].items()
                            if not a.get("optional") and "default" not in a]
                required += [k for k, r in node["relationships"].items() if not r["optional"]]
                assert set(required) <= set(entry), (name, kind, entry.get("name"))
    assert seen_kinds == {"OrganizationManufacturer", "DcimDeviceType", "DcimModuleType"}


def test_a_device_type_refers_to_a_manufacturer_the_first_file_creates(out):
    makers = {e["name"] for e in _read(out)[MANUFACTURERS_FILE][0]["spec"]["data"]}
    for kind in ("DcimDeviceType", "DcimModuleType"):
        assert {e["manufacturer"] for _, e in entries(out, kind)} <= makers


def test_the_overlay_is_the_note_s_and_only_names_overlay_attributes(out):
    overlay = load(out / "schema" / "portrayal-overlay.yml")
    assert list(overlay) == ["extensions"]
    nodes = overlay["extensions"]["nodes"]
    assert {n["kind"] for n in nodes} == {"InterfacePhysical", "DcimDeviceType"}
    for n in nodes:
        assert len(n["attributes"]) == 1
        a = n["attributes"][0]
        fixture = SCHEMA["nodes"][n["kind"]]["attributes"][a["name"]]
        assert fixture["overlay"] is True
        assert a["kind"] == fixture["kind"] and a["optional"] is True
    used = {k for _, e in entries(out, "DcimDeviceType") for k in e}
    assert "weight_grams" in used


def test_the_output_is_stable(out, tmp_path):
    from portrayal_dev import infrahub_export as ix
    assert ix.main(["--netbox", str(NETBOX), "--out", str(tmp_path)]) == 0
    first = sorted(p.relative_to(out) for p in out.rglob("*") if p.is_file())
    second = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*") if p.is_file())
    assert first == second
    for rel in first:
        assert (out / rel).read_bytes() == (tmp_path / rel).read_bytes(), rel
    assert (out / "README.md") in [out / r for r in first]


def test_out_has_no_default():
    from portrayal_dev import infrahub_export as ix
    with pytest.raises(SystemExit):
        ix.main(["--netbox", str(NETBOX)])


def test_the_readme_names_the_load_sequence_and_what_is_unverified(out):
    text = (out / "README.md").read_text(encoding="utf-8")
    sequence = ["base/organization.yml", "base/location.yml", "base/dcim.yml",
                "extensions/location_site/", "extensions/rack/", "extensions/cable/",
                "extensions/device_module/", "extensions/module_port/", "extensions/patch_panel/",
                "schema/portrayal-overlay.yml", "objects/" + MANUFACTURERS_FILE]
    positions = [text.index(item) for item in sequence]
    assert positions == sorted(positions)
    low = " ".join(text.lower().split())
    for phrase in ("unverified", "no load", "taken from `docs/infrahub-export-design.md`, not from the schema library",
                   "without `weight_grams`", "<manufacturer> <model>", "rounded up", "left out"):
        assert phrase in low, phrase
    for what in ("racks", "placed devices", "interfaces", "cables", "drawings", "console and power ports"):
        assert what in low, what


def test_the_readme_names_every_zero_u_type(out):
    text = (out / "README.md").read_text(encoding="utf-8")
    for name in zero_u_names():
        assert name in text
