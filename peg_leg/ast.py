import re
from abc import ABC, abstractmethod
from typing import Union, List, Dict, Set, Tuple, Optional

Node = Union['Rule', 'Seq', 'Alt', 'Mult', 'Opt', 'Look', 'NLook', 'Str', 'Rgx']


class Clause(ABC):
    topo_idx: int
    dependant: Set['Clause']
    matches_empty: Optional[bool]

    def __init__(self):
        self.dependant = set()
        self.matches_empty = None

    def depend_on_child(self):
        for child in self:
            child.dependant.add(self)

    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def __hash__(self):
        pass

    @abstractmethod
    def __eq__(self, other):
        pass

    @abstractmethod
    def determine_matches_empty(self):
        pass


class MultiSubClause(Clause, ABC):
    clauses: List[Clause]

    def __iter__(self):
        return iter(self.clauses)

    def __hash__(self):
        return hash((self.__class__, *self.clauses))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               len(self.clauses) == len(other.clauses) and \
               all([x == y for x, y in zip(self.clauses, other.clauses)])


class SingleSubClause(Clause, ABC):
    clause: Clause

    def __iter__(self):
        return iter([self.clause])

    def __hash__(self):
        return hash((self.__class__, self.clause))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.clause == other.clause


class NoSubClause(Clause, ABC):
    def __iter__(self):
        return iter([])


class Rule(SingleSubClause):
    name: str

    def __init__(self, name, clause=None):
        super().__init__()
        self.name = name
        self.clause = clause

    def __hash__(self):
        return hash((Rule, self.name))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.name == other.name

    def __str__(self):
        return f"{self.name}"

    def determine_matches_empty(self):
        self.matches_empty = self.clause.matches_empty

    def visit(self, visitor, *a, **kw):
        return visitor.visit_rule(self, *a, **kw)


class Seq(MultiSubClause):
    def __init__(self, *subclauses: Clause):
        super().__init__()
        self.clauses = list(subclauses)

    def __iter__(self):
        return reversed(self.clauses)

    def __str__(self):
        return f'({" ".join(str(clause) for clause in self)})'

    def determine_matches_empty(self):
        for clause in self:
            if clause.matches_empty == True:
                self.matches_empty = True
            elif clause.matches_empty == False:
                self.matches_empty = False
                return

    def depend_on_child(self):
        for child in self:
            child.dependant.add(self)
            if not child.matches_empty:
                break

    def visit(self, visitor, *a, **kw):
        return visitor.visit_seq(self, *a, **kw)


class Alt(MultiSubClause):
    def __init__(self, *subclauses: Clause):
        super().__init__()
        self.clauses = list(subclauses)

    def __str__(self):
        return " | ".join(str(clause) for clause in self)

    def determine_matches_empty(self):
        for clause in self:
            if clause.matches_empty == False:
                self.matches_empty = False
            elif clause.matches_empty == True:
                self.matches_empty = True
                return

    def visit(self, visitor, *a, **kw):
        return visitor.visit_alt(self, *a, **kw)


class Mult(SingleSubClause):
    min: int

    def __init__(self, min, clause):
        super().__init__()
        self.min = min
        self.clause = clause

    def __hash__(self):
        return hash((Mult, self.min, self.clause))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.min == other.min and \
               self.clause == other.clause

    def __str__(self):
        if self.min == 0:
            symbol = "*"
        elif self.min > 0:
            symbol = "+"
        return f"{self.clause}{symbol}"

    def determine_matches_empty(self):
        assert self.clause.matches_empty == False
        if self.min == 0:
            self.matches_empty = True
        else:
            self.matches_empty = self.clause.matches_empty

    def visit(self, visitor, *a, **kw):
        return visitor.visit_mult(self, *a, **kw)


class Opt(SingleSubClause):
    def __init__(self, clause):
        super().__init__()
        self.clause = clause

    def __str__(self):
        return f"{self.clause}?"

    def determine_matches_empty(self):
        self.matches_empty = True

    def visit(self, visitor, *a, **kw):
        return visitor.visit_opt(self, *a, **kw)


class Look(SingleSubClause):
    def __init__(self, clause):
        super().__init__()
        self.clause = clause

    def __str__(self):
        return f"&{self.clause}"

    def determine_matches_empty(self):
        assert self.clause.matches_empty == False
        # matches_empty is False because Lookahead needs to be scheduled only
        # when its subclause matches
        self.matches_empty = False

    def visit(self, visitor, *a, **kw):
        return visitor.visit_look(self, *a, **kw)


class NLook(SingleSubClause):
    def __init__(self, clause):
        super().__init__()
        self.clause = clause

    def __str__(self):
        return f"!{self.clause}"

    def determine_matches_empty(self):
        assert self.clause.matches_empty == False
        # matches_empty is True because Negative Lookahead needs to be
        # triggered when its subcaluse does not match
        self.matches_empty = True

    def visit(self, visitor, *a, **kw):
        return visitor.visit_nlook(self, *a, **kw)


class Str(NoSubClause):
    string: str

    def __init__(self, string):
        super().__init__()
        self.string = string

    def __hash__(self):
        return hash((Str, self.string))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.string == other.string

    def __repr__(self):
        return f"Str(\"{self.string}\")"

    def __str__(self):
        return f'"{self.string}"'

    def determine_matches_empty(self):
        self.matches_empty = len(self.string) == 0

    def visit(self, visitor, *a, **kw):
        return visitor.visit_str(self, *a, **kw)


class Rgx(NoSubClause):
    pattern: str

    def __init__(self, pattern):
        super().__init__()
        self.pattern = pattern

    def __hash__(self):
        return hash((Rgx, self.pattern))

    def __eq__(self, other):
        return self.__class__ == other.__class__ and \
               self.pattern == other.pattern

    def __str__(self):
        return f'/{self.pattern}/'

    def determine_matches_empty(self):
        self.matches_empty = False

    def visit(self, visitor, *a, **kw):
        return visitor.visit_rgx(self, *a, **kw)


class GrammarResolver:
    def visit_rule(self, rule: Rule, rules) -> Rule:
        if rule.name in rules:
            return rules[rule.name]
        else:
            raise AssertionError(f"Cannot link rule {rule.name}")

    def visit_seq(self, seq: Seq, rules) -> Seq:
        for i, clause in enumerate(seq.clauses):
            seq.clauses[i] = clause.visit(self, rules)
        return seq

    def visit_alt(self, alt: Alt, rules) -> Alt:
        for i, clause in enumerate(alt.clauses):
            alt.clauses[i] = clause.visit(self, rules)
        return alt

    def visit_mult(self, mult: Mult, rules) -> Mult:
        mult.clause = mult.clause.visit(self, rules)
        return mult

    def visit_opt(self, opt: Opt, rules) -> Opt:
        opt.clause = opt.clause.visit(self, rules)
        return opt

    def visit_look(self, look: Look, rules) -> Look:
        look.clause = look.clause.visit(self, rules)
        return look

    def visit_nlook(self, nlook: NLook, rules) -> NLook:
        nlook.clause = nlook.clause.visit(self, rules)
        return nlook

    def visit_str(self, string: Str, rules) -> Str:
        return string

    def visit_rgx(self, regex: Rgx, rules) -> Rgx:
        return regex
