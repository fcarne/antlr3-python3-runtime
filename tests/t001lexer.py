import unittest

import testbase

import antlr3


class t001lexer(testbase.ANTLRTest):
    def setUp(self):
        self.compileGrammar()

    def lexerClass(self, base):
        class TLexer(base):
            def emitErrorMessage(self, msg):
                # report errors to /dev/null
                pass

            def reportError(self, re):
                # no error recovery yet, just crash!
                raise re

        return TLexer

    def testValid(self):
        stream = antlr3.StringStream("0")
        lexer = self.getLexer(stream)

        token = lexer.nextToken()
        self.assertEqual(token.type, self.lexerModule.ZERO)

        token = lexer.nextToken()
        self.assertEqual(token.type, self.lexerModule.EOF)

    def testIteratorInterface(self):
        stream = antlr3.StringStream("0")
        lexer = self.getLexer(stream)

        types = [token.type for token in lexer]

        self.assertEqual(types, [self.lexerModule.ZERO])

    def testMalformedInput(self):
        stream = antlr3.StringStream("1")
        lexer = self.getLexer(stream)

        try:
            token = lexer.nextToken()
            self.fail()

        except antlr3.MismatchedTokenException as exc:
            self.assertEqual(exc.expecting, "0")
            self.assertEqual(exc.unexpectedType, "1")


if __name__ == "__main__":
    unittest.main()
