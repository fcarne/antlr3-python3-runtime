import unittest

import testbase

import antlr3


class t031emptyAlt(testbase.ANTLRTest):
    def setUp(self):
        self.compileGrammar()

    def testValid1(self):
        cStream = antlr3.StringStream("foo")
        lexer = self.getLexer(cStream)
        tStream = antlr3.CommonTokenStream(lexer)
        parser = self.getParser(tStream)
        events = parser.r()


if __name__ == "__main__":
    unittest.main()
