import errno
import hashlib
import imp
import inspect
import os
import re
import sys
import tempfile
import unittest
from distutils.errors import DistutilsFileError


def unlink(path):
    try:
        os.unlink(path)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise


class GrammarCompileError(Exception):
    """Grammar failed to compile."""


# At least on MacOSX tempdir (/tmp) is a symlink. It's sometimes dereferences,
# sometimes not, breaking the inspect.getmodule() function.
testbasedir = os.path.join(os.path.realpath(tempfile.gettempdir()), "antlr3-test")


class BrokenTest(unittest.TestCase.failureException):
    def __repr__(self):
        name, reason = self.args
        return "{}: {}: {} works now".format((self.__class__.__name__, name, reason))


def broken(reason, *exceptions):
    """Indicates a failing (or erroneous) test case fails that should succeed.
    If the test fails with an exception, list the exception type in args"""

    def wrapper(test_method):
        def replacement(*args, **kwargs):
            try:
                test_method(*args, **kwargs)
            except exceptions or unittest.TestCase.failureException:
                pass
            else:
                raise BrokenTest(test_method.__name__, reason)

        replacement.__doc__ = test_method.__doc__
        replacement.__name__ = "XXX_" + test_method.__name__
        replacement.todo = reason
        return replacement

    return wrapper


dependencyCache = {}
compileErrorCache = {}

# setup java CLASSPATH
if "CLASSPATH" not in os.environ:
    cp = []

    baseDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    libDir = os.path.join(baseDir, "lib")

    jar = os.path.join(libDir, "ST-4.0.5.jar")
    if not os.path.isfile(jar):
        raise DistutilsFileError(
            f"Missing file '{jar}'. Grab it from a distribution package."
        )
    cp.append(jar)

    jar = os.path.join(libDir, "antlr-3.4.1-SNAPSHOT.jar")
    if not os.path.isfile(jar):
        raise DistutilsFileError(
            f"Missing file '{jar}'. Grab it from a distribution package."
        )
    cp.append(jar)

    jar = os.path.join(libDir, "antlr-runtime-3.4.jar")
    if not os.path.isfile(jar):
        raise DistutilsFileError(
            f"Missing file '{jar}'. Grab it from a distribution package."
        )
    cp.append(jar)

    cp.append(os.path.join(baseDir, "runtime", "Python", "build"))

    classpath = '-cp "' + ":".join([os.path.abspath(p) for p in cp]) + '"'

else:
    classpath = ""


class ANTLRTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.moduleName = os.path.splitext(
            os.path.basename(sys.modules[self.__module__].__file__)
        )[0]
        self.className = self.__class__.__name__
        self._baseDir = None

        self.lexerModule = None
        self.parserModule = None

        self.grammarName = None
        self.grammarType = None

    @property
    def baseDir(self):
        if self._baseDir is None:
            testName = "unknownTest"
            for frame in inspect.stack():
                code = frame[0].f_code
                codeMod = inspect.getmodule(code)
                if codeMod is None:
                    continue

                # skip frames not in requested module
                if codeMod is not sys.modules[self.__module__]:
                    continue

                # skip some unwanted names
                if code.co_name in ("nextToken", "<module>"):
                    continue

                if code.co_name.startswith("test"):
                    testName = code.co_name
                    break

            self._baseDir = os.path.join(
                testbasedir, self.moduleName, self.className, testName
            )
            if not os.path.isdir(self._baseDir):
                os.makedirs(self._baseDir)

        return self._baseDir

    def _invokeantlr(self, dir, file, options, javaOptions=""):
        cmd = "cd {}; java {} {} org.antlr.Tool -o . {} {} 2>&1".format(
            dir, javaOptions, classpath, options, file
        )
        fp = os.popen(cmd)
        output = ""
        failed = False
        for line in fp:
            output += line

            if line.startswith("error("):
                failed = True

        rc = fp.close()
        if rc:
            failed = True

        if failed:
            raise GrammarCompileError(
                f"Failed to compile grammar '{file}':\n{cmd}\n\n{output}"
            )

    def compileGrammar(self, grammarName=None, options="", javaOptions=""):
        if grammarName is None:
            grammarName = self.moduleName + ".g"

        self._baseDir = os.path.join(testbasedir, self.moduleName)
        if not os.path.isdir(self._baseDir):
            os.makedirs(self._baseDir)

        if self.grammarName is None:
            self.grammarName = os.path.splitext(grammarName)[0]

        grammarPath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), grammarName
        )

        # get type and name from first grammar line
        with open(grammarPath) as fp:
            grammar = fp.read()
        m = re.match(
            r"\s*((lexer|parser|tree)\s+|)grammar\s+(\S+);", grammar, re.MULTILINE
        )
        self.assertIsNotNone(m, grammar)
        self.grammarType = m.group(2) or "combined"

        self.assertIn(self.grammarType, ("lexer", "parser", "tree", "combined"))

        # don't try to rebuild grammar, if it already failed
        if grammarName in compileErrorCache:
            return

        try:
            #     # get dependencies from antlr
            #     if grammarName in dependencyCache:
            #         dependencies = dependencyCache[grammarName]

            #     else:
            #         dependencies = []
            #         cmd = ('cd %s; java %s %s org.antlr.Tool -o . -depend %s 2>&1'
            #                % (self.baseDir, javaOptions, classpath, grammarPath))

            #         output = ""
            #         failed = False

            #         fp = os.popen(cmd)
            #         for line in fp:
            #             output += line

            #             if line.startswith('error('):
            #                 failed = True
            #             elif ':' in line:
            #                 a, b = line.strip().split(':', 1)
            #                 dependencies.append(
            #                     (os.path.join(self.baseDir, a.strip()),
            #                      [os.path.join(self.baseDir, b.strip())])
            #                     )

            #         rc = fp.close()
            #         if rc is not None:
            #             failed = True

            #         if failed:
            #             raise GrammarCompileError(
            #                 "antlr -depend failed with code {} on grammar '{}':\n\n{}\n{}".format(
            #                     rc, grammarName, cmd, output)
            #                 )

            #         # add dependencies to my .stg files
            #         templateDir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tool', 'src', 'main', 'resources', 'org', 'antlr', 'codegen', 'templates', 'Python'))
            #         templates = glob.glob(os.path.join(templateDir, '*.stg'))

            #         for dst, src in dependencies:
            #             src.extend(templates)

            #         dependencyCache[grammarName] = dependencies

            #     rebuild = False
            #     for dest, sources in dependencies:
            #         if not os.path.isfile(dest):
            #             rebuild = True
            #             break

            #         for source in sources:
            #             if os.path.getmtime(source) > os.path.getmtime(dest):
            #                 rebuild = True
            #                 break

            #     if rebuild:
            #         self._invokeantlr(self.baseDir, grammarPath, options, javaOptions)

            self._invokeantlr(self.baseDir, grammarPath, options, javaOptions)

        except:
            # mark grammar as broken
            compileErrorCache[grammarName] = True
            raise

    def lexerClass(self, base):
        """Optionally build a subclass of generated lexer class"""

        return base

    def parserClass(self, base):
        """Optionally build a subclass of generated parser class"""

        return base

    def walkerClass(self, base):
        """Optionally build a subclass of generated walker class"""

        return base

    def __load_module(self, name):
        modFile, modPathname, modDescription = imp.find_module(name, [self.baseDir])

        with modFile:
            return imp.load_module(name, modFile, modPathname, modDescription)

    def getLexer(self, *args, **kwargs):
        """Build lexer instance. Arguments are passed to lexer.__init__()."""

        if self.grammarType == "lexer":
            self.lexerModule = self.__load_module(self.grammarName)
            cls = getattr(self.lexerModule, self.grammarName)
        else:
            self.lexerModule = self.__load_module(self.grammarName + "Lexer")
            cls = getattr(self.lexerModule, self.grammarName + "Lexer")

        cls = self.lexerClass(cls)

        lexer = cls(*args, **kwargs)

        return lexer

    def getParser(self, *args, **kwargs):
        """Build parser instance. Arguments are passed to parser.__init__()."""

        if self.grammarType == "parser":
            self.lexerModule = self.__load_module(self.grammarName)
            cls = getattr(self.lexerModule, self.grammarName)
        else:
            self.parserModule = self.__load_module(self.grammarName + "Parser")
            cls = getattr(self.parserModule, self.grammarName + "Parser")
        cls = self.parserClass(cls)

        parser = cls(*args, **kwargs)

        return parser

    def getWalker(self, *args, **kwargs):
        """Build walker instance. Arguments are passed to walker.__init__()."""

        self.walkerModule = self.__load_module(self.grammarName + "Walker")
        cls = getattr(self.walkerModule, self.grammarName + "Walker")
        cls = self.walkerClass(cls)

        walker = cls(*args, **kwargs)

        return walker

    def writeInlineGrammar(self, grammar):
        # Create a unique ID for this test and use it as the grammar name,
        # to avoid class name reuse. This kinda sucks. Need to find a way so
        # tests can use the same grammar name without messing up the namespace.
        # Well, first I should figure out what the exact problem is...
        id = hashlib.md5(self.baseDir.encode("utf-8")).hexdigest()[-8:]
        grammar = grammar.replace("$TP", "TP" + id)
        grammar = grammar.replace("$T", "T" + id)

        # get type and name from first grammar line
        m = re.match(
            r"\s*((lexer|parser|tree)\s+|)grammar\s+(\S+);", grammar, re.MULTILINE
        )
        self.assertIsNotNone(m, grammar)
        grammarType = m.group(2) or "combined"
        grammarName = m.group(3)

        self.assertIn(grammarType, ("lexer", "parser", "tree", "combined"))

        grammarPath = os.path.join(self.baseDir, grammarName + ".g")

        # dump temp grammar file
        with open(grammarPath, "w") as fp:
            fp.write(grammar)

        return grammarName, grammarPath, grammarType

    def writeFile(self, name, contents):
        testDir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(self.baseDir, name)

        with open(path, "w") as fp:
            fp.write(contents)

        return path

    def compileInlineGrammar(
        self, grammar, options="", javaOptions="", returnModule=False
    ):
        # write grammar file
        grammarName, grammarPath, grammarType = self.writeInlineGrammar(grammar)

        # compile it
        self._invokeantlr(
            os.path.dirname(grammarPath),
            os.path.basename(grammarPath),
            options,
            javaOptions,
        )

        if grammarType == "combined":
            lexerMod = self.__load_module(grammarName + "Lexer")
            parserMod = self.__load_module(grammarName + "Parser")
            if returnModule:
                return lexerMod, parserMod

            lexerCls = getattr(lexerMod, grammarName + "Lexer")
            lexerCls = self.lexerClass(lexerCls)
            parserCls = getattr(parserMod, grammarName + "Parser")
            parserCls = self.parserClass(parserCls)

            return lexerCls, parserCls

        if grammarType == "lexer":
            lexerMod = self.__load_module(grammarName)
            if returnModule:
                return lexerMod

            lexerCls = getattr(lexerMod, grammarName)
            lexerCls = self.lexerClass(lexerCls)

            return lexerCls

        if grammarType == "parser":
            parserMod = self.__load_module(grammarName)
            if returnModule:
                return parserMod

            parserCls = getattr(parserMod, grammarName)
            parserCls = self.parserClass(parserCls)

            return parserCls

        if grammarType == "tree":
            walkerMod = self.__load_module(grammarName)
            if returnModule:
                return walkerMod

            walkerCls = getattr(walkerMod, grammarName)
            walkerCls = self.walkerClass(walkerCls)

            return walkerCls
