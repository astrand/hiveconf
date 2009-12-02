#!/bin/sh

last_working=""

# Create .pth files
for binary in python2 python2.2 python2.3 python2.4 python2.5 python2.6 python _python_preferred_; do
    if ${binary} -c "" 2>/dev/null; then
        last_working=${binary}
        ${binary} - <<EOF
pthfile="hiveconf.pth"
mod_dir="/usr/lib/hiveconf"
import sys, os
sitedirs = filter(lambda s: s.endswith("site-packages") or s.endswith("dist-packages"), sys.path)
if len(sitedirs) < 1:
    sys.exit("Unable to find a site packages directory in sys.path")
filename = sitedirs[0] + "/" + pthfile
want = mod_dir + "\n"
if not os.path.exists(filename) or open(filename, "r").read() != want:
    open(filename, "w").write(want)
    print "Created", filename
EOF
    fi
done

# Modify hashbang of hivetool. If we are inside a sparse Solaris zone,
# site-packages is likely read only, but if the package is installed
# in the global zone (which is what we are supporting at this point),
# this script has already been executed there. Assuming the target
# Python interpreter ends up being the same, there's no need to modify
# hivetool, thus the read only file system is no problem. 
if [ ${last_working} ]; then
    ${last_working} - <<EOF
toolfile="/usr/bin/hivetool"
import sys, os
binary = sys.executable
if binary[-len("_python_preferred_"):] == "_python_preferred_":
    binary = os.readlink(binary)
want = "#!%s\n" % binary
f = open(toolfile, "r")
if f.readline() != want:
    f.close()
    f = open(toolfile, "r+")
    lines = f.readlines()
    lines[0] = want
    f.seek(0)
    f.writelines(lines)
    f.truncate()
f.close()
EOF
fi
