#!/usr/bin/env python2

DESCRIPTION = """\
hiveconf is a configuration framework
"""

from distutils.core import setup

setup (name = "hiveconf",
       version = "0.0",
       license = "LGPL",
       description = "configuration framework",
       long_description = DESCRIPTION,
       author = "Peter Astrand",
       author_email = "peter@cendio.se",
       url = "http://www.cendio.se/~peter/hiveconf",
       py_modules = ["hiveconf"],
       data_files=[('/usr/bin', ['hivetool']),
                   ('/etc', ['etc/root.hive']),
                   ('/etc/hiveconf.d', [])
                   ]
       )
