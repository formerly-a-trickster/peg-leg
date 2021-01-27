from unittest import TestCase

from peg_leg.ast import Rule, Str, Alt, Rgx, Seq
from peg_leg.parser import Parser


class ParserTestCase(TestCase):
    def test_direct_left_recursive_rules(self):
        """
        expr <- expr "+" num ;
        num  <- /[0-9/ ;
        """
        rules = [
            Rule('expr', Alt(Seq(Rule('expr'),
                                 Str('+'),
                                 Rule('num')),
                             Rule('num'))),
            Rule('num', Rgx('[0-9]'))
        ]

        parser = Parser()
        parser.rules = {rule.name: rule for rule in rules}
        parser.grammar = parser.rules['expr']
        parser.link_rules()

        res = parser.parse("1+2+3")
        expected = [['1', '+', '2'], '+', '3']
        self.assertListEqual(res, expected)

    def test_indirect_left_recursive_rules(self):
        """
        x    <- expr ;
        expr <- x "+" num | num ;
        num  <- /[0-9]/ ;
        """

        x = Rule('x', Rule('expr'))
        expr = Rule('expr', Alt(Seq(Rule('x'),
                                    Str('+'),
                                    Rule('num')),
                                Rule('num')))
        num = Rule('num', Rgx('[0-9]'))

        parser = Parser()
        parser.rules = {'x': x,
                        'expr': expr,
                        'num': num}
        parser.grammar = x
        parser.link_rules()

        res = parser.parse("1+2+3")
        expected = [['1', '+', '2'], '+', '3']
        self.assertListEqual(res, expected)

    def test_multiple_mutually_recursive_rules(self):
        """
        lr1 <- lr2 '1' | '1' ;
        lr2 <- lr3 '2' | '2' ;
        lr3 <- lr1 '3' | '3' ;
        """

        lr1 = Rule('lr1', Alt(Seq(Rule('lr2'),
                                  Str('1')),
                              Str('1')))
        lr2 = Rule('lr2', Alt(Seq(Rule('lr3'),
                                  Str('2')),
                              Str('2')))
        lr3 = Rule('lr3', Alt(Seq(Rule('lr1'),
                                  Str('3')),
                              Str('3')))
        parser = Parser()
        parser.rules = {'lr1': lr1,
                        'lr2': lr2,
                        'lr3': lr3}
        parser.grammar = lr1
        parser.link_rules()

        res = parser.parse('321321321')
        expected = [[[[[[[['3', '2'], '1'], '3'], '2'], '1'], '3'], '2'], '1']
        self.assertListEqual(res, expected)

        res = parser.parse('321321')
        expected = [[[[['3', '2'], '1'], '3'], '2'], '1']
        self.assertListEqual(res, expected)

        res = parser.parse('321')
        expected = [['3', '2'], '1']
        self.assertListEqual(res, expected)

    def test_interleaved_recursion(self):
        """
        primary <- field-access | array-access | id ;
        field-access <- primary "." id ;
        array-access <- primary "[" id "]" ;
        id <- /[a-z]+/ ;
        """

        rules = [
            Rule("primary",
                 Alt(Rule("field-access"),
                     Rule("array-access"),
                     Rule("id"))),
            Rule("field-access",
                 Seq(Rule("primary"),
                     Str("."),
                     Rule("id"))),
            Rule("array-access",
                 Seq(Rule("primary"),
                     Str("["),
                     Rule("id"),
                     Str("]"))),
            Rule("id", Rgx("[a-z]+"))
        ]
        parser = Parser()
        parser.rules = {rule.name: rule for rule in rules}
        parser.grammar = parser.rules['primary']
        parser.link_rules()

        res = parser.parse("a")
        self.assertEqual(res, 'a')

        res = parser.parse("a.b")
        expected = ['a', '.', 'b']
        self.assertListEqual(res, expected)

        res = parser.parse("a[b]")
        expected = ['a', '[', 'b', ']']
        self.assertListEqual(res, expected)

        res = parser.parse("a.b.c")
        expected = [['a', '.', 'b'], '.', 'c']
        self.assertListEqual(res, expected)

        res = parser.parse("a[b][c]")
        expected = [['a', '[', 'b', ']'], '[', 'c', ']']
        self.assertListEqual(res, expected)

        res = parser.parse("a.b[c]")
        expected = [['a', '.', 'b'], '[', 'c', ']']
        self.assertListEqual(res, expected)

        res = parser.parse("a[b].c[d][e].f")
        expected = [[[[['a', '[', 'b', ']'],
                       '.', 'c'
                       ],
                      '[', 'd', ']'
                      ],
                     '[', 'e', ']'
                     ],
                    '.', 'f'
                    ]
        self.assertListEqual(res, expected)
