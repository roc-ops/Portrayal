"""`superseded-by` (L101): a part says it is RETIRED, as a fact and not a
sentence.

`unplaced:` and `superseded-by` look like they could be the same field - both
sit on a contract nothing is required to seat - but they answer different
questions. `unplaced:` says WHY NOTHING SEATS THIS PART, for a reader deciding
whether to use, extend or delete it, and it is required minimum-length prose so
it always carries an answer. It is also true of parts that are very much alive:
every `generic/sfp-lc@1`-shaped contract under `generic/` carries one too,
because a generic is seated by configurations downstream of this library
(docs/pluggables-design.md, decision 2) - deliberate, not a defect, and not
retirement. `superseded-by` says the opposite kind of thing: a specific
successor exists, this major should gain no new occupants, and a consumer
offering parts to a user must not offer this one. Before this field, the only
record of that fact for `common/sfp-lc-duplex@1` and `common/qsfp-transceiver@1`
was the opening word of their `unplaced:` sentence - SUPERSEDED - which nothing
in the tree read. A later swap-list feature needs to filter on retirement
specifically; filtering on `unplaced:` would catch every `generic/` part too and
empty the list.
"""
import pathlib

import yaml

import libdata
from portrayal import lint as L

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = [str(ROOT / "library")]

RETIRED = {
    "common/sfp-lc-duplex@1": "generic/sfp-lc@1",
    "common/qsfp-transceiver@1": "generic/qsfp-lc@1",
}


def major_ref(ref, path):
    """`libdata.components()` keys by `ns/name`, dropping the `@major` a
    retirement fact needs to be unambiguous. Rebuild it from the `vN`
    directory, the same way `lint._major_of` does, off the same path."""
    return f"{ref}@{path.parent.name[1:]}"


def run(doc, path="t/contract.yaml", lib=LIB):
    with L.collecting() as found:
        L.lint_component_superseded_by(path, doc, lib)
    return [e for e in found.errors if "[L101]" in e]


# --- the live library -----------------------------------------------------

def test_the_two_retired_parts_carry_superseded_by():
    """Exactly the two parts the brief names, naming exactly the successors
    spec A built to replace them."""
    docs = {major_ref(ref, path): doc for ref, path, doc in libdata.components()
             if major_ref(ref, path) in RETIRED}
    assert set(docs) == set(RETIRED), docs
    for ref, successor in RETIRED.items():
        assert docs[ref].get("superseded-by") == successor, ref


def test_superseded_by_resolves_to_a_real_component():
    """Not just present - a working pointer. Both successors are generics
    already in the library, and the lint rule itself must find them clean."""
    by_ref = {major_ref(ref, path): doc for ref, path, doc in libdata.components()}
    for ref, successor in RETIRED.items():
        assert successor in by_ref, f"{ref} points at {successor}, which is not in the library"
    for ref, path, doc in libdata.components():
        if major_ref(ref, path) in RETIRED:
            assert run(doc, path=str(path)) == [], (ref, run(doc, path=str(path)))


def test_no_generic_part_carries_superseded_by():
    """A generic stands for every module of its kind (L99's territory) and is
    seated downstream by design - it is never itself a retired part. If one
    ever gained `superseded-by`, that would mean a whole shape was being
    retired, which is a different, much louder change than this field is for."""
    offenders = [ref for ref, _path, doc in libdata.components()
                 if ref.startswith("generic/") and doc.get("superseded-by")]
    assert offenders == [], offenders


def test_a_retired_part_still_carries_its_unplaced_sentence():
    """The two fields are not a swap - `unplaced:` still answers its own
    question (why nothing seats it) even once `superseded-by` answers a
    different one (what replaced it). The brief is explicit that this prose is
    left alone, not migrated away."""
    docs = {major_ref(ref, path): doc for ref, path, doc in libdata.components()
             if major_ref(ref, path) in RETIRED}
    for ref, doc in docs.items():
        unplaced = doc.get("unplaced")
        assert unplaced and len(unplaced) >= 40, ref
        assert "SUPERSEDED" in unplaced, ref


# --- the rule, on contracts built to exercise one thing each ---------------

def test_no_superseded_by_is_not_asked():
    assert run({"class": "transceiver"}) == []


def test_a_superseded_by_that_resolves_is_clean():
    got = run({"class": "transceiver", "superseded-by": "generic/sfp-lc@1"})
    assert got == [], got


def test_a_dangling_superseded_by_is_an_error(tmp_path):
    """ERROR, not warning - a dangling successor reads as a working pointer,
    which is worse than no pointer at all."""
    got = run({"class": "transceiver", "superseded-by": "fs/not-a-real-part@1"},
               lib=[str(tmp_path)])
    assert len(got) == 1, got
    assert "not in the library" in got[0]
    assert "fs/not-a-real-part@1" in got[0]


def test_a_self_pointer_is_an_error(tmp_path):
    """THE ONE THAT RESOLVES AND STILL LIES. A contract at
    `components/common/sfp-lc-duplex/v1/` naming `common/sfp-lc-duplex@1` as
    its successor passes "the ref resolves" - the file it names is itself -
    and a consumer following the pointer to show the replacement loops. The
    path is a real one in the real library, so `libwalk.ref_of` has the
    grammar it needs to recognise the part.

    NOT VACUOUS: the same contract with the successor it actually carries is
    clean below, so what fails here is the self-pointer and not the path."""
    path = "library/components/common/sfp-lc-duplex/v1/contract.yaml"
    got = run({"class": "transceiver",
               "superseded-by": "common/sfp-lc-duplex@1"}, path=path)
    assert len(got) == 1, got
    assert "this part itself" in got[0], got[0]

    assert run({"class": "transceiver",
                "superseded-by": "generic/sfp-lc@1"}, path=path) == []


def test_a_superseded_by_built_in_a_synthetic_library_resolves(tmp_path):
    """The rule reads the library it is handed, not a hardcoded one - a
    successor that exists only in a throwaway tree still resolves."""
    d = tmp_path / "components" / "generic" / "sfp-lc" / "v1"
    d.mkdir(parents=True)
    (d / "contract.yaml").write_text(
        "format: 1\nkind: component\nname: sfp-lc\nversion: 1.0.0\n"
        "class: transceiver\nsize: {w: 1, h: 1}\n")
    got = run({"class": "transceiver", "superseded-by": "generic/sfp-lc@1"},
               lib=[str(tmp_path)])
    assert got == [], got


def test_l101_is_registered_as_a_component_rule():
    assert L.RULES["L101"][0] == "component"


# --- the schema --------------------------------------------------------------

def test_the_schema_accepts_a_valid_ref_and_rejects_a_malformed_one():
    import json
    import jsonschema
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    v = jsonschema.Draft202012Validator(schema)
    part = {"format": 1, "kind": "component", "name": "t", "version": "1.0.0",
            "class": "transceiver", "size": {"w": 1.0, "h": 1.0}}
    assert not list(v.iter_errors(dict(part, **{"superseded-by": "generic/sfp-lc@1"})))
    assert list(v.iter_errors(dict(part, **{"superseded-by": "not a ref"})))


def test_the_live_contracts_still_validate_against_the_schema():
    """Sanity check that the two edits under `library/` are well-formed YAML
    that satisfies the schema this task also changed - belt and braces beyond
    what a full lint run already covers."""
    import json
    import jsonschema
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    v = jsonschema.Draft202012Validator(schema)
    for ref, path in (("common/sfp-lc-duplex@1",
                        ROOT / "library/components/common/sfp-lc-duplex/v1/contract.yaml"),
                       ("common/qsfp-transceiver@1",
                        ROOT / "library/components/common/qsfp-transceiver/v1/contract.yaml")):
        doc = yaml.safe_load(path.read_text())
        errs = list(v.iter_errors(doc))
        assert errs == [], (ref, errs)
