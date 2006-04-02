#!/bin/sh

PATH=$PATH:/usr/local/bin
last_working=""

# Create .pth files
for binary in python python2 python2.0 python2.1 python2.2 python2.3 python2.4 python2.5; do
    if $binary -c "" 2>/dev/null; then
        last_working=$binary
        $binary - <<EOF
import sys
sitedirs = filter(lambda s: s.endswith("site-packages"), sys.path)
if len(sitedirs) < 1:
    sys.exit("Unable to find a site-packages directory in sys.path")
filename = sitedirs[0] + "/hiveconf.pth"
open(filename, "w").write("/usr/lib/hiveconf\n")
print "Created", filename
EOF
    fi
done

# Modify hashbang of hivetool
if [ $last_working ]; then
    $last_working - <<EOF
import sys
f = open("/usr/bin/hivetool", "r+")
lines = f.readlines()
lines[0] = "#!%s\n" % sys.executable
f.seek(0)
f.writelines(lines)
f.close()
EOF
fi
