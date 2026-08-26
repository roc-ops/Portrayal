"""The search haystack has to be the same on two builds of the same tree.

`search_blob` collects component refs into a set and used to iterate it
unsorted, so devices.json came out with the same tokens in a different order
every time the build ran in a fresh process. Nothing about the FILTER cared -
it matches tokens - but a build that differs from itself cannot be checked by
checksum, and "the rendered output is byte-identical" is how this project
verifies that a refactor moved nothing. Two agents leaned on exactly that
check today.

A single-process test cannot see this: set order is stable within one
interpreter. It only appears across processes, so that is what this runs.
"""
import subprocess
import sys
import textwrap
from pathlib import Path

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"

SNIPPET = textwrap.dedent(f"""
    import sys, yaml
    sys.path.insert(0, {str(SPEC / "tools/portrayal")!r})
    from devices_index import search_blob
    man = {str(LIB / "devices/ufispace/s9510-28dc/device.yaml")!r}
    d = yaml.safe_load(open(man).read())
    print(search_blob(d, __import__("pathlib").Path(man).parent))
""")


def _blob(seed):
    """One fresh interpreter with a chosen hash seed, which is what decides set order."""
    return subprocess.run([sys.executable, "-c", SNIPPET], capture_output=True, text=True,
                          env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"},
                          check=True).stdout.strip()


def test_the_haystack_does_not_depend_on_hash_seed():
    seeds = ["0", "1", "12345"]
    blobs = {s: _blob(s) for s in seeds}
    first = blobs[seeds[0]]
    assert first, "the fixture device produced no search blob at all"
    for s in seeds[1:]:
        assert blobs[s] == first, (
            f"search blob differs under PYTHONHASHSEED={s}; a set is being "
            f"iterated unsorted in search_blob")


def test_the_tokens_themselves_did_not_change():
    """Ordering was the bug. Losing or gaining a token would be a different one,
    and this is the assertion that tells the two apart."""
    blob = _blob("0")
    # component refs, a group attr and a device attr - one of each source that
    # feeds the blob, so a regression in any of them fails here. NOT "arcos":
    # the S9510 has no overlay of its own, and asserting it would be asserting
    # a fact about a different device.
    for token in ("qsfp-cage", "sfp-ganged", "400g", "800"):
        assert token in blob.split(), f"{token!r} fell out of the haystack"
