import inspect
import optparse as op
import os
import re
import sys
import textwrap
import types

FILE   = 1
DIR    = 2
EXISTS = 4
PARENT = 8

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}\b")
IP_ADDR = re.compile(
    r"""
        \b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}
        (?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b
    """,
    re.VERBOSE
)

def progname():
    if not len(sys.argv):
        return 'unknown_program'
    return os.path.split(sys.argv[0])[-1]

class OptforkParser(op.OptionParser):
        
    TYPE_VALIDATORS = {
        int: (int, "%(name)s must be an integer"),
        long: (long, "%(name)s must be an integer"),
        float: (float, "%(name)s must be a float"),
        str: (str, "The world is ending."), # This help should never be seen.
    }
    
    def __init__(self, func, *args, **kwargs):
        # can't use super() because OptionParser is an old style class
        op.OptionParser.__init__(self, *args, **kwargs)
        self.opt_names = {}

        self.help = func.__doc__
        self.strict = not hasattr(func, "optfork_notstrict")
        self.optdict = getattr(func, 'optfork_optdict', {})
        self.validators = getattr(func, 'optfork_validators', {})

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

    def print_help(self):
        print textwrap.dedent(self.help).lstrip() % {"prog": progname()}

    def parse(self, argv):
        opts, args = op.OptionParser.parse_args(self, argv)
        for k,v in list(opts.__dict__.items()):
            if k in self.opt_names:
                opts.__dict__[self.opt_names[k]] = v
                del opts.__dict__[k]

        if len(args) < len(self.required) and self.strict:
            missing = self.required[len(args):]
            raise sys.exit("Missing arguments: %s" % ', '.join(missing))
            
        if len(args) > len(self.required):
            extra = args[len(self.required):]
            sys.exit("Extra arguments: %s" % ', '.join(extra))

        args += [None] * (len(self.required) - len(args))
        for idx, name in enumerate(self.required):
            try:
                value = self._validate(name, args[idx])
            except op.OptionValueError, inst:
                sys.exit(inst)
            setattr(opts, name, value)

        return opts.__dict__

    def validate(self, option, optstr, value, parser):
        optname = self.opt_names.get(option.dest, option.dest)
        value = self._validate(optname, value)
        setattr(parser.values, option.dest, value)
    
    def append(self, option, optstr, value, parser):
        optname = self.opt_names.get(option.dest, option.dest)
        value = self._validate(optname, value)
        curr = getattr(parser.values, optname, [])
        if not isinstance(curr, list):
            curr = [curr]
        curr.append(value)
        setattr(parser.values, option.dest, curr)
    
    def _validate(self, name, value):
        v = self.validators.get(name, None)
        if not v:
            return value
        try:
            return v[0](value)
        except op.OptionValueError:
            raise
        except:
            if v[1]:
                mesg = v[1] % {"name": name, "value": value}
            else:
                mesg = "Failed to validate: %r = %r" % (name, value)
            raise op.OptionValueError(mesg)

    def make_option(self, name, default, shortnames):
        (short, name) = self.short_name(name, shortnames)
        shortnames.add(short)
        
        if name not in self.validators:
            vtype = getattr(default, "__class__", None)
            if vtype in self.TYPE_VALIDATORS:
                self.validators[name] = self.TYPE_VALIDATORS[vtype]
            elif isinstance(default, list) and len(default) > 0:
                vtype = getattr(default[0], "__class__", None)
                if vtype in self.TYPE_VALIDATORS:
                    self.validators[name] = self.TYPE_VALIDATORS[vtype]

        short = '-%s' % short
        long = '--%s' % name.replace('_', '-')
        
        if isinstance(default, bool):
            action = 'store_true'
            callback = None
            type = None
            nargs = None
        elif isinstance(default, list):
            action = 'callback'
            callback = self.append
            type = 'string'
            nargs = 1
        else:
            action = 'callback'
            callback = self.validate
            type = 'string'
            nargs = 1

        kwargs = {
            "action": action,
            "dest": name,
            "default": default,
            "callback": callback,
            "type": type,
            "nargs": nargs,
            "help": ""
        }
        kwargs.update(self.optdict.get(name, {}))
        return op.make_option(short, long, **kwargs)

    def short_name(self, arg, used):
        # Allow specification of a short option name by naming
        # function arguments with a 'x_' prefix where 'x' becomes
        # the short option.
        if re.match('^[a-zA-Z0-9]_', arg):
            self.opt_names[arg[2:]] = arg
            return (arg[0], arg[2:])
        for ch in arg:
            if ch in used:
                continue
            return (ch, arg)

def run(func, argv=None, help=None):
    if argv is None:
        argv = sys.argv[1:]
    if not isinstance(argv, list):
        raise TypeError("Invalid argument list: %r" % argv)
    helpmesg = "Try '%s -h'\n"
    try:
        if not isinstance(func, (tuple, list)):
            return run_single(func, argv)
        helpmesg = "Try '%s help'\n"
        return run_many(func, argv)
    except Exception, inst:
        if os.getenv("OPTFUNC_RAISE", True):
            raise
        sys.stderr.write("%s\n" % str(inst))
        sys.stderr.write(helpmesg % progname())
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

    parser = OptforkParser(desc)
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
        sys.stderr.write("Try '%s help'\n" % progname())
        return -1

    if fname not in funcs and fname == "help":
        if len(argv) < 1:
            subcommand_help(funcs)
            return 0
        for arg in argv:
            if arg in funcs:
                parser = OptforkParser(funcs[arg])
                parser.print_help()
                sys.stderr.write('\n')
            else:
                sys.stderr.write("Unknown command: '%s'\n" % arg)
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
        if hasattr(funcs[func], "optfork_desc"):
            desc += " - " + funcs[func].optfork_desc
        doc.append(desc)
    doc.append('')
    sys.stderr.write(os.linesep.join(doc))

# Decorators
def notstrict(fn):
    fn.optfork_notstrict = True
    return fn

class option(object):
    def __init__(self, name, **kwargs):
        self.name = name
        self.kwargs = kwargs
    def __call__(self, fn):
        curr = getattr(fn, 'optfork_optdict', {})
        curr[self.name] = self.kwargs
        setattr(fn, 'optfork_optdict', curr)
        return fn

class cmd(object):
    def __init__(self, desc):
        self.desc = desc
    def __call__(self, fn):
        fn.optfork_desc = self.desc
        return fn

class valid(object):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.help = kwargs.get("help", None)
        self.names = args

    def __call__(self, func):
        curr = getattr(func, 'optfork_validators', {})
        for name in self.names:
            curr[name] = (self.valid, self.help)
        setattr(func, 'optfork_validators', curr)
        return func

    def valid(self, value):
        return self.func(value)

class choices(valid):
    def __init__(self, opts, *args, **kwargs):
        valid.__init__(self, self, *args, **kwargs)
        self.opts = opts
        self.validator = kwargs.get("validator", None)

    def valid(self, value):
        if self.validator:
            value = self.validator(value)
        if value in self.opts:
            return value
        mesg = "%r is not a valid choice (%s)" % (value, ', '.join(self.opts))
        raise op.OptionValueError(mesg)            

class regexp(valid):
    def __init__(self, pattern, *args, **kwargs):
        valid.__init__(self, self, *args, **kwargs)
        kwargs.pop("help", None)
        self.pattern = re.compile(pattern, **kwargs)

    def valid(self, value):
        if not self.pattern.match(value):
            raise ValueError()
        return value

class stream(valid):
    def __init__(self, flags, *args, **kwargs):
        valid.__init__(self, self, *args, **kwargs)
        self.flags = flags
        self.mode = kwargs.get("mode", None)

    def valid(self, value):
        head, tail = os.path.split(value)
        if self.flags & FILE and not tail:
            raise op.OptionValueError("File '%s' does not exist." % value)
        if self.flags & DIR and tail:
            mesg = "Path '%s' does not end with %s" % (value, os.path.sep)
            raise op.OptionValueError(mesg)
        if self.flags & EXISTS and not os.path.exists(value):
            raise op.OptionValueError("Path '%s' does not exist." % value)
        if self.flags & PARENT and not os.path.exists(head):
            mesg = "Parent directory '%s' does not exist." % head
            raise op.OptionValueError(mesg)
        if not self.mode:
            return value
        try:
            return open(value, self.mode)
        except IOError, inst:
            mesg = "Failed to open file '%s' : %s" % (value, inst.strerror)
            raise op.OptionValueError(mesg)

# Convenience runner
def main(*args, **kwargs):
    prev_frame = inspect.stack()[-1][0]
    mod = inspect.getmodule(prev_frame)
    if mod is not None and mod.__name__ == '__main__':
        if len(args) > 0:
            return run(*args, **kwargs)
        # Pull in subcommands
        comms = []
        for name, obj in inspect.getmembers(mod):
            if callable(obj) and hasattr(obj, "optfork_desc"):
                comms.append(obj)
        return run(comms, **kwargs)
    return args[0] # So it won't break anything if used as a decorator

