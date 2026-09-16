"""Turning vendor PDFs, CAD and photographs into something a modeller can read.

A SIBLING OF `portrayal`, NOT A PART OF IT. Nothing in the build or the gates
imports anything here, and none of these dependencies - docling, DracoPy,
OpenCV - is needed to lint, render or publish the library. The conversion
usually runs on a different and beefier box; `pip install -e ".[intake]"` is
what that box installs.

Importable at all so that a test can reach `extract` without inserting a
directory onto `sys.path`, which is what 94 files used to do (#178).
"""
