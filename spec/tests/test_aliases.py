"""#514: `aliases:` - one structured list of a device's other names - and L111.

An HCL names an Edgecore box by its AS number and Portrayal ids it by the
marketing name, or the other way round. `aliases:` is what joins the two, so
the tests hold three things: the shape the schema accepts, the lint that keeps
a name pointing at one drawing, and that the names reach the two indexes a
consumer actually reads.
"""
import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

from portrayal import devicelock, devices_index, lint, libwalk
from portrayal.manifest import alias_names, load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())


def _all_devices():
    out = []
    for man in libwalk.iter_devices([LIB]):
        d = load_yaml(man)
        if isinstance(d, dict) and d.get("kind") == "device":
            out.append((man, d))
    return out


def l111(docs):
    got = []
    real = lint.err
    lint.err = lambda path, rule, msg: got.append((str(path), rule, msg))
    try:
        lint.lint_library_aliases(docs)
    finally:
        lint.err = real
    return [(p, m) for p, r, m in got if r == "L111"]


def dev(model, *aliases):
    return {"kind": "device", "model": model, "aliases": list(aliases)}


# ------------------------------------------------------------------ schema ---

def _alias_errors(aliases):
    v = Draft202012Validator(SCHEMA["properties"]["aliases"])
    return list(v.iter_errors(aliases))


def test_the_object_form_validates():
    assert _alias_errors([{"name": "AS9716-32D", "kind": "vendor"},
                          {"name": "NCP-40C", "kind": "oem", "note": "x", "shared": True}]) == []


@pytest.mark.parametrize("bad", [
    ["AS9716-32D"],                                   # a bare string loses its kind
    [{"name": "AS9716-32D"}],                         # kind is required
    [{"name": "AS9716-32D", "kind": "nickname"}],     # kind is a closed set
    [{"name": " AS9716-32D", "kind": "vendor"}],      # no padding a lookup would miss
    [{"name": "X", "kind": "vendor", "shared": False}],  # shared is only ever `true`
    [{"name": "X", "kind": "vendor", "sku": "Y"}],    # SKUs live in configurations
    [],                                               # absent, not empty
])
def test_the_schema_refuses(bad):
    assert _alias_errors(bad), bad


# -------------------------------------------------------------------- L111 ---

def test_distinct_aliases_pass():
    assert l111([("a", dev("AS1", {"name": "DCS1", "kind": "marketing"})),
                 ("b", dev("AS2", {"name": "DCS2", "kind": "marketing"}))]) == []


def test_two_claimants_fail_and_it_is_case_insensitive():
    msgs = l111([("a", dev("AS1", {"name": "NCP-1", "kind": "oem"})),
                 ("b", dev("AS2", {"name": "ncp-1", "kind": "oem"}))])
    assert {p for p, _ in msgs} == {"a", "b"}


def test_shared_passes_only_when_every_claimant_says_so():
    shared = {"name": "NCP-1", "kind": "oem", "shared": True}
    assert l111([("a", dev("AS1", shared)), ("b", dev("AS2", shared))]) == []
    msgs = l111([("a", dev("AS1", shared)),
                 ("b", dev("AS2", {"name": "NCP-1", "kind": "oem"}))])
    assert [p for p, _ in msgs] == ["b"]


def test_a_shared_flag_nothing_else_claims_is_stale():
    msgs = l111([("a", dev("AS1", {"name": "NCP-1", "kind": "oem", "shared": True}))])
    assert msgs and "no other" in msgs[0][1]


def test_an_alias_may_not_be_another_devices_model():
    msgs = l111([("a", dev("AS1", {"name": "as2", "kind": "vendor"})), ("b", dev("AS2"))])
    assert [p for p, _ in msgs] == ["a"]


def test_an_alias_may_not_repeat_its_own_model():
    assert l111([("a", dev("AS1", {"name": "AS1", "kind": "vendor"}))])


def test_a_name_listed_twice_on_one_device_fails():
    assert l111([("a", dev("AS1", {"name": "X", "kind": "vendor"},
                           {"name": "x", "kind": "marketing"}))])


def test_the_library_passes_l111_and_measures_something():
    docs = _all_devices()
    claimed = [a for _, d in docs for a in alias_names(d)]
    assert len(claimed) >= 40, "the migration's aliases went missing"
    assert l111(docs) == []


# -------------------------------------------------------------- migration ---

def test_the_old_prose_keys_are_gone():
    left = []
    for man, d in _all_devices():
        a = d.get("attrs") or {}
        if "vendor-alias" in (a.get("features") or {}) or \
           "marketing-name" in (a.get("features") or {}) or \
           "oem-alias" in (a.get("platform") or {}):
            left.append(str(man))
    assert left == []


def test_the_hcl_names_the_issue_asked_about_resolve():
    by = {}
    for man, d in _all_devices():
        for n in alias_names(d):
            by.setdefault(n.casefold(), []).append(d["name"])
    for name, want in [("AS9817-64O", "ais800-64o"), ("DCS560", "ais800-64o"),
                       ("AS9716-32D", "dcs510"), ("CSR440", "csr440"),
                       ("DCS203", "as7326-56x"), ("NCP-40C", "s9700-53dx")]:
        assert by.get(name.casefold()) == [want], name
    # the DriveNets name that maps to either of a pair names both
    assert sorted(by["ncp-96x6c-s"]) == ["s9600-102xc", "s9601-102xc"]


# ---------------------------------------------------------------- outputs ---

def test_alias_names_reads_the_names_in_order():
    assert alias_names({"aliases": [{"name": "B", "kind": "vendor"},
                                    {"name": "A", "kind": "marketing"}]}) == ["B", "A"]
    assert alias_names({}) == []


def test_the_search_blob_carries_the_aliases():
    d = {"attrs": {}, "aliases": [{"name": "AS9716-32D", "kind": "vendor"}]}
    assert "as9716-32d" in devices_index.search_blob(d).split()


def test_devicelock_does_not_rehash_a_device_without_aliases():
    base = {"kind": "device", "model": "X", "description": "d"}
    assert devicelock.buckets(dict(base))["surface"] == \
        devicelock.buckets(dict(base, aliases=None))["surface"]
    with_alias = dict(base, aliases=[{"name": "Y", "kind": "vendor"}])
    assert devicelock.buckets(with_alias)["surface"] != devicelock.buckets(base)["surface"]
    assert devicelock.buckets(with_alias)["names"] == devicelock.buckets(base)["names"]
