"""kit/index.html is the page the visual gates are run in, so it has to keep working.

`docs/modelling-a-device.md` gate 5 asks a contributor to put the render beside the
reference at matched scale, and CONTRIBUTING asks for the sentence that comes out of
doing it. Neither is possible without a page to look at the render in. That is what
this file exists for, and why it is worth a test at all: it is not a demo, it is a
tool the documented process depends on.

WHAT ROTS IS THE SEAM, NOT THE PAGE. The page carries almost no logic - the shell and
the 3D viewer are kit modules - so the thing that breaks is `kit/shell.js` changing
what `createShell` hands back while the page goes on calling it. That is invisible
until somebody opens the page, which on a repository where the page is not part of any
build is a long time. This draft sat unopened for 170 commits and survived by luck.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
PAGE = KIT / "index.html"


@pytest.fixture(scope="module")
def page():
    return PAGE.read_text()


def _page_code(text):
    """The page's script, with comments and the import line removed.

    All three would otherwise be read as usage: the header comment names the shell,
    `from './shell.js'` looks exactly like `shell.js` being called, and so does a
    JS line comment explaining which shell the page is running against.

    THE LINE COMMENTS ARE NOT A THIRD KIND OF THE SAME MISTAKE, they are the same
    one: this parser reads prose as code, and the fix is to stop showing it prose
    rather than to ask contributors not to write `shell.js` in a comment. The page
    now explains at some length which shell methods it needs and why - that is the
    documentation the seam deserves - and every sentence of it was a false
    `shell.js` call until this stripped them.

    `(?<!:)` keeps the `https://` in the import map from being read as a comment.
    """
    src = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"(?<!:)//[^\n]*", "", src)
    return re.sub(r"""import\s*\{[^}]*\}\s*from\s*['"][^'"]+['"]""", "", src)


def _strip_comments(src):
    """JS with its comments taken out.

    THE SAME DEFECT AS `_page_code`'S, ON THE OTHER SIDE OF THE SEAM. This parser
    reads prose as code too: a shorthand key on a line preceded by a comment -
    `viewer3d.js` explains `frus` with "what a host needs to rebuild the chrome
    this module gave up" - arrives as one piece of comment-plus-name, which
    matches no identifier, so the key silently vanishes from the surface and the
    page is told it calls something the module does not return. Stripping is the
    fix in both places, for the same reason: stop showing the parser prose.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"(?<!:)//[^\n]*", "", src)


def _object_keys(block):
    """The keys of a JS object literal body, split on top-level commas."""
    out = set()
    for piece in re.split(r",(?![^(]*\))", _strip_comments(block)):
        name = piece.strip().split(":")[0].strip()
        if re.fullmatch(r"[A-Za-z_$][\w$]*", name):
            out.add(name)
    return out


def _shell_surface():
    """(what createShell returns, what its `el` holds) read out of kit/shell.js."""
    js = (KIT / "shell.js").read_text()
    body = js[js.index("export function createShell"):]
    ret = body[body.index("\n  return {") + len("\n  return {"):]
    ret = ret[:ret.index("\n  };")]
    el = body[body.index("const el = {") + len("const el = {"):]
    el = el[:el.index("};")]
    return _object_keys(ret), _object_keys(el)


def test_the_page_is_in_the_tree():
    """A viewer that lives on a deploy host is a viewer a contributor has not got."""
    assert PAGE.is_file()


def test_every_module_the_page_imports_exists(page):
    """Static and dynamic imports both - the 3D viewer is imported on first use."""
    missing = [m for m in re.findall(r"""from\s*['"](\./[^'"]+)['"]|import\(\s*['"](\./[^'"]+)['"]""", page)
               for m in m if m and not (KIT / m).exists()]
    assert not missing, f"kit/index.html imports files that are not there: {missing}"


def test_the_page_only_calls_shell_methods_the_shell_returns(page):
    """THE SEAM. If `createShell` stops handing back something the page calls, the
    page breaks silently and nothing else in the suite notices."""
    code = _page_code(page)
    used = set(re.findall(r"\bshell\.([A-Za-z_$][\w$]*)", code)) - {"el"}
    returned, _ = _shell_surface()
    assert used, "parsed no shell calls at all - the parser has stopped working"
    assert not (used - returned), (
        f"kit/index.html calls shell.{sorted(used - returned)} and kit/shell.js "
        f"returns {sorted(returned)}")


def test_the_page_only_reaches_for_elements_the_shell_builds(page):
    code = _page_code(page)
    used = set(re.findall(r"\bshell\.el\.([A-Za-z_$][\w$]*)", code))
    _, el = _shell_surface()
    assert used, "parsed no shell.el uses at all - the parser has stopped working"
    assert not (used - el), (
        f"kit/index.html reaches for shell.el.{sorted(used - el)}; the shell builds "
        f"{sorted(el)}")


def test_the_seam_test_would_notice_a_rename():
    """NON-VACUITY, and this file needs it more than most.

    Both checks above pass by finding nothing missing, which is also what they do if
    the parser silently stops matching. Rename one method in a copy of the page and
    the check has to fail.
    """
    returned, _ = _shell_surface()
    code = _page_code(PAGE.read_text()).replace("shell.select", "shell.selectTheThing")
    used = set(re.findall(r"\bshell\.([A-Za-z_$][\w$]*)", code)) - {"el"}
    assert "selectTheThing" in used, "the parser did not see the renamed call"
    assert used - returned == {"selectTheThing"}


def _viewer_surface():
    """What `createViewer` hands back, read out of kit/viewer3d.js."""
    js = (KIT / "viewer3d.js").read_text()
    body = js[js.index("export function createViewer"):]
    ret = body[body.index("\n  return {") + len("\n  return {"):]
    return _object_keys(ret[:ret.index("\n  };")])


def test_the_page_only_calls_viewer_methods_the_viewer_returns(page):
    """THE OTHER HALF OF THE SEAM, and it was not covered.

    The shell half above has been checked since this file was written; the viewer
    half had nobody watching it, which mattered the moment the page started doing
    more than load and select. `setStates` and `setPulled` are how a lit lamp and
    an unseated card reach the scene at all - the two things gate 5 asks a
    contributor to look at - and a rename in viewer3d.js would take both out with
    no failure anywhere until somebody opened the page and clicked.
    """
    code = _page_code(page)
    used = set(re.findall(r"\b(?:viewer|v)\.([A-Za-z_$][\w$]*)", code))
    returned = _viewer_surface()
    assert used, "parsed no viewer calls at all - the parser has stopped working"
    assert not (used - returned), (
        f"kit/index.html calls viewer.{sorted(used - returned)} and kit/viewer3d.js "
        f"returns {sorted(returned)}")


def test_the_viewer_seam_test_would_notice_a_rename():
    """Non-vacuity, for the same reason the shell one has it."""
    returned = _viewer_surface()
    code = _page_code(PAGE.read_text()).replace("v.setPulled", "v.setPulledTheThing")
    used = set(re.findall(r"\b(?:viewer|v)\.([A-Za-z_$][\w$]*)", code))
    assert "setPulledTheThing" in used, "the parser did not see the renamed call"
    assert used - returned == {"setPulledTheThing"}


def test_three_js_is_asked_for_by_version_and_not_bundled(page):
    """NOTICE says three.js is 'Not bundled ... an optional peer dependency that the
    host page supplies', so this page is the host that supplies it. Pinned to an exact
    version: a floating range would make the 3D gate depend on what shipped today."""
    imports = re.search(r'<script type="importmap">(.*?)</script>', page, re.S)
    assert imports, "the page must supply three.js itself; the kit resolves nothing"
    assert re.search(r"three@\d+\.\d+\.\d+", imports.group(1)), \
        "pin three.js to an exact version"
    assert not list(KIT.glob("three*.js")), "three.js must not be vendored into kit/"
