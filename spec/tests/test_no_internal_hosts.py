"""No internal address or login reaches a tracked file.

This repository is meant to go public, and roc-ops/Portrayal#253 is the record of
what is already in its history: an internal demo host, its port, and a deploy
username, across four paths that are all deleted now. The decision there was to
accept the history and stop it recurring, because the interesting part of that
finding was HOW it got in.

IT WAS NOT SOMETHING ANYONE WROTE. Two of the four paths are tooling droppings -
twenty `.playwright-mcp/console-*.log` files from one afternoon's browser
debugging, committed because nothing was ignoring them yet. A person writing a
handoff note at least knows they are writing. A tool that drops a log in the
working tree does not, and neither does the person who runs `git add`.

So this is a gate rather than a rule in CONTRIBUTING. It reads what git tracks,
which means anything correctly ignored is out of scope for free, and it fails
BEFORE the push rather than in an audit six months later.

Documentation that needs an example address should use the ranges reserved for
exactly that - RFC 5737's 192.0.2.0/24, 198.51.100.0/24 and 203.0.113.0/24, or
RFC 3849's 2001:db8::/32 - which are unroutable and unmistakably examples.
"""
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

# RFC 1918: 10/8, 172.16/12, 192.168/16. Each octet bounded so a version string
# or a run of dimensions cannot be mistaken for an address.
OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
PRIVATE_IP = re.compile(
    rf"\b(?:10\.{OCTET}\.{OCTET}\.{OCTET}"
    rf"|172\.(?:1[6-9]|2\d|3[01])\.{OCTET}\.{OCTET}"
    rf"|192\.168\.{OCTET}\.{OCTET})\b")

# `deploy.sh rocnet@10.22.32.248` - a login against a literal address. A bare
# `user@host` placeholder is fine and common in documentation, so the host half
# has to be an actual address for this to fire.
SSH_TARGET = re.compile(rf"\b[a-z_][a-z0-9_.-]*@{OCTET}\.{OCTET}\.{OCTET}\.{OCTET}\b")

# This file necessarily contains the patterns it looks for.
EXEMPT = {"spec/tests/test_no_internal_hosts.py"}


def _tracked_text_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout
    for rel in out.split("\0"):
        if not rel or rel in EXEMPT:
            continue
        p = ROOT / rel
        try:
            yield rel, p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue                      # binary or unreadable: nothing to read


@pytest.fixture(scope="module")
def tracked():
    return list(_tracked_text_files())


def test_the_sweep_reads_the_repository(tracked):
    """NON-VACUITY. A scan that finds no files reports the same clean bill as a
    repository with nothing to find, and `git ls-files` returning nothing is
    exactly what happens if this is ever run outside a checkout."""
    assert len(tracked) > 500, f"only {len(tracked)} tracked text files - the walk is broken"


def test_no_tracked_file_carries_a_private_address(tracked):
    hits = []
    for rel, text in tracked:
        for n, line in enumerate(text.splitlines(), 1):
            m = PRIVATE_IP.search(line)
            if m:
                hits.append(f"{rel}:{n}: {m.group(0)}")
    assert not hits, (
        "RFC 1918 address in a tracked file:\n  " + "\n  ".join(hits[:20]) +
        "\n\nIf this is a documentation example, use a range reserved for that: "
        "192.0.2.0/24, 198.51.100.0/24 or 203.0.113.0/24 (RFC 5737). "
        "If it is a real host, it does not belong in a repository that is going public - "
        "see roc-ops/Portrayal#253.")


def test_no_tracked_file_carries_a_login_against_an_address(tracked):
    hits = []
    for rel, text in tracked:
        for n, line in enumerate(text.splitlines(), 1):
            m = SSH_TARGET.search(line)
            if m:
                hits.append(f"{rel}:{n}: {m.group(0)}")
    assert not hits, (
        "a login against a literal address in a tracked file:\n  " + "\n  ".join(hits[:20]) +
        "\n\n`user@host` as a placeholder is fine; a username against a real address is not.")


@pytest.mark.parametrize("sample,should_fire", [
    ("http://10.22.32.248:9003/demo/3d.html", True),      # what was in history
    ("./deploy.sh rocnet@10.22.32.248", True),
    ("192.168.1.1", True),
    ("172.16.0.5", True),
    ("172.32.0.5", False),                                 # outside 172.16/12
    ("192.0.2.14", False),                                 # RFC 5737, the right answer
    ("8.8.8.8", False),
    ("version 1.10.22.3", False),                          # not a dotted quad
    ("20 × 10.15 × 37", False),                            # a component's size
    ("git clone user@host:repo.git", False),               # a placeholder
])
def test_the_patterns_fire_on_what_they_should_and_nothing_else(sample, should_fire):
    """THE CHECK THAT MAKES THE SWEEP WORTH ANYTHING. Both sweeps above pass by
    finding nothing, which is also what they do if the patterns stop matching.
    These cases are the real strings from #253 plus the things this library is
    full of that must not be mistaken for them."""
    fired = bool(PRIVATE_IP.search(sample) or SSH_TARGET.search(sample))
    assert fired is should_fire, f"{sample!r}: fired={fired}, expected {should_fire}"
