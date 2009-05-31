import inspect
import optparse as op
import os
import re
import sys
import types

def progname():
    if not len(sys.argv):
        return 'unknown_program'
    return sys.argv[0]

class OptfuncParser(op.OptionParser):
    def __init__(self, func, *args, **kwargs):
        # can't use super() because OptionParser is an old style class
        op.OptionParser.__init__(self, *args, usage=func.__doc__, **kwargs)
        self._opt_names = {}
        self._errors = []

        self.strict = not hasattr(func, "optfunc_notstrict")
        self.helpdict = getattr(func, 'optfunc_arghelp', {})

        args, varargs, varkw, defaults = inspect.getargspec(func)
        defaults = defaults or ()
        options = zip(args[-len(defaults):], defaults)

        numargs = len(args)
        if len(defaults) > 0:
            numargs -= len(defaults)
        
        # Account for the self argument
        if isinstance(func, (types.BuiltinMethodType, types.MethodType)):
            self.required = args[1:numargs]
        else:
            self.required = args[:numargs]

        # Build option descriptions for keyword arguments.
        shortnames = set(['h'])
        for optname, default in options:
            opt = self.make_option(optname, default, shortnames)
            self.add_option(opt)

    def parse(self, argv):
        opts, args = op.OptionParser.parse_args(self, argv)
        for k,v in opts.__dict__.iteritems():
            if k in self._opt_names:
                opts.__dict__[self._opt_names[k]] = v
                del opts.__dict__[k]

        for pipe in ('stdin', 'stderr', 'stdout'):
            if pipe in self.required:
                self.required.remove(pipe)
                setattr(opts, pipe, getattr(sys, pipe))

        if len(args) > len(self.required):
            extra = args[len(self.required):]
            raise RuntimeError("Extra arguments: %s" % ', '.join(extra))

        if len(args) < len(self.required) and self.strict:
            missing = self.required[len(args):]
            raise RuntimeError("Missing arguments: %s" % ', '.join(missing))

        args += [None] * (len(self.required) - len(args))
        for idx, name in enumerate(self.required):
            setattr(opts, name, args[idx])

        return opts.__dict__

    def make_option(self, name, default, shortnames):
        (short, name) = self.short_name(name, shortnames)
        shortnames.add(short)

        short = '-%s' % short
        long = '--%s' % name.replace('_', '-')
        if default in (True, False, bool):
            action = 'store_true'
        else:
            action = 'store'
       
        return op.make_option(short, long, action=action, dest=name,
            default=default, help=self.helpdict.get(name, ''))

    def short_name(self, arg, used):
        # Allow specification of a short option name by naming
        # function arguments with a 'x_' prefix where 'x' becomes
        # the short option.
        if re.match('^[a-zA-Z0-9]_', arg):
            self._opt_names[arg[2:]] = arg
            return (arg[0], arg[2:])
        for ch in arg:
            if ch in used:
                continue
            return (ch, arg)

def run(func, argv=None, catch=True):
    try:
        if not isinstance(func, (tuple, list)):
            return run_single(func, argv)
        return run_many(func, argv)
    except Exception, inst:
        if not catch:
            raise
        sys.stderr.write("%s\n" % str(inst))
        sys.stderr.write("Try '%s -h'\n" % progname())
        return -1

def run_single(func, argv):
    desc = func
    if isinstance(func, types.ClassType):
        if not hasattr(func, "__init__"):
            raise TypeError("%r has no '__init__' method." % func)
        desc = func.__init__
    if not callable(func):
        raise TypeError("%r is not callable." % func)
    
    functypes = (
        types.BuiltinFunctionType, types.FunctionType,
        types.BuiltinMethodType, types.MethodType
    )
    if not isinstance(desc, functypes):
        if not hasattr(func, '__call__'):
            raise TypeError('Unable to figure out how to call object.')
        desc = func.__call__

    parser = OptfuncParser(desc)
    opts = parser.parse(argv)
    return func(**opts)

def run_many(funcs, argv):
    funcs = dict([(fn.__name__, fn) for fn in funcs])

    if not argv or len(argv) < 1:
        subcommand_help(funcs)
        return 0
    
    fname = argv.pop(0)

    if fname not in funcs and fname != "help":
        sys.stderr.write("Unknown command: '%s'\n" % fname)
        sys.stderr.write("Type '%s help' for usage'\n" % progname())
        return -1
    
    if fname not in funcs and fname == "help":
        if len(argv) > 1:
            for arg in argv:
                if arg in funcs:
                    parser = OptfuncParser(funcs[arg])
                    parser.print_help(file=sys.stderr)
                else:
                    sys.stderr.write("Unknown command: '%s'" % arg)
            return 0
        subcommand_help(funcs)
        return 0

    return run_single(funcs[fname], argv)

def subcommand_help(funcs):
    doc = map(lambda x: x.strip(), ("""
        usage: %(prog)s <subcommand> [options] [args]
        Type '%(prog)s help <subcommand>' for help on a specific subcommand.
    """ % {"prog": progname()}).strip().split('\n'))
    
    doc.extend(['', 'Available subcommands:'])
    
    maxlen = len(max(funcs, key=lambda x: len(x)))
    fmt = "    %%%ds" % maxlen
    for func in funcs:
        desc = fmt % func
        if hasattr(funcs[func], "optfunc_desc"):
            desc += " - " + funcs[func].optfunc_desc
        doc.append(desc)
    doc.append('')
    sys.stderr.write(os.linesep.join(doc))

# Decorators
def notstrict(fn):
    fn.optfunc_notstrict = True
    return fn

def arghelp(name, help):
    def inner(fn):
        d = getattr(fn, 'optfunc_arghelp', {})
        d[name] = help
        setattr(fn, 'optfunc_arghelp', d)
        return fn
    return inner

def cmddesc(desc):
    def inner(fn):
        fn.optfunc_desc = desc
        return fn
    return inner

# Convenience runner
def main(*args, **kwargs):
    prev_frame = inspect.stack()[-1][0]
    mod = inspect.getmodule(prev_frame)
    if mod is not None and mod.__name__ == '__main__':
        return run(*args, **kwargs)
    return args[0] # So it won't break anything if used as a decorator

