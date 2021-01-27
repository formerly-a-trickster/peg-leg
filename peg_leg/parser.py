import re
from collections import defaultdict
from typing import Callable, Dict, Optional, Tuple, Any, List, Set

from .ast import GrammarResolver, Node, Rule, Seq, Alt, Mult, Opt, Str, Rgx, \
    Look, NLook


class ParsingError(Exception):
    def __init__(self, msg: str, index: int, input: str):
        lines = input.split('\n')
        curr_len = 0
        for line_no, line in enumerate(lines):
            if curr_len + len(line) > index:
                pos = index - curr_len
                self.args = msg, (line_no + 1, pos), line
                return
            else:
                curr_len += len(line)
        self.args = msg, None, lines[-1]
        return

    def __str__(self):
        msg, loc, line = self.args
        if line[-1] != '\n':
            line += '\n'
        if loc:
            line_no, pos = loc
            context = f'at line {line_no}, pos {pos}:'
            pointer = (" " * (pos - 1)) + "/\\"
            return f'{msg} {context}\n{line}{pointer}'
        else:
            return f'{msg} at end of input:\n{line}'

    def prepend_msg(self, new_msg):
        msg, loc, line = self.args
        self.args = f'{new_msg}\n{msg}', loc, line


class Parser:
    grammar: Optional[Node]
    rules: Dict[str, Rule]
    actions: Dict[str, Callable]
    ignore_ws: bool

    def __init__(self, ignore_ws: bool = False):
        self.grammar = None
        self.rules = {}
        self.actions = {}
        self.ignore_ws = ignore_ws

    @staticmethod
    def from_grammar(grammar: str, *args, **kwargs):
        from .peg import peg_parser

        rules = peg_parser.parse_rule("grammar", grammar)

        parser = Parser(*args, **kwargs)
        parser.grammar = rules[0]
        parser.rules = {rule.name: rule for rule in rules}
        parser.link_rules()
        return parser

    def add_rule(self, pattern: str, action: Optional[Callable] = None):
        from .peg import peg_parser

        rule = peg_parser.parse_rule('rule', pattern)
        if self.grammar is None:
            self.grammar = rule

        name = rule.name
        self.rules[name] = rule
        if action:
            self.actions[name] = action

    def register_action(self, pattern: str):
        def wrap(action: Callable):
            self.add_rule(pattern, action)
            return action

        return wrap

    def link_rules(self):
        resolver = GrammarResolver()
        for rule in self.rules.values():
            rule.node = rule.node.visit(resolver, self.rules)

    def parse(self, input: str) -> Any:
        return self.parse_node(self.grammar, input)

    def parse_rule(self, name: str, input: str) -> Any:
        return self.parse_node(self.rules[name], input)

    def parse_node(self, node: Node, input: str) -> Any:
        run = ParserRun(self.actions, input, self.ignore_ws)
        res, end_index = node.visit(run, 0, [], set())
        if is_err(res):
            raise ParsingError(res.msg, end_index, input)
        if self.ignore_ws:
            end_index = run.skip_whitespace(end_index)
        if len(input) == end_index:
            return res
        raise ParsingError('Expected end of input', end_index, input)


PRes = Tuple[Any, int]


class Error:
    msg: str

    def __init__(self, msg):
        self.msg = msg

    def prepend_msg(self, msg):
        self.msg = msg + self.msg


def is_err(x):
    return type(x) == Error


class LeftRecursion:
    involved: Set[str]

    def __init__(self):
        self.involved = set()


def is_lr(x):
    return type(x) == LeftRecursion


class MemoEntry:
    res: Any
    idx: int

    def __init__(self, res: Any, idx: int):
        self.res = res
        self.idx = idx

    def __str__(self):
        return f"MemoEntry(res={self.res}, idx={self.idx})"

    def unwrap(self) -> Tuple[Any, int]:
        return self.res, self.idx


class ParserRun:
    actions: Dict[str, Callable]
    input: str
    ignore_ws: bool

    memotable: Dict[Tuple[str, int], MemoEntry]

    def __init__(self, actions, input: str, ignore_ws: bool):
        self.actions = actions
        self.input = input
        self.ignore_ws = ignore_ws

        self.memotable = defaultdict(lambda: None)

    def skip_whitespace(self, index: int) -> int:
        curr_index = index
        while True:
            char = self.input[curr_index:curr_index + 1]
            if len(char) > 0 and char.isspace():
                curr_index += 1
            else:
                return curr_index

    def apply_action(self, res, rule):
        if rule.name in self.actions and not is_err(res) and not is_lr(res):
            res = self.actions[rule.name](res)
        return res

    def grow_parse(self,
                   rule: Rule,
                   beg_idx: int,
                   stack: List[str],
                   involved: Set[str],
                   memo: MemoEntry) -> Tuple[Any, int]:
        while True:
            res, end_idx = rule.node.visit(
                self, beg_idx, stack, involved - {rule.name})
            if is_err(res) or end_idx <= memo.idx:
                break
            memo.res = self.apply_action(res, rule)
            memo.idx = end_idx
        return memo.unwrap()

    def get_involved_rules(self, stack: List[str], head: Rule) -> List[str]:
        involved = []
        for name in reversed(stack):
            involved.insert(0, name)
            if name == head.name:
                break
        return involved

    def visit_rule(self,
                   rule: Rule,
                   index: int,
                   stack: List[str],
                   involved: Set[Tuple[str, int]]) -> PRes:
        assert rule.node is not None, f'Rule {rule.name} does not have a body'

        memo = self.memotable[rule.name, index]
        if memo:
            if rule.name in involved:
                memo.res, memo.idx = rule.node.visit(
                    self, index, stack + [rule.name], involved - {rule.name})
                memo.res = self.apply_action(memo.res, rule)
                return memo.unwrap()
            elif is_lr(memo.res):
                path = self.get_involved_rules(stack, rule)
                str_path = "->".join(path)
                memo.res.involved |= set(path)
                msg = f'Infinite left recursion in path {str_path}'
                return Error(msg), index
            else:
                return memo.unwrap()
        else:
            lr = LeftRecursion()
            memo = MemoEntry(lr, index)
            self.memotable[rule.name, index] = memo
            memo.res, memo.idx = rule.node.visit(
                self, index, stack + [rule.name], involved)
            memo.res = self.apply_action(memo.res, rule)
            if lr.involved and not is_err(memo.res):
                return self.grow_parse(rule, index, stack, lr.involved, memo)
            else:
                return memo.unwrap()

    def visit_seq(self, seq: Seq, index: int, *args) -> PRes:
        res = []
        curr_index = index

        for node in seq.nodes:
            val, curr_index = node.visit(self, curr_index, *args)
            if is_err(val):
                return val, curr_index
            res.append(val)
        return res, curr_index

    def visit_alt(self, alt: Alt, index: int, *args) -> PRes:
        for node in alt.nodes:
            res, idx = node.visit(self, index, *args)
            if is_err(res):
                continue
            else:
                return res, idx
        return Error(f'No alternative matched in {alt}'), index

    def visit_mult(self, mult: Mult, index: int, *args) -> PRes:
        res = []
        curr_index = index

        while True:
            val, curr_index = mult.node.visit(self, curr_index, *args)
            if is_err(val):
                if len(res) < mult.min:
                    msg = f'{mult} matched fewer than {mult.min} time(s):\n'
                    val.prepend_msg(msg)
                    return val, curr_index
                else:
                    return res, curr_index
            else:
                res.append(val)

    def visit_opt(self, opt: Opt, index: int, *args) -> PRes:
        res, idx = opt.node.visit(self, index, *args)
        if is_err(res):
            return None, index
        else:
            return res, idx

    def visit_look(self, look: Look, index: int, *args) -> PRes:
        res, _ = look.node.visit(self, index, *args)
        return res, index

    def visit_nlook(self, nlook: NLook, index: int, *args) -> PRes:
        res, _ = nlook.node.visit(self, index, *args)
        if is_err(res):
            return None, index
        else:
            return Error(f'Did not expect {nlook.node}'), index

    def visit_str(self, string: Str, index: int, *args) -> PRes:
        if self.ignore_ws:
            index = self.skip_whitespace(index)
        str_len = len(string.string)
        if str_len <= len(self.input[index:]) and \
                string.string == self.input[index:index + str_len]:
            return string.string, index + str_len
        else:
            return Error(f'Expected `{string.string}`'), index

    def visit_rgx(self, regex: Rgx, index: int, *args) -> PRes:
        if self.ignore_ws:
            index = self.skip_whitespace(index)
        match = re.match(regex.pattern, self.input[index:])
        if match:
            string = match.group()
            return string, index + len(string)
        else:
            return Error(f'Could not match /{regex.pattern}/'), index
