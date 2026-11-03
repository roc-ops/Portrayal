"""The suite's two tiers: what makes a test `heavy`, and the tool that marks it.

A pull request push runs the light tier (`-m "not heavy"`); a full run - the
dispatch before a merge, the nightly, a fork's pull request - runs both. A test
is heavy when it is marked, and it is marked from a measurement: the seconds a
full run's `test-times` record gives every parameter of the function, summed.
Per FUNCTION, because seventy-four parameters at four seconds each are one
three-hundred-second cost, whatever any one of them says.
"""
import textwrap

from portrayal import suite_times
from portrayal_dev import mark_heavy


def test_params_and_groups_fold_into_their_function():
    times = {"t_a::f[1]": 3.0, "t_a::f[2]": 3.0, "t_a::g@full-lint": 1.0}
    assert mark_heavy.heavy_functions(times, threshold=5.0) == {("t_a", "f")}


def test_a_class_method_is_named_by_its_class():
    assert suite_times.fold_function("t_b::C.m[x]") == ("t_b", "C.m")


def test_an_at_sign_inside_a_parameter_is_not_a_group():
    """Component refs carry `@1`, so `@` alone does not start a group name; a
    group suffix comes after the parameter's closing bracket."""
    assert suite_times.fold_function("t_c::f[common/x@1]") == ("t_c", "f")
    assert suite_times.fold_function("t_c::f[common/x@1]@full-lint") == ("t_c", "f")
    assert suite_times.fold_function("t_c::g@public-dist") == ("t_c", "g")


def test_the_marker_is_registered(request):
    lines = request.config.getini("markers")
    assert any(l.startswith("heavy:") for l in lines), lines


def test_marking_adds_the_decorator_once_and_the_import_it_needs(tmp_path):
    src = tmp_path / "test_x.py"
    src.write_text(textwrap.dedent('''\
        """A module."""
        import json


        def test_slow():
            pass


        class TestC:
            @staticmethod
            def helper():
                pass

            def test_m(self):
                pass


        def test_fast():
            pass
        '''))
    assert mark_heavy.mark_file(src, {"test_slow", "TestC.test_m"}) == 2
    assert mark_heavy.mark_file(src, {"test_slow", "TestC.test_m"}) == 0
    text = src.read_text()
    assert "import pytest\n" in text
    assert "@pytest.mark.heavy\ndef test_slow" in text
    assert "    @pytest.mark.heavy\n    def test_m" in text
    assert "@pytest.mark.heavy\ndef test_fast" not in text
    compile(text, str(src), "exec")


def test_a_group_is_heavy_together():
    """THE TESTS OF AN xdist GROUP WAIT ON ONE SHARED RUN, and whichever of them
    runs first is billed for it: in a full run one `full-lint` reader took 290 s
    and its group-mates 0.01 s. Marked singly, the cheap-looking readers stay
    light and the light tier runs the whole-library lint anyway."""
    times = {"test_l::a@full-lint": 200.0, "test_l::b@full-lint": 0.01,
             "test_o::c[x@1]@full-lint": 0.02, "test_l::d": 0.1}
    assert mark_heavy.heavy_functions(times) == {
        ("test_l", "a"), ("test_l", "b"), ("test_o", "c")}


def test_the_heaviest_of_several_runs_decides():
    """A module fixture is billed to whichever test a worker runs first, so the
    same function measures heavy in one run and light in the next."""
    one = {"test_m::f": 6.0, "test_m::g": 0.1}
    two = {"test_m::f": 0.1, "test_m::g": 6.0}
    assert mark_heavy.heavy_functions([one, two]) == {("test_m", "f"), ("test_m", "g")}


def test_a_key_splits_into_module_function_and_group():
    assert suite_times.split_key("test_c::C.f[common/x@1]@full-lint") == (
        "test_c", "C.f", "full-lint")
    assert suite_times.split_key("test_c::f[common/x@1]") == ("test_c", "f", None)


def test_the_import_goes_before_the_first_definition_and_an_alias_is_not_it(tmp_path):
    """A LATE TOP-LEVEL IMPORT is not where `import pytest` goes: put after it, the
    mark it serves would be read before the name exists and collection would fail.
    And `import pytest as pt` binds `pt`, not `pytest`."""
    src = tmp_path / "test_y.py"
    src.write_text('"""Doc."""\nimport json\nimport pytest as pt\n\n\n'
                   "def test_slow():\n    pass\n\n\nimport re\n")
    assert mark_heavy.mark_file(src, {"test_slow"}) == 1
    text = src.read_text()
    assert text.index("import pytest\n") < text.index("def test_slow")
    ns = {}
    exec(compile(text, str(src), "exec"), ns)
    assert ns["test_slow"].pytestmark[0].name == "heavy"


def test_a_name_that_cannot_be_found_is_named(tmp_path):
    src = tmp_path / "test_z.py"
    src.write_text('class Outer:\n    """A class with a docstring."""\n    class Inner:\n'
                   "        def test_x(self):\n            pass\n")
    assert mark_heavy.unfound(src, {"Outer.Inner.test_x", "test_gone"}) == {
        "Outer.Inner.test_x", "test_gone"}
