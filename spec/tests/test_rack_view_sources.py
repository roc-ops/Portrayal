"""What kit/rack/view/ may read and import, and what its package entry and its
goldens must say (docs/rack-views-design.md §1, §4.3, §5, §6). These read files
and run nothing: the drawing itself is compared on the page,
spec/tests/browser/rack-view-2d.html."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
VIEW = KIT / "rack/view"
GOLDENS = ROOT / "spec/tests/fixtures/rack-views"
SITE_COMMIT = "5dbbd41bd35e92a1b46e315eb5d7215213c6aeb0"

# The names a view reads from the document it is given, or from that document's
# window, and never as a global (§1, §4.3). `CSS` and `DOMPoint` are window
# properties too; the note's table does not name them, and the modules read them
# from the window as well.
GLOBALS = ["document", "window", "DOMParser", "XMLSerializer", "localStorage", "devicePixelRatio",
           "ResizeObserver", "requestAnimationFrame", "HTMLCanvasElement", "CSS", "DOMPoint"]


def modules(directory=VIEW):
    return sorted(directory.glob("*.js"))


def code_of(src):
    """The source with its comments and the text of its strings and templates
    blanked, so that a name in a sentence is not a use. The expressions inside a
    template's ${ } are kept: they are code."""
    out, i, n = [], 0, len(src)
    stack = []                     # for templates: the brace depth at each open ${
    depth = 0
    while i < n:
        c = src[i]
        two = src[i:i + 2]
        if two == "//":
            while i < n and src[i] != "\n":
                i += 1
        elif two == "/*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c in "'\"":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(c + c)
            i = j + 1
        elif c == "`":
            out.append("``")
            i += 1
            while i < n and src[i] != "`":
                if src[i] == "\\":
                    i += 2
                elif src[i:i + 2] == "${":
                    # copy the expression up to its closing brace, templates inside it included
                    k, d = i + 2, 1
                    while k < n and d:
                        d += {"{": 1, "}": -1}.get(src[k], 0)
                        k += 1
                    out.append(" " + code_of(src[i + 2:k - 1]) + " ")
                    i = k
                else:
                    i += 1
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def global_uses(src):
    """[(name, line)] for each name used as a global: not a property (`win.DOMParser`),
    not an object key (`{document: domDoc}`)."""
    code, found = code_of(src), []
    for name in GLOBALS:
        for m in re.finditer(rf"(?<![\w$.]){name}\b(?!\s*:)", code):
            found.append((name, code.count("\n", 0, m.start()) + 1))
    return sorted(found, key=lambda f: f[1])


def test_there_are_modules_to_scan():
    assert {p.name for p in modules()} >= {"view.js", "elevation.js", "dom.js", "face.js", "faces.js",
                                           "ear-holes.js", "settable.js"}


def test_the_view_takes_a_document_and_never_reads_window():
    for p in modules():
        uses = global_uses(p.read_text())
        assert not uses, f"{p.relative_to(ROOT)} reads {uses} as a global: take it from the document that is passed in (§1)"


def test_the_scan_sees_a_global_and_ignores_a_sentence_and_a_property():
    assert global_uses("const n = document.createElement('g');") == [("document", 1)]
    assert global_uses("x = new DOMParser();\ny = window.CSS.escape(a)") == [("DOMParser", 1), ("window", 2)]
    assert global_uses("// the document and window\nconst s = 'new DOMParser()'; const w = d.defaultView.DOMParser;") == []
    assert global_uses("f({document: domDoc}); `${localStorage.x}`") == [("localStorage", 1)]


SPEC = re.compile(r"""(?:\bfrom\s*|\bimport\s*\(\s*|\bimport\s+)(['"])(.*?)\1""")


def specifiers(src):
    """Every import specifier, static or dynamic, with its line; a dynamic import
    whose argument is not a literal is returned as None."""
    found = []
    for m in SPEC.finditer(src):
        found.append((m.group(2), src.count("\n", 0, m.start()) + 1))
    for m in re.finditer(r"\bimport\s*\(\s*(?!['\"])", src):
        found.append((None, src.count("\n", 0, m.start()) + 1))
    return found


def import_problems(path, root=KIT):
    problems = []
    for spec, line in specifiers(path.read_text()):
        where = f"{path.name}:{line}"
        if spec is None:
            problems.append(f"{where}: a dynamic import that is not a literal")
        elif not spec.startswith("."):
            problems.append(f"{where}: {spec!r} is not relative")
        elif re.search(r"\bthree\b|vendor/|site/|https?:", spec):
            problems.append(f"{where}: {spec!r} reaches outside the kit")
        else:
            target = (path.parent / spec).resolve()
            if root.resolve() not in target.parents:
                problems.append(f"{where}: {spec!r} leaves {root.name}/")
            elif not target.is_file():
                problems.append(f"{where}: {spec!r} is no file")
    return problems


def test_nothing_in_kit_rack_view_imports_from_outside_the_kit():
    problems = [p for m in modules() for p in import_problems(m)]
    assert not problems, "\n".join(problems)


def test_the_import_check_refuses_a_site_path_a_url_and_three(tmp_path):
    kit = tmp_path / "kit/rack/view"
    kit.mkdir(parents=True)
    (tmp_path / "kit/rack/rails.js").write_text("")
    f = kit / "x.js"
    f.write_text("import a from '../rails.js';\nimport '../../site/x.js';\nimport * as T from 'three';\n"
                 "const m = await import('https://cdn.example/x.js');\nconst n = await import(name);\n")
    got = import_problems(f, tmp_path / "kit")
    assert len(got) == 4 and not any("rails.js" in g for g in got), got


def test_every_module_under_kit_rack_view_has_an_export_a_files_entry_and_a_node_check():
    pkg = json.loads((KIT / "package.json").read_text())
    for p in modules():
        name = p.stem
        assert pkg["exports"].get(f"./rack/view/{name}") == f"./rack/view/{name}.js", f"{name} has no export"
        assert (KIT / pkg["exports"][f"./rack/view/{name}"]).is_file()
    assert "rack/view/*.js" in pkg["files"], "rack/view/*.js is not published"
    assert re.search(r"for f in rack/view/\*\.js; do node --check \$f \|\| exit 1; done", pkg["scripts"]["test"]), \
        "`npm test` does not node --check rack/view/*.js"


def golden_files():
    return sorted(GOLDENS.glob("*.txt"))


def test_the_goldens_are_present_one_per_fixture_and_face_each_naming_both_commits():
    want = {f"{fixture}.2d.{face}.txt" for fixture in ("acceptance", "cable-lay") for face in ("front", "rear")}
    assert {p.name for p in golden_files()} == want
    for p in golden_files():
        head = [line for line in p.read_text().splitlines()[:8] if line.startswith("# ")]
        keyed = dict(line[2:].split(": ", 1) for line in head if ": " in line)
        assert keyed.get("site-commit") == SITE_COMMIT, f"{p.name} does not name the site commit"
        assert re.fullmatch(r"[0-9a-f]{40}", keyed.get("portrayal-commit", "")), f"{p.name} does not name the Portrayal commit"
        assert keyed.get("recorded-by"), f"{p.name} does not say how it was recorded"
        assert "<svg" in p.read_text(), p.name
