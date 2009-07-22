#!/usr/bin/env python
import runfunc as rf

class Script(rf.Script):
    version = "0.0.0"
    arg = rf.Check(int, "This is an argument.")

class One(Script):
    "The first command."
    def main(self, arg):
        print "One: %s" % arg
    
class Two(Script):
    "Another command."
    def main(self, arg):
        print "Two: %s" % arg

class Three(Script):
    "I'm detecting a pattern."
    verbose = rf.Flag("Do it verbosely.")
    def main(self, arg, verbose=False):
        print "Three: %s %s" % (arg, "verbosely" if verbose else "")

class MainScript(rf.Script):
    """
    Some stuff about the main program here.
    """
    one = One()
    two = Two()
    three = Three()

MainScript.run()
