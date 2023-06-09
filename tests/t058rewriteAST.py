import textwrap
import unittest

import testbase

import antlr3
import antlr3.tree


class TestRewriteAST(testbase.ANTLRTest):
    def parserClass(self, base):
        class TParser(base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self._errors = []
                self._output = ""

            def capture(self, t):
                self._output += t

            def traceIn(self, ruleName, ruleIndex):
                self.traces.append(">" + ruleName)

            def traceOut(self, ruleName, ruleIndex):
                self.traces.append("<" + ruleName)

            def emitErrorMessage(self, msg):
                self._errors.append(msg)

        return TParser

    def lexerClass(self, base):
        class TLexer(base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self._output = ""

            def capture(self, t):
                self._output += t

            def traceIn(self, ruleName, ruleIndex):
                self.traces.append(">" + ruleName)

            def traceOut(self, ruleName, ruleIndex):
                self.traces.append("<" + ruleName)

            def recover(self, input, re):
                # no error recovery yet, just crash!
                raise

        return TLexer

    def execParser(self, grammar, grammarEntry, input, expectErrors=False):
        lexerCls, parserCls = self.compileInlineGrammar(grammar)

        cStream = antlr3.StringStream(input)
        lexer = lexerCls(cStream)
        tStream = antlr3.CommonTokenStream(lexer)
        parser = parserCls(tStream)
        r = getattr(parser, grammarEntry)()

        if not expectErrors:
            self.assertEqual(len(parser._errors), 0, parser._errors)

        result = ""

        if r:
            if hasattr(r, "result"):
                result += r.result

            if r.tree:
                result += r.tree.toStringTree()

        if not expectErrors:
            return result

        else:
            return result, parser._errors

    def execTreeParser(self, grammar, grammarEntry, treeGrammar, treeEntry, input):
        lexerCls, parserCls = self.compileInlineGrammar(grammar)
        walkerCls = self.compileInlineGrammar(treeGrammar)

        cStream = antlr3.StringStream(input)
        lexer = lexerCls(cStream)
        tStream = antlr3.CommonTokenStream(lexer)
        parser = parserCls(tStream)
        r = getattr(parser, grammarEntry)()
        nodes = antlr3.tree.CommonTreeNodeStream(r.tree)
        nodes.setTokenStream(tStream)
        walker = walkerCls(nodes)
        r = getattr(walker, treeEntry)()

        if r:
            return r.tree.toStringTree()

        return ""

    def testDelete(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID INT -> ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc 34")
        self.assertEqual("", found)

    def testSingleToken(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID -> ID;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc")
        self.assertEqual("abc", found)

    def testSingleTokenToNewNode(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID -> ID["x"];
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc")
        self.assertEqual("x", found)

    def testSingleTokenToNewNodeRoot(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID -> ^(ID["x"] INT);
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc")
        self.assertEqual("(x INT)", found)

    def testSingleTokenToNewNode2(self):
        # Allow creation of new nodes w/o args.
        grammar = textwrap.dedent(
            r"""
            grammar TT;
            options {language=Python3;output=AST;}
            a : ID -> ID[ ];
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc")
        self.assertEqual("ID", found)

    def testSingleCharLiteral(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : 'c' -> 'c';
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "c")
        self.assertEqual("c", found)

    def testSingleStringLiteral(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : 'ick' -> 'ick';
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "ick")
        self.assertEqual("ick", found)

    def testSingleRule(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : b -> b;
            b : ID ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc")
        self.assertEqual("abc", found)

    def testReorderTokens(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID INT -> INT ID;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc 34")
        self.assertEqual("34 abc", found)

    def testReorderTokenAndRule(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : b INT -> INT b;
            b : ID ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc 34")
        self.assertEqual("34 abc", found)

    def testTokenTree(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID INT -> ^(INT ID);
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc 34")
        self.assertEqual("(34 abc)", found)

    def testTokenTreeAfterOtherStuff(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : 'void' ID INT -> 'void' ^(INT ID);
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "void abc 34")
        self.assertEqual("void (34 abc)", found)

    def testNestedTokenTreeWithOuterLoop(self):
        # verify that ID and INT both iterate over outer index variable
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {DUH;}
            a : ID INT ID INT -> ^( DUH ID ^( DUH INT) )+ ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a 1 b 2")
        self.assertEqual("(DUH a (DUH 1)) (DUH b (DUH 2))", found)

    def testOptionalSingleToken(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID -> ID? ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc")
        self.assertEqual("abc", found)

    def testClosureSingleToken(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID ID -> ID* ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testPositiveClosureSingleToken(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID ID -> ID+ ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testOptionalSingleRule(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : b -> b?;
            b : ID ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc")
        self.assertEqual("abc", found)

    def testClosureSingleRule(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : b b -> b*;
            b : ID ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testClosureOfLabel(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : x+=b x+=b -> $x*;
            b : ID ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testOptionalLabelNoListLabel(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : (x=ID)? -> $x?;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a")
        self.assertEqual("a", found)

    def testPositiveClosureSingleRule(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : b b -> b+;
            b : ID ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testSinglePredicateT(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID -> {True}? ID -> ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc")
        self.assertEqual("abc", found)

    def testSinglePredicateF(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID -> {False}? ID -> ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc")
        self.assertEqual("", found)

    def testMultiplePredicate(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID INT -> {False}? ID
                       -> {True}? INT
                       ->
              ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a 2")
        self.assertEqual("2", found)

    def testMultiplePredicateTrees(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID INT -> {False}? ^(ID INT)
                       -> {True}? ^(INT ID)
                       -> ID
              ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a 2")
        self.assertEqual("(2 a)", found)

    def testSimpleTree(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : op INT -> ^(op INT);
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "-34")
        self.assertEqual("(- 34)", found)

    def testSimpleTree2(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : op INT -> ^(INT op);
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "+ 34")
        self.assertEqual("(34 +)", found)

    def testNestedTrees(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : 'var' (ID ':' type ';')+ -> ^('var' ^(':' ID type)+) ;
            type : 'int' | 'float' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "var a:int; b:float;")
        self.assertEqual("(var (: a int) (: b float))", found)

    def testImaginaryTokenCopy(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {VAR;}
            a : ID (',' ID)*-> ^(VAR ID)+ ;
            type : 'int' | 'float' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a,b,c")
        self.assertEqual("(VAR a) (VAR b) (VAR c)", found)

    def testTokenUnreferencedOnLeftButDefined(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {VAR;}
            a : b -> ID ;
            b : ID ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a")
        self.assertEqual("ID", found)

    def testImaginaryTokenCopySetText(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {VAR;}
            a : ID (',' ID)*-> ^(VAR["var"] ID)+ ;
            type : 'int' | 'float' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a,b,c")
        self.assertEqual("(var a) (var b) (var c)", found)

    def testImaginaryTokenNoCopyFromToken(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : lc='{' ID+ '}' -> ^(BLOCK[$lc] ID+) ;
            type : 'int' | 'float' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "{a b c}")
        self.assertEqual("({ a b c)", found)

    def testImaginaryTokenNoCopyFromTokenSetText(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : lc='{' ID+ '}' -> ^(BLOCK[$lc,"block"] ID+) ;
            type : 'int' | 'float' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "{a b c}")
        self.assertEqual("(block a b c)", found)

    def testMixedRewriteAndAutoAST(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : b b^ ; // 2nd b matches only an INT; can make it root
            b : ID INT -> INT ID
              | INT
              ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a 1 2")
        self.assertEqual("(2 1 a)", found)

    def testSubruleWithRewrite(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : b b ;
            b : (ID INT -> INT ID | INT INT -> INT+ )
              ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a 1 2 3")
        self.assertEqual("1 a 2 3", found)

    def testSubruleWithRewrite2(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {TYPE;}
            a : b b ;
            b : 'int'
                ( ID -> ^(TYPE 'int' ID)
                | ID '=' INT -> ^(TYPE 'int' ID INT)
                )
                ';'
              ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "int a; int b=3;")
        self.assertEqual("(TYPE int a) (TYPE int b 3)", found)

    def testNestedRewriteShutsOffAutoAST(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : b b ;
            b : ID ( ID (last=ID -> $last)+ ) ';' // get last ID
              | INT // should still get auto AST construction
              ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b c d; 42")
        self.assertEqual("d 42", found)

    def testRewriteActions(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : atom -> ^({self.adaptor.create(INT,"9")} atom) ;
            atom : INT ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "3")
        self.assertEqual("(9 3)", found)

    def testRewriteActions2(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : atom -> {self.adaptor.create(INT,"9")} atom ;
            atom : INT ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "3")
        self.assertEqual("9 3", found)

    def testRefToOldValue(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : (atom -> atom) (op='+' r=atom -> ^($op $a $r) )* ;
            atom : INT ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "3+4+5")
        self.assertEqual("(+ (+ 3 4) 5)", found)

    def testCopySemanticsForRules(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : atom -> ^(atom atom) ; // NOT CYCLE! (dup atom)
            atom : INT ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "3")
        self.assertEqual("(3 3)", found)

    def testCopySemanticsForRules2(self):
        # copy type as a root for each invocation of (...)+ in rewrite
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : type ID (',' ID)* ';' -> ^(type ID)+ ;
            type : 'int' ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "int a,b,c;")
        self.assertEqual("(int a) (int b) (int c)", found)

    def testCopySemanticsForRules3(self):
        # copy type *and* modifier even though it's optional
        # for each invocation of (...)+ in rewrite
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : modifier? type ID (',' ID)* ';' -> ^(type modifier? ID)+ ;
            type : 'int' ;
            modifier : 'public' ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "public int a,b,c;")
        self.assertEqual("(int public a) (int public b) (int public c)", found)

    def testCopySemanticsForRules3Double(self):
        # copy type *and* modifier even though it's optional
        # for each invocation of (...)+ in rewrite
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : modifier? type ID (',' ID)* ';' -> ^(type modifier? ID)+ ^(type modifier? ID)+ ;
            type : 'int' ;
            modifier : 'public' ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "public int a,b,c;")
        self.assertEqual(
            "(int public a) (int public b) (int public c) (int public a) (int public b) (int public c)",
            found,
        )

    def testCopySemanticsForRules4(self):
        # copy type *and* modifier even though it's optional
        # for each invocation of (...)+ in rewrite
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {MOD;}
            a : modifier? type ID (',' ID)* ';' -> ^(type ^(MOD modifier)? ID)+ ;
            type : 'int' ;
            modifier : 'public' ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "public int a,b,c;")
        self.assertEqual(
            "(int (MOD public) a) (int (MOD public) b) (int (MOD public) c)", found
        )

    def testCopySemanticsLists(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {MOD;}
            a : ID (',' ID)* ';' -> ID+ ID+ ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a,b,c;")
        self.assertEqual("a b c a b c", found)

    def testCopyRuleLabel(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x=b -> $x $x;
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a")
        self.assertEqual("a a", found)

    def testCopyRuleLabel2(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x=b -> ^($x $x);
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a")
        self.assertEqual("(a a)", found)

    def testQueueingOfTokens(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : 'int' ID (',' ID)* ';' -> ^('int' ID+) ;
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "int a,b,c;")
        self.assertEqual("(int a b c)", found)

    def testCopyOfTokens(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : 'int' ID ';' -> 'int' ID 'int' ID ;
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "int a;")
        self.assertEqual("int a int a", found)

    def testTokenCopyInLoop(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : 'int' ID (',' ID)* ';' -> ^('int' ID)+ ;
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "int a,b,c;")
        self.assertEqual("(int a) (int b) (int c)", found)

    def testTokenCopyInLoopAgainstTwoOthers(self):
        # must smear 'int' copies across as root of multiple trees
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : 'int' ID ':' INT (',' ID ':' INT)* ';' -> ^('int' ID INT)+ ;
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "int a:1,b:2,c:3;")
        self.assertEqual("(int a 1) (int b 2) (int c 3)", found)

    def testListRefdOneAtATime(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID+ -> ID ID ID ; // works if 3 input IDs
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b c")
        self.assertEqual("a b c", found)

    def testSplitListWithLabels(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {VAR;}
            a : first=ID others+=ID* -> $first VAR $others+ ;
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b c")
        self.assertEqual("a VAR b c", found)

    def testComplicatedMelange(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : A A b=B B b=B c+=C C c+=C D {s=$D.text} -> A+ B+ C+ D ;
            type : 'int' | 'float' ;
            A : 'a' ;
            B : 'b' ;
            C : 'c' ;
            D : 'd' ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a a b b b c c c d")
        self.assertEqual("a a b b b c c c d", found)

    def testRuleLabel(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x=b -> $x;
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a")
        self.assertEqual("a", found)

    def testAmbiguousRule(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID a -> a | INT ;
            ID : 'a'..'z'+ ;
            INT: '0'..'9'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc 34")
        self.assertEqual("34", found)

    def testRuleListLabel(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x+=b x+=b -> $x+;
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testRuleListLabel2(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x+=b x+=b -> $x $x*;
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testOptional(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x=b (y=b)? -> $x $y?;
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a")
        self.assertEqual("a", found)

    def testOptional2(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x=ID (y=b)? -> $x $y?;
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testOptional3(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x=ID (y=b)? -> ($x $y)?;
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testOptional4(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x+=ID (y=b)? -> ($x $y)?;
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("a b", found)

    def testOptional5(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : ID -> ID? ; // match an ID to optional ID
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a")
        self.assertEqual("a", found)

    def testArbitraryExprType(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : x+=b x+=b -> {CommonTree(None)};
            b : ID ;
            ID : 'a'..'z'+ ;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "a b")
        self.assertEqual("", found)

    def testSet(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a: (INT|ID)+ -> INT+ ID+ ;
            INT: '0'..'9'+;
            ID : 'a'..'z'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "2 a 34 de")
        self.assertEqual("2 34 a de", found)

    def testSet2(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a: (INT|ID) -> INT? ID? ;
            INT: '0'..'9'+;
            ID : 'a'..'z'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "2")
        self.assertEqual("2", found)

    @testbase.broken(
        "http://www.antlr.org:8888/browse/ANTLR-162",
        antlr3.tree.RewriteEmptyStreamException,
    )
    def testSetWithLabel(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : x=(INT|ID) -> $x ;
            INT: '0'..'9'+;
            ID : 'a'..'z'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "2")
        self.assertEqual("2", found)

    def testRewriteAction(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens { FLOAT; }
            r
                : INT -> {CommonTree(CommonToken(type=FLOAT, text=$INT.text+".0"))}
                ;
            INT : '0'..'9'+;
            WS: (' ' | '\n' | '\t')+ {$channel = HIDDEN};
            """
        )

        found = self.execParser(grammar, "r", "25")
        self.assertEqual("25.0", found)

    def testOptionalSubruleWithoutRealElements(self):
        # copy type *and* modifier even though it's optional
        # for each invocation of (...)+ in rewrite
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {PARMS;}

            modulo
             : 'modulo' ID ('(' parms+ ')')? -> ^('modulo' ID ^(PARMS parms+)?)
             ;
            parms : '#'|ID;
            ID : ('a'..'z' | 'A'..'Z')+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "modulo", "modulo abc (x y #)")
        self.assertEqual("(modulo abc (PARMS x y #))", found)

    ## C A R D I N A L I T Y  I S S U E S

    def testCardinality(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            tokens {BLOCK;}
            a : ID ID INT INT INT -> (ID INT)+;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        self.assertRaises(
            antlr3.tree.RewriteCardinalityException,
            self.execParser,
            grammar,
            "a",
            "a b 3 4 5",
        )

    def testCardinality2(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID+ -> ID ID ID ; // only 2 input IDs
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        self.assertRaises(
            antlr3.tree.RewriteCardinalityException,
            self.execParser,
            grammar,
            "a",
            "a b",
        )

    def testCardinality3(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID? INT -> ID INT ;
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        self.assertRaises(
            antlr3.tree.RewriteEmptyStreamException, self.execParser, grammar, "a", "3"
        )

    def testLoopCardinality(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID? INT -> ID+ INT ;
            op : '+'|'-' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        self.assertRaises(
            antlr3.tree.RewriteEarlyExitException, self.execParser, grammar, "a", "3"
        )

    def testWildcard(self):
        grammar = textwrap.dedent(
            r"""
            grammar T;
            options {language=Python3;output=AST;}
            a : ID c=. -> $c;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found = self.execParser(grammar, "a", "abc 34")
        self.assertEqual("34", found)

    # E R R O R S

    def testExtraTokenInSimpleDecl(self):
        grammar = textwrap.dedent(
            r"""
            grammar foo;
            options {language=Python3;output=AST;}
            tokens {EXPR;}
            decl : type ID '=' INT ';' -> ^(EXPR type ID INT) ;
            type : 'int' | 'float' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found, errors = self.execParser(
            grammar, "decl", "int 34 x=1;", expectErrors=True
        )
        self.assertEqual(["line 1:4 extraneous input '34' expecting ID"], errors)
        self.assertEqual("(EXPR int x 1)", found)  # tree gets correct x and 1 tokens

    # @testbase.broken("FIXME", AssertionError)
    def testMissingIDInSimpleDecl(self):
        grammar = textwrap.dedent(
            r"""
            grammar foo;
            options {language=Python3;output=AST;}
            tokens {EXPR;}
            decl : type ID '=' INT ';' -> ^(EXPR type ID INT) ;
            type : 'int' | 'float' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found, errors = self.execParser(grammar, "decl", "int =1;", expectErrors=True)
        self.assertEqual(["line 1:4 missing ID at '='"], errors)
        self.assertEqual(
            "(EXPR int <missing ID> 1)", found
        )  # tree gets invented ID token

    def testMissingSetInSimpleDecl(self):
        grammar = textwrap.dedent(
            r"""
            grammar foo;
            options {language=Python3;output=AST;}
            tokens {EXPR;}
            decl : type ID '=' INT ';' -> ^(EXPR type ID INT) ;
            type : 'int' | 'float' ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found, errors = self.execParser(grammar, "decl", "x=1;", expectErrors=True)
        self.assertEqual(["line 1:0 mismatched input 'x' expecting set None"], errors)
        self.assertEqual("(EXPR <error: x> x 1)", found)  # tree gets invented ID token

    def testMissingTokenGivesErrorNode(self):
        grammar = textwrap.dedent(
            r"""
            grammar foo;
            options {language=Python3;output=AST;}
            a : ID INT -> ID INT ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found, errors = self.execParser(grammar, "a", "abc", expectErrors=True)
        self.assertEqual(["line 1:3 missing INT at '<EOF>'"], errors)
        # doesn't do in-line recovery for sets (yet?)
        self.assertEqual("abc <missing INT>", found)

    def testExtraTokenGivesErrorNode(self):
        grammar = textwrap.dedent(
            r"""
            grammar foo;
            options {language=Python3;output=AST;}
            a : b c -> b c;
            b : ID -> ID ;
            c : INT -> INT ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found, errors = self.execParser(grammar, "a", "abc ick 34", expectErrors=True)
        self.assertEqual(["line 1:4 extraneous input 'ick' expecting INT"], errors)
        self.assertEqual("abc 34", found)

    # @testbase.broken("FIXME", AssertionError)
    def testMissingFirstTokenGivesErrorNode(self):
        grammar = textwrap.dedent(
            r"""
            grammar foo;
            options {language=Python3;output=AST;}
            a : ID INT -> ID INT ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found, errors = self.execParser(grammar, "a", "34", expectErrors=True)
        self.assertEqual(["line 1:0 missing ID at '34'"], errors)
        self.assertEqual("<missing ID> 34", found)

    # @testbase.broken("FIXME", AssertionError)
    def testMissingFirstTokenGivesErrorNode2(self):
        grammar = textwrap.dedent(
            r"""
            grammar foo;
            options {language=Python3;output=AST;}
            a : b c -> b c;
            b : ID -> ID ;
            c : INT -> INT ;
            ID : 'a'..'z'+ ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found, errors = self.execParser(grammar, "a", "34", expectErrors=True)
        # finds an error at the first token, 34, and re-syncs.
        # re-synchronizing does not consume a token because 34 follows
        # ref to rule b (start of c). It then matches 34 in c.
        self.assertEqual(["line 1:0 missing ID at '34'"], errors)
        self.assertEqual("<missing ID> 34", found)

    def testNoViableAltGivesErrorNode(self):
        grammar = textwrap.dedent(
            r"""
            grammar foo;
            options {language=Python3;output=AST;}
            a : b -> b | c -> c;
            b : ID -> ID ;
            c : INT -> INT ;
            ID : 'a'..'z'+ ;
            S : '*' ;
            INT : '0'..'9'+;
            WS : (' '|'\n') {$channel=HIDDEN} ;
            """
        )

        found, errors = self.execParser(grammar, "a", "*", expectErrors=True)
        # finds an error at the first token, 34, and re-syncs.
        # re-synchronizing does not consume a token because 34 follows
        # ref to rule b (start of c). It then matches 34 in c.
        self.assertEqual(["line 1:0 no viable alternative at input '*'"], errors)
        self.assertEqual("<unexpected: [@0,0:0='*',<S>,1:0], resync=*>", found)


if __name__ == "__main__":
    unittest.main()
