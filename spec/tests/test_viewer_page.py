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

    Both would otherwise be read as usage: the header comment names the shell, and
    `from './shell.js'` looks exactly like `shell.js` being called.
    """
    src = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return re.sub(r"""import\s*\{[^}]*\}\s*from\s*['"][^'"]+['"]""", "", src)


def _object_keys(block):
    """The keys of a JS object literal body, split on top-level commas."""
    out = set()
    for piece in re.split(r",(?![^(]*\))", block):
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


def test_three_js_is_asked_for_by_version_and_not_bundled(page):
    """NOTICE says three.js is 'Not bundled ... an optional peer dependency that the
    host page supplies', so this page is the host that supplies it. Pinned to an exact
    version: a floating range would make the 3D gate depend on what shipped today."""
    imports = re.search(r'<script type="importmap">(.*?)</script>', page, re.S)
    assert imports, "the page must supply three.js itself; the kit resolves nothing"
    assert re.search(r"three@\d+\.\d+\.\d+", imports.group(1)), \
        "pin three.js to an exact version"
    assert not list(KIT.glob("three*.js")), "three.js must not be vendored into kit/"
