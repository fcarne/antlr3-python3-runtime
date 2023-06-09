import unittest

import testbase

import antlr3


class t013parser(testbase.ANTLRTest):
    def setUp(self):
        self.compileGrammar()

    def testValid(self):
        cStream = antlr3.StringStream("foobar")
        lexer = self.getLexer(cStream)
        tStream = antlr3.CommonTokenStream(lexer)
        parser = self.getParser(tStream)
        parser.document()

        self.assertEqual(parser.events, ["before", "after"])


if __name__ == "__main__":
    unittest.main()
