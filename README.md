runfunc
=======

I liked optfunc but it hasn't been put on PyPI for actual use so I went ahead
and rewrote it to use a different syntax to be able to include option help
and input validators.

Basic Example
=============

    import sys
    import runfunc as rf
    
    class Help(rf.Help):
        """\
        This is a blurb about this program. Its very entertaining to
        watch and think about what we might do with it.
        
            Look ma. Formatted text.
            
        And stuff
        """
        usage   = "%prog [options] value"
        
        value = rf.Check(int, "A value to multiply.")
        factor = rf.Check(float, "A factor by which to multiply.", opt='f')
        random = rf.Stream("r", "An input file to read from.", opt='r')
        verbose = rf.Flag("Multiply verbosely.", opt='v')
        
    def main(value, factor=2.0, random=sys.stdin, verbose=False):
        newval = value * factor
        if verbose:
            print "%d * %s = %s" % (value, factor, newval)
        else:
            print newval
            
    rf.run(main, Help())


Help Class
==========

The basic outline for using `runfunc` is to create a subclass of `runfunc.Help`
and provide this class when running the function. This subclass is responsible
for specifying all of the possible arguments to be passed to the function. It
can contain extra arguments that are ignored so that the same subclass can be
reused for multiple command line scripts.

    class Help(rf.Help):
        """\
        This is a blurb about this program. Its very entertaining to
        watch and think about what we might do with it.
    
            Look ma. Formatted text.
        
        And stuff
        """
        usage   = "%prog [options] value"
    
        value = rf.Check(int, "A value to multiply.")
        factor = rf.Check(float, "A factor by which to multiply.", opt='f')
        random = rf.Stream("r", "An input file to read from.", opt='r')
        verbose = rf.Flag("Multiply verbosely.", opt='v')

A couple points to note:

* The class's doc string will be used as the program's help description
* If a `usage` attribute is present, it will be used for the program's help
* Any other attributes that inherit from `runfunc.Arg` will be available for use as a program argument.

Running a function
==================

    runfunc.run(callable, help_object, argv=None, check=True)

* `callable` is callable object.
* `help_object` is an instance of a class that inherits from `runfunc.Help`.
* `argv` is a list of arguments. If None, `sys.argv[1:]` is used
* `check=True` will prevent the function from running when imported as a module.


Functions
---------

When you specify a function, the arguments will be treated as required values on
the command line. Any keyword arguments will be able to be specified as options
the the program. For instance:

    def foo(bar, val=None):
        pass

Will have one required argument for `bar` and an option for `val`. Required
arguments are taken in order of specification on the command line. If you use
required arguments you should be sure to specify a helpful `usage` description
on your Help class.

All arguments to the function must be present as attributes on the
`runfunc.Help` instance passed to `runfunc.run`.

Validator Types
===============

Check(func, desc, opt=None)
---------------------------

Use an arbitrary function to validate an input.

* func - A callable taking a single argument. Raises an exception on error.
* desc - Help message that describes the option
* opt - A single character option name.

Flag(desc, opt=None)
--------------------

Passes true based on the presence of an option. Generally only useful for
keyword arguments.

* desc - Help message that describes the option
* opt - A single character option name.

List(desc, opt=None, validator=None)
--------------------------

Append each value seen to a list. Validator is applied before appending each
value.

* desc - Help message that describes the option
* opt - A single character option name.
* validator - A callable taking a single argument. Raises an exception on error.

Choice(choices, desc, opt=None, validator=None)
-----------------------------------------------

Limit input to a specified set of values. Validator is applied before testing
for membership in the set.

* choices - A on object providing item access to test if an option is allowable.
* desc - Help message that describes the option
* opt - A single character option name.
* validator - A callable taking a single argument. Raises an exception on error.

Regexp(pattern, desc, opt=None, flags=0)
----------------------------------------

Require input to match a regular expression.

* pattern - A string acceptable for `re.compile(pattern, flags)`
* desc - Help message that describes the option
* opt - A single character option name.
* flags - Any modifiers for compiling the regular expression

Email(desc, opt=None)
---------------------

Require input to look like a valid email address. Subclass of Regexp

* desc - Help message that describes the option
* opt - A single character option name.

IpAddr(desc, opt=None)
----------------------

Require input to look like a valid IP Address. Subclass of Regexp.

* desc - Help message that describes the option
* opt - A single character option name.

Path(flags, desc, opt=None)
---------------------------

Require that input specifies a path. Tests are executed depending on the flags
passed. FILE requires that the path looks like a file (no trailing path
specifier). DIR requires the trailing path specifier. EXISTS will check if the
path actually exists. PARENT requires that the path's parent exist. Any
combination of flags can be passed though passing FILE | DIR would guarantee an
error during validation.
 
* flags - An OR of FILE, DIR, EXISTS, PARENT
* desc - Help message that describes the option
* opt - A single character option name.

Stream(mode, desc, opt=None)
----------------------------

Open a path for use as a `file` object. A useful pattern is to use a default
value of `sys.stdin`, `sys.stdout`, or `sys.stderr` for common command line
semantics.

* mode - Passed to `open(path, mode)` when opening the stream 
* desc - Help message that describes the option
* opt - A single character option name.

Custom Validators
=================

Custom validators can be created by subclassing the Arg class and overriding
the validate method.

An example for specifying a Range validator would look something like this:

    import runfunc as rf
    
    class Range(rf.Arg):
        def __init__(self, func, left, right, desc, opt=None):
            super(Range, self).__init__(desc, opt=opt)
            self.func = func
            self.left = left
            self.right = right
            
        def validate(self, option, optstr, value, parser):
            value = self.func(value)
            if value < self.left or value > self.right:
                raise rf.OptionValueError("Value is outside range.")
            setattr(parser.values, option.dest, value)

Notice that func is specifiable so that users can convert the raw value to
an appropriate data type.


