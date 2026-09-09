"""Everything buildFaceRelief destructures must be something extractRelief returns.

The two halves of relief.js talk through one object literal: `extractRelief`
reads the face SVG and returns a bag of collections, and `buildFaceRelief`
destructures that bag and turns it into meshes. Nothing checks that the two
agree, and nothing can at import time - the mismatch only bites when a viewer
actually builds a face.

It bit for real. A `flatLifted` collection was added to `extractRelief` and used
in `buildFaceRelief` without being added to the return, and the viewer failed at
runtime with "flatLifted is not defined". `node --check` passes that happily,
because it is a scope error and not a syntax one, and the unit tests pass too
because none of them builds a face. The first thing that noticed was a person
opening the 3D view.

This is a text check rather than an execution one on purpose: exercising
buildFaceRelief needs a DOM, a WebGL context and THREE, and the bug is not in the
building - it is in the handoff, which is two lines of source that can simply be
read.
"""
import re
from pathlib import Path

import pytest

RELIEF = Path(__file__).resolve().parents[2] / "kit" / "relief.js"


def _extract_return(src):
    """extractRelief's own return object, not the first one in the file.

    The first cut of this test matched `return {x, y, w, h}` from an unrelated
    helper and reported every name as missing - a test that fails for its own
    reasons teaches nothing. Slice the function body first: from its signature to
    the next top-level declaration, then take the last object return in it.
    """
    i = src.index("export async function extractRelief(")
    j = src.find("\nexport ", i + 1)
    body = src[i:j if j > 0 else len(src)]
    rets = re.findall(r"\n  return \{([^}]*)\};", body)
    assert rets, "extractRelief has no object return"
    return rets[-1]


def _names(block):
    """Identifiers in a destructuring or object literal, ignoring defaults."""
    out = []
    for part in re.split(r",(?![^{]*})", block):
        part = part.strip()
        if not part:
            continue
        out.append(re.split(r"[:=]", part)[0].strip())
    return [n for n in out if re.fullmatch(r"\w+", n)]


@pytest.mark.skipif(not RELIEF.exists(), reason="kit/relief.js not present")
def test_the_extract_to_build_handoff_has_no_missing_names():
    src = RELIEF.read_text()

    returned = set(_names(_extract_return(src)))

    dest = re.search(r"const \{([^}]*)\}\s*=\s*await extractRelief\(", src, re.S)
    assert dest, "could not find buildFaceRelief's destructuring of extractRelief"
    wanted = set(_names(dest.group(1)))

    missing = sorted(wanted - returned)
    assert not missing, (
        "buildFaceRelief destructures %s from extractRelief, which does not return "
        "them. The viewer will throw '<name> is not defined' the moment it builds a "
        "face; node --check will not see it and neither will any test that does not "
        "render." % missing
    )


@pytest.mark.skipif(not RELIEF.exists(), reason="kit/relief.js not present")
def test_every_collection_extract_returns_is_actually_consumed():
    """The other direction: a collection built and then never read is dead work.

    Weaker than the check above - it is a smell rather than a fault - so it names
    what it found instead of guessing why.
    """
    src = RELIEF.read_text()
    dest = re.search(r"const \{([^}]*)\}\s*=\s*await extractRelief\(", src, re.S)
    if not dest:
        pytest.skip("relief.js handoff not in the expected shape")
    unused = sorted(set(_names(_extract_return(src))) - set(_names(dest.group(1))))
    assert not unused, (
        "extractRelief returns %s and buildFaceRelief never destructures them - "
        "either the consumer was dropped or the producer is dead work" % unused
    )
