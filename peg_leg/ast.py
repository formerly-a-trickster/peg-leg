import re
from abc import ABC, abstractmethod
from typing import Union, List, Dict, Set, Tuple, Optional

Node = Union['Rule', 'Seq', 'Alt', 'Mult', 'Opt', 'Look', 'NLook', 'Str', 'Rgx']


def extend_clauses(left, right):
    for seed in right:
        if seed not in left:
            left.append(seed)


class Clause(ABC):
    priority: int
    seeds: Tuple['Clause', ...]
    saplings: List['Clause']
    matches_empty: Optional[bool]

    def __init__(self):
        self.saplings = []
        self.seeds = tuple()
        self.matches_empty = None

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
    def determine_saplings(self):
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

    def determine_saplings(self):
        extend_clauses(self.clause.saplings, [self])

    def visit(self, visitor, *a, **kw):
        return visitor.visit_singlesub(self, *a, **kw)


class NoSubClause(Clause, ABC):
    def __iter__(self):
        return iter([])

    def determine_saplings(self):
        pass


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

    def __repr__(self):
        return f"Rule({repr(self.name)})"

    def __str__(self):
        return f"{self.name}"

    def determine_matches_empty(self):
        self.matches_empty = self.clause.matches_empty

    def visit(self, visitor, *a, **kw):
        if hasattr(visitor, 'visit_rule'):
            return visitor.visit_rule(self, *a, **kw)
        else:
            return visitor.visit_singlesub(self, *a, **kw)


class Seq(MultiSubClause):
    def __init__(self, *subclauses: Clause):
        super().__init__()
        self.clauses = list(subclauses)

    def __repr__(self):
        return f'Seq({", ".join(repr(clause) for clause in self)})'

    def __str__(self):
        return f'({" ".join(str(clause) for clause in self)})'

    def determine_matches_empty(self):
        for clause in self:
            if clause.matches_empty == True:
                self.matches_empty = True
            elif clause.matches_empty == False:
                self.matches_empty = False
                return

    def determine_saplings(self):
        for clause in self:
            extend_clauses(clause.saplings, [self])
            if not clause.matches_empty:
                return

    def visit(self, visitor, *a, **kw):
        if hasattr(visitor, 'visit_seq'):
            return visitor.visit_seq(self, *a, **kw)
        else:
            return visitor.visit_multisub(self, *a, **kw)


class Alt(MultiSubClause):
    def __init__(self, *subclauses: Clause):
        super().__init__()
        self.clauses = list(subclauses)

    def __repr__(self):
        return f'Alt({", ".join(repr(clause) for clause in self)})'

    def __str__(self):
        return " | ".join(str(clause) for clause in self)

    def determine_matches_empty(self):
        for clause in self:
            if clause.matches_empty == False:
                self.matches_empty = False
            elif clause.matches_empty == True:
                self.matches_empty = True
                return

    def determine_saplings(self):
        for clause in self:
            extend_clauses(clause.saplings, [self])

    def visit(self, visitor, *a, **kw):
        if hasattr(visitor, 'visit_alt'):
            return visitor.visit_alt(self, *a, **kw)
        else:
            return visitor.visit_multisub(self, *a, **kw)


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

    def __repr__(self):
        return f'Mult({self.min}, {repr(self.clause)})'

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
        if hasattr(visitor, 'visit_mult'):
            return visitor.visit_mult(self, *a, **kw)
        else:
            return visitor.visit_singlesub(self, *a, **kw)


class Opt(SingleSubClause):
    def __init__(self, clause):
        super().__init__()
        self.clause = clause

    def __repr__(self):
        return f"Opt({repr(self.clause)})"

    def __str__(self):
        return f"{self.clause}?"

    def determine_matches_empty(self):
        self.matches_empty = True

    def visit(self, visitor, *a, **kw):
        if hasattr(visitor, 'visit_opt'):
            return visitor.visit_opt(self, *a, **kw)
        else:
            return visitor.visit_singlesub(self, *a, **kw)


class Look(SingleSubClause):
    def __init__(self, clause):
        super().__init__()
        self.clause = clause

    def __repr__(self):
        return f"Look({repr(self.clause)})"

    def __str__(self):
        return f"&{self.clause}"

    def determine_matches_empty(self):
        assert self.clause.matches_empty == False
        # matches_empty is False because Lookahead needs to be scheduled only
        # when its subclause matches
        self.matches_empty = False

    def visit(self, visitor, *a, **kw):
        if hasattr(visitor, 'visit_look'):
            return visitor.visit_look(self, *a, **kw)
        else:
            return visitor.visit_singlesub(self, *a, **kw)


class NLook(SingleSubClause):
    def __init__(self, clause):
        super().__init__()
        self.clause = clause

    def __repr__(self):
        return f"NLook({repr(self.clause)})"

    def __str__(self):
        return f"!{self.clause}"

    def determine_matches_empty(self):
        assert self.clause.matches_empty == False
        # matches_empty is True because Negative Lookahead needs to be
        # triggered when its subcaluse does not match
        self.matches_empty = True

    def visit(self, visitor, *a, **kw):
        if hasattr(visitor, 'visit_nlook'):
            return visitor.visit_nlook(self, *a, **kw)
        else:
            return visitor.visit_singlesub(self, *a, **kw)


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
        return f"Str({repr(self.string)})"

    def __str__(self):
        return f'"{self.string}"'

    def determine_matches_empty(self):
        self.matches_empty = len(self.string) == 0

    def visit(self, visitor, *a, **kw):
        if hasattr(visitor, 'visit_str'):
            return visitor.visit_str(self, *a, **kw)
        else:
            return visitor.visit_nosub(self, *a, **kw)


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

    def __repr__(self):
        return f"Rgx({repr(self.pattern)})"

    def __str__(self):
        return f'/{self.pattern}/'

    def determine_matches_empty(self):
        self.matches_empty = False

    def visit(self, visitor, *a, **kw):
        if hasattr(visitor, 'visit_rgx'):
            return visitor.visit_rgx(self, *a, **kw)
        else:
            return visitor.visit_nosub(self, *a, **kw)


class RuleResolver:
    rules: Dict[str, Rule]

    def __init__(self, rules):
        self.rules = rules

    def visit_rule(self, rule: Rule) -> Rule:
        if rule.name in self.rules:
            return self.rules[rule.name]
        else:
            raise AssertionError(f"Cannot link rule {rule.name}")

    def visit_multisub(self, multi: MultiSubClause) -> MultiSubClause:
        for i, subclause in enumerate(multi.clauses):
            multi.clauses[i] = subclause.visit(self)
        return multi

    def visit_singlesub(self, single: SingleSubClause) -> SingleSubClause:
        single.clause = single.clause.visit(self)
        return single

    def visit_nosub(self, none: NoSubClause) -> NoSubClause:
        return none
