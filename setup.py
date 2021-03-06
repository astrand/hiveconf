#!/usr/bin/env python

DESCRIPTION = """\
hiveconf is a configuration framework
"""

from distutils.core import setup

setup (name = "hiveconf",
       version = "0.5",
       license = "LGPL",
       description = "configuration framework",
       long_description = DESCRIPTION,
       author = "Peter Astrand",
       author_email = "astrand@cendio.se",
       url = "http://www.lysator.liu.se/~astrand/projects/hiveconf/",
       package_dir = {'': 'python'},
       py_modules = ["hiveconf"],
       data_files=[('/usr/bin', ['python/hivetool']),
                   ('/etc', ['etc/root.hconf']),
                   ('/etc/hiveconf.d', ["etc/hiveconf.d/kde.hconf", "etc/hiveconf.d/samba.hconf"]),
                   ('/usr/lib/hiveconf', ['setup.sh'])
                   ]
       )
