"""The comment-spelling check reads comments and nothing else."""
from pathlib import Path

from portrayal import comment_spelling as cs

ROOT = Path(__file__).resolve().parents[2]


def found(tmp_path, src):
    (tmp_path / "x.js").write_text(src)
    return list(cs.findings(tmp_path))


def test_an_american_spelling_in_a_comment_fails(tmp_path):
    assert len(found(tmp_path, "// the color of it\nconst a = 1;\n")) == 1


def test_a_block_comment_is_read_too(tmp_path):
    assert len(found(tmp_path, "/* the center\n   of it */\n")) == 1


def test_a_trailing_comment_is_read(tmp_path):
    assert len(found(tmp_path, "const a = 1; // the color\n")) == 1


def test_a_quoted_identifier_passes(tmp_path):
    assert found(tmp_path, "// asks `colorOf` and the `color` key\n") == []


def test_code_and_strings_are_not_looked_at(tmp_path):
    assert found(tmp_path, "const color = 'color';\nconst centers = \"gray\";\n") == []


def test_british_spelling_passes(tmp_path):
    assert found(tmp_path, "// the colour of the centre\n") == []


def test_a_marker_inside_a_string_is_not_a_comment(tmp_path):
    assert found(tmp_path, "const a = 'a // color';\nconst b = \"x /* center */\";\n") == []


def test_a_string_holding_a_block_opener_does_not_swallow_the_file(tmp_path):
    assert len(found(tmp_path, "const a = '/*';\n// the color\n")) == 1


def test_a_block_and_a_line_comment_on_one_line_are_both_read(tmp_path):
    assert len(found(tmp_path, "/* color */ // center\n")) == 2


def test_the_kit_rack_comments_are_british():
    """The D6 check, run by pytest so CI enforces it."""
    assert list(cs.findings(ROOT / "kit/rack")) == []
