"""The lists that every new maker, connector key or exported part appends to
merge without a conflict.

A new maker is an entry in `spec/schemas/vendors.yaml`, a new connector key is
one in `spec/schemas/connectors.yaml`, and a part the exporter must name is one
in a register table. Two changes that each append one entry at the same place
in one of those files used to conflict, although neither touches the other's
line, and each conflict cost a merge of main.

`.gitattributes` marks those files `merge=union`: where two sides changed the
same place, git keeps the lines of both. That is right for a file that is
nothing but appended entries and wrong for one with logic in it, where it would
glue two edits of one function together without a word. So this module holds
the files to what the attribute assumes: the register tables live in their own
module that holds literals only, and no entry is written twice, which is what a
union of two edits of one entry would look like.
"""
import ast
import pathlib
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTERS = ROOT / "spec/tools/portrayal/dcim_registers.py"
SHARED = ("spec/schemas/connectors.yaml", "spec/schemas/vendors.yaml",
          "spec/tools/portrayal/dcim_registers.py")
# The tables that moved out of dcim_export.py, so the file the attribute covers
# holds nothing else.
TABLES = ("NOT_A_DCIM_PORT", "MGMT_NOT_A_DCIM_PORT", "PART_OUTLET", "OUTLET_LABEL",
          "POWER_LABEL")


def git(*args, cwd=ROOT, check=True):
    p = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                        "-c", "commit.gpgsign=false", *args],
                       cwd=cwd, capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(cwd),
                            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"})
    if check:
        assert p.returncode == 0, p.stderr
    return p


@pytest.mark.parametrize("path", SHARED)
def test_a_shared_list_file_merges_by_union(path):
    out = git("check-attr", "merge", "--", path).stdout
    assert out.strip().endswith("merge: union"), out


def test_the_register_module_holds_the_tables_and_literals_only():
    tree = ast.parse(REGISTERS.read_text())
    names = []
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue                                   # the docstring
        assert isinstance(node, ast.Assign) and len(node.targets) == 1, \
            f"line {node.lineno}: only `NAME = <literal>` may live in the union-merged module"
        ast.literal_eval(node.value)                   # raises on a call or a name
        names.append(node.targets[0].id)
    assert set(TABLES) <= set(names), sorted(set(TABLES) - set(names))


def test_no_register_entry_is_written_twice():
    tree = ast.parse(REGISTERS.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            keys = [ast.literal_eval(k) for k in node.value.keys]
            dup = sorted({str(k) for k in keys if keys.count(k) > 1})
            assert not dup, f"{node.targets[0].id} writes {dup} twice"


class _Strict(yaml.SafeLoader):
    """A loader that refuses a mapping key written twice, which yaml otherwise
    answers by keeping the last one."""


def _no_dup(loader, node, deep=False):
    seen = set()
    for k, _ in node.value:
        key = loader.construct_object(k, deep=deep)
        assert key not in seen, f"{key!r} is written twice (line {k.start_mark.line + 1})"
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dup)


@pytest.mark.parametrize("path", [p for p in SHARED if p.endswith(".yaml")])
def test_no_registry_key_is_written_twice(path):
    doc = yaml.load((ROOT / path).read_text(), Loader=_Strict)
    assert doc


def _repo(tmp_path, attributes):
    """A throwaway repository holding the real vendors registry, with this
    checkout's attributes file in it or without."""
    git("init", "-q", "-b", "main", cwd=tmp_path)
    target = tmp_path / "spec/schemas/vendors.yaml"
    target.parent.mkdir(parents=True)
    shutil.copy(ROOT / "spec/schemas/vendors.yaml", target)
    if attributes:
        shutil.copy(ROOT / ".gitattributes", tmp_path / ".gitattributes")
    git("add", "-A", cwd=tmp_path)
    git("commit", "-q", "-m", "base", cwd=tmp_path)
    return target


def _append_vendor(target, tmp_path, branch, name):
    git("checkout", "-q", "-b", branch, "main", cwd=tmp_path)
    text = target.read_text()
    anchor = "  oscilloquartz:\n"
    assert anchor in text
    target.write_text(text.replace(
        anchor, f"  {name}:\n    display: {name}\n    role: hardware\n    source: test\n\n{anchor}", 1))
    git("commit", "-q", "-am", branch, cwd=tmp_path)


def test_two_appends_at_one_place_merge_clean_and_keep_both(tmp_path):
    target = _repo(tmp_path, attributes=True)
    _append_vendor(target, tmp_path, "a", "zzfirst")
    _append_vendor(target, tmp_path, "b", "zzsecond")
    git("checkout", "-q", "a", cwd=tmp_path)
    git("merge", "-q", "--no-edit", "b", cwd=tmp_path)
    vendors = yaml.load(target.read_text(), Loader=_Strict)["vendors"]
    assert {"zzfirst", "zzsecond"} <= set(vendors)


def test_the_same_two_appends_conflict_without_the_attribute(tmp_path):
    """The control: the clean merge above is the attribute's doing."""
    target = _repo(tmp_path, attributes=False)
    _append_vendor(target, tmp_path, "a", "zzfirst")
    _append_vendor(target, tmp_path, "b", "zzsecond")
    git("checkout", "-q", "a", cwd=tmp_path)
    assert git("merge", "-q", "--no-edit", "b", cwd=tmp_path, check=False).returncode != 0
