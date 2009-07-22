#!/usr/bin/env python
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
    if verbose:
        print "value: %d" % value
    newval = value * 2
    if verbose:
        print "%d * 2 = %d" % (value, newval)
    print newval

rf.run(main, Help())
