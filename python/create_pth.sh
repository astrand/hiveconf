
python - <<EOF
import sys
sitedir = sys.prefix + "/lib/python" + sys.version[:3] + "/site-packages"
filename = sitedir + "/hiveconf.pth"
f = open(filename, "w")
f.write("/usr/lib/hiveconf\n")
f.close()
print "Created", filename
EOF
