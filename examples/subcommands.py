#!/usr/bin/env python
import optfork as opt

@opt.cmd("The first command.")
def one(arg):
    "usage: %prog one arg"
    print "One: %s" % arg

@opt.cmd("The second command.")
def two(arg):
    "usage: %prog two arg"
    print "Two: %s" % arg

@opt.cmd("The third command is three times as awesome!")
def three(arg):
    "usage: %prog three arg"
    print "Three: %s" % arg

optfunc.main()
