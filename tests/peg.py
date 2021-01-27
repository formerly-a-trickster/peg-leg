from unittest import TestCase

from peg_leg.ast import Rule, Seq, Alt, Str, Rgx, Opt, Look, NLook, Mult
from peg_leg.peg import peg_parser


class PegTestCase(TestCase):
    def assertAstEqual(self, left, right):
        self.assertEqual(type(left), type(right))

        node_type = type(left)
        if node_type == Rule:
            self.assertEqual(left.name, right.name)
            self.assertAstEqual(left.node, right.node)
        elif node_type in {Seq, Alt}:
            self.assertEqual(len(left.nodes), len(right.nodes))
            for l, r in zip(left.nodes, right.nodes):
                self.assertAstEqual(l, r)
        elif node_type == Mult:
            self.assertEqual(left.min, right.min)
            self.assertAstEqual(left.node, right.node)
        elif node_type in {Opt, Look, NLook}:
            self.assertAstEqual(left.node, right.node)
        elif node_type == Str:
            self.assertEqual(left.string, right.string)
        elif node_type == Rgx:
            self.assertEqual(left.pattern, right.pattern)

    def test_one_item_sequences_are_not_wrapped(self):
        rule = 'test <- one'
        res = peg_parser.parse(rule)
        expect = Rule('test', Rule('one'))
        self.assertAstEqual(res, expect)

    def test_sequences_are_parsed(self):
        rule = 'test <- one two three'
        res = peg_parser.parse(rule)
        expect = Rule('test', Seq(Rule('one'),
                                  Rule('two'),
                                  Rule('three')))
        self.assertAstEqual(res, expect)

    def test_alternatives_are_parsed(self):
        rule = 'test <- one | two | three'
        res = peg_parser.parse(rule)
        expect = Rule('test', Alt(Rule('one'),
                                  Rule('two'),
                                  Rule('three')))
        self.assertAstEqual(res, expect)

    def test_sequence_binds_tighter_than_alternative(self):
        rule = 'test <- one two | three four'
        res = peg_parser.parse(rule)
        expect = Rule('test', Alt(
            Seq(Rule('one'), Rule('two')),
            Seq(Rule('three'), Rule('four'))
        ))
        self.assertAstEqual(res, expect)

    def test_multiples_are_parsed(self):
        rule = 'test <- one*'
        res = peg_parser.parse(rule)
        expect = Rule('test', Mult(0, Rule('one')))
        self.assertAstEqual(res, expect)

    def test_multiple_binds_tighter_than_seq_or_alt(self):
        rule = 'test <- one | two three*'
        res = peg_parser.parse(rule)
        expect = Rule('test', Alt(Rule('one'),
                                  Seq(Rule('two'),
                                      Mult(0, Rule('three')))))
        self.assertAstEqual(res, expect)

        rule = 'test <- one | two three+'
        res = peg_parser.parse(rule)
        expect = Rule('test', Alt(Rule('one'),
                                  Seq(Rule('two'),
                                      Mult(1, Rule('three')))))
        self.assertAstEqual(res, expect)

    def test_optional_is_parsed(self):
        rule = 'test <- one?'
        res = peg_parser.parse(rule)
        expect = Rule('test', Opt(Rule('one')))
        self.assertAstEqual(res, expect)

    def test_optional_binds_tighter_than_seq_or_alt(self):
        rule = 'test <- one | two three?'
        res = peg_parser.parse(rule)
        expect = Rule('test', Alt(Rule('one'),
                                  Seq(Rule('two'),
                                      Opt(Rule('three')))))
        self.assertAstEqual(res, expect)

    def test_group_contents_are_extracted(self):
        rule = 'test <- (one two)'
        res = peg_parser.parse(rule)
        expect = Rule('test', Seq(Rule('one'),
                                  Rule('two')))
        self.assertAstEqual(res, expect)

    def test_lookahead_is_parsed(self):
        rule = 'test <- &one'
        res = peg_parser.parse(rule)
        expect = Rule('test', Look(Rule('one')))
        self.assertAstEqual(res, expect)

    def test_lookahead_binds_tighter_than_seq_or_alt(self):
        rule = 'test <- &one | two three'
        res = peg_parser.parse(rule)
        expect = Rule('test', Alt(Look(Rule('one')),
                                  Seq(Rule('two'),
                                      Rule('three'))))
        self.assertAstEqual(res, expect)

    def test_negative_lookahead_is_parsed(self):
        rule = 'test <- !one'
        res = peg_parser.parse(rule)
        expect = Rule('test', NLook(Rule('one')))
        self.assertAstEqual(res, expect)

    def test_that_negative_lookahead_bings_tighter_than_seq_or_alt(self):
        rule = 'test <- !one | two three'
        res = peg_parser.parse(rule)
        expect = Rule('test', Alt(NLook(Rule('one')),
                                  Seq(Rule('two'), Rule('three'))))
        self.assertAstEqual(res, expect)

    def test_suffixes_bind_tighter_than_prefixes(self):
        rule = 'test <- &one*'
        res = peg_parser.parse(rule)
        expect = Rule('test', Look(Mult(0, Rule('one'))))
        self.assertAstEqual(res, expect)

    def test_string_is_parsed(self):
        rule = 'test <- "one"'
        res = peg_parser.parse(rule)
        expect = Rule('test', Str('one'))
        self.assertAstEqual(res, expect)

    def test_strings_with_spaces_are_parsed(self):
        rule = 'test <- "one "'
        res = peg_parser.parse(rule)
        expect = Rule('test', Str('one '))
        self.assertAstEqual(res, expect)

        rule = 'test <- " one"'
        res = peg_parser.parse(rule)
        expect = Rule('test', Str(' one'))
        self.assertAstEqual(res, expect)

        rule = 'test <- " one "'
        res = peg_parser.parse(rule)
        expect = Rule('test', Str(' one '))
        self.assertAstEqual(res, expect)

    def test_regex_is_parsed(self):
        rule = 'test <- /one/'
        res = peg_parser.parse(rule)
        expect = Rule('test', Rgx('one'))
        self.assertAstEqual(res, expect)
