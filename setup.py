#!/usr/bin/env python2

DESCRIPTION = """\
hiveconf is a configuration framework
"""

from distutils.core import setup

setup (name = "hiveconf",
       version = "0.1",
       license = "LGPL",
       description = "configuration framework",
       long_description = DESCRIPTION,
       author = "Peter Astrand",
       author_email = "peter@cendio.se",
       url = "http://www.cendio.se/~peter/hiveconf",
       package_dir = {'': 'python'},
       py_modules = ["hiveconf"],
       data_files=[('/usr/bin', ['python/hivetool']),
                   ('/etc', ['etc/root.hconf']),
                   ('/etc/hiveconf.d', ["etc/hiveconf.d/kde.hconf", "etc/hiveconf.d/samba.hconf"])
                   ]
       )
