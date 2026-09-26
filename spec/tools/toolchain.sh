# Sourced by build.sh and publish.sh from the repository root. Not executable
# on its own. It makes every `python3 spec/tools/portrayal/X.py` that follows
# import THIS checkout's portrayal, and it stops the build if one does not (#561).
#
# WHY IT IS NEEDED. A script run by path gets its own directory on sys.path[0]:
# `spec/tools/portrayal`, not `spec/tools`. So `from portrayal import ...` finds
# nothing on the path and falls through to the editable install, which points
# at whichever checkout ran `pip install -e .`, often another worktree. That
# compiler then succeeds against this checkout's library: right data, wrong
# code, exit 0. setuptools' editable finder sits AFTER PathFinder on
# sys.meta_path, so putting spec/tools on PYTHONPATH is enough to win.
export PYTHONPATH="$PWD/spec/tools${PYTHONPATH:+:$PYTHONPATH}"

# THE GUARD, because silence is the whole defect. It imports portrayal the way
# the stages do, with the script's directory INSERTED at sys.path[0] - not
# written over it, which under PYTHONSAFEPATH is the pin itself - and refuses any
# answer that is not this checkout. A PYTHONPATH the caller set, or a .pth file,
# can still get there first, and then the build stops and prints both paths.
toolchain_check() {
  python3 -c '
import pathlib, sys
here = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(here))
import portrayal
got = pathlib.Path(portrayal.__file__).resolve().parent
if got != here:
    sys.exit(f"refusing to build: the tools import portrayal from\n  {got}\n"
             f"but this checkout is\n  {here}\n"
             "so the build would compile this library with another checkout\x27s code (#561).")
' "$PWD/spec/tools/portrayal"
}
toolchain_check
