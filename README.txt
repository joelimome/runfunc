optfunc
=======

Parse command line options in Python using function introspection.

Post feedback here: http://simonwillison.net/2009/May/28/optfunc/

I can never remember how to use any of Python's regular command line parsing
libraries.

optfunc uses introspection to make a Python function available as a command
line utility. It's syntactic sugar around optparse from the standard library.

Here's what the API looks like so far:

    import optfunc
    
    def upper(filename, verbose = False):
        "Usage: %prog <file> [--verbose] - output file content in uppercase"
        s = open(filename).read()
        if verbose:
            print "Processing %s bytes..." % len(s)
        print s.upper()
    
    if __name__ == '__main__':
        optfunc.run(upper)

And here's the resulting command-line interface:

    $ ./demo.py --help
    Usage: demo.py <file> [--verbose] - output file content in uppercase
    
    Options:
      -h, --help     show this help message and exit
      -v, --verbose  
    $ ./demo.py README.txt 
    OPTFUNC
    ...
    $ ./demo.py README.txt -v
    Processing 2049 bytes...
    OPTFUNC
    ...

If you don't mind relying on some stack inspecting magic, you can replace the 
__name__ == '__main__ idiom with the following:

    optfunc.main(upper)

If you like really short scripts, you can even use this function as a 
decorator:

    @optfunc.main
    def upper(filename):
        print open(filename).read().upper()

How arguments work
------------------

Non-keyword arguments are treated as required arguments - optfunc.run will 
throw an error if the number of arguments provided on the command line 
doesn't match the number expected by the function (unless @notstrict is used, 
see below).

Keyword arguments with defaults are treated as options. Option types are set to
match the type of the default value. This can be controlled using the @option
decorator described later.

Consider the following:

    def geocode(s, api_key='', geocoder='google', list_geocoders=False):

's' is a required argument. api_key, geocoder and list_geocoders are all 
options, with defaults provided. Since list_geocoders has a boolean as its 
default it will be treated slightly differently (in optparse terms, it will 
store True if the flag is provided on the command line and False otherwise).

The command line options are derived from the parameter names like so:

    Options:
      -h, --help            show this help message and exit
      -l, --list-geocoders
      -a API_KEY, --api-key=API_KEY
      -g GEOCODER, --geocoder=GEOCODER

Note that the boolean --list-geocoders is a flag, not an option that sets a
value.

The short option is derived from the first letter of the parameter. If that 
character is already in use, the second character will be used and so on.

The long option is the full name of the parameter with underscores converted 
to hyphens.

If you want complete control over the name of the options, simply name your 
parameter as follows:

    def foo(q_custom_name=False):

This will result in a short option of -q and a long option of --custom-name.

Special arguments
-----------------

Arguments with the names 'stdin', 'stdout' or 'stderr' will be automatically 
passed the relevant Python objects, for example:
    
    #!/usr/bin/env python
    # upper.py
    import optfunc
    
    @optfunc.main
    def upper_stdin(stdin, stdout):
        stdout.write(stdin.read().upper())

Does the following:

    $ echo "Hello, world" | ./upper.py
    HELLO, WORLD

Subcommands
-----------

Some command line applications feature subcommands, with the first argument 
to the application indicating which subcommand should be executed.

optfunc has the beginnings of support for this - you can pass an array of 
functions to the optfunc.run() and the names of the functions will be used 
to select a subcommand based on the first argument:

    import optfunc
    
    def one(arg):
        print "One: %s" % arg
    
    def two(arg):
        print "Two: %s" % arg
    
	@optfunc.cmddesc("The third command")
    def three(arg):
        print "Three: %s" % arg
    
    if __name__ == '__main__':
        optfunc.run([one, two, three])

Usage looks like this:

    $ ./subcommands.py
	usage: ./subcommands.py <subcommand> [options] [args]
	Type './subcommands.py help <subcommand>' for help on a specific subcommand.

	Available subcommands:
	    three - The third command is three times as awesome!
	      two
	      one
	$ ./subcommands.py help one
	Usage: subcommands.py one arg

	Options:
	  -h, --help  show this help message and exit

    $ ./subcommands.py one
    Missing arguments: arg
	Try './subcommands.py help'
	$ ./subcommands.py two arg
    Two: arg

Decorators
----------

optfunc also supports a couple decorators for stuff I couldn't work out how to 
shoehorn in to a regular function definition. geocode.py shows them in action:

    @optfunc.notstrict
    @optfunc.option('list_geocoders', help='list available geocoders and exit')
    def geocode(s, api_key='', geocoder='google', list_geocoders=False):
        # ...

@notstrict means "don't throw an error if one of the required positional 
arguments is missing" - in the above example we use this because we still want
the list_geocoders argument to work even if a string has not been provided.

@option('arg-name', **kwargs) allows you to override any keyword argument to
optparse.Option's constructor. A list of common arguments:

    * help - Displayed when `./program -h` is called
    * metavar - The variable name to display when `./program -h` is called
    * type - Type of parameter to cast to.
    * choices - A list of choices for the parameter

TODO
----

* Support for opening files or using one of the std* pipes
* Proper unix error semantics (sys.exit(1) etc)
* Allow the function to be a generator, print iterations to stdout
* Support for *args (I don't think **kwargs makes sense for optfunc)
* Errors when running subcommands need to report the subcommand help
