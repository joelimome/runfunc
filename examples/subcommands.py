#!/usr/bin/env python
"""
This is some documentation on a command.
"""

import optfork as opt

@opt.cmd("The first command.")
def one(arg):
    "usage: %(prog)s one arg"
    print "One: %s" % arg

@opt.cmd("The second command.")
def two(arg):
    "usage: %(prog)s two arg"
    print "Two: %s" % arg

@opt.cmd("The third command is three times as awesome!")
def three(arg):
    "usage: %(prog)s three arg"
    print "Three: %s" % arg

opt.main()
