#!/usr/bin/env python
import optparse as op
import os
import sys
import unittest
from StringIO import StringIO

os.putenv("OPTFUNC_RAISE", "TRUE")

import optfork


class StreamDup(object):
    def __init__(self, stream):
        self.stream = stream
        if isinstance(self.stream, StreamDup):
            self.stream = self.stream.stream
        self.dupped = StringIO()
        self.silent = False
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
    def setUp(self):
        sys.stdin = StreamDup(sys.stdin)
        sys.stdout = StreamDup(sys.stdout)
        sys.stderr = StreamDup(sys.stderr)

class OptforkProgNameTest(unittest.TestCase):
    def test_success(self):
        self.assertEqual(optfork.progname(), sys.argv[0])
    
    def test_fail(self):
        oldargv = sys.argv
        sys.argv = []
        self.assertEqual(optfork.progname(), 'unknown_program')
        sys.argv = oldargv

class OptforkParserTest(BaseTest):
    def test_required_args(self):
        "Required arguments are parsed correctly"

        def func(one, two, three):
            pass

        parser = optfork.OptforkParser(func)
        
        self.assertEqual(len(parser.option_list), 1)
        self.assertEqual(str(parser.option_list[0]), '-h/--help')
        self.assertEqual(parser.required, ["one", "two", "three"])
        
    def test_kwargs(self):
        "Keyword args are made into options"

        def func(one="foo", two=True):
            pass

        parser = optfork.OptforkParser(func)

        self.assertEqual(len(parser.option_list), 3)
        self.assertEqual(len(parser.required), 0)
        self.assertEqual(str(parser.option_list[0]), '-h/--help')
        
        self.assertEqual(str(parser.option_list[1]), '-o/--one')
        self.assertEqual(parser.option_list[1].default, 'foo')
        self.assertEqual(parser.option_list[1].action, 'callback')
        self.assertEqual(parser.option_list[1].callback, parser.validate)

        self.assertEqual(str(parser.option_list[2]), '-t/--two')
        self.assertEqual(parser.option_list[2].default, True)
        self.assertEqual(parser.option_list[2].action, 'store_true')

    def test_short_names(self):
        "Repeated short names are resolved"

        def check_parsed(expect, opts):
            for opt in opts:
                self.assertEqual(str(opt) in expect, True)
                expect.remove(str(opt))
            self.assertEqual(len(expect), 0)            
        
        def func1(one, version='', verbose=False):
            pass
        
        parser = optfork.OptforkParser(func1)
        expect = ['-h/--help', '-v/--version', '-e/--verbose']
        check_parsed(expect, parser.option_list)
            
        def func2(one, host=''):
            pass
        
        parser = optfork.OptforkParser(func2)
        expect = ['-h/--help', '-o/--host']
        check_parsed(expect, parser.option_list)

    def test_custom_short_name(self):
        "Custom short names"
        
        def func(b_far=3):
            pass
        
        parser = optfork.OptforkParser(func)
        
        self.assertEqual(len(parser.option_list), 2)
        self.assertEqual(str(parser.option_list[1]), '-b/--far')

    def test_optfork_replaces_underscores(self):
        "Replace underscores with hyphens"
        
        def func(something_here=2):
            pass
        
        parser = optfork.OptforkParser(func)
        self.assertEqual(len(parser.option_list), 2)
        self.assertEqual(str(parser.option_list[1]), '-s/--something-here')

    def test_optfork_parses_methods(self):
        "Object methods are handled correctly"
        
        class Foo(object):
            def method(self, foo, baz="bing!"):
                pass
        
        parser = optfork.OptforkParser(Foo().method)
        self.assertEqual(len(parser.option_list), 2)
        self.assertEqual(str(parser.option_list[1]), '-b/--baz')
        self.assertEqual(parser.required, ["foo"])

    def test_optfork_parses_lambda(self):
        "Lambdas are handled correctly"
        
        # Not at all sure on a use case, but OptforkParse handles
        # it with zero extra code.

        parser = optfork.OptforkParser(lambda x: x.doh())
        self.assertEqual(len(parser.option_list), 1)
        self.assertEqual(parser.required, ["x"])
    
    def test_optfork_parses_callable_objects(self):
        "Callable objects aren't directly kosher"
        
        class Foo(object):
            def __call__(self, args, data=4):
                pass
        
        # OptforkParser uses inspect.getargspec which doesn't do
        # magic to check for a __call__ method. Although, callable
        # objects *are* handled by the run methods.
        
        self.assertRaises(TypeError, optfork.OptforkParser, Foo())

    def test_option_decorator(self):
        "@option('foo', **kwargs) affects the Option instance"

        @optfork.option('foo', help='help about foo')
        def func(foo=False):
            pass

        parser = optfork.OptforkParser(func)
        self.assertEqual(parser.option_list[1].help, 'help about foo')

        @optfork.option('foo', type='int')
        def func(foo=2):
            return foo
        
        parser = optfork.OptforkParser(func)
        self.assertEqual(parser.option_list[1].type, 'int')

    def test_arg_validator(self):
        "@valid checks required arguments"
        
        @optfork.valid(int, 'foo', help="%(name)s must be an integer.")
        def func(foo):
            return foo
        
        parser = optfork.OptforkParser(func)
        self.assertEqual(parser.validators["foo"][0], int)
        self.assertEqual(optfork.run(func, ["1"]), 1)
        self.assertRaises(SystemExit, optfork.run, func, ["wheee"])
    
    def test_opt_validator(self):
        "@valid checks option arguments"

        @optfork.valid(int, 'foo', help="%(name)s must be an integer.")
        def func(foo=None):
            return foo
        
        parser = optfork.OptforkParser(func)
        self.assertEqual(parser.validators["foo"][0], int)
        self.assertEqual(optfork.run(func, []), None)
        self.assertEqual(optfork.run(func, ["-f", "10"]), 10)
        self.assertRaises(SystemExit, optfork.run, func, ["zippy"])

    def test_multi_validations(self):
        "@valid checks all named parameters."
        
        @optfork.valid(int, "foo", "bar")
        def func(foo, bar=None):
            return foo, bar

        valid = [
            (["-b", "4", "1"], (1, 4)),
            (["2"], (2, None))
        ]
        for pair in valid:
            self.assertEqual(optfork.run(func, pair[0]), pair[1])

        invalid = [
            ["-b", "c", "1"],
            ["z"],
            ["-b", "5", "t"],
            ["1", "-b", "foo"]
        ]
        for args in invalid:
            sys.stderr.silence()
            self.assertRaises(SystemExit, optfork.run, func, args)
            sys.stderr.unsilence()

class OptforkRunTest(BaseTest):
    def test_args(self):
        "Check running the basics"

        def func(a, b=2, d=False):
            if d: return int(b)*3 + int(a)
            return -1

        self.assertEqual(optfork.run(func, ["1", "-b", "3", "-d"]), 10)
        self.assertEqual(optfork.run(func, ["1"]), -1)
        self.assertEqual(optfork.run(func, ["1", "-d"]), 7)
    
    def test_missing_required(self):
        "Throws an error for missing arguments"

        def func(a, b):
            pass
        
        self.assertRaises(SystemExit, optfork.run, func, [])
        self.assertRaises(SystemExit, optfork.run, func, ['2'])
    
    def test_too_many_args(self):
        "Throws an error for too many arguments"
        
        def func(a):
            pass
        
        test = lambda: optfork.run(func, ['2', '3'])
        self.assertRaises(SystemExit, test)

    def test_custom_short_name(self):
        "Custom short names"

        def func(b_far=3):
            return b_far

        self.assertEqual(optfork.run(func, ['-b', 10]), 10)

    def test_notstrict(self):
        "@notstrict fills missing args with None"
        
        @optfork.notstrict
        def func(a, b):
            return [a, b]
        
        self.assertEqual(optfork.run(func, ['foo']), ['foo', None])

    def test_notstrict_too_many(self):
        "Even with @notstrict too many args is an error"
        
        @optfork.notstrict
        def func(a):
            pass
    
        test = lambda: optfork.run(func, ['foo', 'bar'])
        self.assertRaises(SystemExit, test)

class OptforkClassTest(BaseTest):
    def test_run_class(self):
        "Running a class executes it's init method."

        class InitClass:
            def __init__(self, one, option=''):
                self.vals = (one, option)

        test = lambda: optfork.run(InitClass, ['f', '-o', 'z'])
        self.assertEqual(test().vals, ('f', 'z'))

    def test_no_init_is_error(self):
        "No __init__ method on a class throws an error."
        
        # I can't figure out how this would be useful. Calling it an
        # an error until someone shows me different.

        class NoInitClass:
            pass
        
        self.assertRaises(TypeError, optfork.run, NoInitClass, [])

    def test_runs_callable_instance(self):
        "Instances of callable classes are ok."

        class CallableClass(object):
            def __init__(self):
                pass
            def __call__(self, arg, opt=2):
                return arg + str(opt)

        self.assertEqual(optfork.run(CallableClass(), ['f', '-o', '3']), 'f3')

    def test_ridiculous_error(self):
        "Ridiculous error to force checked condition"
        class HidesCallable(object):
            def __init__(self):
                self.found = 0
            def __call__(self):
                pass
            def __getattribute__(self, name):
                if name == '__call__' and self.found > 1:
                    raise AttributeError("I am hiding")
                self.found += 1
                return super(HidesCallable, self).__getattribute__(self, name)
        
        test = lambda: optfork.run(HidesCallable(), [])
        self.assertRaises(TypeError, test)

class OptforkCommandsTest(BaseTest):
    def test_basics(self):
        "Executes subcommands successfully"
    
        def one(arg):
            return "One " + str(arg)
        def two(arg, some='stuff'):
            return "Two " + str(arg) + ' ' + some
        def three(arg):
            return "Three " + str(arg)
            
        test = lambda x: optfork.run([one, two, three], x)
        self.assertEqual(test(['two', '2']), 'Two 2 stuff')
        self.assertEqual(test(['three', '5']), 'Three 5')
        
    def test_no_args(self):
        "No args prints the command list"
        
        def one(arg):
            pass
        def two(arg):
            pass

        self.assertEqual(sys.stderr.getvalue(), "")
        sys.stderr.silence()
        self.assertEqual(optfork.run([one, two], []), 0)
        sys.stderr.unsilence()
        self.assertNotEqual(sys.stderr.getvalue(), "")

    def test_invalid_command(self):
        "Invalid command is an error and prints help"
        
        def one(arg):
            pass
        def two(arg):
            pass
        
        self.assertEqual(sys.stderr.getvalue(), "")
        sys.stderr.silence() # Quiet output
        self.assertEqual(optfork.run([one, two], ['three']), -1)
        sys.stderr.unsilence()
        self.assertNotEqual(sys.stderr.getvalue(), "")
    
    def test_help_prints_help(self):
        "Default help command prints a command list"
        
        def one(arg):
            pass
        def two(arg):
            pass
        
        self.assertEqual(sys.stderr.getvalue(), "")
        sys.stderr.silence()
        self.assertEqual(optfork.run([one, two], ['help']), 0)
        sys.stderr.unsilence()
        self.assertNotEqual(sys.stderr.getvalue(), "")
    
    def test_cmd(self):
        "@desc describes a command in list output"
        
        @optfork.cmd("Captain commando!")
        def one(arg):
            pass
        
        self.assertEqual(sys.stderr.getvalue(), "")
        sys.stderr.silence()
        self.assertEqual(optfork.run([one], ['help']), 0)
        sys.stderr.unsilence()
        self.assertNotEqual(sys.stderr.getvalue(), "")
        self.assertEqual("commando!" in sys.stderr.getvalue(), True)
    
    def test_help_with_args(self):
        "Help with commands prints some help"
        
        def one(arg):
            "Some stuff"
            pass
        def two(arg):
            pass
        
        self.assertEqual(sys.stderr.getvalue(), "")
        sys.stderr.silence()
        self.assertEqual(optfork.run([one, two], ['help', 'one', 'three']), 0)
        sys.stderr.unsilence()
        self.assertNotEqual(sys.stderr.getvalue(), "")
    
    def test_help_as_command(self):
        "If a command is named 'help' it is run"
        
        def one(arg):
            pass
        def help(arg):
            return arg + ' bar'
        
        self.assertEqual(sys.stderr.getvalue(), "")
        sys.stderr.silence()
        self.assertEqual(optfork.run([one, help], ['help', 'foo']), 'foo bar')
        sys.stderr.unsilence()
        self.assertEqual(sys.stderr.getvalue(), "")

class OptforkPipesTest(BaseTest):
    def test_stdin(self):
        "stdin, stdout, stderr as argument names gets passed sys.* streams"
        
        def func(stdin, stdout, stderr):
            self.assertEqual(stdin, sys.stdin)
            self.assertEqual(stdout, sys.stdout)
            self.assertEqual(stderr, sys.stderr)
            return "awesome!"
        
        self.assertEqual(optfork.run(func, []), 'awesome!')

class OptforkMainTest(BaseTest):
    def test_run_func(self):
        "optfork.main runs passed function"

        def stuff():
            return -2

        self.assertEqual(optfork.main(stuff, []), -2)

    # I have no idea how to force the condition in optfork.main
    # into thinking it's a frame down from main.
    #
    # def test_as_runner(self):
    #     "optfork.main runs the function"
    # 
    #     def func():
    #         return 34
    # 
    #     self.assertEqual(optfork.main(func, []), 34)

if __name__ == '__main__':
    unittest.main()
