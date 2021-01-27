from dataclasses import dataclass
from typing import Union, List, Dict, Optional

Node = Union['Rule', 'Seq', 'Alt', 'Mult', 'Opt', 'Look', 'NLook', 'Str', 'Rgx']


@dataclass
class Rule:
    name: str
    node: Optional[Node] = None

    def __str__(self):
        return self.name

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_rule(self, *args, **kwargs)


@dataclass
class Seq:
    nodes: List[Node]

    def __init__(self, *nodes):
        self.nodes = list(nodes)

    def __str__(self):
        nodes = " ".join([str(node) for node in self.nodes])
        return f"( {nodes} )"

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_seq(self, *args, **kwargs)


@dataclass
class Alt:
    nodes: List[Node]

    def __init__(self, *nodes):
        self.nodes = list(nodes)

    def __str__(self):
        nodes = " | ".join([str(node) for node in self.nodes])
        return f"( {nodes} )"

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_alt(self, *args, **kwargs)


@dataclass
class Mult:
    min: int
    node: Node

    def __str__(self):
        if self.min == 0:
            symbol = "*"
        elif self.min == 1:
            symbol = "+"
        else:
            symbol = "{%d,}" % self.min
        return f"{self.node}{symbol}"

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_mult(self, *args, **kwargs)


@dataclass
class Opt:
    node: Node

    def __str__(self):
        return f"{self.node}?"

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_opt(self, *args, **kwargs)


@dataclass
class Look:
    node: Node

    def __str__(self):
        return f"&{self.node}"

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_look(self, *args, **kwargs)


@dataclass
class NLook:
    node: Node

    def __str__(self):
        return f"!{self.node}"

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_nlook(self, *args, **kwargs)


@dataclass
class Str:
    string: str

    def __str__(self):
        return self.string

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_str(self, *args, **kwargs)


@dataclass
class Rgx:
    pattern: str

    def __str__(self):
        return f"/{self.pattern}/"

    def visit(self, visitor, *args, **kwargs):
        return visitor.visit_rgx(self, *args, **kwargs)


class GrammarResolver:
    def visit_rule(self, rule: Rule, rules: Dict[str, Rule]) -> Rule:
        if rule.name in rules:
            return rules[rule.name]
        else:
            return rule

    def visit_seq(self, seq: Seq, rules) -> Seq:
        for i, node in enumerate(seq.nodes):
            seq.nodes[i] = node.visit(self, rules)
        return seq

    def visit_alt(self, alt: Alt, rules) -> Alt:
        for i, node in enumerate(alt.nodes):
            alt.nodes[i] = node.visit(self, rules)
        return alt

    def visit_mult(self, mult: Mult, rules) -> Mult:
        mult.node = mult.node.visit(self, rules)
        return mult

    def visit_opt(self, opt: Opt, rules) -> Opt:
        opt.node = opt.node.visit(self, rules)
        return opt

    def visit_look(self, look: Look, rules) -> Look:
        look.node = look.node.visit(self, rules)
        return look

    def visit_nlook(self, nlook: NLook, rules) -> NLook:
        nlook.node = nlook.node.visit(self, rules)
        return nlook

    def visit_str(self, string: Str, rules) -> Str:
        return string

    def visit_rgx(self, regex: Rgx, rules) -> Rgx:
        return regex
