import re
from typing import Dict, Set, Any, Tuple

from peg_leg.ast import Clause, Rule, Alt, Rgx, Seq, Str, GrammarResolver, \
    NoSubClause, NLook
from peg_leg.utils import ClauseQueue


def reachable_clauses(clause, visited: Set[Clause]):
    clauses = []
    if clause not in visited:
        visited.add(clause)
        for subclause in clause:
            clauses.extend(reachable_clauses(subclause, visited))
        clauses.append(clause)
    return clauses


def find_cycle_head_clauses(clause,
                            discovered: Set[Clause],
                            finished: Set[Clause]):
    discovered.add(clause)
    heads = set()
    for subclause in clause:
        if subclause in discovered:
            # reached a cycle
            heads.add(subclause)
        elif subclause not in finished:
            heads |= find_cycle_head_clauses(subclause, discovered, finished)
    discovered.remove(clause)
    finished.add(clause)
    return heads


def topo_sort(all_rules):
    visited = set()
    all_clauses_unordered = []
    for clause in all_rules:
        all_clauses_unordered.extend(reachable_clauses(clause, visited))

    top_clauses = set(all_clauses_unordered)
    for clause in all_clauses_unordered:
        for subclause in clause:
            if subclause in top_clauses:
                top_clauses.remove(subclause)

    dfs_roots = list(top_clauses)
    cycle_discovered = set()
    cycle_finished = set()
    cycle_head_clauses = set()
    for clause in top_clauses:
        cycle_head_clauses |= find_cycle_head_clauses(
            clause, cycle_discovered, cycle_finished)
    for rule in all_rules:
        cycle_head_clauses |= find_cycle_head_clauses(
            rule, cycle_discovered, cycle_finished)

    dfs_roots.extend(cycle_head_clauses)
    all_clauses = []
    reachable_visited = set()
    for top_clause in dfs_roots:
        all_clauses.extend(reachable_clauses(top_clause, reachable_visited))
    for i, clause in enumerate(all_clauses):
        clause.topo_idx = i
    return all_clauses


class Grammar:
    all_rules: Dict[str, Rule]
    all_clauses: Set[Clause]
    top: Rule

    def __init__(self, *rules: Rule):
        self.all_rules = {rule.name: rule for rule in rules}
        self.top = rules[0]
        for rule in self.all_rules.values():
            rule.clause.visit(GrammarResolver(), self.all_rules)
        all_clauses = topo_sort(self.all_rules.values())

        for clause in all_clauses:
            clause.determine_matches_empty()
            clause.depend_on_child()
            print(clause.topo_idx, clause.matches_empty, clause)

        self.all_clauses = set(all_clauses)


class MemoKey:
    start: int
    clause: Clause

    def __init__(self, start, clause):
        self.start = start
        self.clause = clause

    def __repr__(self):
        return f"MemoKey({self.start}, {self.clause})"

    def __hash__(self):
        return hash((self.start, self.clause))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.start == other.start and \
               self.clause == other.clause


class MemoMatch:
    length: int
    content: Any
    alt_prec: int

    def __init__(self, length, content, alt_prec=0):
        self.length = length
        self.content = content
        self.alt_prec = alt_prec

    def __repr__(self):
        if self.alt_prec == 0:
            return f"MemoMatch({self.length}, {self.content})"
        else:
            return f"MemoMatch({self.length}, {self.content}, {self.alt_prec})"


class PikaParser:
    memotable: Dict[MemoKey, MemoMatch]
    grammar: Grammar
    input: str

    def __init__(self, grammar, input):
        self.grammar = grammar
        self.input = input

        self.memotable = {}

    def find_match(self, key: MemoKey) -> MemoMatch:
        if key in self.memotable:
            return self.memotable[key]
        elif isinstance(key.clause, NLook):
            key.clause.visit(self, key.start)
        elif key.clause.matches_empty:
            return MemoMatch(0, None)

    def add_match(self, key: MemoKey, new_match: MemoMatch) -> bool:
        if key in self.memotable:
            old_match = self.memotable[key]
            if isinstance(key.clause, Alt) and \
                    new_match.alt_prec < old_match.alt_prec:
                self.memotable[key] = new_match
                return True
            elif new_match.length > old_match.length:
                self.memotable[key] = new_match
                return True
            else:
                return False
        else:
            self.memotable[key] = new_match
            return True

    def parse(self):
        curr_index = len(self.input) - 1
        queue = ClauseQueue()
        terminals = {clause
                     for clause in self.grammar.all_clauses
                     if isinstance(clause, NoSubClause)}

        while curr_index >= 0:
            for terminal in terminals:
                queue.schedule(terminal)
            while queue:
                clause = queue.pop()
                match = clause.visit(self, curr_index)
                stored = False
                if match:
                    print(f"Matched `{clause}` at {curr_index}")
                    key = MemoKey(curr_index, clause)
                    stored = self.add_match(key, match)

                if stored:
                    for parent in clause.dependant:
                        queue.schedule(parent)
                else:
                    # print(f"Failed to match `{clause}` at {curr_index}")
                    for parent in clause.dependant:
                        if parent.matches_empty:
                            queue.schedule(parent)
            curr_index -= 1

        top_key = MemoKey(0, self.grammar.top)
        if top_key in self.memotable:
            match = self.memotable[top_key]
            if match.length == len(self.input):
                return match.content
        return None

    def visit_str(self, str, index):
        str_len = len(str.string)
        if len(self.input[index:]) >= str_len and \
                str.string == self.input[index:index + str_len]:
            return MemoMatch(str_len, str.string)

    def visit_rgx(self, rgx, index):
        match = re.match(rgx.pattern, self.input[index:])
        if match:
            result = match.group()
            return MemoMatch(len(result), result)

    def visit_seq(self, seq, index):
        res = []
        curr_index = index
        for clause in seq:
            key = MemoKey(curr_index, clause)
            match = self.find_match(key)
            if match:
                res.append(match.content)
                curr_index += match.length
            else:
                return None
        return MemoMatch(curr_index - index, res)

    def visit_alt(self, alt, index):
        for prec, clause in enumerate(alt, start=1):
            key = MemoKey(index, clause)
            match = self.find_match(key)
            if match:
                match.alt_prec = prec
                return match
        return None

    def visit_mult(self, mult, index):
        key = MemoKey(index, mult.clause)
        match = self.find_match(key)
        if match:
            tail_key = MemoKey(index + match.length, mult)
            tail_match = self.find_match(tail_key)
            if tail_match:
                return MemoMatch(match.length + tail_match.length,
                                 [match.content, tail_match.content])
            else:
                return MemoMatch(match.length, match.content)
        elif mult.min == 0:
            return MemoMatch(0, None)
        else:
            return None

    def visit_opt(self, opt, index):
        key = MemoKey(index, opt.clause)
        match = self.find_match(key)
        if match:
            return match
        else:
            return MemoMatch(0, None)

    def visit_look(self, look, index):
        key = MemoKey(index, look.clause)
        match = self.find_match(key)
        if match:
            return MemoMatch(0, match.content)
        else:
            return None

    def visit_nlook(self, nlook, index):
        key = MemoKey(index, nlook.clause)
        match = self.find_match(key)
        if match:
            return None
        else:
            return MemoMatch(0, None)

    def visit_rule(self, rule, index):
        key = MemoKey(index, rule.clause)
        return self.find_match(key)
