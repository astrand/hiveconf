#!/bin/sh

for binary in python2 python2.0 python2.1 python2.2 python2.3; do
    if $binary -c "" ; then
        $binary - <<EOF
import sys
sitedir = sys.prefix + "/lib/python" + sys.version[:3] + "/site-packages"
filename = sitedir + "/hiveconf.pth"
open(filename, "w").write("/usr/lib/hiveconf\n")
print "Created", filename
EOF
    fi
done
