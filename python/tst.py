#!/usr/bin/env python2

import hiveconf



def main():
    rootfolder = hiveconf.open_hive("foo.hive")

    print "XXX", rootfolder.get("key1").get_string()

    print "Walking:"
    print_objs(rootfolder)
    





def print_objs(folder):
    print "Folder folders:", folder.folders
    print "Folder parameters:", folder.parameters
    


main()
