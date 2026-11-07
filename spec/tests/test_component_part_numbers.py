"""A component may carry a `part-numbers` map, and each key is one module type.

One drawing can be two things to order: the Casa BDM2m is sold as BDM2M-W (Open)
and BDM2M-N (No Licenses), the same card with the same ports. A device with two
SKUs is exported as two device types from one chassis; a component with two
order codes is exported as two module types from one contract, and for the same
reason - a part number is not an identity for the metal (roc-ops/Portrayal#70).

BUILT FIXTURES FOR THE RULES, THE LIVE LIBRARY FOR THE THREE CASA CARDS. The
fixtures are real module entries renamed, so the export rule is measured whether
or not the library holds a second order code today; the live tests pin what the
library says about the three Casa cards the first slice moved.
"""
import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from portrayal.manifest import load_yaml

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
SCHEMA = json.loads((ROOT / "spec" / "schemas" / "component.schema.json").read_text())
TEMPLATE = "juniper/mpc7e-mrate@2"
CASA = "Casa Systems"


def _dist():
    if not (DIST / "components.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    from portrayal.artifacts import Dist
    return Dist(str(DIST))


class _With:
    """The real build with `modules()` narrowed to the entries a test passes."""

    def __init__(self, dist, entries):
        self._dist, self._entries = dist, list(entries)
        self._by_ref = {_ref(c): c for c in self._entries}

    def modules(self):
        return list(self._entries)

    def component_by_ref(self, ref):
        return self._by_ref.get(ref) or self._dist.component_by_ref(ref)

    def __getattr__(self, name):
        return getattr(self._dist, name)


def _ref(c):
    return f"{c['ns']}/{c['name']}@{str(c['major'])[1:]}"


def _fixture(dist, name, model=None, part_numbers=None):
    c = copy.deepcopy(dist.component_by_ref(TEMPLATE))
    c.update({"name": name, "major": "v1", "version": "1.0.0"})
    c.pop("superseded-by", None)
    attrs = dict(c.get("attrs") or {})
    attrs.pop("model", None)
    if model:
        attrs["model"] = model
    c["attrs"] = attrs
    c.pop("part-numbers", None)
    if part_numbers:
        c["part-numbers"] = part_numbers
    return c


def _export(dist, entries, root):
    from portrayal.dcim_export import export_modules
    export_modules(_With(dist, entries), str(root))


def _type(root, target, man, model):
    p = Path(root) / target / "module-types" / man / f"{model}.yaml"
    return yaml.safe_load(p.read_text()) if p.exists() else None


def _files(root, target, man):
    d = Path(root) / target / "module-types" / man
    return sorted(p.stem for p in d.glob("*.yaml")) if d.exists() else []


# ── the export ─────────────────────────────────────────────────────────────

@pytest.mark.heavy
@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_a_component_with_two_part_numbers_exports_two_module_types(tmp_path, target):
    dist = _dist()
    two = _fixture(dist, "fixture-two", part_numbers={
        "FIX-OPEN": {"part": "FIX-OPEN"}, "FIX-NOLIC": {"part": "FIX-NOLIC-P"}})
    _export(dist, [two], tmp_path)
    man = dist.manufacturer_of(two["ns"])
    assert _files(tmp_path, target, man) == ["FIX-NOLIC", "FIX-OPEN"]
    a, b = (_type(tmp_path, target, man, m) for m in ("FIX-OPEN", "FIX-NOLIC"))
    assert (a["model"], a["part_number"]) == ("FIX-OPEN", "FIX-OPEN")
    assert (b["model"], b["part_number"]) == ("FIX-NOLIC", "FIX-NOLIC-P")
    assert a["interfaces"] == b["interfaces"] and a["interfaces"], "the same drawing has the same ports"
    for k in ("model", "part_number"):
        a.pop(k), b.pop(k)
    assert a == b


def test_a_component_without_part_numbers_exports_exactly_as_before(tmp_path):
    dist = _dist()
    plain = _fixture(dist, "fixture-plain", model="FIX-PLAIN")
    unnamed = _fixture(dist, "fixture-unnamed")
    _export(dist, [plain, unnamed], tmp_path)
    man = dist.manufacturer_of(plain["ns"])
    assert _files(tmp_path, "netbox", man) == ["FIX-PLAIN", "fixture-unnamed"]
    for model in ("FIX-PLAIN", "fixture-unnamed"):
        doc = _type(tmp_path, "netbox", man, model)
        assert doc["model"] == model and "part_number" not in doc, model


def test_a_part_numbers_entry_with_no_part_states_no_part_number(tmp_path):
    """The schema requires `part`; the exporter still must not invent one for a
    file the schema never saw."""
    dist = _dist()
    c = _fixture(dist, "fixture-bare", part_numbers={"FIX-BARE": {}})
    _export(dist, [c], tmp_path)
    doc = _type(tmp_path, "netbox", dist.manufacturer_of(c["ns"]), "FIX-BARE")
    assert doc["model"] == "FIX-BARE" and "part_number" not in doc


@pytest.mark.heavy
def test_every_part_number_of_a_card_has_the_depth_the_card_seats_at():
    """Seating is keyed by (manufacturer, model). A card that seats in a bay is
    seated under EACH of its models, or the second type would lose the depth,
    the withheld bays and the port prefix the first one has."""
    from portrayal.dcim_export import module_keys, seating_depths
    dist = _dist()
    ref = "juniper/mpc1e-3d@3"
    live = dist.component_by_ref(ref)
    (only,) = module_keys(dist, live)
    assert seating_depths(dist).get(only), "the live card is seated nowhere - nothing measured"
    # the same ref, now with two order codes: the devices that seat it are unchanged
    two = copy.deepcopy(live)
    two["attrs"] = {k: v for k, v in (two.get("attrs") or {}).items() if k != "model"}
    two["part-numbers"] = {"FIX-CAR-A": {"part": "FIX-CAR-A"}, "FIX-CAR-B": {"part": "FIX-CAR-B"}}

    class Swapped(_With):
        def modules(self):
            return [c for c in self._dist.modules() if _ref(c) != ref] + self._entries

    swapped = Swapped(dist, [two])
    keys = module_keys(swapped, two)
    assert [m for _man, m in keys] == ["FIX-CAR-A", "FIX-CAR-B"]
    depths = seating_depths(swapped)
    assert depths[keys[0]] == depths[keys[1]] == seating_depths(dist)[only]


def test_a_module_model_includes_every_part_number():
    """`module_models` tells a FRU's part number from a chassis one, so a device
    that lists BDM2M-N among its SKUs must find it among the modules."""
    dist = _dist()
    c = _fixture(dist, "fixture-fru", part_numbers={"FRU-A": {"part": "FRU-A"}, "FRU-B": {"part": "FRU-B"}})
    from portrayal.artifacts import Dist
    models = Dist.module_models(_With(dist, [c]))
    assert {"FRU-A", "FRU-B"} <= models and "fixture-fru" not in models


# ── the schema ─────────────────────────────────────────────────────────────

def _problems(contract):
    return [e.message for e in Draft202012Validator(SCHEMA).iter_errors(contract)]


def _casa(name):
    return copy.deepcopy(
        load_yaml(ROOT / "library" / "components" / "casa" / name / "v1" / "contract.yaml"))


def test_the_schema_takes_a_part_numbers_map():
    c = _casa("bdm2m")
    c.pop("attrs", None)
    c["part-numbers"] = {"BDM2M-W": {"part": "BDM2M-W"}, "BDM2M-N": {"part": "BDM2M-N"}}
    assert _problems(c) == []


@pytest.mark.parametrize("bad", [
    ["BDM2M-W"],                                  # a list, not a map
    "BDM2M-W",
    {},                                           # a map that names nothing
    {"BDM2M-W": "BDM2M-W"},                       # a bare string, not {part}
    {"BDM2M-W": {}},                              # no part
    {"BDM2M-W": {"part": ""}},
    {"BDM2M-W": {"part": 7}},
    {"BDM2M-W": {"part": "BDM2M-W", "power-cord": "C13"}},   # a module has no cord
    {"BDM2M-W": {"part": "BDM2M-W", "color": "red"}},
    {"": {"part": "X"}},                          # a key that names nothing
])
def test_the_schema_refuses_a_malformed_part_numbers(bad):
    c = _casa("bdm2m")
    c.pop("attrs", None)
    c["part-numbers"] = bad
    assert _problems(c), bad


def test_part_numbers_and_attrs_model_together_are_refused():
    """ONE SOURCE OF THE NAME. With both, a reader could not say which of
    `attrs.model` and the map names the module type, and a rename in one would
    quietly leave the other."""
    c = _casa("bdm2m")
    c["part-numbers"] = {"BDM2M-W": {"part": "BDM2M-W"}}
    c["attrs"]["model"] = "BDM2m"
    assert _problems(c), "a contract naming itself twice is valid"
    c["attrs"].pop("model")
    assert _problems(c) == []


def test_a_kit_takes_no_part_numbers():
    """A kit admits only the kit keys; the library holds none today, so the
    kit is the smallest one the schema names."""
    kit = {"format": 1, "kind": "kit", "name": "k", "version": "1.0.0", "motion": "fixed",
           "parts": [{"ref": "std/x@1", "count": 1}], "configurations": {}}
    before = set(_problems(kit))
    kit["part-numbers"] = {"K": {"part": "K"}}
    assert set(_problems(kit)) - before


def test_lint_reads_a_components_part_number_keys():
    from portrayal import lint as L
    with L.collecting() as found:
        L.lint_part_number_keys("t/contract.yaml", {"part-numbers": {"BDM2M W": {"part": "x"}}})
    assert [e for e in found.errors if "[L128]" in e]


# ── the three Casa cards ───────────────────────────────────────────────────

CASA_CARDS = {
    "bdm2m": ["BDM2M-W", "BDM2M-N"],
    "io-6p12-io2": ["BDM6-12-IO2"],
    "smm-300gm": ["SMM-300-GM"],
}


@pytest.mark.parametrize("name,models", sorted(CASA_CARDS.items()))
def test_the_casa_contract_states_its_order_codes(name, models):
    c = _casa(name)
    assert list(c["part-numbers"]) == models
    assert all(v == {"part": k} for k, v in c["part-numbers"].items())
    assert "model" not in (c.get("attrs") or {}), "the name has one source"
    assert _problems(c) == []
    said = c["provenance"]["part-numbers"]
    assert "C40G_DS_RevA" in said and "C100G_DS_RevA" in said and "page 5" in said


def test_the_casa_exports_are_named_by_order_code(tmp_path):
    dist = _dist()
    cards = [dist.component_by_ref(f"casa/{n}@1") for n in CASA_CARDS]
    _export(dist, cards, tmp_path)
    for target in ("netbox", "nautobot"):
        assert _files(tmp_path, target, CASA) == sorted(
            ["BDM2M-W", "BDM2M-N", "BDM6-12-IO2", "SMM-300-GM"]), target
        w, n = (_type(tmp_path, target, CASA, m) for m in ("BDM2M-W", "BDM2M-N"))
        assert (w["part_number"], n["part_number"]) == ("BDM2M-W", "BDM2M-N")
        # one drawing, one set of ports: the card has none, its rear partner has them
        assert {k: v for k, v in w.items() if k not in ("model", "part_number")} == \
               {k: v for k, v in n.items() if k not in ("model", "part_number")}
        assert _type(tmp_path, target, CASA, "BDM6-12-IO2")["part_number"] == "BDM6-12-IO2"
        assert _type(tmp_path, target, CASA, "SMM-300-GM")["part_number"] == "SMM-300-GM"
        assert len(_type(tmp_path, target, CASA, "BDM6-12-IO2")["interfaces"]) == 18


def test_the_index_publishes_part_numbers_sorted_like_the_rest_of_the_file():
    dist = _dist()
    assert list(dist.component_by_ref("casa/bdm2m@1")["part-numbers"]) == ["BDM2M-N", "BDM2M-W"]
    assert "part-numbers" not in dist.component_by_ref("casa/ds-8x192@1"), \
        "a component without the key publishes exactly what it did"


def test_a_bay_names_the_component_it_accepts_not_an_order_code():
    """A bay's `Accepts:` line lists component names, and a component with two
    order codes is still one name there. The C40G and C100G device types are
    unchanged by this."""
    from portrayal.dcim_export import bay_row
    row = bay_row("front-0", ["casa/bdm2m@1", "casa/bdm2@1"])
    assert row["description"] == "Accepts: bdm2m, bdm2"
