#
# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of the run package released under the BSD license.
#

import inspect
import os
import re
import sys
import textwrap
import types
from optparse import make_option, IndentedHelpFormatter, \
                OptionParser, OptionValueError, BadOptionError

def progname():
    if not sys.argv or not len(sys.argv):
        raise RuntimeError("Empty sys.argv")
    return os.path.basename(sys.argv[0])

class Arg(object):
    def __init__(self, desc, opt=None):
        self.desc = desc
        self.short = opt
        self.name = None
        self.argname = None
    
    def as_opt(self, default):
        name = self.name.replace('_', '-')
        if self.short:
            args = ('-%s' % self.short, '--%s' % name)
        else:
            args = ('--%s' % name,)
        kwargs = {"dest": self.name, "default": default, "help": self.desc}
        ret = self.add_args(kwargs)
        if ret: kwargs = ret
        return make_option(*args, **kwargs)

    def add_args(self, args):
        args.update({
            "action": "callback",
            "callback": self.do_validate,
            "type": "string",
            "nargs": 1
        })

    def do_validate(self, option, optstr, value, parser):
        try:
            self.validate(option, optstr, value, parser)
        except (BadOptionError, OptionValueError):
            raise
        except Exception, inst:
            raise OptionValueError(str(inst))

    def validate(self, option, optstr, value, parser):
        raise NotImplementedError()
    
class Check(Arg):
    def __init__(self, func, desc, opt=None):
        Arg.__init__(self, desc, opt=opt)
        self.func = func
    
    def validate(self, option, optstr, value, parser):
        try:
            setattr(parser.values, option.dest, self.func(value))
        except:
            raise OptionValueError("Invalid value for %r" % self.name)
    
class Flag(Arg):
    def __init__(self, desc, opt=None):
        Arg.__init__(self, desc, opt=opt)

    def add_args(self, args):
        args.update({
            "action": "store_true",
            "callback": None,
            "type": None,
            "nargs": None
        })

class List(Arg):
    def __init__(self, desc, opt=None, validator=None):
        Arg.__init__(self, desc, opt=opt)
        self.validator = validator
    
    def validate(self, option, optstr, value, parser):
        if self.validator:
            value = self.validator(value)
        parser.values.ensure_value(option.dest, []).append(value)

class Choice(Arg):
    def __init__(self, choices, desc, opt=None, validator=None):
        Arg.__init__(self, desc, opt=opt)
        self.choices = choices
        self.validator = validator

    def validate(self, option, optstr, value, parser):
        if self.validator:
            value = self.validator(value)
        if value not in self.choices:
            raise OptionValueError("%r is not a valid choice." % value)
        setattr(parser.values, option.dest, value)

class Regexp(Arg):
    def __init__(self, pattern, desc, opt=None, flags=0):
        Arg.__init__(self, desc, opt=opt)
        self.pattern = re.compile(pattern, flags)

    def validate(self, option, optstr, value, parser):
        if not self.pattern.match(value):
            raise OptionValueError("%r does not match pattern." % value)
        setattr(parser.values, option.dest, value)

class Email(Regexp):
    def __init__(self, desc, opt=None):
        Arg.__init__(self, desc, opt=opt)
        self.pattern = re.compile(
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}\b",
            re.IGNORECASE
        )

class IpAddr(Regexp):
    def __init__(self, desc, opt=None):
        Arg.__init__(self, desc, opt=opt)
        self.pattern = re.compile(r"""
            \b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}
            (?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b
        """, re.VERBOSE)

FILE   = 1
DIR    = 2
EXISTS = 4
PARENT = 8

class Path(Arg):
    def __init__(self, flags, desc, opt=None):
        Arg.__init__(self, desc, opt=opt)
        self.flags = flags
    
    def validate(self, option, optstr, value, parser):
        head, tail = os.path.split(value)
        if self.flags & FILE and not tail:
            raise OptionValueError("File '%s' does not exist." % value)
        if self.flags & DIR and tail:
            mesg = "Path '%s' does not end with %s" % (value, os.path.sep)
            raise OptionValueError(mesg)
        if self.flags & EXISTS and not os.path.exists(value):
            raise OptionValueError("Path '%s' does not exist." % value)
        if self.flags & PARENT and not os.path.exists(head):
            mesg = "Parent directory '%s' does not exist." % head
            raise OptionValueError(mesg)
        setattr(parser.values, option.dest, value)

class Stream(Arg):
    def __init__(self, mode, desc, opt=None):
        Arg.__init__(self, desc, opt=opt)
        self.mode = mode

    def validate(self, option, optstr, value, parser):
        setattr(parser.values, option.dest, open(value, self.mode))

class HelpMeta(type):
    def __new__(cls, name, bases, d):
        args = {}
        for base in bases:
            if hasattr(base, '_args'):
                args.update(base._args)
        for attrname, attrval in d.items():
            if isinstance(attrval, Arg):
                if not attrval.name:
                    attrval.name = attrname
                args[attrname] = attrval
        d['_args'] = args
        return type.__new__(cls, name, bases, d)

class Help(object):
    __metaclass__ = HelpMeta

    def __contains__(self, name):
        return name in self._args

    def __getitem__(self, name):
        return self._args[name]

class Formatter(IndentedHelpFormatter):
    def __init__(self):
        # indent incr, max_help_pos, width, short_first
        IndentedHelpFormatter.__init__(self, 2, 26, None, 1)
    
    def format_description(self, desc):
        desc = textwrap.dedent(desc)
        indent = " " * self.current_indent
        lines = map(lambda x: indent + x, desc.splitlines())
        return '\n'.join(lines + [''])

    def format_option_strings(self, option):
        opts = option._short_opts + option._long_opts
        opts = '/'.join(opts)
        if option.takes_value():
            opts += " " + (option.metavar or option.dest.upper())
        return opts

class Parser(OptionParser):

    METHOD_TYPES = (
        types.BuiltinMethodType, types.MethodType, types.UnboundMethodType
    )
    
    CALLABLE_TYPES = (
        types.BuiltinFunctionType, types.FunctionType, types.LambdaType
    ) + METHOD_TYPES

    def __init__(self, func, help):
        OptionParser.__init__(self)
        self.formatter = Formatter()
        self.func = func
        self.help = help
        self.usage = getattr(help, "usage", None)
        self.description = help.__doc__

        runner = self._runner(func)
        args, varargs, varkw, defaults = inspect.getargspec(runner)
        defaults = defaults or ()

        # Account for the self argument
        if isinstance(runner, self.METHOD_TYPES):
            args = args[1:]

        # Check that we know about everything
        for arg in args:
            if arg in self.help: continue
            raise RuntimeError("Unknown argument: %r" % arg)

        self.required = args[:len(args)-len(defaults)]
        for name, value in zip(args[len(args)-len(defaults):], defaults):
            opt = help[name].as_opt(value)
            self.add_option(opt)
        
    def parse(self, argv):
        opts, args = OptionParser.parse_args(self, argv)

        if len(args) < len(self.required):
            missing = self.required[len(args):]
            plural = "s" if len(missing) else ""
            self.error("Missing argument%s: %s" % (plural, ', '.join(missing)))
            
        if len(args) > len(self.required):
            extra = args[len(self.required):]
            plural = "s" if len(extra) else ""
            self.error("Unexpected argument%s: %s" % (plural, ', '.join(extra)))

        for name, value in zip(self.required, args):
            try:
                opt = self.help[name].as_opt(value)
                self.help[name].validate(opt, '', value, self)
            except (BadOptionError, OptionValueError), inst:
                self.error(str(inst))

        return opts.__dict__

    def _runner(self, func):
        runner = func
        if isinstance(runner, (types.ClassType, types.TypeType)):
            if not hasattr(runner, "__init__"):
                raise TypeError("%r has no '__init__' method." % func)
            runner = func.__init__

        if not isinstance(runner, self.CALLABLE_TYPES):
            if not hasattr(runner, '__call__'):
                raise TypeError('Unable to figure out how to call object.')
            runner = runner.__call__

        assert callable(runner), "%r is not callable." % func

        return runner

def is_main():
    stack = inspect.stack()
    if len(stack) < 2: return True
    prev_frame = inspect.stack()[2][0]
    mod = inspect.getmodule(prev_frame)
    return mod is not None and mod.__name__ == '__main__'

def run(func, help, argv=None, check=True):
    if check and not is_main():
        return # Don't run when imported.

    if argv is None:
        argv = sys.argv[1:]
    if not isinstance(argv, list):
        raise TypeError("Invalid argument list: %r" % argv)

    parser = Parser(func, help)
    opts = parser.parse(argv)
    return func(**opts)
