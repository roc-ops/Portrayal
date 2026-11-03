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
