"""The device library, parsed once per test session.

Parsing all 84 manifests takes 4.09 seconds, and 22 places across 15 test
modules were each doing it for themselves. That set the floor for any
library-wide test at four seconds whatever it actually checked, and the worst
re-parsed per item: one test walked the library once per optics key and took 33
seconds to answer a question about seven strings.

It is not a CPU problem, and that matters because the obvious fix was the wrong
one. CI runs on two cores against a twelve-core laptop, and the suite was 13.7
of the run's 19.7 minutes - so `-n auto` looked like the answer. Parallelism
would have bought a constant factor while leaving every worker re-reading the
same YAML.

A MODULE, NOT A FIXTURE, so a test module can use it from a plain helper
function without threading a fixture argument through every signature it calls.
conftest exposes the same data as fixtures for tests that prefer them; both go
through the cache below, so the library is read once either way.

READ-ONLY. The documents are shared. A test that mutates one changes what every
later test sees, and nothing here needs to - a library-wide test asks what the
library says. `copy.deepcopy` if you must.
"""
import functools
import pathlib

import yaml
from portrayal import libwalk

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"


@functools.lru_cache(maxsize=1)
def library():
    """((slug, path, doc), ...) for every device manifest."""
    out = []
    for f in libwalk.iter_devices([LIB]):
        doc = yaml.safe_load(f.read_text())
        if (doc or {}).get("kind") != "device":
            continue
        out.append((f"{f.parent.parent.name}/{f.parent.name}", f, doc))
    return tuple(out)


def devices():
    """((slug, doc), ...) - the common shape."""
    return tuple((slug, doc) for slug, _, doc in library())


@functools.lru_cache(maxsize=1)
def components():
    """((ref, path, doc), ...) for every component contract."""
    out = []
    for f in sorted(LIB.glob("components/*/*/v*/contract.yaml")):
        doc = yaml.safe_load(f.read_text())
        if doc:
            out.append((f"{f.parent.parent.parent.name}/{f.parent.parent.name}", f, doc))
    return tuple(out)
