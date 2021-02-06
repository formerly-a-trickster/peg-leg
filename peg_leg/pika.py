import re
from abc import abstractmethod, ABC
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
        clause.priority = i
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
            clause.determine_saplings()
            clause.determine_seeds()
        for clause in all_clauses:
            saplings = [str(s) for s in clause.saplings]
            saplings = "\n      ".join(saplings)
            saplings = "{" + saplings + "}"

            seeds = [str(s) for s in clause.seeds]
            seeds = "\n       ".join(seeds)
            seeds = "{" + seeds + "}"

            print(f"""Rule: {clause}
Prio: {clause.priority}
Sapl: {saplings}
Seed: {seeds}
Empt: {clause.matches_empty}
""")

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


class MemoEntry(ABC):
    success: bool


class MemoMatch(MemoEntry):
    length: int
    content: Any
    alt_prec: int

    def __init__(self, length, content, alt_prec=0):
        self.length = length
        self.content = content
        self.success = True
        self.alt_prec = alt_prec

    def __repr__(self):
        if self.alt_prec == 0:
            return f"MemoMatch({self.length}, {self.content})"
        else:
            return f"MemoMatch({self.length}, {self.content}, {self.alt_prec})"


class MemoFail(MemoEntry):
    error: Any
    alt_prec: int

    def __init__(self, error, alt_prec=0):
        self.error = error
        self.success = False
        self.alt_prec = alt_prec

    def __repr__(self):
        if self.alt_prec == 0:
            return f"MemoFail({self.error})"
        else:
            return f"MemoFail({self.error}, {self.alt_prec})"


class PikaParser:
    memotable: Dict[MemoKey, MemoMatch]
    grammar: Grammar
    input: str

    def __init__(self, grammar, input):
        self.grammar = grammar
        self.input = input

        self.memotable = {}

    def add_match(self, key: MemoKey, new_match: MemoMatch) -> bool:
        if key in self.memotable:
            old_match = self.memotable[key]
            if new_match.length > old_match.length:
                self.memotable[key] = new_match
                return True
            else:
                return False
        else:
            self.memotable[key] = new_match
            return True

    def parse(self):
        return self.match(0, self.grammar.top)

    def match(self, index, clause):
        key = MemoKey(index, clause)
        if key in self.memotable:
            return self.memotable[key]
        else:
            return self.grow(index, clause)

    def grow(self, index, clause):
        assert clause.seeds, f"Cannot grow `{clause}`, no available seeds"

        queue = ClauseQueue()
        for seed in clause.seeds:
            queue.schedule(seed)
        while queue:
            current = queue.pop()
            key = MemoKey(index, current)
            match = current.visit(self, index)
            stored = False
            if match.success:
                print(f"Matched `{current}` @ {index}")
                stored = self.add_match(key, match)
            if stored:
                for parent in current.saplings:
                    if parent.priority <= clause.priority:
                        queue.schedule(parent)
            else:
                print(f"Failed to match `{current}` @ {index}")
                self.memotable[key] = match
                for parent in current.saplings:
                    if parent.matches_empty and \
                            parent.priority <= clause.priority:
                        queue.schedule(parent)
        key = MemoKey(index, current)
        if key in self.memotable:
            return self.memotable[key]

    def visit_str(self, str, index):
        str_len = len(str.string)
        if len(self.input[index:]) >= str_len and \
                str.string == self.input[index:index + str_len]:
            return MemoMatch(str_len, str.string)
        else:
            return MemoFail(f"Could not match `{str.string}`")

    def visit_seq(self, seq, index):
        res = []
        curr_index = index
        for clause in seq:
            match = self.match(curr_index, clause)
            if match.success:
                res.append(match.content)
                curr_index += match.length
            else:
                return match
        return MemoMatch(curr_index - index, res)

    def visit_alt(self, alt, index):
        for clause in alt:
            match = self.match(index, clause)
            if match.success:
                return match
            else:
                continue
        return MemoFail(f"Could not match `{alt}`")

    def visit_mult(self, mult, index):
        res = []
        times_matched = 0
        curr_index = index
        while True:
            match = self.match(curr_index, mult.clause)
            if match.success:
                res.append(match.content)
                curr_index += match.length
                times_matched += 1
            elif times_matched < mult.min:
                return MemoFail(
                        f"{mult} did not match at least {mult.min} times")
            else:
                return MemoMatch(curr_index, res)

    def visit_opt(self, opt, index):
        match = self.match(index, opt.clause)

    def visit_rule(self, rule, index):
        return self.match(index, rule.clause)
