"""Portrayal's compiler and its gates.

THE TOOLS WERE ALWAYS A PACKAGE; NOTHING SAID SO. Fifty modules imported each
other by bare name and 94 files inserted this directory onto `sys.path` in
fourteen different spellings to make that work - a hack that a test could get
subtly wrong, and that no editor, type checker or import linter could follow
(#178).

They are importable as `portrayal` now. A module still runs as a script by path,
because the package is installed (`pip install -e .`) and its own imports are
absolute; `python -m portrayal` wraps the shell gates for anyone who prefers a
driver to a path.
"""
