"""A power supply that does not draw power from anything is not a thing.

The library had 31 of them - half the PSU catalogue, exporting no power port,
with nothing anywhere to say so. A DCIM built from those exports showed half a
rack's supplies with no port to cable and raised nothing, which is #254's shape
one layer down: the export was right to write nothing, and the silence was
indistinguishable from a supply nobody had modelled.

It was never 31 oversights. Most are DC supplies whose entry is a screw-terminal
block; the library has one DC terminal component against two IEC ones, so the
studs were drawn as ELEMENTS in the skin - `terminal-block`, `terminals`,
`dc-input`, named differently by each modeller - and the connector was described
in prose. The hardware was modelled all along. What was missing was a fact a tool
could read without guessing at an element's name, which would be the `port-`
prefix defect a third time.

So `attrs.inlet` says it once, from a closed vocabulary, and L95 asks every
supply for it.
"""
import functools
import json
import pathlib
import sys

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

from portrayal import dcim_export as dx
from portrayal import lint


@functools.lru_cache(maxsize=1)
def _psus():
    """Every class:psu contract, parsed once: ref -> document."""
    out = {}
    for cf in sorted(LIB.glob("components/*/*/*/contract.yaml")):
        d = yaml.safe_load(cf.read_text()) or {}
        if (d.get("class") or "") == "psu":
            out[f"{cf.parent.parent.parent.name}/{cf.parent.parent.name}"] = d
    return out


@functools.lru_cache(maxsize=1)
def _module_exports():
    out = {}
    for p in sorted((LIB / "exports/netbox/module-types").glob("*/*.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        out[str(d.get("model", ""))] = d
    return out


# --- the vocabulary is closed, and closed on purpose -------------------------

def test_the_enum_and_the_table_are_the_same_list():
    """A token the schema allows and the exporter cannot map exports NOTHING,
    which is the silence this whole change exists to remove - arriving through
    the one door left open. The schema is the authority; the table follows it."""
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    enum = set(schema["properties"]["attrs"]["properties"]["inlet"]["enum"])
    assert enum == set(dx.INLET_TYPE), (
        f"schema-only: {sorted(enum - set(dx.INLET_TYPE))}, "
        f"table-only: {sorted(set(dx.INLET_TYPE) - enum)}")


def test_every_token_in_use_is_in_the_vocabulary():
    """The schema validates this too; asserting it here names the file."""
    bad = {ref: (d.get("attrs") or {}).get("inlet") for ref, d in _psus().items()
           if (d.get("attrs") or {}).get("inlet") not in (None, *dx.INLET_TYPE)}
    assert not bad, bad


# --- what the tokens do ------------------------------------------------------

def test_a_declared_terminal_block_exports_a_power_port():
    """The 20 DC supplies whose terminal block was drawn as an element and
    described in prose. PSU-302-DESR is the shape: 'two-stud screw-terminal
    block under a hinged plastic cover', and it exported nothing."""
    d = _module_exports().get("PSU-302-DESR")
    if d is None:
        pytest.skip("PSU-302-DESR is not in this library")
    assert d.get("power-ports") == [{"name": "Inlet", "type": "dc-terminal"}]


def test_none_is_a_claim_and_exports_nothing():
    """`none` says the CHASSIS carries the inlet. The MX960's four C20
    receptacles sit on a strip above the supplies and `build` exports them
    (#286); this supply must stay empty or the chassis's four are counted
    twice. The pair is asserted in test_dcim_interfaces.py."""
    assert (_psus()["juniper/mx960-psu-ac"].get("attrs") or {})["inlet"] == "none"
    assert dx.INLET_TYPE["none"] is None
    d = _module_exports().get("MX960 AC PSU")
    if d is None:
        pytest.skip("the MX960 AC PSU is not in this library")
    assert not d.get("power-ports")


def test_a_composed_part_still_wins():
    """The three Dell supplies carry both a composed inlet and the token, and
    have since they were modelled. The part is more specific - it knows its own
    id, and there may be several - so it decides."""
    d = _module_exports().get("psu-1100w-ac-14g")
    if d is None:
        pytest.skip("the Dell 1100 W AC supply is not in this library")
    assert d.get("power-ports") == [{"name": "inlet", "type": "iec-60320-c14"}]


def test_a_typed_inlet_is_not_also_listed_as_a_fact_with_no_field():
    """The comments carry `attrs` the schema has no field for. Once the token
    types, the schema plainly has one, and listing it under that heading tells
    the reader something false about their own DCIM."""
    d = _module_exports().get("PSU-302-DESR")
    if d is None:
        pytest.skip("PSU-302-DESR is not in this library")
    assert "inlet: dc-terminal" not in (d.get("comments") or "")
    assert "input: dc" in (d.get("comments") or ""), "the other facts still list"


# --- the rule ----------------------------------------------------------------

def test_l95_is_registered_as_a_component_rule():
    assert lint.RULES["L95"][0] == "component"


def test_the_backlog_is_named_and_shrinking():
    """A CENSUS WARNING, of the L92/L93 kind: it fired on 31 the day it landed
    and is meant to shrink. The ten left are the ones the library genuinely
    cannot answer - the Cisco supplies whose contracts say nothing about power
    entry, the MX240's 'C-type appliance inlet' (some IEC 60320 receptacle, and
    calling that `other` would be a wrong answer dressed as a modest one), and
    the C40G's, whose inlet is on a face this model does not draw.

    The assertion is an upper bound, not an equality: filling one in is a good
    day's work and must not fail the suite.
    """
    silent = [ref for ref, d in _psus().items()
              if not (d.get("attrs") or {}).get("inlet")
              and not any(isinstance(p, dict) and "inlet" in p.get("ref", "")
                          for p in (d.get("parts") or []))]
    assert len(silent) <= 10, (
        f"{len(silent)} supplies say nothing about power entry, up from 10: {sorted(silent)}")
    assert len(_psus()) >= 55, "the census did not find the catalogue"
