"""The elements file's `parent` is the Explorer's tree, row for row (#727).

The nesting rule exists twice: kit/swap.js `faceTree`, which shell.js
buildTree returns, and elements.py `face_tree`, which writes `parent` into
every published `<face>.elements.json`. A rule that exists twice drifts, and
the place it drifts is a fallback - a projection's host, a cutout's filler,
a single local `data-for` owner, the chassis for a lamp that watches another
view - so the faces checked here are chosen to exercise every one of them on
real compiled output, and the test asserts that each rule actually fired
on them. Parity itself is checked over every face in the build.

The kit's function runs under node on spec/tests/js/fake-dom.mjs, fed the
elements of every face exactly as library/dist holds it, and its rows are
compared with the published file's: the same keys with the same parents.
"""
import json
import pathlib
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
SCRIPT = ROOT / "spec/tests/js/face-tree-parity.mjs"

# Each face is here for a rule; `rules` below proves it still exercises it.
FACES = [
    "asr-9006.ac.front.svg",              # seated line cards in bays
    "ch3000.half-depth-mix.front.svg",    # seated modules, caps occupying their cages
    "fhd-1ufce.populated.rear.svg",       # cassette backs drawn as projections
    "ds3001.f2b.front.svg",               # 333 cutouts, most filled by a port
    "agr110.ac.front.svg",                # lamps whose only target is /rear/...
    "c40g.base.front.svg",                # a placed cover `for` four PSU bays
]


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _spec(el):
    """A drawing as fake-dom builds it: {t, a, c}, elements only."""
    return {"t": _local(el.tag), "a": {_local(k): v for k, v in el.attrib.items()},
            "c": [_spec(c) for c in el if isinstance(c.tag, str)]}


@pytest.fixture(scope="module")
def faces(tmp_path_factory):
    """EVERY FACE IN THE BUILD, not a sample: the whole of library/dist runs
    through the kit in about four seconds, so there is no reason to trust a
    handful. Fed in chunks to keep each node process's input modest."""
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    if not (DIST / "devices.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    missing = [f for f in FACES if not (DIST / f).exists()]
    assert not missing, f"the parity faces left the build: {missing}; choose others " \
                        "that exercise the same rules"
    names = sorted(p.name for p in DIST.glob("*.svg") if len(p.name.split(".")) == 4)
    tmp = tmp_path_factory.mktemp("parity")
    out = {}
    for i in range(0, len(names), 300):
        chunk = names[i:i + 300]
        src = tmp / f"faces-{i}.json"
        src.write_text(json.dumps({f: _spec(ET.parse(DIST / f).getroot()) for f in chunk}))
        p = subprocess.run(["node", str(SCRIPT), str(src)], capture_output=True, text=True,
                           cwd=str(SCRIPT.parent))
        assert p.returncode == 0, p.stderr
        kit = json.loads(p.stdout.strip().splitlines()[-1])
        for f in chunk:
            pub = json.loads((DIST / (f[:-4] + ".elements.json")).read_text())
            out[f] = {"kit": [tuple(r) for r in kit[f]], "rows": pub["elements"]}
    return out


def _published(rows):
    return [(r.get("path", r.get("of")), r["parent"]) for r in rows]


def test_parents_match_the_explorer(faces):
    assert len(faces) > 1000, f"only {len(faces)} faces; the build is not the library"
    differ, rows = [], 0
    for face, got in faces.items():
        kit, pub = got["kit"], _published(got["rows"])
        rows += len(kit)
        # the kit lists depth-first from the roots; the file is document order
        if sorted(kit) != sorted(pub):
            differ.append((face, sorted(set(kit) ^ set(pub))[:4]))
    assert rows > 100000, f"only {rows} rows compared"
    assert not differ, f"{len(differ)} faces differ from the Explorer: {differ[:5]}"


def test_the_explorer_tree_is_face_tree():
    """The parity above is with `faceTree`; this holds the Explorer to it. A
    buildTree that grew its own nesting again would pass every row above."""
    js = (ROOT / "kit/shell.js").read_text()
    body = js[js.index("function buildTree(root) {"):]
    body = body[:body.index("\n  }\n")]
    assert "return faceTree(root, entries);" in body
    assert "byPath" not in body, "shell.js buildTree nests rows itself again"


def test_every_fallback_fired_somewhere(faces):
    """A parity test over faces that never reach a rule proves nothing about
    that rule. Count each one on the published rows."""
    fired = {"prefix": 0, "projection-host": 0, "cutout-filler": 0,
             "for-owner": 0, "chassis-fallback": 0, "seated": 0}
    for face in FACES:                  # the chosen faces must still reach every rule
        rows = faces[face]["rows"]
        for r in rows:
            key, up = r.get("path", r.get("of")), r["parent"]
            if r.get("seat"):
                fired["seated"] += 1
            if up is None:
                continue
            if key.startswith(up + "/"):
                fired["prefix"] += 1
            elif "of" in r:
                fired["projection-host"] += 1
            elif key.startswith("cutout:") and key[7:] == up:
                fired["cutout-filler"] += 1
            elif up == "chassis" and r.get("for"):
                fired["chassis-fallback"] += 1
            elif up in (r.get("for") or []):
                fired["for-owner"] += 1
    assert all(fired.values()), f"a rule went unexercised: {fired}"
