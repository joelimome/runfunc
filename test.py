#!/usr/bin/env python
import sys
import unittest
import optfunc
from StringIO import StringIO

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

class OptfuncProgNameTest(unittest.TestCase):
    def test_success(self):
        self.assertEqual(optfunc.progname(), sys.argv[0])
    
    def test_fail(self):
        oldargv = sys.argv
        sys.argv = []
        self.assertEqual(optfunc.progname(), 'unknown_program')
        sys.argv = oldargv

class OptfuncParserTest(BaseTest):
    def test_required_args(self):
        "Required arguments are parsed correctly"

        def func(one, two, three):
            pass

        parser = optfunc.OptfuncParser(func)
        
        self.assertEqual(len(parser.option_list), 1)
        self.assertEqual(str(parser.option_list[0]), '-h/--help')
        self.assertEqual(parser.required, ["one", "two", "three"])
        
    def test_kwargs(self):
        "Keyword args are made into options"

        def func(one="foo", two=True):
            pass

        parser = optfunc.OptfuncParser(func)

        self.assertEqual(len(parser.option_list), 3)
        self.assertEqual(len(parser.required), 0)
        self.assertEqual(str(parser.option_list[0]), '-h/--help')
        
        self.assertEqual(str(parser.option_list[1]), '-o/--one')
        self.assertEqual(parser.option_list[1].default, 'foo')
        self.assertEqual(parser.option_list[1].action, 'store')

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
        
        parser = optfunc.OptfuncParser(func1)
        expect = ['-h/--help', '-v/--version', '-e/--verbose']
        check_parsed(expect, parser.option_list)
            
        def func2(one, host=''):
            pass
        
        parser = optfunc.OptfuncParser(func2)
        expect = ['-h/--help', '-o/--host']
        check_parsed(expect, parser.option_list)

    def test_custom_short_name(self):
        "Custom short names"
        
        def func(b_far=3):
            pass
        
        parser = optfunc.OptfuncParser(func)
        
        self.assertEqual(len(parser.option_list), 2)
        self.assertEqual(str(parser.option_list[1]), '-b/--far')

    def test_optfunc_replaces_underscores(self):
        "Replace underscores with hyphens"
        
        def func(something_here=2):
            pass
        
        parser = optfunc.OptfuncParser(func)
        self.assertEqual(len(parser.option_list), 2)
        self.assertEqual(str(parser.option_list[1]), '-s/--something-here')

    def test_optfunc_parses_methods(self):
        "Object methods are handled correctly"
        
        class Foo(object):
            def method(self, foo, baz="bing!"):
                pass
        
        parser = optfunc.OptfuncParser(Foo().method)
        self.assertEqual(len(parser.option_list), 2)
        self.assertEqual(str(parser.option_list[1]), '-b/--baz')
        self.assertEqual(parser.required, ["foo"])

    def test_optfunc_parses_lambda(self):
        "Lambdas are handled correctly"
        
        # Not at all sure on a use case, but OptfuncParse handles
        # it with zero extra code.

        parser = optfunc.OptfuncParser(lambda x: x.doh())
        self.assertEqual(len(parser.option_list), 1)
        self.assertEqual(parser.required, ["x"])
    
    def test_optfunc_parses_callable_objects(self):
        "Callable objects aren't directly kosher"
        
        class Foo(object):
            def __call__(self, args, data=4):
                pass
        
        # OptfuncParser uses inspect.getargspec which doesn't do
        # magic to check for a __call__ method. Although, callable
        # objects *are* handled by the run methods.
        
        self.assertRaises(TypeError, optfunc.OptfuncParser, Foo())

    def test_arghelp(self):
        "@arghelp('foo', 'help about foo') sets the help output"

        @optfunc.arghelp('foo', 'help about foo')
        def func(foo=False):
            pass

        parser = optfunc.OptfuncParser(func)
        self.assertEqual(parser.option_list[1].help, 'help about foo')


class OptfuncRunTest(BaseTest):
    def test_args(self):
        "Check running the basics"

        def func(a, b=2, d=False):
            if d: return int(b)*3 + int(a)
            return -1

        self.assertEqual(optfunc.run(func, ["1", "-b", "3", "-d"]), 10)
        self.assertEqual(optfunc.run(func, ["1"]), -1)
        self.assertEqual(optfunc.run(func, ["1", "-d"]), 7)
    
    def test_missing_required(self):
        "Throws an error for missing arguments"

        def func(a, b):
            pass
        
        self.assertRaises(RuntimeError, optfunc.run, func, [], catch=False)
        self.assertRaises(RuntimeError, optfunc.run, func, ['2'], catch=False)
    
    def test_too_many_args(self):
        "Throws an error for too many arguments"
        
        def func(a):
            pass
        
        test = lambda: optfunc.run(func, ['2', '3'], catch=False)
        self.assertRaises(RuntimeError, test)
    def test_custom_short_name(self):
        "Custom short names"

        def func(b_far=3):
            return b_far

        self.assertEqual(optfunc.run(func, ['-b', 10]), 10)

    def test_notstrict(self):
        "@notstrict fills missing args with None"
        
        @optfunc.notstrict
        def func(a, b):
            return [a, b]
        
        self.assertEqual(optfunc.run(func, ['foo']), ['foo', None])

    def test_notstrict_too_many(self):
        "Even with @notstrict too many args is an error"
        
        @optfunc.notstrict
        def func(a):
            pass
    
        test = lambda: optfunc.run(func, ['foo', 'bar'], catch=False)
        self.assertRaises(RuntimeError, test)

class OptfuncClassTest(BaseTest):
    def test_run_class(self):
        "Running a class executes it's init method."

        class InitClass:
            def __init__(self, one, option=''):
                self.vals = (one, option)

        test = lambda: optfunc.run(InitClass, ['f', '-o', 'z'])
        self.assertEqual(test().vals, ('f', 'z'))

    def test_no_init_is_error(self):
        "No __init__ method on a class throws an error."
        
        # I can't figure out how this would be useful. Calling it an
        # an error until someone shows me different.

        class NoInitClass:
            pass
        
        self.assertRaises(TypeError, optfunc.run, NoInitClass, [], catch=False)

    def test_runs_callable_instance(self):
        "Instances of callable classes are ok."

        class CallableClass(object):
            def __init__(self):
                pass
            def __call__(self, arg, opt=2):
                return arg + str(opt)

        self.assertEqual(optfunc.run(CallableClass(), ['f', '-o', '3']), 'f3')

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
        
        test = lambda: optfunc.run(HidesCallable(), [], catch=False)
        self.assertRaises(TypeError, test)

class OptfuncCommandsTest(BaseTest):
    def test_basics(self):
        "Executes subcommands successfully"
    
        def one(arg):
            return "One " + str(arg)
        def two(arg, some='stuff'):
            return "Two " + str(arg) + ' ' + some
        def three(arg):
            return "Three " + str(arg)
            
        test = lambda x: optfunc.run([one, two, three], x)
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
        self.assertEqual(optfunc.run([one, two], catch=False), 0)
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
        self.assertEqual(optfunc.run([one, two], ['three']), -1)
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
        self.assertEqual(optfunc.run([one, two], ['help']), 0)
        sys.stderr.unsilence()
        self.assertNotEqual(sys.stderr.getvalue(), "")
    
    def test_cmd_desc(self):
        "@cmddesc describes a command in list output"
        
        @optfunc.cmddesc("Captain commando!")
        def one(arg):
            pass
        
        self.assertEqual(sys.stderr.getvalue(), "")
        sys.stderr.silence()
        self.assertEqual(optfunc.run([one], ['help']), 0)
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
        self.assertEqual(optfunc.run([one, two], ['help', 'one', 'three']), 0)
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
        self.assertEqual(optfunc.run([one, help], ['help', 'foo']), 'foo bar')
        sys.stderr.unsilence()
        self.assertEqual(sys.stderr.getvalue(), "")

class OptfuncPipesTest(BaseTest):
    def test_stdin(self):
        "stdin, stdout, stderr as argument names gets passed sys.* streams"
        
        def func(stdin, stdout, stderr):
            self.assertEqual(stdin, sys.stdin)
            self.assertEqual(stdout, sys.stdout)
            self.assertEqual(stderr, sys.stderr)
            return "awesome!"
        
        self.assertEqual(optfunc.run(func, []), 'awesome!')

class OptfuncMainTest(BaseTest):
    def test_run_func(self):
        "optfunc.main runs passed function"

        def stuff():
            return -2

        self.assertEqual(optfunc.main(stuff, []), -2)

    # I have no idea how to force the condition in optfunc.main
    # into thinking it's a frame down from main.
    #
    # def test_as_runner(self):
    #     "optfunc.main runs the function"
    # 
    #     def func():
    #         return 34
    # 
    #     self.assertEqual(optfunc.main(func, []), 34)

if __name__ == '__main__':
    unittest.main()
