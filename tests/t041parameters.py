import unittest

import testbase

import antlr3


class t041parameters(testbase.ANTLRTest):
    def setUp(self):
        self.compileGrammar()

    def lexerClass(self, base):
        class TLexer(base):
            def recover(self, input, re):
                # no error recovery yet, just crash!
                raise

        return TLexer

    def parserClass(self, base):
        class TParser(base):
            def recover(self, input, re):
                # no error recovery yet, just crash!
                raise

        return TParser

    def testValid1(self):
        cStream = antlr3.StringStream("a a a")

        lexer = self.getLexer(cStream)
        tStream = antlr3.CommonTokenStream(lexer)
        parser = self.getParser(tStream)
        r = parser.a("foo", "bar")

        self.assertEqual(r, ("foo", "bar"))


if __name__ == "__main__":
    unittest.main()
