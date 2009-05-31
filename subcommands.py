#!/usr/bin/env python
import optfunc

def one(arg):
    "usage: %prog one arg"
    print "One: %s" % arg

def two(arg):
    "usage: %prog two arg"
    print "Two: %s" % arg

@optfunc.cmddesc("The third command is three times as awesome!")
def three(arg):
    "usage: %prog three arg"
    print "Three: %s" % arg

optfunc.main([one, two, three])
