#!/usr/bin/env -S uv run --script

"""
Display a tree of files / directories
"""

import io
import sys
from dataclasses import dataclass, field
from rich.text import Text
from rich.tree import Tree
from rich.table import Table
from rich.console import Console
from rich.measure import Measurement
from rich.markup import escape
import re
from typing import ClassVar, Any, Callable, Optional
from enum import Enum
from textwrap import TextWrapper
import argparse
from curvtools.cli.curvcfg.lib.util import CfgValue, CfgValues
import logging
from . import init_logging
from .settings import get_env_or_defaults, LOG_FILE_WIDTH_BUFFER
from curvpyutils.colors import AnsiColorsTool

log = logging.getLogger(__name__)

# console = Console(force_terminal=True, color_system="truecolor")
console = Console()

DEFAULT_SPACING_AFTER_TREE = 4
DEFAULT_RIGHT_MARGIN_WIDTH = 4

DEBUG_DISABLE_REPLACEMENTS = not True

@dataclass
class Node:
    class Type(Enum):
        LEAF = "leaf"
        BRANCH = "branch"
    class SpecialCharacteristics(Enum):
        NONE = "none"
        SPACER_UNDER_LAST_NON_SPACER_LEAF_IN_PARENT = "spacer_under_last_non_spacer_leaf_in_parent"
    
    # class variable for the maximum width of a comment line.
    MAX_COMMENT_LINE_WIDTH: ClassVar[int] = None
    SPACING_BEFORE_COMMENT_STR: ClassVar[str] = (' ' * DEFAULT_SPACING_AFTER_TREE)
    COMMENT_LINE_PREFIX: ClassVar[str] = "# "
    SPACING_AFTER_COMMENT_STR: ClassVar[str] = (' ' * DEFAULT_RIGHT_MARGIN_WIDTH)

    name: str = field(default="")
    parent: "Node" = field(default=None)
    children: list["Node"] = field(default_factory=list)
    trailing_comment: str = field(default="")
    is_spacer: bool = field(default=False)

    # internal use only
    _original_trailing_comment: str = field(default="")
    _nodes_created_by_spilling: list["Node"] = field(default_factory=list)
    _node_type: "Node.Type" = field(default=Type.LEAF)
    _special_characteristics: "Node.SpecialCharacteristics" = field(default=SpecialCharacteristics.NONE)

    def __post_init__(self):
        self._original_trailing_comment = self.trailing_comment
        # root node cannot have a comment that spills into siblings b/c
        # it cannot have siblings
        if self.is_root:
            max_width = Node.MAX_COMMENT_LINE_WIDTH or 0
            if len(Node.COMMENT_LINE_PREFIX + self.trailing_comment) > max_width:
                # truncate the comment to prevent any spilling
                truncation_len = max_width - len(Node.COMMENT_LINE_PREFIX) - len("...")
                if truncation_len <= 0:
                    # just kill the comment entirely
                    self.trailing_comment = ""
                else:
                    self.trailing_comment = self.trailing_comment[:truncation_len] + "..."
            self._node_type = Node.Type.BRANCH
        else:
            self.parent._node_type = Node.Type.BRANCH
        
        if self.is_spacer:
            # invariant: a spacer can never have children, so assert this
            if len(self.children) > 0:
                raise ValueError(f"A spacer node cannot have children!")
            self._node_type = Node.Type.LEAF

    def spill_recursively(self, add_extra_trailing_spacer: bool = False) -> None:
        """
        Spill the comment of this node and all its descendants recursively.
        Errors if this is not the root node.
        """
        if self.parent is not None:
            raise ValueError(f"Can only be called on the root node")
        self._spill_recursively(add_extra_trailing_spacer)
    
    def _spill_recursively(self, add_extra_trailing_spacer: bool = False) -> None:
        """
        Internal function that implements recursive spilling.
        """
        BREADTH_FIRST = True
        if BREADTH_FIRST:
            self.spill_comment_into_siblings(add_extra_trailing_spacer )#if self.parent is not None else False)
            for child in self.children:
                if child.is_spacer: continue
                child.spill_comment_into_siblings(add_extra_trailing_spacer)
            for child in self.children:
                if child.is_spacer: continue
                child._spill_recursively(add_extra_trailing_spacer)
        else:
            if self._node_type == Node.Type.LEAF:
                self.spill_comment_into_siblings(add_extra_trailing_spacer)
            else:
                for child in self.children:
                    if child.is_spacer: continue
                    child._spill_recursively(add_extra_trailing_spacer)
                    child.spill_comment_into_siblings(add_extra_trailing_spacer)
                self.spill_comment_into_siblings(add_extra_trailing_spacer )#if self.parent is not None else False)

    def visitor(
            self, 
            fn: Callable[["Node", list[Any], ...], bool], 
            args: tuple = (), 
            accum: list[Any] = [], 
            is_breadth_first: bool = True,
            filter_fn: Callable[["Node"], bool] = lambda node: True
        ) -> list[Any]:
        """
        Internal function that implements visitor pattern traversal of the tree.

        Args:
            fn: a function to call on each node in the tree as it is visited.  
               - The function must return a boolean value. If it returns True, traversal continues.
               If it returns False, traversal stops and 'accum' is returned to the caller.
               - The function must take these arguments:
                  - a single Node object as its first argument
                  - an accumulator of type 'list' as its second argument
                  - any number of additional arguments which must match the 'args' tuple
            args: a tuple of arguments to pass to the function fn on each node as it is visited.
            accum: an accumulated list of values that fn may append to as it visits each node.
            is_breadth_first: True => traverse breadth-first; else depth-first.
            filter_fn: a function to decide whether to visit a node:
                - Arguments:  a single Node object
                - Returns: True to visit the node and potentially its children, False to skip it
                - Default value will visit all nodes.
        
        Returns:
            accum: the final list of accumulated values that fn may have added results to
        """
        if is_breadth_first:
            res = fn(self, accum, *args)
            if not res: return accum if self.is_root else res
            for child in self.children:
                res = fn(child, accum, *args)
                if not res: return accum if self.is_root else res
            for child in self.children:
                if not filter_fn(child): continue
                res = child.visitor(fn, args, accum, is_breadth_first)
                if not res: return accum if self.is_root else res
        else:
            if self._node_type == Node.Type.LEAF:
                res = fn(self, accum, *args)
                if not res: return accum if self.is_root else res
            else:
                for child in self.children:
                    if not filter_fn(child): continue
                    res = child.visitor(fn, args, accum, is_breadth_first)
                    if not res: return accum if self.is_root else res
                    res = fn(child, accum, *args)
                    if not res: return accum if self.is_root else res
        # we should only reach here if every fn invocation returned True
        return accum if self.is_root else res

    @property
    def style(self) -> str:
        #return "bold cornflower_blue" if len(self.children) > 0 else "bold red3"
        return "bold cornflower_blue" if self._node_type == Node.Type.BRANCH else "bold red3"
    @property
    def icon(self) -> str:
        use_erase_marker = self._special_characteristics == Node.SpecialCharacteristics.SPACER_UNDER_LAST_NON_SPACER_LEAF_IN_PARENT
        return "📂" if len(self.children) > 0 else ("📄" if not self.is_spacer else "<" if not use_erase_marker else "^")
    @property
    def comment(self) -> str:
        if self.trailing_comment:
            if self.is_last_non_spacer_leaf():
                return (
                    Node.SPACING_BEFORE_COMMENT_STR.replace(' ', '<') + 
                    Node.COMMENT_LINE_PREFIX + 
                    self.trailing_comment + 
                    Node.SPACING_AFTER_COMMENT_STR)
            else:
                return (
                    Node.SPACING_BEFORE_COMMENT_STR + 
                    Node.COMMENT_LINE_PREFIX + 
                    self.trailing_comment + 
                    Node.SPACING_AFTER_COMMENT_STR
                )
        else:
            return ""
    @comment.setter
    def comment(self, value: str) -> None:
        """
        Set a new trailing comment for this node.
        """
        self._original_trailing_comment = value
        max_width = Node.MAX_COMMENT_LINE_WIDTH or 0
        if max_width <= 0:
            console.log("Can't spill long coments because MAX_COMMENT_LINE_WIDTH is not set to a positive integer!", style="yellow")
        else:
            self.spill_comment_into_siblings()
    @property
    def is_root(self) -> bool:
        """
        Returns True if this node is the root node.
        """
        return self.parent is None
    @property
    def is_last_leaf_in_entire_tree(self) -> bool:
        """
        Returns True if this node is the last leaf node in the entire tree.
        """
        if self.is_root or self._node_type != Node.Type.LEAF:
            return False
        else:
            # visit every node, storing all leaf nodes in the accumulator
            filter_fn = lambda node: not node.is_spacer
            def fn(node: "Node", accum: list[Any]) -> bool:
                if node._node_type == Node.Type.LEAF:
                    accum.append(node)
                return True
            accum = self.visitor(fn, args=(), accum=[], filter_fn=filter_fn)
            return accum[-1] == self

    def add_next_sibling(self, name: str, trailing_comment: str = "", is_spacer: bool = False, will_be_beneath_last_non_spacer_leaf_in_parent: bool = False) -> "Node":
        """
        Inserts a Node into this Node's parent's children list AFTER this node. 

        Args:
            name: the name of the new node
            trailing_comment: the trailing comment for the new node
            is_spacer: True if the new node is a spacer node
            will_be_beneath_last_non_spacer_leaf_in_parent: True if the new node will be beneath 
                the last non-spacer leaf node in its parent's children list
        
        Returns:
            None

        Raises:
            ValueError: If this Node has no parent (i.e., is the root node)
        """
        if self.parent is None:
            raise ValueError(f"Can't add a sibling to the root node!")
        child = Node(name=name, parent=self.parent, trailing_comment=trailing_comment, is_spacer=is_spacer)
        self.parent.children.insert(self.parent.children.index(self) + 1, child)
        if will_be_beneath_last_non_spacer_leaf_in_parent and is_spacer:
            child._special_characteristics = Node.SpecialCharacteristics.SPACER_UNDER_LAST_NON_SPACER_LEAF_IN_PARENT
        return child

    def add_child(self, name: str, trailing_comment: str = "", is_spacer: bool = False, prepend: bool = False) -> "Node":
        child = Node(name=name, parent=self, trailing_comment=trailing_comment, is_spacer=is_spacer)
        if prepend:
            self.children.insert(0, child)
        else:
            self.children.append(child)
        return child

    def is_last_node_in_parent(self) -> bool:
        """
        Returns True if this node is the last non-spacer node in its parent's children list.
        """
        # non_spacer_children_of_parent = [child for child in self.parent.children if not child.is_spacer]
        # ret = (len(non_spacer_children_of_parent) > 0) and (non_spacer_children_of_parent[-1] == self)
        last = self._find_last_non_spacer_of_type(acceptable_types=[Node.Type.BRANCH, Node.Type.LEAF])
        ret = last == self
        # if ret:
        #     console.log(f"{self.name}.is_last_node_in_parent() = True", style="bold bright_green")
        # else:
        #     console.log(f"{self.name}.is_last_node_in_parent() = False", style="bold bright_red")
        return ret

    def _find_last_non_spacer_of_type(self, acceptable_types: list["Node.Type"]) -> "Node":
        """
        Internal function that finds the last non-spacer node of one of the given types under its parent.
        """
        if self.is_root:
            return None
        assert len(self.parent.children) > 0, f"Parent of '{self.name}' has no children!"
        for child in reversed(self.parent.children):
            if (not child.is_spacer) and (child._node_type in acceptable_types):
                return child
        return None

    def is_last_non_spacer_leaf(self) -> bool:
        """
        Returns True if this node is the last non-spacer leaf node under its parent.
        """
        if self.is_spacer:
            return False
        last = self._find_last_non_spacer_of_type(acceptable_types=[Node.Type.LEAF])
        ret = last == self
        # if ret:
        #     console.log(f"{self.name}.is_last_non_spacer_leaf() = True (last = {last.name if last else 'none'})", style="bold bright_green")
        # else:
        #     console.log(f"{self.name}.is_last_non_spacer_leaf() = False (last = {last.name if last else 'none'})", style="bold bright_red")
        return ret
    def is_after_last_non_spacer(self) -> bool:
        """
        Returns True if this node is the last non-spacer branch node under its parent.
        """
        if self.is_spacer:
            return False
        last = self._find_last_non_spacer_of_type(acceptable_types=[Node.Type.BRANCH, Node.Type.LEAF])
        ret = last == self
        # if ret:
        #     console.log(f"{self.name}.is_last_non_spacer(any type) = True (last = {last.name if last else 'none'})", style="bold bright_green")
        # else:
        #     console.log(f"{self.name}.is_last_non_spacer(any type) = False (last = {last.name if last else 'none'})", style="bold bright_red")
        return ret

    def _undo_previous_comment_spill(self) -> None:
        """
        If this node was spilled into siblings, undo the spill by removing the spacer nodes
        and restoring the original trailing comment.

        This is called by spill_comment_into_siblings() if the spill needs to be repeated
        because either the comment was changed or the MAX_COMMENT_LINE_WIDTH was changed.
        """
        self.trailing_comment = self._original_trailing_comment
        for node in reversed(self._nodes_created_by_spilling):
            node.parent.children.remove(node)
        self._nodes_created_by_spilling.clear() # clear the list of nodes created by spilling
    
    def spill_comment_into_siblings(self, add_extra_trailing_spacer: bool = False) -> None:
        """
        Spill a comment that is too long for one line into additional lines by inserting
        spacer nodes immediately after this node.
        """
        self._undo_previous_comment_spill()
        max_width = Node.MAX_COMMENT_LINE_WIDTH or 0

        # is this node the last under its parent?
        will_be_beneath_last_non_spacer_leaf_in_parent = self.is_last_non_spacer_leaf()

        # track the last node we inserted a spacer after, which initially will be
        # ourselves if we insert any at all
        insert_after_node = self

        if (len(Node.COMMENT_LINE_PREFIX) + len(self.trailing_comment)) <= max_width:
            # nothing to spill to another node
            pass
        else:
            lines = self._break_comment_into_lines()
            self.trailing_comment = lines[0]
            for line in lines[1:]:
                if insert_after_node._node_type == Node.Type.BRANCH:
                    insert_after_node = self.add_child(name="", trailing_comment=line, is_spacer=True, prepend=True)
                else:
                    insert_after_node = insert_after_node.add_next_sibling(name="", trailing_comment=line, is_spacer=True, will_be_beneath_last_non_spacer_leaf_in_parent=will_be_beneath_last_non_spacer_leaf_in_parent)
                self._nodes_created_by_spilling.append(insert_after_node)
        if add_extra_trailing_spacer and bool(self.trailing_comment):
            if insert_after_node.is_root:
                console.log(f"Can't add a trailing spacer to root node '{insert_after_node.name}'!", style="yellow")
                return
            if (insert_after_node.parent.is_root and insert_after_node.is_last_node_in_parent()):
                console.log(f"Can't add a trailing spacer to '{self.name}' b/c it's the last child of the root node!", style="yellow")
                return
            insert_after_node = insert_after_node.add_next_sibling(name="", trailing_comment=f"<[DEBUG:{self.name}]", is_spacer=True, will_be_beneath_last_non_spacer_leaf_in_parent=will_be_beneath_last_non_spacer_leaf_in_parent)
            self._nodes_created_by_spilling.append(insert_after_node)

    def _break_comment_into_lines(self) -> [str]:
        lines = []
        max_width = (Node.MAX_COMMENT_LINE_WIDTH or 0) - len(Node.COMMENT_LINE_PREFIX)
        if max_width <= 0:
            # nothing we can do here except return entire comment as one line
            return [self.trailing_comment]
        
        # first split by newline if the any were included
        original_comment = self.trailing_comment
        for line in original_comment.split("\n"):
            wrapper = TextWrapper(
                width=max_width,
                break_long_words=True, # only applies when a single word > max_width
                break_on_hyphens=True,
                drop_whitespace=True,
                subsequent_indent="",
                fix_sentence_endings=True,
            )
            for chunk in wrapper.wrap(line):
                lines.append(chunk)
        return lines

##########################################################################################################################

from dotenv import dotenv_values
import os
from pathlib import PurePosixPath, Path

def _match_vars(s: str) -> list[tuple[str, tuple[int, int], str]]:
    """
    Match all $(VAR_NAME) and ${VAR_NAME} patterns in the given string and 
    return a list of tuples containing the variable name, the span of the match, 
    and the match itself.

    Args:
        s: the string to match $(VAR_NAME) and ${VAR_NAME} patterns in

    Returns:
        A list of tuples containing the variable name, the span of the match, and the match itself.
    """
    import re
    regex = re.compile(r'\$\((?P<var_name_parens>[^)]+)\)|\$\{(?P<var_name_braces>[^}]+)\}')
    vars_spans = []
    for match in regex.finditer(s):
        var_name = match.group("var_name_parens") or match.group("var_name_braces")
        vars_spans.append((var_name, match.span(), s[match.start():match.end()]))
    return vars_spans or []

def test_match_vars():
    s = "$(X)/${Y}/$(Z)"
    m = _match_vars(s)
    assert len(m) == 3, f"Expected 3 matches, got {len(m)}"
    var_name, (start, end), match = m[0]
    assert var_name == "X", f"Expected X, got {var_name}"
    assert start == 0, f"Expected 0, got {start}"
    assert end == 4, f"Expected 4, got {end}"
    assert match == "$(X)", f"Expected $(X), got {match}"
    var_name, (start, end), match = m[1]
    assert var_name == "Y", f"Expected Y, got {var_name}"
    assert start == 5, f"Expected 5, got {start}"
    assert end == 9, f"Expected 9, got {end}"
    assert match == "${Y}", f"Expected ${Y}, got {match}"
    var_name, (start, end), match = m[2]
    assert var_name == "Z", f"Expected Z, got {var_name}"
    assert start == 10, f"Expected 10, got {start}"
    assert end == 14, f"Expected 14, got {end}"
    assert match == "$(Z)", f"Expected $(Z), got {match}"

def _replace_vars(s: str, vars: dict[str, str]) -> str:
    """
    Replace all $(VAR_NAME) and ${VAR_NAME} patterns in the given string with the value of the variable.

    Args:
        s: the string to replace $(VAR_NAME) and ${VAR_NAME} patterns in
        vars: a dict[str, str] of variable names -> their values 
            (None values are ignored and the $(VAR_NAME) or ${VAR_NAME} is left unchanged)

    Returns:
        The string with the $(VAR_NAME) and ${VAR_NAME} patterns replaced with 
        the value of the variable if provided and not None.
    """
    vars_spans = _match_vars(s)
    pos_delta = 0
    for var_name, (start, end), match in vars_spans:
        if vars is not None and var_name in vars and vars[var_name] is not None:
            s = s[:start + pos_delta] + vars[var_name] + s[end + pos_delta:]
            pos_delta += len(vars[var_name]) - len(match)
    return s

def test_replace_vars():
    vars = { 'X': 'xxx', 'Y': 'yyy', 'Z': 'zzz' }
    s = "$(X)/${Y}/$(Z)"
    s = _replace_vars(s, vars)
    assert s == "xxx/yyy/zzz", f"Expected xxx/yyy/zzz, got {s}"

def test_replace_vars_edge_cases():
    # nothing to replace
    vars = { 'X': 'xxx', 'Y': 'yyy', 'Z': 'zzz' }
    s = "xxx/yyy/zzz"
    s = _replace_vars(s, vars)
    assert s == "xxx/yyy/zzz", f"Expected xxx/yyy/zzz, got {s}"

def test_replace_vars_only_some():
    # some vars are not provided and should be left unchanged
    vars = { 'Z': 'zzz' }
    s = "$(X)/${Y}/$(Z)"
    s = _replace_vars(s, vars)
    assert s == "$(X)/${Y}/zzz", f"Expected $(X)/${{Y}}/zzz, got {s}"

def test_replace_vars_some_vars_are_none():
    # some vars are provided asNone and should be left unchanged
    vars = { 'X': None, 'Y': 'yyy', 'Z': 'zzz' }
    s = "$(X)/${Y}/$(Z)"
    s = _replace_vars(s, vars)
    assert s == "$(X)/yyy/zzz", f"Expected $(X)/yyy/zzz, got {s}"

class CurvConfigPath:
    def __init__(self, path: str|Path, PROFILE: str = None, BOARD: str = None, DEVICE: str = None, BUILD_DIR: str = None, CURV_ROOT_DIR: str = None, cfgvalues: CfgValues = None):
        self.path_str = str(path)
        self.profile = PROFILE
        self.board = BOARD
        self.device = DEVICE
        self.build_dir = BUILD_DIR
        self.curv_root_dir = CURV_ROOT_DIR
        self.cfgvalues = cfgvalues
        self._run_var_replacement()

    def is_fully_resolved(self) -> bool:
        return len(_match_vars(self.path_str)) == 0

    def __str__(self):
        if not self.is_fully_resolved():
            return self.path_str
        return str(Path(self.path_str).resolve())

    def __repr__(self):
        resolved_str = "[resolved]" if self.is_fully_resolved() else "[unresolved]"
        return f"CurvConfigPath({str(self)} {resolved_str})"

    def _run_var_replacement(self) -> None:
        """
        Replace all $(VAR_NAME) and ${VAR_NAME} patterns in the given string 
        with the value of the variable from this CurvConfigPath object.
        """
        replacement_vals = { 
            'PROFILE': self.profile, 
            'BOARD': self.board, 
            'DEVICE': self.device,
            'BUILD_DIR': self.build_dir, 
            'CURV_ROOT_DIR': self.curv_root_dir,
        }
        if self.cfgvalues is not None:
            for k, v in self.cfgvalues.items():
                replacement_vals[k] = str(v)
        self.path_str = _replace_vars(self.path_str, replacement_vals)

class CurvConfigPathEnv(dict[str, CurvConfigPath]):
    def __init__(self, env_file: str, PROFILE: str | None = None, BOARD: str | None = None, DEVICE: str | None = None, BUILD_DIR: str | None = None, CURV_ROOT_DIR: str | None = None, cfgvalues: CfgValues | None = None):
        super().__init__()
        self.env_file = env_file
        self.profile = PROFILE
        self.board = BOARD
        self.device = DEVICE
        self.build_dir = BUILD_DIR
        self.curv_root_dir = CURV_ROOT_DIR
        self.cfgvalues = cfgvalues
        self._refresh_from_path_env_file()

    def _refresh_from_path_env_file(self) -> None:
        """
        Read a path_raw.env file and return a dictionary of the variables with their values interpreted where possible.
        """
        env_values = dotenv_values(self.env_file)

        # now replace and $(VAR_NAME) with the value of VAR_NAME
        replacement_vals = { 
            'PROFILE': self.profile, 
            'BOARD': self.board, 
            'DEVICE': self.device,
            'BUILD_DIR': self.build_dir, 
            'CURV_ROOT_DIR': self.curv_root_dir,
        }
        if self.cfgvalues is not None:
            for k, v in self.cfgvalues.items():
                replacement_vals[k] = str(v)
        self.clear()
        for k, v in env_values.items():
            if v is None:
                continue
            new_value = CurvConfigPath(
                path=v, 
                PROFILE=self.profile, 
                BOARD=self.board, 
                DEVICE=self.device,
                BUILD_DIR=self.build_dir, 
                CURV_ROOT_DIR=self.curv_root_dir, 
                cfgvalues=self.cfgvalues
            )
            self[k] = new_value
    
    def refresh(self, PROFILE: str | None = None, BOARD: str | None = None, BUILD_DIR: str | None = None, CURV_ROOT_DIR: str | None = None, DEVICE: str | None = None, cfgvalues: CfgValues | None = None) -> None:
        self.profile = PROFILE if PROFILE is not None else self.profile
        self.board = BOARD if BOARD is not None else self.board 
        self.device = DEVICE if DEVICE is not None else self.device
        self.build_dir = BUILD_DIR if BUILD_DIR is not None else self.build_dir
        self.curv_root_dir = CURV_ROOT_DIR if CURV_ROOT_DIR is not None else self.curv_root_dir
        self.cfgvalues = cfgvalues if cfgvalues is not None else self.cfgvalues
        self._refresh_from_path_env_file()

def make_data_from_path_env(
    max_comment_line_width: int,
    env_file: str = "path_raw.env",
) -> Node:
    """
    Build a Node tree from path_raw.env using python-dotenv.

    - Uses CURV_ROOT_DIR from the process environment.
    - Ignores any env var whose resolved value has no '/'.
    - Keeps only paths that start with CURV_ROOT_DIR.
    - Rewrites prefix CURV_ROOT_DIR => literal 'CURV_ROOT_DIR'.
    - 'CURV_ROOT_DIR' becomes the root node.
    - Each subsequent path component becomes a Node created via add_child().
      The final component carries a trailing_comment equal to the env var name.
      If multiple vars hit the same leaf, their names are comma-joined.
    """
    Node.MAX_COMMENT_LINE_WIDTH = max_comment_line_width

    # 2) Get CURV_ROOT_DIR from the environment
    curv_root_dir = "/home/mwg/ecp5-first-steps/my-designs/riscv-soc"
    build_dir = "/home/mwg/ecp5-first-steps/my-designs/riscv-soc/riscv/tb/verilator/riscvcpu/build"

    # 3) Resolve values from path_raw.env
    env_file_values = CurvConfigPathEnv(env_file, BUILD_DIR=build_dir, CURV_ROOT_DIR=curv_root_dir)
    cfgvalues = CfgValues(vals={'CFG_CACHE_HEX_FILES_SRC_NAME' : CfgValue(
            value="auipc-bypass",
            meta={
                'makefile_type': 'string',
                'locations': ['all'],
                'toml_path': 'cache.hex_files.src_name',
                'sv_type': 'string',
                'type': 'string',
                'is_default': False
            },
            schema_entry={
                'toml_path': 'cache.hex_files.src_name',
                'type': 'string',
                'default': 'auipc-bypass'
            },
        )
    })
    env_file_values.refresh(cfgvalues=cfgvalues, PROFILE='default', BOARD='gcm-v1', DEVICE='85f')

    # Normalize to a POSIX-style string for prefix matching
    curv_repo_dir = Path(os.path.join(curv_root_dir, '../..')).resolve().as_posix()

    # Root node of the tree
    root_node = Node(
        name="CURV_REPO_DIR/",
        trailing_comment="root of curvcpu/curv repository",
    )

    # Helper to find or create a child with a given name under a parent
    def get_or_create_child(parent: Node, name: str, trailing_comment: str | None = None, is_leaf: bool = False) -> Node:
        # Look for an existing child with the same name
        for child in parent.children:
            if child.name == name:
                # If this is the final component and we have a comment, merge comments
                if is_leaf and trailing_comment:
                    if child.trailing_comment:
                        child.trailing_comment += f", {trailing_comment}"
                    else:
                        child.trailing_comment = trailing_comment
                return child
        # Not found: create it
        comment = trailing_comment if is_leaf else ""
        return parent.add_child(name=name, trailing_comment=comment)

    # 3) Walk all resolved env vars
    for var_name, curv_config_path in env_file_values.items():
        raw_val = str(curv_config_path)
        if not curv_config_path.is_fully_resolved():
            print(f"not fully resolved: {curv_config_path}")
        if not raw_val:
            continue

        # Force to POSIX style (in case of Windows or mixed separators)
        val = PurePosixPath(raw_val).as_posix()

        # 4) Keep only paths under CURV_REPO_DIR
        if not val.startswith(curv_repo_dir):
            print(f"not starting with curv_repo_dir: {val}")
            continue

        # 5) Replace that prefix with literal CURV_REPO_DIR
        #    Example: /home/.../curv/config/schema.toml
        #    → CURV_REPO_DIR/config/schema.toml
        tail = val[len(curv_repo_dir):]
        if tail.startswith("/"):
            tail = tail[1:]
        canonical = "CURV_REPO_DIR" + ("/" + tail if tail else "")

        # 6) Split into components
        #    parts[0] == "CURV_REPO_DIR", remaining are subdirs/files
        parts = PurePosixPath(canonical).parts
        if not parts or parts[0] != "CURV_REPO_DIR":
            print(f"not parts or parts[0] != CURV_REPO_DIR: {parts}")
            continue

        # Build / extend the tree for this path
        current = root_node
        for i, part in enumerate(parts[1:], start=1):
            is_last = (i == len(parts) - 1)

            # Heuristic: treat last component as file if it has a dot,
            # otherwise as directory. For non-last components, always dir.
            if is_last:
                if "." in part:
                    node_name = part  # file
                else:
                    node_name = part + "/"  # dir-looking leaf
                current = get_or_create_child(
                    current,
                    node_name,
                    trailing_comment=var_name,
                    is_leaf=True,
                )
            else:
                node_name = part + "/"
                current = get_or_create_child(
                    current,
                    node_name,
                    trailing_comment=None,
                    is_leaf=False,
                )

    # Spill comments for nicer layout (no-op when max_comment_line_width is None/0)
    root_node.spill_recursively(add_extra_trailing_spacer=False)
    return root_node

##########################################################################################################################

def make_dummy_data(max_comment_line_width: int) -> Node:
    Node.MAX_COMMENT_LINE_WIDTH = max_comment_line_width

    root_node = Node(name="build/", trailing_comment="<-- example build dir struct")
    target_id = root_node.add_child(name="<build-id>/", trailing_comment="build-id derived from {config+overlays, board, device, memmap}")
    
    ##########################################################################################################################
    # Phase 1: Generated configuration and build artifacts
    ##########################################################################################################################
    generated_dir = target_id.add_child(name="generated/", trailing_comment="Phase 1: Generated configuration and build artifacts")
    config_dir = generated_dir.add_child(name="config/", trailing_comment="")
    config_dir.add_child(name="merged.toml", trailing_comment="")
    make_dir = generated_dir.add_child(name="make/", trailing_comment="")
    make_dir.add_child(name="config.mk.d", trailing_comment="")
    make_dir.add_child(name="curv.mk", trailing_comment="")
    sv_dir = generated_dir.add_child(name="sv/", trailing_comment="")
    sv_dir.add_child(name="curvcfgpkg.sv", trailing_comment="")
    sv_dir.add_child(name="curvcfg.svh", trailing_comment="")
    sv_dir.add_child(name="memmappkg.sv", trailing_comment="")
    docs_dir = generated_dir.add_child(name="docs/", trailing_comment="")
    docs_dir.add_child(name="MEMORY_MAP.md", trailing_comment="")
    shell_dir = generated_dir.add_child(name="shell/", trailing_comment="")
    shell_dir.add_child(name="curv.env", trailing_comment="")
    
    ##########################################################################################################################
    # Phase 2: Firmware build (uses generated/ files)
    ##########################################################################################################################
    firmware_dir = target_id.add_child(name="fw/", trailing_comment="Phase 2: Firmware build (uses generated/ files)")
    cache_prefills_dir = firmware_dir.add_child(name="cache-prefills/", trailing_comment="")
    auipc_bypass_dir = cache_prefills_dir.add_child(name="auipc-bypass/", trailing_comment="")
    auipc_bypass_build_dir = auipc_bypass_dir.add_child(name="build/", trailing_comment="")
    auipc_bypass_build_dir.add_child(name="cache-prefill.elf", trailing_comment="")
    auipc_bypass_build_dir.add_child(name="icache.hex", trailing_comment="")
    auipc_bypass_build_dir.add_child(name="dcache.hex", trailing_comment="")
    auipc_docs_dir = auipc_bypass_dir.add_child(name="docs/", trailing_comment="")
    auipc_docs_dir.add_child(name="cache_readme.txt", trailing_comment="")
    auipc_sv_dir = auipc_bypass_dir.add_child(name="sv/", trailing_comment="")
    auipc_sv_dir.add_child(
        name="cache_hex_files_paths.svh",
        trailing_comment="This gets included by the cache SV files to find the paths to all the hex files in this directory.",
    )
    dcache_dir = auipc_bypass_dir.add_child(name="dcache/", trailing_comment="")
    dcache_cachelines_dir = dcache_dir.add_child(name="cachelines/", trailing_comment="")
    dcache_cachelines_dir.add_child(name="way0.hex", trailing_comment="")
    dcache_cachelines_dir.add_child(name="way1.hex", trailing_comment="")
    dcache_tagram_dir = dcache_dir.add_child(name="tagram/", trailing_comment="")
    dcache_tagram_dir.add_child(name="way0.hex", trailing_comment="")
    dcache_tagram_dir.add_child(name="way1.hex", trailing_comment="")
    dcache_tagram_dir.add_child(name="interleaved.bin", trailing_comment="")
    icache_dir = auipc_bypass_dir.add_child(name="icache/", trailing_comment="")
    icache_cachelines_dir = icache_dir.add_child(name="cachelines/", trailing_comment="")
    icache_cachelines_dir.add_child(name="way0.hex", trailing_comment="")
    icache_cachelines_dir.add_child(name="way1.hex", trailing_comment="")
    icache_tagram_dir = icache_dir.add_child(name="tagram/", trailing_comment="")
    icache_tagram_dir.add_child(name="way0.hex", trailing_comment="")
    icache_tagram_dir.add_child(name="way1.hex", trailing_comment="")
    icache_tagram_dir.add_child(name="interleaved.bin", trailing_comment="")
    bootrom_dir = firmware_dir.add_child(name="bootrom/", trailing_comment="")
    bootrom_build_dir = bootrom_dir.add_child(name="build/", trailing_comment="")
    bootrom_build_dir.add_child(name="firmware.elf", trailing_comment="")
    bootrom_build_dir.add_child(name="firmware.hex", trailing_comment="")

    ##########################################################################################################################
    # Phase 3a (tb only): Verilator simulations (uses generated/ files + fw/build/)
    ##########################################################################################################################
    sims_dir = firmware_dir.add_child(name="sims/", trailing_comment="")
    auipc_bypass_sims_dir = sims_dir.add_child(name="auipc-bypass/", trailing_comment="")
    obj_dir = auipc_bypass_sims_dir.add_child(name="obj_dir/", trailing_comment="Phase 3a (tb only): Verilator binary (uses generated/ files + fw/build/)")
    obj_dir.add_child(name="...", trailing_comment="")
    vcd_dir = auipc_bypass_sims_dir.add_child(name="vcds/", trailing_comment="Phase 3a (tb only): wave files from Verilator simulation")
    vcd_dir.add_child(name="...", trailing_comment="")
    
    ##########################################################################################################################
    # Phase 3b (FPGA only): FPGA synthesis (uses generated/ files + fw/build/)
    ##########################################################################################################################
    synthesis_dir = target_id.add_child(name="synthesis/", trailing_comment="Phase 3b (FPGA only): FPGA synthesis (uses generated/ files + fw/build/)")
    ulx3s_dir = synthesis_dir.add_child(name="ulx3s/", trailing_comment="")
    ulx3s_dir.add_child(name="curvsoc.ldf", trailing_comment="")
    ulx3s_dir.add_child(name="curvsoc.sty", trailing_comment="")
    logs_dir = ulx3s_dir.add_child(name="logs/", trailing_comment="These are logs that are extracted from the FPGA synthesis tools to highlight specific issues.")
    logs_dir.add_child(name="par_timing_problems.txt", trailing_comment="")
    logs_dir.add_child(name="script2.jq", trailing_comment="")
    logs_dir.add_child(name="script.jq", trailing_comment="")
    logs_dir.add_child(name="slang.json", trailing_comment="")
    logs_dir.add_child(name="syn_compile_report.txt", trailing_comment="")
    logs_dir.add_child(name="syn_error.txt", trailing_comment="")
    logs_dir.add_child(name="syn_warning.txt", trailing_comment="")
    diamond_project_dir = ulx3s_dir.add_child(name="diamond/", trailing_comment="")
    diamond_project_dir.add_child(name="...", trailing_comment="all the usual Diamond generated files")
    constraints_dir = ulx3s_dir.add_child(name="constraints/", trailing_comment="")
    constraints_dir.add_child(name="constraints.lpf", trailing_comment="copied from the board dir")
    constraints_dir.add_child(name="final.sdc", trailing_comment="combination of board-specific and design-specific")
    bitstreams_dir = ulx3s_dir.add_child(name="bitstreams/", trailing_comment="")
    bitstreams_dir.add_child(name="curvcsoc-ulx3s-85f.bit", trailing_comment="bitstream file for the FPGA")
    rom_hex_dir = ulx3s_dir.add_child(name="rom-hex/", trailing_comment="")
    rom_hex_dir.add_child(name="curvcsoc-ulx3s-85f.hex", trailing_comment="hex file for the FPGA boot flash programming")

    root_node.spill_recursively(add_extra_trailing_spacer=not True)

    return root_node

def render_node(node: Node, parent_tree: Tree, node_list: list[Node]) -> None:
    """Attach a Node and its descendants to the given parent Tree."""
    node_text = Text(f"{node.icon} {node.name}", style=node.style)
    branch = parent_tree.add(node_text, guide_style=None)
    node_list.append(node)
    for child in node.children:
        render_node(child, branch, node_list)

def calculate_max_comment_line_width(tree: Tree, spacing_after_tree: int = DEFAULT_SPACING_AFTER_TREE, right_margin_width: int = DEFAULT_RIGHT_MARGIN_WIDTH) -> int:
    m = Measurement.get(console, console.options, tree)
    max_comment_line_width = console.width - m.maximum - spacing_after_tree - right_margin_width
    if max_comment_line_width < 0:
        max_comment_line_width = 0
    return max_comment_line_width

def parse_args(grandparent_parser: Optional[argparse.ArgumentParser] = None) -> argparse.Namespace:
    parent_parser = argparse.ArgumentParser(add_help=False)
    ansi = AnsiColorsTool()
    ANSI_GREY = ansi.lt_grey
    ANSI_DARK_GREY = ansi.drk_grey
    ANSI_BOLD = ansi.bold
    ANSI_BRIGHT_BLUE = ansi.bright_blue
    ANSI_RESET = ansi.reset
    parser = argparse.ArgumentParser(
        description="Render a tree of files / directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=([grandparent_parser] if grandparent_parser is not None else []),
        epilog="""
{ANSI_BOLD}Examples:{ANSI_RESET}

  $ {ANSI_BRIGHT_BLUE}{prog} -d{ANSI_RESET}
  {ANSI_GREY}[...prints the entire tree based on test data...]{ANSI_RESET}

  $ {ANSI_BRIGHT_BLUE}{prog} -e [env-file-path]{ANSI_RESET}
  {ANSI_GREY}[...prints the entire tree based on the environment file specified by -e/--env-file...]{ANSI_RESET}

  {ANSI_DARK_GREY}# -q flag emits lines that can be eval'd in a shell script{ANSI_RESET}
  $ {ANSI_BRIGHT_BLUE}{prog} -L 70 -q{ANSI_RESET}
  {ANSI_GREY}CHUNKS_COUNT=2{ANSI_RESET}
  {ANSI_GREY}LAST_CHUNK_LINE_COUNT=35{ANSI_RESET}
  $ {ANSI_BRIGHT_BLUE}eval "$({prog} -L 70 -q)" ; printf '%s\\n' "$CHUNKS_COUNT"{ANSI_RESET}
  {ANSI_GREY}2{ANSI_RESET}
  $ {ANSI_BRIGHT_BLUE}eval "$({prog} -L 70 -q)" ; printf '%s\\n' "$LAST_CHUNK_LINE_COUNT"{ANSI_RESET}
  {ANSI_GREY}35{ANSI_RESET}

  {ANSI_DARK_GREY}# print one chunk at a time{ANSI_RESET}
  $ {ANSI_BRIGHT_BLUE}{prog} -L 70 -l 0{ANSI_RESET}
  {ANSI_GREY}[...prints the first chunk of 70 lines...]{ANSI_RESET}
  $ {ANSI_BRIGHT_BLUE}{prog} -L 70 -l 1{ANSI_RESET}
  {ANSI_GREY}[...prints the second chunk of 35 lines...]{ANSI_RESET}
  $ {ANSI_BRIGHT_BLUE}{prog} -L 70 -l 2{ANSI_RESET}
  {ANSI_GREY}No more chunks remaining{ANSI_RESET}
""".format(prog=parent_parser.prog, ANSI_GREY=ANSI_GREY, ANSI_DARK_GREY=ANSI_DARK_GREY, ANSI_RESET=ANSI_RESET, ANSI_BOLD=ANSI_BOLD, ANSI_BRIGHT_BLUE=ANSI_BRIGHT_BLUE),
    )
    chunk_group = parser.add_argument_group("Chunk Mode Options")
    chunk_group.add_argument("--chunk-lines-amount", '-L', type=int, default=None, help="Emit lines in chunks of this amount. If 0, will print the entire tree.  If not specified, will print the entire tree and chunk mode is disabled so other options like --chunk-number and --chunks-count are ignored.")
    chunk_group.add_argument("--chunk-number", '-l', type=int, default=0, help="If there are more than --chunk-lines-amount lines, emit this chunk. The first chunk is numbered zero.  If you request a chunk number beyond the final one, the program will exit with code 1 to indicate no additional lines remain.  Ignored unless --chunk-lines-amount/-L is specified. (Default: %(default)s).")
    chunk_group.add_argument("--chunk-count", '-q', action="store_true", default=False, help="Query for the total number of chunks that can be emitted. The maximum --chunk-number is one less than the total number of chunks.  Ignored unless --chunk-lines-amount/-L is specified. (Default: %(default)s).")
    data_source_group = parser.add_argument_group("Data Source Options")
    data_source_group_mutex = data_source_group.add_mutually_exclusive_group()
    data_source_group_mutex.add_argument("--env-file", '-e', dest="data_source", type=str, help="Path to the environment file to use for the data source.")
    data_source_group_mutex.add_argument("--dummy-data", '-d', dest="data_source", action="store_const", const="USE_DUMMY_DATA", help="Use dummy data instead of the data source (default).")
    parser.set_defaults(data_source="USE_DUMMY_DATA")
    args = parser.parse_args()

    if args.data_source is None:
        parser.error("Either --env-file or --dummy-data must be specified.")
    
    try:
        console.width = args.width
    except Exception as e:
        log.error(f"ERROR: could not set console width to {args.width}: {e}")
        raise SystemExit(1) from e

    return args

def main(parent_parser: Optional[argparse.ArgumentParser] = None) -> None:
    env_values:dict[str, int | str] = {}
    env_values = get_env_or_defaults()

    def logger_strip_ansi(s: str) -> str:
        ansi_re = re.compile(r"\x1b\[[0-9;]*m")
        return ansi_re.sub("", s).rstrip()

    args = parse_args(grandparent_parser=parent_parser)
    
    # use either dummy data or the environment file to make the data per the CLI args
    max_comment_line_width = None # initial value to prevent any spilling until we know tree width
    if args.data_source == "USE_DUMMY_DATA":
        data_fn = lambda max_comment_line_width: make_dummy_data(max_comment_line_width)
    else:
        data_fn = lambda max_comment_line_width: make_data_from_path_env(max_comment_line_width, env_file=args.data_source)
    
    # make the Node tree from the data source
    root = data_fn(max_comment_line_width)

    invisible_table = Table.grid(padding=0)
    invisible_table.add_column("tree", justify="left", no_wrap=True)
    invisible_table.add_column("comments", justify="left", no_wrap=True)

    # first render of the tree is just to determine its width
    node_list = [root]
    root_text = Text(f"{root.icon} {root.name}", style=root.style)
    tree = Tree(root_text, guide_style="bold bright_blue")
    for child in root.children:
        render_node(child, tree, node_list)
    max_comment_line_width = calculate_max_comment_line_width(tree)
    # print(f"max_comment_line_width: {max_comment_line_width}")

    # second render of the tree with the spacer nodes inserted
    root = data_fn(max_comment_line_width)
    node_list = [root]
    root_text = Text(f"{root.icon} {root.name}", style=root.style)
    tree = Tree(root_text, guide_style="bold bright_blue")
    for child in root.children:
        render_node(child, tree, node_list)

    # creat the comment text nodes list and append them to the invisible table
    text_nodes = []
    for n in node_list:
        text_nodes.append(Text(n.comment))
        text_nodes.append(Text("\n"))
    invisible_table.add_row(tree, Text.assemble(*text_nodes[:-1]))

    def ansi_aware_replace(s: str) -> str:
        ANSI_RE = r"\x1b\[[0-9;]*m"

        # prefix: any number of SGRs applied to the guides
        # mid:    any SGRs between the guides and "<"
        pat_non_corner = re.compile(
            rf"(?P<prefix>(?:{ANSI_RE})*)┣━━ (?P<mid>(?:{ANSI_RE})*)(?P<erase_marker>[<^])(?P<precomment_space>[\s<]*)(?P<mid2>(?:{ANSI_RE})*)(?P<comment>[^\n]*)"
        )
        pat_corner = re.compile(
            rf"(?P<prefix>(?:{ANSI_RE})*)┗━━ (?P<mid>(?:{ANSI_RE})*)(?P<erase_marker>[<^])(?P<precomment_space>[\s<]*)(?P<mid2>(?:{ANSI_RE})*)(?P<comment>[^\n]*)"
        )
        # pat_last_node_in_subtree = re.compile(
        #     rf"(?P<prefix>(?:{ANSI})*)┣━━ (?P<mid0>(?:{ANSI})*)📄 (?P<mid1>(?:{ANSI})*)(?P<name>[^\n<\x1b]*)(?P<mid2>(?:{ANSI})*)(?P<precomment_space>\s*<<<<\s*)(?P<mid3>(?:{ANSI})*)(?P<comment>[^\n]*)"
        # )
        pat_last_node_in_subtree2 = re.compile(
            rf"""
            (?P<prefix>(?:{ANSI_RE})*)            # guides / prefix
            [┗|┣]━━\s                             # literal guides and space
            (?P<mid0>(?:{ANSI_RE})*)              # color for the leaf
            📄\s                                  # leaf emoji + space
            (?P<mid1>(?:{ANSI_RE})*)              # any ANSI before name
            (?P<name>[^\n<\x1b]*)                 # name: anything but newline, '<', or ESC
            (?P<mid2>(?:{ANSI_RE})*)              # ANSI after name
            (?P<precomment_space>\s*<<<<\s*)      # require '<<<<' (with optional spaces)
            (?P<mid3>(?:{ANSI_RE})*)              # ANSI before comment
            (?P<comment>[^\n]*)                   # rest of the line, up to newline
            """,
            re.VERBOSE,
        )

        def repl_non_corner(m: re.Match) -> str:
            prefix = m.group("prefix")  # guide style
            mid = m.group("mid")        # style that was applied to "<"
            erase_marker = m.group("erase_marker") # "<" or "^"
            comment = m.group("comment") # the comment text
            precomment_space = m.group("precomment_space") # the space before the comment
            mid2 = m.group("mid2") # style that was applied to the space before the comment

            # console.print(f"erase_marker: '{erase_marker}'")
            # console.print(f"comment: '{comment}'")
            # console.print(f"precomment_space: '{precomment_space}'")
            # console.print(f"mid2: '{mid2}'")

            # Keep the styles, swap visible glyphs only.
            if '# <[DEBUG:' in comment:
                comment = ""
            if erase_marker == "<":
                return f"{prefix}┃    {mid}{precomment_space}{mid2}{comment}"
            else:
                return f"{prefix}     {mid}{precomment_space}{mid2}{comment}"

        def repl_corner(m: re.Match) -> str:
            prefix = m.group("prefix")  # guide style
            mid = m.group("mid")        # style that was applied to "<"
            erase_marker = m.group("erase_marker") # "<" or "^"
            comment = m.group("comment") # the comment text
            precomment_space = m.group("precomment_space") # the space before the comment
            mid2 = m.group("mid2") # style that was applied to the space before the comment

            # console.print(f"erase_marker: '{erase_marker}'")
            # console.print(f"comment: '{comment}'")
            # console.print(f"precomment_space: '{precomment_space}'")
            # console.print(f"mid2: '{mid2}'")

            if '# <[DEBUG:' in comment:
                comment = ""

            # Keep the styles, swap visible glyphs only.
            return f"{prefix}     {mid}{precomment_space}{mid2}{comment}"

        def repl_last_node_in_subtree(m: re.Match) -> str:
            prefix = m.group("prefix")   # guide style
            mid0 = m.group("mid0")        # style that was applied to "<"
            emoji = '📄 '                 # the emoji used for the last node in a subtree
            mid1 = m.group("mid1")        # style that was applied to the name
            name = m.group("name")        # the name of the last node in a subtree
            mid2 = m.group("mid2")        # style that was applied to the space before the comment
            precomment_space = m.group("precomment_space") # the space before the comment
            mid3 = m.group("mid3")        # style that was applied to the comment
            comment = m.group("comment") # the comment text

            # console.print(f"(pat_last_node_in_subtree) prefix: '{prefix}'")
            # console.print(f"(pat_last_node_in_subtree) mid0: '{mid0}'")
            # console.print(f"(pat_last_node_in_subtree) emoji: '{emoji}'")
            # console.print(f"(pat_last_node_in_subtree) mid1: '{mid1}'")
            # console.print(f"(pat_last_node_in_subtree) name: '{name}'")
            # console.print(f"(pat_last_node_in_subtree) mid2: '{mid2}'")
            # console.print(f"(pat_last_node_in_subtree) precomment_space: '{precomment_space}'")
            # console.print(f"(pat_last_node_in_subtree) mid3: '{mid3}'")
            # console.print(f"(pat_last_node_in_subtree) comment: '{comment}'")

            precomment_space = precomment_space.replace('<', ' ')

            return f"{prefix}┗━━ {mid0}{emoji}{mid1}{name}{mid2}{precomment_space}{mid3}{comment}"

        if not DEBUG_DISABLE_REPLACEMENTS:
            s = pat_corner.sub(repl_corner, s)
            s = pat_non_corner.sub(repl_non_corner, s)
            s = pat_last_node_in_subtree2.sub(repl_last_node_in_subtree, s)
        return s

    # capture to termianl with force_terminal=True, then use ansi-aware regex to 
    # replace intentionally marked lines with ' <' with '┃    ', ' ^' with '┗━━', 
    # and '<<<<' with '┗━━'
    with console.capture() as capture:
        console.print(invisible_table)
    s = capture.get()
    s = ansi_aware_replace(s)

    if args.chunk_lines_amount is None or args.chunk_lines_amount == 0:
        lines = s.split('\n')
        for ln in lines:
            if ln.strip() != "":
                print(ln)
                log.debug(logger_strip_ansi(ln))
        sys.exit(0)
    else:
        # chunk mode enabled
        lines1 = s.split('\n')
        lines = [ln for ln in lines1 if ln.strip() != ""]
        chunks = [lines[i:i+args.chunk_lines_amount] for i in range(0, len(lines), args.chunk_lines_amount)]
        if args.chunk_count:
            print(f"CHUNKS_COUNT={len(chunks)}")
            print(f"LAST_CHUNK_LINE_COUNT={len(chunks[-1])}")
            log.info(f"CHUNKS_COUNT={len(chunks)}")
            log.info(f"LAST_CHUNK_LINE_COUNT={len(chunks[-1])}")
            sys.exit(0)
        elif args.chunk_number < len(chunks):
            for ln in chunks[args.chunk_number]:
                print(ln)
                log.debug(logger_strip_ansi(escape(ln)))
            sys.exit(0)
        else:
            console.print("No more chunks remaining")
            log.error("No more chunks remaining")
            sys.exit(1)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        log.critical(f"Error: %s", e, exc_info=True)
        sys.exit(1)

