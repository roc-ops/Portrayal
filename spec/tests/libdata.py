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


def each_device():
    """Every device as a pytest param, with its slug as the id.

    THE POINT IS WHAT A FAILURE SAYS. A library-wide sweep that loops inside one
    test and asserts on a list gives a contributor `['juniper/mx240']` and a test
    name; they then open the test to learn what the rule was. Parametrised, the
    failure names the device in the test id and the rule in the message, and
    `pytest -k mx240` runs every sweep against one device - the equivalent of
    `./build.sh --device` that the suite did not have (#184).

    Use it as `@pytest.mark.parametrize("slug,path,doc", libdata.each_device())`.
    """
    import pytest
    return [pytest.param(slug, path, doc, id=slug) for slug, path, doc in library()]


def each_component():
    """The same for component contracts, keyed `ns/name`."""
    import pytest
    return [pytest.param(ref, path, doc, id=ref) for ref, path, doc in components()]


def built_component(ns_name, skin="default"):
    """The compiled drawing of `ns/name` at its CURRENT major, in
    `library/dist/components/`.

    THE MAJOR IS READ, NOT WRITTEN. A test that names
    `common--lc-duplex-adapter--v6--default.svg` goes quiet the day the part
    moves to v7: the file is gone, the test skips, and the check it made is
    made nowhere. So the major is the library's highest `v<N>` directory for
    the part, checked against that contract's own `version:`.

    SKIP ONLY WHEN THERE IS NO BUILD. With no compiled component drawings at
    all this skips, as every dist test does; with a build present and this one
    file absent it FAILS - a built dist that lacks the part is a finding, not
    an absence of evidence."""
    import pytest
    ns, name = ns_name.split("/")
    contracts = sorted((LIB / "components" / ns / name).glob("v*/contract.yaml"),
                       key=lambda p: int(p.parent.name[1:]))
    assert contracts, f"{ns_name}: no contract in the library"
    major = int(contracts[-1].parent.name[1:])
    version = str((yaml.safe_load(contracts[-1].read_text()) or {}).get("version"))
    assert version.split(".")[0] == str(major), (
        f"{ns_name}: v{major}/contract.yaml says version {version}")
    dist = LIB / "dist" / "components"
    if not any(dist.glob("*.svg")):
        pytest.skip("library/dist/components not built (./publish.sh --no-images)")
    f = dist / f"{ns}--{name}--v{major}--{skin}.svg"
    assert f.exists(), (
        f"the dist is built but {f.name} is not in it: {ns_name}@{major} is the "
        "part's current major, so the build should have drawn it")
    return f
