"""Nothing private reaches a tracked file: no internal address or login, no
path on somebody's machine, no personal email address, and no customer,
employer or maintainer name outside the files that are meant to carry one.

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

THE FIRST VERSION ONLY KNEW ADDRESSES (#452). The 2026-09-21 audit found what it
could not see, at the tip: a customer named in two device provenances, an
employer's product named in a component's, first-name citations in two
contracts, a test and the linter, and absolute `/Volumes/...` paths in a
tracked plan. Each is a category below, and each has cases that must fire.

Documentation that needs an example address should use the ranges reserved for
exactly that - RFC 5737's 192.0.2.0/24, 198.51.100.0/24 and 203.0.113.0/24, or
RFC 3849's 2001:db8::/32 - which are unroutable and unmistakably examples. An
example email belongs at example.com (RFC 2606); an example path at
`/home/me/`.
"""
import hashlib
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

# `deploy.sh svc@10.1.2.3` - a login against a literal address. A bare
# `user@host` placeholder is fine and common in documentation, so the host half
# has to be an actual address for this to fire.
SSH_TARGET = re.compile(rf"\b[a-z_][a-z0-9_.-]*@{OCTET}\.{OCTET}\.{OCTET}\.{OCTET}\b")

# A home or volume on a real machine. `/home/me/` is the placeholder
# test_generic_stays_generic.py uses on purpose, so it is the one home allowed.
# The lookbehind keeps a URL's own path (`example.com/Users/...`) out of it.
MACHINE_PATH = re.compile(
    r"(?<![\w.])(?:/Volumes/|/Users/[A-Za-z]|/home/(?!me/)[a-z_][\w-]*/"
    r"|[A-Za-z]:\\+Users\\+)")

# An address a person can be reached at. The domain must end in letters, so a
# component ref at a version (`three@0.160.0`, `usb-a@2`) is not one, and it
# must not end in a file extension, so a retina asset (`icon@2x.png`) is not.
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})\b")
FILE_EXTENSIONS = frozenset({"png", "svg", "jpg", "jpeg", "webp", "gif", "js", "mjs",
                             "json", "yaml", "yml", "md", "css", "html", "glb", "py"})
EMAIL_DOMAINS_ALLOWED = ("example.com", "example.org", "example.net",
                         "users.noreply.github.com", "anthropic.com",
                         "portrayal.dev")   # the project's own role addresses


def _allowed_email(m):
    local, domain = m.group(0).split("@", 1)
    if domain.rsplit(".", 1)[-1].lower() in FILE_EXTENSIONS:
        return True                        # a file name, not a mailbox
    if domain.lower() == "github.com" and local == "git":
        return True                        # an ssh remote, not a person
    return any(domain.lower() == d or domain.lower().endswith("." + d)
               for d in EMAIL_DOMAINS_ALLOWED)


# NAMES, STORED AS HASHES, AND WHY. A list of the customer and employer names
# this repository must not carry would itself be the one tracked file that
# carries all of them - published at the flip, with a label saying what they
# are. So each is the first 16 hex digits of the sha256 of the lowercased word,
# and the sweep hashes every word it reads. It is not secret - a short word is
# easy to guess - it is only not a list.
#
# To add one: python3 -c "import hashlib;print(hashlib.sha256(b'word').hexdigest()[:16])"
#
# The value is the set of files that MAY carry the word; empty means none. The
# maintainer is named as the copyright holder in LICENSE and NOTICE, which is
# exactly where a name belongs, and nowhere else: a provenance that says who
# measured something says "the maintainer" (#152, and #452 when it came back).
_LICENCE_FILES = frozenset({"LICENSE", "NOTICE",
                            "library/exports/LICENSE", "library/exports/NOTICE"})
# THE SPONSOR CREDIT IS THE ONE PLACE THE EMPLOYER IS NAMED ON PURPOSE (#446):
# the permission to publish came with one request, a visible "sponsored by"
# credit with the logo and a link. The README carries it; the logo files carry
# nothing but paths. Anywhere else the name is still a finding.
_SPONSOR_FILES = frozenset({"README.md"})
PRIVATE_NAMES = {
    "a2848e0afd90d6e7": frozenset(),       # a customer
    "e0fcd351b53ffafa": _SPONSOR_FILES,    # the employer, as the sponsor credit names it
    "619e045974e6cf5d": _SPONSOR_FILES,    # the employer, as its domain reads
    "5b090874c87b019a": frozenset(),       # the maintainer's own domain
    "06b9a6eacd7a77b9": _LICENCE_FILES,    # the maintainer, given name
    "6f12ebf934ac8261": _LICENCE_FILES,    # the maintainer, family name
}
WORD = re.compile(r"[a-z0-9]+")


def _h(word):
    return hashlib.sha256(word.encode()).hexdigest()[:16]


def private_names_in(rel, line, table=PRIVATE_NAMES):
    """The words of `line` whose hash is in `table` and which `rel` may not carry."""
    return [w for w in WORD.findall(line.lower())
            if _h(w) in table and rel not in table[_h(w)]]


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


def _sweep(tracked, pattern, keep=lambda m: True):
    hits = []
    for rel, text in tracked:
        for n, line in enumerate(text.splitlines(), 1):
            for m in pattern.finditer(line):
                if keep(m):
                    hits.append(f"{rel}:{n}: {m.group(0)}")
    return hits


def test_the_sweep_reads_the_repository(tracked):
    """NON-VACUITY. A scan that finds no files reports the same clean bill as a
    repository with nothing to find, and `git ls-files` returning nothing is
    exactly what happens if this is ever run outside a checkout."""
    assert len(tracked) > 500, f"only {len(tracked)} tracked text files - the walk is broken"


def test_no_tracked_file_carries_a_private_address(tracked):
    hits = _sweep(tracked, PRIVATE_IP)
    assert not hits, (
        "RFC 1918 address in a tracked file:\n  " + "\n  ".join(hits[:20]) +
        "\n\nIf this is a documentation example, use a range reserved for that: "
        "192.0.2.0/24, 198.51.100.0/24 or 203.0.113.0/24 (RFC 5737). "
        "If it is a real host, it does not belong in a repository that is going public - "
        "see roc-ops/Portrayal#253.")


def test_no_tracked_file_carries_a_login_against_an_address(tracked):
    hits = _sweep(tracked, SSH_TARGET)
    assert not hits, (
        "a login against a literal address in a tracked file:\n  " + "\n  ".join(hits[:20]) +
        "\n\n`user@host` as a placeholder is fine; a username against a real address is not.")


def test_no_tracked_file_carries_a_machine_path(tracked):
    hits = _sweep(tracked, MACHINE_PATH)
    assert not hits, (
        "a path on somebody's machine in a tracked file:\n  " + "\n  ".join(hits[:20]) +
        "\n\nWrite it relative to the repository root, or use `/home/me/` as the example.")


def test_no_tracked_file_carries_a_personal_email(tracked):
    hits = _sweep(tracked, EMAIL, keep=lambda m: not _allowed_email(m))
    assert not hits, (
        "an email address in a tracked file:\n  " + "\n  ".join(hits[:20]) +
        "\n\nUse example.com for an example, a noreply address for attribution.")


def test_no_tracked_file_names_a_customer_employer_or_maintainer(tracked):
    hits = []
    for rel, text in tracked:
        for n, line in enumerate(text.splitlines(), 1):
            for w in private_names_in(rel, line):
                hits.append(f"{rel}:{n}: {w}")
    assert not hits, (
        "a private name in a tracked file:\n  " + "\n  ".join(hits[:20]) +
        "\n\nA customer or employer does not belong in a public library - say what the "
        "source WAS (\"a requested-parts list\", \"a third-party-branded optic\"). "
        "A person who measured or ruled on something is \"the maintainer\".")


@pytest.mark.parametrize("sample,should_fire", [
    ("http://10.1.2.3:9003/demo/3d.html", True),           # the shape that was in history
    ("./deploy.sh svc@10.1.2.3", True),
    ("192.168.1.1", True),
    ("172.16.0.5", True),
    ("172.32.0.5", False),                                 # outside 172.16/12
    ("192.0.2.14", False),                                 # RFC 5737, the right answer
    ("8.8.8.8", False),
    ("version 1.10.22.3", False),                          # not a dotted quad
    ("20 × 10.15 × 37", False),                            # a component's size
    ("git clone user@host:repo.git", False),               # a placeholder
])
def test_the_address_patterns_fire_on_what_they_should_and_nothing_else(sample, should_fire):
    """THE CHECK THAT MAKES THE SWEEP WORTH ANYTHING. Every sweep above passes by
    finding nothing, which is also what it does if its pattern stops matching.
    These cases are the shape of the strings from #253 plus the things this
    library is full of that must not be mistaken for them."""
    fired = bool(PRIVATE_IP.search(sample) or SSH_TARGET.search(sample))
    assert fired is should_fire, f"{sample!r}: fired={fired}, expected {should_fire}"


@pytest.mark.parametrize("sample,should_fire", [
    ("/Volumes/External/Some-Repo/working/intake/x.pdf", True),   # what #452 found
    ("cd /Users/someone/src", True),
    ("/home/alice/work/Portrayal", True),
    (r"C:\Users\someone\Portrayal", True),
    ("/home/me/generic/Portrayal/library", False),        # the allowed placeholder
    ("~/generic/", False),
    ("https://example.com/Users/guide", False),            # a URL's own path
    ("library/devices/cisco/asr-9901", False),
])
def test_the_path_pattern_fires_on_what_it_should_and_nothing_else(sample, should_fire):
    fired = bool(MACHINE_PATH.search(sample))
    assert fired is should_fire, f"{sample!r}: fired={fired}, expected {should_fire}"


@pytest.mark.parametrize("sample,should_fire", [
    ("mail someone@company.co.uk", True),
    ("First.Last@corp.com", True),
    ("noreply@anthropic.com", False),                      # commit attribution
    ("12345+someone@users.noreply.github.com", False),
    ("reports to security@example.org", False),
    ("git@github.com:roc-ops/Portrayal.git", False),       # an ssh remote
    ("three@0.160.0/build/three.module.js", False),        # a package at a version
    ("common/usb-a@2", False),                             # a component ref
    ("kit/icon@2x.png", False),                            # a retina asset
])
def test_the_email_pattern_fires_on_what_it_should_and_nothing_else(sample, should_fire):
    fired = any(not _allowed_email(m) for m in EMAIL.finditer(sample))
    assert fired is should_fire, f"{sample!r}: fired={fired}, expected {should_fire}"


def test_the_name_matcher_fires_on_a_planted_word_in_any_case_and_punctuation():
    """The real table cannot be exercised by name without writing the names
    here, so the MATCHER is proved on a planted word instead - case, possessive,
    hyphenation and the per-file allowance - and the table is proved separately."""
    table = {_h("zzplanted"): frozenset({"LICENSE"})}
    assert private_names_in("a.md", "the ZZPLANTED gap list", table) == ["zzplanted"]
    assert private_names_in("a.md", "zzplanted's reading", table) == ["zzplanted"]
    assert private_names_in("a.md", "a zzplanted-supply part", table) == ["zzplanted"]
    assert private_names_in("LICENSE", "Copyright zzplanted", table) == []
    assert private_names_in("a.md", "zzplantedx and xzzplanted", table) == []


def test_the_name_table_is_live():
    """NON-VACUITY FOR THE TABLE. Every entry is a 16-hex hash, every allowed
    file exists, and the maintainer's entries really do match the copyright line
    they are allowed in - so a mistyped hash cannot sit here matching nothing."""
    assert PRIVATE_NAMES
    for h, allowed in PRIVATE_NAMES.items():
        assert re.fullmatch(r"[0-9a-f]{16}", h), h
        for rel in allowed:
            assert (ROOT / rel).is_file(), f"{rel} is allowed a name and does not exist"
    for rel in _LICENCE_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        found = {_h(w) for w in WORD.findall(text.lower())} & set(PRIVATE_NAMES)
        assert len(found) >= 2, f"{rel}: the maintainer's entries match nothing in it"


def test_the_sponsor_credit_is_still_there():
    """THE OTHER HALF OF THE ALLOWANCE ABOVE. Permission to publish came with a
    single request, a visible sponsor credit (#446), so removing it is not a tidy-up.
    This fails if the README stops carrying the credit, the link or either logo."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "sponsored by" in readme.lower()
    assert "https://www.rocnetsupply.com/" in readme
    for logo in ("docs/sponsor/RocNet-Primary-Logo.svg",
                 "docs/sponsor/RocNet-Primary-Logo-white.svg"):
        assert logo in readme, f"the README no longer shows {logo}"
        assert (ROOT / logo).is_file(), f"{logo} is referenced and missing"
