#
# Copyright 2009 Paul J. Davis <paul.joseph.davis@gmail.com>
#
# This file is part of the run package released under the BSD license.
#

import os
import ez_setup
ez_setup.use_setuptools()
from setuptools import setup

base_dir = os.path.dirname(__file__)
long_desc = open(os.path.join(base_dir, "README.md")).read()

setup(
    name = "runfunc",
    description = "An alternative syntax for optparse",
    long_description = long_desc,
    author = "Paul Joseph Davis",
    author_email = "paul.joseph.davis@gmail.com",
    url = "http://github.com/davisp/runfunc",
    version = "0.0.1",
    license = "BSD",
    keywords = "optparse command-line help",
    platforms = ["any"],
    zip_safe = False,

    classifiers = [
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],

    py_modules = ["runfunc"],

    setup_requires = ["setuptools>=0.6c8"],
    tests_require = ["nose>=0.10.0"],

    test_suite = "nose.collector"
)
