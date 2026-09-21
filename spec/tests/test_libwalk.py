"""One walk and one ref grammar, instead of eleven copies of each.

`ns/name@major` resolves to `<root>/components/<ns>/<name>/v<major>/contract.yaml`,
and that sentence was written out by hand in eleven places - six times in
`lint.py`, once in `render.py`'s resolver, and in four tools besides. A change
to the ref grammar touched all of them, and a reader checking one had no way to
know the other ten agreed (#181).

The same for walking: `glob("devices/*/*/device.yaml")` appeared in ten tools
and twenty-one tests, each with its own idea of whether to sort.

THE GRAMMAR IS ASSERTED AGAINST THE CORPUS, not against examples. A regex that
accepts every ref in a handful of unit tests and rejects one real part is a
silent resolution failure - `contract_path` would answer None and the caller
would read it as "no such component".
"""
import pathlib

import pytest

from portrayal import libwalk
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


def _refs_in(node, out):
    """Refs read from the STRUCTURE, not scanned out of the text.

    Scanning the text first found "21 malformed refs", every one of them a
    fragment the regex had started matching mid-string - `ac@1` off the tail of
    `common/psu-ac@1`. Searching prose measures the searcher.
    """
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("ref", "default") and isinstance(v, str) and "@" in v:
                out.add(v)
            elif k == "accepts" and isinstance(v, list):
                out |= {x for x in v if isinstance(x, str) and "@" in x}
            else:
                _refs_in(v, out)
    elif isinstance(node, list):
        for v in node:
            _refs_in(v, out)


@pytest.fixture(scope="module")
def corpus_refs():
    out = set()
    for f in list(libwalk.iter_devices([LIB])) + list(libwalk.iter_components([LIB])):
        _refs_in(load_yaml(f) or {}, out)
    return out


def test_the_grammar_accepts_every_ref_the_library_states(corpus_refs):
    assert len(corpus_refs) > 400, f"only {len(corpus_refs)} refs found; the walk is wrong"
    bad = sorted(r for r in corpus_refs if not libwalk.split_ref(r))
    assert not bad, f"well-formed in the library, rejected by the grammar: {bad}"


def test_every_ref_the_library_states_resolves_to_a_file(corpus_refs):
    """The end of the chain. A ref that parses and does not resolve is a
    component nothing can draw, and `contract_path` answering None reads to
    every caller as "no such part" rather than as "look again"."""
    missing = sorted(r for r in corpus_refs if not libwalk.contract_path(r, [LIB]))
    assert not missing, missing


def test_a_malformed_ref_is_none_and_not_an_exception():
    """Half the callers are lint rules whose job is to REPORT a malformed ref as
    a finding; a raise would make them catch it back. One of the six copies this
    replaced wrapped the unpack in try/except and three beside it did not."""
    for bad in ("", "nope", "no-slash@1", "ns/name", "ns/name@", "ns/name@v1",
                "NS/name@1", "ns/name@1 ", "a/b@1/c"):
        assert libwalk.split_ref(bad) is None, bad
        assert libwalk.contract_path(bad, [LIB]) is None, bad
        assert libwalk.load_contract(bad, [LIB]) is None, bad


def test_resolution_and_its_inverse_agree(corpus_refs):
    for ref in sorted(corpus_refs):
        assert libwalk.ref_of(libwalk.contract_path(ref, [LIB])) == ref


def test_the_walks_find_the_library_and_are_sorted():
    devs = list(libwalk.iter_devices([LIB]))
    comps = list(libwalk.iter_components([LIB]))
    assert len(devs) > 80 and len(comps) > 400
    assert devs == sorted(devs) and comps == sorted(comps)
    assert all(p.name == "device.yaml" for p in devs)
    assert all(p.name == "contract.yaml" for p in comps)


def test_the_walk_is_sorted_because_committed_output_depends_on_it():
    """Filesystem order is not stable across machines, and this walk feeds the
    lock, the indexes and a dozen censuses whose output is COMMITTED. Several of
    the ten hand-rolled copies sorted and several did not."""
    import random
    devs = list(libwalk.iter_devices([LIB]))
    shuffled = devs[:]
    random.shuffle(shuffled)
    assert sorted(shuffled) == devs


def test_nothing_hand_rolls_the_walk_or_the_grammar_any_more():
    """Asserted over the tree, because the next copy will not be on a list."""
    import ast

    def strings_in_code(src):
        """Every string LITERAL that is not a docstring - so a file may name the
        old spelling in prose while explaining why it no longer uses it. The
        first version of this grepped the source and flagged its own docstring,
        which is the mistake #178's sweep made too."""
        tree = ast.parse(src)
        docs = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)) and (d := ast.get_docstring(n, clean=False)):
                docs.add(d)
        return [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n.value not in docs]

    walk, grammar = [], []
    for f in sorted((ROOT / "spec").rglob("*.py")):
        # The module that OWNS the spellings, and the file that forbids them -
        # this one names both globs as literals in the comparison below, which
        # is the only honest way to check for them.
        if f.name in ("libwalk.py", "test_libwalk.py"):
            continue
        lits = strings_in_code(f.read_text())
        if any(g in lits for g in ("devices/*/*/device.yaml",
                                   "components/*/*/*/contract.yaml")):
            walk.append(str(f.relative_to(ROOT)))
        if any("contract.yaml" in s and "v{major}" in s for s in lits):
            grammar.append(str(f.relative_to(ROOT)))
    assert not walk, f"these still hand-roll the walk: {walk}"
    assert not grammar, f"these still hand-roll the ref grammar: {grammar}"


def test_the_walks_can_be_walked_twice():
    """A caller that binds a walk once and iterates it from two tests gets a real
    check the first time and a VACUOUS PASS every time after.

    These yielded for one release. `test_attrs_sections.py` bound
    `MANIFESTS = libwalk.iter_devices([LIB])` at module scope and six tests
    iterated it: 114 devices on the first pass, ZERO on the other five. Nothing
    failed - the five simply did not run, and under `-n auto` WHICH one got the
    devices varied, so the hole moved between runs. Making them run found a
    transceiver operating range filed under `attrs.features` on two devices, and
    it had been invisible for months.

    The sort was always the tell: `sorted()` materialised each root's whole glob
    before the first item came out, so the laziness saved no memory and gave
    away re-iterability for nothing.
    """
    for walk in (libwalk.iter_devices, libwalk.iter_components):
        found = walk([LIB])
        first = list(found)
        assert first, f"{walk.__name__} found nothing - the assertion below would be vacuous"
        assert list(found) == first, (
            f"{walk.__name__} is exhausted by one pass; a module-scope binding "
            f"iterated from two tests would pass the second one vacuously")


def test_nothing_binds_a_lazy_walk_at_module_scope():
    """Belt and braces, and it catches the NEXT lazy helper as well as this one.

    Asserted over the tree because the next module-scope binding will not be on
    a list - the same reason the hand-rolled-walk sweep above is written this
    way. A generator expression at module scope has the identical failure mode
    and no walk of ours has to be involved.
    """
    import ast

    lazy = {"iter_devices", "iter_components", "map", "filter", "zip",
            "glob", "iglob", "rglob", "finditer", "islice", "chain"}
    offenders = []
    for f in sorted((ROOT / "spec" / "tests").rglob("*.py")):
        for node in ast.parse(f.read_text()).body:   # MODULE SCOPE ONLY
            if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
                continue
            v = node.value
            if isinstance(v, ast.GeneratorExp):
                what = "a generator expression"
            elif isinstance(v, ast.Call):
                fn = v.func
                name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
                what = f"{name}()" if name in lazy else None
            else:
                what = None
            if what:
                offenders.append(f"{f.relative_to(ROOT)}:{node.lineno} binds {what}")
    assert not offenders, (
        "module-scope bindings that may be exhausted by the first test that "
        f"iterates them - wrap in list(): {offenders}")


def test_a_root_may_be_given_bare_or_in_a_list():
    """Callers carry `--library` as a list and as a single path in about equal
    numbers, and a walk that silently iterates the CHARACTERS of a string is the
    kind of thing that returns nothing and looks like an empty library."""
    assert list(libwalk.iter_devices(LIB)) == list(libwalk.iter_devices([LIB]))
    assert list(libwalk.iter_devices(str(LIB))) == list(libwalk.iter_devices([LIB]))
