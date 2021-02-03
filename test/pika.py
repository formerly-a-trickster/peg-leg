from peg_leg.ast import Rule, Seq, Str, Alt, Rgx, Opt, Mult, Look, NLook
from peg_leg.pika import Grammar, PikaParser

if __name__ == "__main__":
    # g = Grammar(
    #     Rule("P",
    #          Mult(1, Rule("V"))),
    #     Rule("V",
    #          Alt(Rgx('[a-z]'),
    #              Seq(Str("("),
    #                  Rule("P"),
    #                  Str(")")))),
    # )
    # g = Grammar(
    #     Rule("primary",
    #          Alt(Rule("field-access"),
    #              Rule("array-access"),
    #              Rule("id"))),
    #     Rule("field-access",
    #          Seq(Rule("primary"),
    #              Str("."),
    #              Rule("id"))),
    #     Rule("array-access",
    #          Seq(Rule("primary"),
    #              Str("["),
    #              Rule("id"),
    #              Str("]"))),
    #     Rule("id", Rgx("[a-z]"))
    # )
    # g = Grammar(
    #     Rule("dish", Seq(Rule("ingredient"),
    #                      Mult(0,
    #                           Seq(Str(" and "),
    #                               Rule("ingredient"))))),
    #     Rule("ingredient", Alt(Str("fish"),
    #                            Str("stick"),
    #                            Str("berry")))
    # )
    # g = Grammar(
    #     Rule("cat", Seq(Str("cat-"),
    #                     NLook(Str("a")),
    #                     Rule("animal"))),
    #     Rule("animal", Alt(Str("aadvark"),
    #                        Str("albatross"),
    #                        Str("alpaca"),
    #                        Str("dog")))
    # )
    g = Grammar(
        Rule('expr', Alt(Seq(Rule('expr'),
                             Str('+'),
                             Rule('num')),
                         Rule('num'))),
        Rule('num', Mult(1, Rgx('[0-9]')))
    )
    p = PikaParser(g, "420+69+314")
    print(p.parse())
    pass
