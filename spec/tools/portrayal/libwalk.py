"""Walking the library, and turning a ref into the file it names.

ONE GRAMMAR, IN ONE PLACE. `ns/name@major` resolves to
`<root>/components/<ns>/<name>/v<major>/contract.yaml`, and that sentence was
written out by hand in eleven places - six times in `lint.py`, once in
`render.py`'s resolver, and in four tools besides. A change to the ref grammar
touched all of them, and a reader checking one had no way to know the other ten
agreed (#181).

The same for walking: `glob("devices/*/*/device.yaml")` appeared ten times
across the tools and thirty more across the tests, each with its own idea of
whether to sort, whether to skip a non-device, and whether to read the file with
`yaml.safe_load` or with `manifest.load_yaml` - which is not the same thing,
because `load_yaml` reports the FILE when a document is malformed and
`safe_load` reports a line number in a stream nobody named.

Nothing here caches. Callers that need a cache have one already and know what
their key is; a cache in here would be a second one with a different lifetime.
"""
import re
from pathlib import Path

from portrayal.manifest import load_yaml

# `ns/name@major`: the namespace and the part are lowercase segments, the major
# is the version DIRECTORY's number - `v1` on disk, `@1` in a ref. Anchored, so
# a ref with a trailing space or an embedded slash fails here rather than three
# frames down in a path that does not exist.
REF = re.compile(r"^(?P<ns>[a-z0-9][a-z0-9-]*)/(?P<name>[a-z0-9][a-z0-9._-]*)@(?P<major>\d+)$")


def split_ref(ref):
    """`common/rj45-eth@1` -> ("common", "rj45-eth", "1"), or None.

    None rather than an exception: half the callers are lint rules whose whole
    job is to report a malformed ref as a finding, and a raise would make them
    catch it back.
    """
    m = REF.match(str(ref or ""))
    return (m["ns"], m["name"], m["major"]) if m else None


def contract_path(ref, roots):
    """The contract file a ref names, or None if no root holds it.

    `roots` is the `--library` list every tool already carries, searched in
    order, because a device can be linted against a checkout plus an overlay.
    """
    parts = split_ref(ref)
    if not parts:
        return None
    ns, name, major = parts
    for r in roots:
        f = Path(r) / "components" / ns / name / f"v{major}" / "contract.yaml"
        if f.exists():
            return f
    return None


def load_contract(ref, roots):
    """The parsed contract a ref names, or None."""
    f = contract_path(ref, roots)
    return load_yaml(f) if f else None


def _roots(roots):
    """One root given bare, or several in a sequence - always a sequence."""
    return [roots] if isinstance(roots, (str, Path)) else list(roots)


def iter_devices(roots):
    """Every device.yaml under every root, sorted, as paths. A LIST.

    SORTED, ALWAYS. Filesystem order is not stable across machines, and this
    walk feeds the lock, the indexes and a dozen censuses whose output is
    committed - a build that differs by directory order is a diff nobody can
    review. Several of the ten hand-rolled copies sorted and several did not.

    A LIST, NOT A GENERATOR, and the sort is the reason it costs nothing. This
    yielded for one release, and `sorted()` inside a generator had already
    materialised each root's whole glob before the first item came out - so the
    laziness bought no memory at all. What it did buy was a walk that answers
    114 devices on the first pass and ZERO on the second, and a caller that
    binds it once and iterates it twice gets a real check the first time and a
    vacuous pass every time after.

    `test_attrs_sections.py` was that caller: six tests over one exhausted
    generator, five of which had never run. Making them run found a transceiver
    operating range filed under `attrs.features`. Under `-n auto` which test
    goes first varies, so the vacuity was invisible AND intermittent - nothing
    failed, and the coverage simply was not there. Re-iterability is the
    property every caller here actually wants; none of the twenty-odd call
    sites wants a stream.
    """
    return [f for r in _roots(roots)
            for f in sorted(Path(r).glob("devices/*/*/device.yaml"))]


def iter_components(roots):
    """Every contract.yaml under every root, sorted, as paths - all majors.

    A LIST, for the reason `iter_devices` gives at length.
    """
    return [f for r in _roots(roots)
            for f in sorted(Path(r).glob("components/*/*/*/contract.yaml"))]


def ref_of(contract_file):
    """The inverse: a contract path -> the `ns/name@major` that names it."""
    p = Path(contract_file)
    return f"{p.parent.parent.parent.name}/{p.parent.parent.name}@{p.parent.name[1:]}"
