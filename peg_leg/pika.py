import re
from typing import Dict, Set, Any, Tuple, List

from peg_leg.ast import Clause, Rule, Alt, Rgx, Seq, Str, GrammarResolver, \
    NoSubClause, NLook
from peg_leg.utils import ClauseQueue


def reachable_from_clause(clause: Clause, visited: Set[Clause]) -> List[Clause]:
    reachable = []
    if clause not in visited:
        visited.add(clause)
        for subclause in clause:
            reachable.extend(reachable_from_clause(subclause, visited))
        reachable.append(clause)
    return reachable


def reachable_from(*clauses):
    visited = set()
    reachable = []
    for clause in clauses:
        reachable.extend(reachable_from_clause(clause, visited))
    return reachable


def cycle_heads_in_clause(clause,
                          discovered: Set[Clause],
                          finished: Set[Clause]):
    heads = set()
    discovered.add(clause)
    for subclause in clause:
        if subclause in discovered:
            # reached a cycle
            heads.add(subclause)
        elif subclause not in finished:
            heads |= cycle_heads_in_clause(subclause, discovered, finished)
    discovered.remove(clause)
    finished.add(clause)
    return heads


def cycle_heads_in(*clauses):
    discovered = set()
    finished = set()
    heads = set()
    for clause in clauses:
        heads |= cycle_heads_in_clause(clause, discovered, finished)
    return heads


def topo_sort(all_rules):
    all_clauses_unordered = reachable_from(*all_rules)

    top_clauses = set(all_clauses_unordered)
    for clause in all_clauses_unordered:
        for subclause in clause:
            if subclause in top_clauses:
                top_clauses.remove(subclause)

    dfs_roots = list(top_clauses)
    cycle_head_clauses = cycle_heads_in(*top_clauses, *all_rules)

    dfs_roots.extend(cycle_head_clauses)
    all_clauses = reachable_from(*dfs_roots)
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
    end: int
    clause: Clause

    def __init__(self, end, clause):
        self.end = end
        self.clause = clause

    def __repr__(self):
        return f"MemoKey({self.end}, {self.clause})"

    def __hash__(self):
        return hash((self.end, self.clause))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.end == other.end and \
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
            key.clause.visit(self, key.end)
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
        curr_index = 1
        queue = ClauseQueue()
        terminals = {clause
                     for clause in self.grammar.all_clauses
                     if isinstance(clause, NoSubClause)}

        while curr_index <= len(self.input):
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
            curr_index += 1

        top_key = MemoKey(len(self.input), self.grammar.top)
        if top_key in self.memotable:
            match = self.memotable[top_key]
            if match.length == len(self.input):
                return match.content
        return None

    def visit_str(self, str, index):
        str_len = len(str.string)
        if len(self.input[:index]) >= str_len and \
                str.string == self.input[index - str_len:index]:
            return MemoMatch(str_len, str.string)

    def visit_rgx(self, rgx, index):
        if index == 0:
            return
        match = re.match(rgx.pattern, self.input[index - 1:index])
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
                curr_index -= match.length
            else:
                return None
        return MemoMatch(index - curr_index, list(reversed(res)))

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
            tail_key = MemoKey(index - match.length, mult)
            tail_match = self.find_match(tail_key)
            if tail_match and tail_match.length > 0:
                return MemoMatch(match.length + tail_match.length,
                                 tail_match.content + [match.content])
            else:
                return MemoMatch(match.length, [match.content])
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
