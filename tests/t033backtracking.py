import unittest

import testbase

import antlr3


class t033backtracking(testbase.ANTLRTest):
    def setUp(self):
        self.compileGrammar()

    def parserClass(self, base):
        class TParser(base):
            def recover(self, input, re):
                # no error recovery yet, just crash!
                raise

        return TParser

    @testbase.broken("Some bug in the tool", SyntaxError)
    def testValid1(self):
        cStream = antlr3.StringStream("int a;")

        lexer = self.getLexer(cStream)
        tStream = antlr3.CommonTokenStream(lexer)
        parser = self.getParser(tStream)
        events = parser.translation_unit()


if __name__ == "__main__":
    unittest.main()
