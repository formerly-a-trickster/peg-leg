from typing import Any, Tuple, List

from .ast import Rule, Seq, Alt, Mult, Opt, Look, NLook, Str, Rgx
from .parser import Parser

rules = [
    Rule("grammar",
         Seq(Mult(1,
                  Seq(Rule("_"),
                      Rule("rule"),
                      Rule("_"),
                      Str(";"))),
             Rule("_"))),
    Rule("rule",
         Seq(Rule("name"),
             Rule("_"),
             Str("<-"),
             Rule("_"),
             Rule("alts"))),
    Rule("name",
         Rgx(r"[\w_-]+")),
    Rule("alts",
         Seq(Rule("seq"),
             Mult(0,
                  Seq(Rule("_"),
                      Str("|"),
                      Rule("_"),
                      Rule("seq"))))),
    Rule("seq",
         Seq(Rule("atom"),
             Mult(0,
                  Seq(Rule("_"),
                      Rule("atom"))))),
    Rule("atom",
         Alt(Rule("prefixed"),
             Rule("suffixed"),
             Rule("group"),
             Rule("string"),
             Rule("regex"),
             Rule("id"))),
    Rule("prefixed",
         Seq(Alt(Str("&"),
                 Str("!")),
             Rule("_"),
             Rule("atom"))),
    Rule("suffixed",
         Seq(Rule("atom"),
             Rule("_"),
             Alt(Str("+"),
                 Str("*"),
                 Str("?")))),
    Rule("group",
         Seq(Str("("),
             Rule("_"),
             Rule("alts"),
             Rule("_"),
             Str(")"))),
    Rule("string",
         Seq(Str('"'),
             Mult(0,
                  Alt(Str('\\"'),
                      Rule('dblslash'),
                      Rgx(r'[^\\"]+'))),
             Str('"'))),
    Rule("dblslash",
         Str(r"\\")),
    Rule("regex",
         Seq(Str("/"),
             Rgx(r'(\\/|[^/])*'),
             Str("/"))),
    Rule("id",
         Rgx(r"[\w_-]+")),
    Rule("_",
         Rgx("\\s*"))
]


def grammar_action(raw):
    rules, _ = raw
    return [rule for _, rule, _, _ in rules]


def rule_action(raw) -> Rule:
    name, _, _, _, body = raw
    return Rule(name, body)


def alts_action(raw) -> Alt:
    first = raw[0]
    rest = [alt for _, _, _, alt in raw[1]]

    if rest:
        alts = [first] + rest
        return Alt(*alts)
    else:
        return first


def seq_action(raw) -> Seq:
    first = raw[0]
    rest = [seq for _, seq in raw[1]]

    if rest:
        seqs = [first] + rest
        return Seq(*seqs)
    else:
        return first


def prefixed_action(raw):
    symbol, _, node = raw
    if symbol == "&":
        return Look(node)
    elif symbol == "!":
        return NLook(node)
    else:
        raise AssertionError(f"Unexpected suffix `{symbol}`")


def suffixed_action(raw):
    node, _, symbol = raw
    if symbol == "+":
        return Mult(1, node)
    elif symbol == "*":
        return Mult(0, node)
    elif symbol == "?":
        return Opt(node)
    else:
        raise AssertionError(f"Unexpected suffix `{symbol}`")


def string_action(raw: Tuple[str, List[str], str]):
    string = ''.join(raw[1])
    return Str(string)


def dblslash_action(raw: str):
    return "\\"


def middle(raw: Tuple[str, Any, str]) -> Any:
    return raw[1]


peg_parser = Parser()
peg_parser.rules = {rule.name: rule for rule in rules}
peg_parser.actions = {"grammar": grammar_action,
                      "rule": rule_action,
                      "alts": alts_action,
                      "seq": seq_action,
                      "prefixed": prefixed_action,
                      "suffixed": suffixed_action,
                      "group": lambda x: x[2],
                      "string": string_action,
                      "dblslash": dblslash_action,
                      "regex": lambda x: Rgx(middle(x)),
                      "id": lambda x: Rule(x)}
peg_parser.grammar = peg_parser.rules['rule']
peg_parser.link_rules()
