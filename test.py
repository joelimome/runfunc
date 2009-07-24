#!/usr/bin/env python
#
# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of the run package released under the BSD license.
#
import optparse as op
import os
import sys
import unittest
from StringIO import StringIO

import runfunc as rf


class ProgNameTest(unittest.TestCase):
    def setUp(self):
        self.oldargv = sys.argv
    def tearDown(self):
        sys.argv = self.oldargv

    def test_success(self):
        self.assertEqual(rf.progname(), os.path.basename(sys.argv[0]))
        sys.argv = ['foo/bar']
        self.assertEqual(rf.progname(), "bar")
    
    def test_fail(self):
        sys.argv = []
        self.assertRaises(RuntimeError, rf.progname)

class StreamDup(object):
    def __init__(self, stream):
        self.stream = stream
        self.dupped = StringIO()
        self.silent = True
    def __getattr__(self, name):
        if callable(getattr(self.stream, name)):
            def dup(*args, **kwargs):
                if not self.silent:
                    getattr(self.stream, name)(*args, **kwargs)
                getattr(self.dupped, name)(*args, **kwargs)
            return dup
        return getattr(self.stream, name)
    def silence(self):
        self.silent = True
    def unsilence(self):
        self.silent = False
    def getvalue(self):
        return self.dupped.getvalue()

class BaseTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(BaseTest, self).__init__(*args, **kwargs)
        self.stdout, self.stderr = sys.stdout, sys.stderr
    
    def setUp(self):
        sys.stdout = StreamDup(sys.stdout)
        sys.stderr = StreamDup(sys.stderr)
    
    def tearDown(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr
        
class ArgTest(BaseTest):
    def setUp(self):
        super(ArgTest, self).setUp()
        self.parser = op.OptionParser()
        arg = self.arg()
        arg.name = 'foo'
        self.parser.add_option(arg.as_opt(None))


class NoImplArg(ArgTest):
    def arg(self):
        return rf.Arg("foo")
    
    def test_needs_implementation(self):
        self.assertRaises(SystemExit, self.parser.parse_args, ['--foo', ''])

class CheckTest(ArgTest):
    def arg(self):
        return rf.Check(int, "This is foo.")

    def test_no_validation(self):
        opts, args = self.parser.parse_args([])
        self.assertEqual(args, [])
        self.assertEqual(opts.foo, None)

    def test_validates(self):
        opts, args = self.parser.parse_args(['--foo', '2'])
        self.assertEqual(args, [])
        self.assertEqual(opts.foo, 2)
    
    def test_validation_error(self):
        self.assertRaises(SystemExit, self.parser.parse_args, ['--foo', 'bar'])

class HidesUnexpectedError(ArgTest):
    def arg(self):
        class BadArg(rf.Arg):
            def validate(self, option, optstr, value, parser):
                raise ValueError()
        return BadArg("stuff")

    def test_hides_error(self):
        self.assertRaises(SystemExit, self.parser.parse_args, ['--foo', '2'])
    
class FlagTest(ArgTest):
    def arg(self):
        return rf.Flag("Another step.", opt='f')
    
    def test_validate_long(self):
        opts, args = self.parser.parse_args(['--foo', '2'])
        self.assertEqual(args, ['2'])
        self.assertEqual(opts.foo, True)

    def test_validate_short(self):
        opts, args = self.parser.parse_args(['-f', '2'])
        self.assertEqual(args, ['2'])
        self.assertEqual(opts.foo, True)

class ListTest(ArgTest):
    def arg(self):
        return rf.List("Some stuff", opt='f')
    
    def test_validates_once(self):
        opts, args = self.parser.parse_args(['-f', '1'])
        self.assertEqual(args, [])
        self.assertEqual(opts.foo, ['1'])

    def test_revalidates(self):
        opts, args = self.parser.parse_args(['-f', '1', '-f', '2'])
        self.assertEqual(args, [])
        self.assertEqual(opts.foo, ['1', '2'])

class ListValidateTest(ArgTest):
    def arg(self):
        return rf.List("Some stuff", opt='f', validator=int)
    
    def test_validate_add(self):
        opts, args = self.parser.parse_args(['-f', '1'])
        self.assertEqual(args, [])
        self.assertEqual(opts.foo, [1])
    
    def test_revalidates_add(self):
        opts, args = self.parser.parse_args(['-f', '1', '-f', '2'])
        self.assertEqual(args, [])
        self.assertEqual(opts.foo, [1, 2])
    
    def test_validation_error(self):
        self.assertRaises(SystemExit, self.parser.parse_args, ['-f', 'bar'])

class ChoiceTest(ArgTest):
    def arg(self):
        return rf.Choice(["bar"], "yay")
    
    def test_validate(self):
        sys.stderr.unsilence()
        opts, args = self.parser.parse_args(['--foo', 'bar'])
        self.assertEqual(args, [])
        self.assertEqual(opts.foo, 'bar')
    
    def test_validation_error(self):
        self.assertRaises(SystemExit, self.parser.parse_args, ['--foo', 'baz'])
    
class ChoiceValidationTest(ArgTest):
    def arg(self):
        return rf.Choice([1, 2, 3], "stuff", validator=int, opt='f')
    
    def test_validate(self):
        opts, args = self.parser.parse_args(['-f', '1'])
        self.assertEqual(args, [])
        self.assertEqual(opts.foo, 1)
    
    def test_validation_error(self):
        self.assertRaises(SystemExit, self.parser.parse_args, ['-f', '5'])
    
    def test_validator_error(self):
        self.assertRaises(SystemExit, self.parser.parse_args, ['-f', 'bar'])

class RegexpTest(ArgTest):
    def arg(self):
        return rf.Regexp('\w{3}', "TLA!", opt='r')
    
    def test_validate(self):
        opts, args = self.parser.parse_args(['-r', 'TLA'])
        self.assertEqual(args, [])
        self.assertEqual(opts.foo, 'TLA')
    
    def test_validation_error(self):
        self.assertRaises(SystemExit, self.parser.parse_args, ['-r', '#'])
    
class EmailTest(ArgTest):
    def arg(self):
        return rf.Email("yep.")
    
    def test_validate(self):
        cases = [
            "person@foo.com",
            "some.one@people.org",
            "an-example_of@this.is.where.we.go.uk"
        ]
        for cs in cases:
            opts, args = self.parser.parse_args(['--foo', cs])
            self.assertEqual(args, [])
            self.assertEqual(opts.foo, cs)

    def test_validation_error(self):
        cases = [
            "@company.com",
            "me@my.homestead",
            "invalid",
            "$their@gone.com"
        ]
        for cs in cases:
            self.assertRaises(SystemExit, self.parser.parse_args, ['--foo', cs])

class IpAddrTest(ArgTest):
    def arg(self):
        return rf.IpAddr("uhuh")
    
    def test_validate(self):
        cases = [
            '127.0.0.1',
            '243.109.3.1',
            '1.201.30.254'
        ]
        for cs in cases:
            opts, args = self.parser.parse_args(['--foo', cs])
            self.assertEqual(args, [])
            self.assertEqual(opts.foo, cs)
        
    def test_vaidation_error(self):
        cases = [
            'not.an.ip.address',
            '127.0.0.256'
            'stuff'
        ]
        for cs in cases:
            self.assertRaises(SystemExit, self.parser.parse_args, ['--foo', cs])

class PathTest(ArgTest):
    def arg(self):
        self.arg = rf.Path(0, "path stuff", opt='f')
        return self.arg
    
    def test_validate(self):
        cases = [
            (rf.FILE, __file__),
            (rf.DIR, os.path.dirname(__file__) + "/"),
            (rf.EXISTS, __file__),
            (rf.PARENT, __file__),
            (rf.FILE | rf.EXISTS, __file__),
            (rf.DIR | rf.PARENT, os.path.dirname(__file__) + "/")
        ]
        for cs in cases:
            self.arg.flags = cs[0]
            opts, args = self.parser.parse_args(['-f', cs[1]])
            self.assertEqual(args, [])
            self.assertEqual(opts.foo, cs[1])

    def test_validation_error(self):
        cases = [
            (rf.FILE, os.path.dirname(__file__) + "/"),
            (rf.DIR, __file__),
            (rf.EXISTS, os.path.join(__file__, "bar")),
            (rf.PARENT, os.path.join(__file__, "baz", "bar")),
        ]
        for cs in cases:
            self.arg.flags = cs[0]
            self.assertRaises(SystemExit, self.parser.parse_args, ['-f', cs[1]])
        
class StreamTest(ArgTest):
    def arg(self):
        self.path = os.path.join(os.path.dirname(__file__), "foo.txt")
        self.arg = rf.Stream("r", "stream", opt='f')
        return self.arg
    
    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)
        super(StreamTest, self).tearDown()
    
    def test_validate(self):
        cases = ["w", "a", "r+", "r"]
        for cs in cases:
            self.arg.mode = cs
            opts, args = self.parser.parse_args(['-f', self.path])
            self.assertEqual(args, [])
            self.assertEqual(opts.foo.__class__, file)

    def test_validation_error(self):
        self.arg.mode = "r"
        self.assertRaises(SystemExit, self.parser.parse_args, ['-r', self.path])

class HelpTest(unittest.TestCase):
    def test_basic(self):
        class Help(rf.Help):
            foo = rf.Check(int, "This is an option.")
        h = Help()
        self.assertEqual(hasattr(h, "_args"), True)
        self.assertEqual("foo" in h, True)
        self.assertEqual(h["foo"].name, "foo")
        self.assertEqual(h["foo"].desc, "This is an option.")

class HelpInherit(BaseTest):
    def test_basic(self):
        class BaseHelp(rf.Help):
            foo = rf.Check(int, "Option 1")
        class Help(BaseHelp):
            foo = rf.Flag("Second option 1")
            bar = rf.Regexp('two', "Another")
        h = Help()
        self.assertEqual(hasattr(h, "_args"), True)
        for name in ["foo", "bar"]:
            self.assertEqual(name in h, True)
            self.assertEqual(h[name].name, name)
        self.assertEqual(h["foo"].desc, "Second option 1")
        self.assertEqual(h["bar"].desc, "Another")

class ParserBasicTests(BaseTest):
    def setUp(self):
        super(ParserBasicTests, self).setUp()
        class Help(rf.Help):
            "Stuff"
            foo = rf.Check(int, "Foo option")
        self.help = Help

    def test_no_help(self):
        def func(bar):
            pass
        self.assertRaises(RuntimeError, rf.Parser, func, self.help())
    
    def test_options(self):
        def func(foo=4):
            pass
        parser = rf.Parser(func, self.help())
        self.assertEqual(parser.description, "Stuff")
        self.assertEqual(len(parser.option_list), 2)
        self.assertEqual(str(parser.option_list[0]), "-h/--help")
        self.assertEqual(str(parser.option_list[1]), "--foo")
        self.assertEqual(parser.option_list[1].default, 4)
        self.assertEqual(parser.parse(['--foo', '2']), {'foo': 2})

    def test_required(self):
        def func(foo):
            pass
        parser = rf.Parser(func, self.help())
        self.assertEqual(len(parser.option_list), 1)
        self.assertEqual(str(parser.option_list[0]), "-h/--help")
        self.assertEqual("foo" in parser.required, True)
        self.assertEqual(parser.parse(['3']), {"foo": 3})

    def test_parse(self):
        def func(foo=None):
            pass
        parser = rf.Parser(func, self.help())
        cases = [
            ([], {"foo": None}),
            (['--foo', '2'], {'foo': 2}),
            (['--foo', '3', '--foo', '5'], {'foo': 5})
        ]
        for cs in cases:
            self.assertEqual(parser.parse(cs[0]), cs[1])

    def test_missing(self):
        def func(foo):
            pass
        parser = rf.Parser(func, self.help())
        self.assertRaises(SystemExit, parser.parse, [])
    
    def test_extra(self):
        def func(foo):
            pass
        parser = rf.Parser(func, self.help())
        self.assertRaises(SystemExit, parser.parse, ['2', '3'])

    def test_wrap_exception(self):
        def throw(bar):
            raise TypeError(bar)
        class Help(rf.Help):
            bar = rf.Check(throw, "bang!")
        parser = rf.Parser(throw, Help())
        self.assertRaises(SystemExit, parser.parse, ["foo"])

class RunTest(BaseTest):
    def setUp(self):
        super(RunTest, self).setUp()
        class Help(rf.Help):
            "Stuff"
            foo = rf.Check(int, "Foo option")
            bar = rf.Flag("Stuff", opt='b')
        self.help = Help

    def test_basic(self):
        def func(bar=False):
            return bar
        cases = [([], False), (['-b'], True)]
        for cs in cases:
            ret = rf.run(func, self.help(), argv=cs[0], check=False)
            self.assertEqual(ret, cs[1])

    def test_lambda(self):
        func = lambda foo, bar=False: (foo, bar)
        cases = [
            (['2'], (2, False)),
            (['-b', '3'], (3, True)),
            (['4', '--bar'], (4, True))
        ]
        for cs in cases:
            ret = rf.run(func, self.help(), argv=cs[0], check=False)
            self.assertEqual(ret, cs[1])

    def test_class(self):
        class Func(object):
            def __init__(self, foo, bar=None):
                self.data = (foo, bar)
        cases = [
            (['2'], (2, None)),
            (['-b', '3'], (3, True)),
            (['4', '--bar'], (4, True))
        ]
        for cs in cases:
            ret = rf.run(Func, self.help(), argv=cs[0], check=False)
            self.assertEqual(ret.data, cs[1])

    def test_old_class(self):
        class Func:
            pass
        self.assertRaises(TypeError, rf.run, Func, self.help(), check=False)

    def test_callable_object(self):
        class Func(object):
            def __call__(self, foo, bar=None):
                return (foo, bar)
        cases = [
            (['2'], (2, None)),
            (['-b', '3'], (3, True)),
            (['4', '--bar'], (4, True))
        ]
        for cs in cases:
            ret = rf.run(Func(), self.help(), argv=cs[0], check=False)
            self.assertEqual(ret, cs[1])

    def test_not_callable(self):
        class Func(object):
            pass
        self.assertRaises(TypeError, rf.run, Func(), self.help(), check=False)

    def test_bad_argv(self):
        def func(foo):
            pass
        self.assertRaises(
            TypeError, rf.run, func, self.help(), argv=1, check=False
        )

class IsMainTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(rf.is_main(), False)

    def test_no_run(self):
        class Help(rf.Help):
            pass
        def func():
            return 10
        self.assertEqual(rf.run(func, Help()), None)

class FormatterTest(BaseTest):
    def setUp(self):
        super(FormatterTest, self).setUp()
        class Help(rf.Help):
            """\
            Indent
                Stuff
            """
            foo = rf.Check(int, "Stuff", opt='f')
            bar = rf.Regexp('\w{3}', "Hi")
        self.help = Help

    def test_description(self):
        def func(foo, bar):
            pass
        parser = rf.Parser(func, self.help())
        desc = parser.formatter.format_description(parser.description)
        self.assertEqual(desc, "Indent\n    Stuff\n")
    
    def test_no_desc(self):
        class Help(rf.Help):
            pass
        def func():
            pass
        parser = rf.Parser(func, Help())
        parser.print_help()
        self.assertEqual(sys.stdout.getvalue().startswith("Options:"), True)
    
    def test_format_option(self):
        def func(foo):
            pass
        parser = rf.Parser(func, self.help())
        opt = parser.help['foo'].as_opt(None)
        ret = parser.formatter.format_option_strings(opt)
        self.assertEqual(ret, "-f/--foo FOO")
        
        
