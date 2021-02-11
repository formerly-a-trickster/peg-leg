from peg_leg.ast import Rule, Seq, Str, Alt, Rgx, Opt, Mult, Look, NLook
from peg_leg.parser import Grammar, Parser

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
    # p = Parser(g, "a.b[c]")

    # g = Grammar(
    #     Rule("cat", Seq(Str("cat-"),
    #                     NLook(Str("a")),
    #                     Rule("animal"))),
    #     Rule("animal", Alt(Str("aadvark"),
    #                        Str("albatross"),
    #                        Str("alpaca"),
    #                        Str("dog")))
    # )
    # p = Parser(g, "cat-dog")

    # g = Grammar(
    #     Rule("eor",
    #          Seq(Rule("eand"),
    #              Mult(0, Seq(Str(" or "),
    #                          Rule("eand"))))),
    #     Rule("eand",
    #          Seq(Rule("bool"),
    #              Mult(0, Seq(Str(" and "),
    #                          Rule("bool"))))),
    #     Rule("bool",
    #          Alt(Str("true"),
    #              Str("false")))
    # )
    # p = Parser(g, "true")

    # g = Grammar(
    #     Rule('expr', Alt(Seq(Rule('expr'),
    #                          Str('+'),
    #                          Rule('num')),
    #                      Rule('num'))),
    #     Rule('num', Str('7'))
    # )
    # p = Parser(g, "7+7+7")

    # g = Grammar(
    #     Rule('pets',
    #          Seq(Str('cats'),
    #              Str(' and '),
    #              Str('dogs')))
    # )
    # p = Parser(g, "cats and dogs")

    # g = Grammar(
    #     Rule("dish",
    #          Seq(Rule("ingredient"),
    #              Str(" and "),
    #              Rule("ingredient"))),
    #     Rule("ingredient", Alt(Str("fish"),
    #                            Str("stick"),
    #                            Str("berry")))
    # )
    # p = Parser(g, "fish and berry")

    # g = Grammar(
    #     Rule("cats",
    #          Mult(0, Str("cat")))
    # )
    # p = Parser(g, "catcatcatcatcat")

    # g = Grammar(
    #     Rule("a",
    #          Seq(Str("a"),
    #              Rule("a-or-b"))),
    #     Rule("b",
    #          Seq(Str("b"),
    #              Rule("a-or-b"))),
    #     Rule("a-or-b",
    #          Alt(Rule("a"),
    #              Rule("b")))
    # )

    g = Grammar(
        Rule("cat",
             Seq(Opt(Seq(Str("c"),
                         Str("a"))),
                 Str("t")))
    )
    p = Parser(g, "t")

    print(p.parse())
    pass
