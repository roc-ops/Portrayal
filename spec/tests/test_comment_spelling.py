"""The comment-spelling check reads comments and nothing else."""
from portrayal import comment_spelling as cs


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
