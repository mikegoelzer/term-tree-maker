import sys

import pytest

import term_tree_maker.term_tree_maker as term_tree_maker


def _dummy_root():
    node = tree.Node(name="root/", trailing_comment="root comment")
    node.add_child(name="child", trailing_comment="child comment")
    return node


def test_tree_main_exits_zero(monkeypatch):
    monkeypatch.setattr(term_tree_maker, "make_data_from_path_env", lambda *args, **kwargs: _dummy_root())
    monkeypatch.setattr(term_tree_maker, "calculate_max_comment_line_width", lambda *args, **kwargs: 80)
    monkeypatch.setattr(sys, "argv", ["term-tree-maker"])

    with pytest.raises(SystemExit) as excinfo:
        term_tree_maker.main()

    assert excinfo.value.code == 0

