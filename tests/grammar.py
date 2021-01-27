from unittest import TestCase

from peg_leg.parser import Parser


class GrammarTestCase(TestCase):
    def test_java_primary(self):
        grammar = """
        primary <- primary-no-new-array ;
        primary-no-new-array <- object-creation
                              | method-invocation
                              | field-access
                              | array-access
                              | "this" ;
        object-creation <- primary ".new " id "()"
                         | "new " class-or-interface-type "()" ;
        method-invocation <- primary "." method-name "()"
                           | method-name "()" ;
        field-access <- primary "." id
                      | "super." id ;
        array-access <- primary "[" expression "]"
                      | id "[" expression "]" ;
        class-or-interface-type <- class-name
                                 | interface-type-name ;
        class-name <- "C" | "D" ;
        interface-type-name <- "I" | "J" ;
        id <- "x" | "y" | class-or-interface-type ;
        method-name <- "m" | "n" ;
        expression <- "i" | "j" ;
        """

        parser = Parser.from_grammar(grammar)

        res = parser.parse("this")
        self.assertEqual(res, "this")

        res = parser.parse("this.x")
        expect = ['this', '.', 'x']
        self.assertListEqual(res, expect)

        res = parser.parse("this.x.y")
        expect = [['this', '.', 'x'], '.', 'y']
        self.assertListEqual(res, expect)

        res = parser.parse("this.x.m()")
        expect = [['this', '.', 'x'], '.', 'm', '()']
        self.assertListEqual(res, expect)

        res = parser.parse("x[i][j].y")
        expect = [[['x', '[', 'i', ']'], '[', 'j', ']'], '.', 'y']
        self.assertListEqual(res, expect)

        res = parser.parse("new C()")
        expect = ['new ', 'C', '()']
        self.assertListEqual(res, expect)

        res = parser.parse("x[i].n()")
        expect = [['x', '[', 'i', ']'], '.', 'n', '()']
        self.assertListEqual(res, expect)

        res = parser.parse("new C().new D()")
        expect = [['new ', 'C', '()'], '.new ', 'D', '()']
        self.assertListEqual(res, expect)