#!/usr/bin/env python
import optfork as opt

@opt.valid(int, "value")
def upper(value, verbose=False):
    """
    basic.py - Basic example for optfork usage
    
    usage: %(prog)s INT [--verbose]
        
        INT       - Multiply an integer by two
        --verbose - Be verbose about it.
    """
    if verbose:
        print "INPUT: %d" % value
    newval = value * 2
    if verbose:
        print "%d * 2 = %d" % (value, newval)
    print newval

opt.main(upper)
