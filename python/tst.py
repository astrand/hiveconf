#!/usr/bin/env python2

import hiveconf



def main():
    hive = hiveconf.open_hive("tst.hconf")

    #comps = hiveconf.path2comps("/foppa/bettan/lotta")
    #hiveconf._create_folders(hive, comps, None)

    #hive.create_new_folder("/foppa/bettan/lotta")

    #hive.lookup("/foo/bar/fie/fum/p1").set_string("q1")

    #hive.set_string("/foo/bar/fie/fum/p4", "v2")




    hive.set_bool("/apple/vanilj/choklad/storlek", 1)
    hive.set_integer_list("/apple/vanilj/choklad/iilist", [1, 2, 3, 4])


    

    #print hive.get_binary_list("globals/hostkeys")

    #print "Walking, ROOT folder:"
    hive.walk()

    print "================="
    #print hive.lookup("/foo/bar/fie/fum/gurka/p3").get_string()


    #hive.set_string("/foppa/bettan/lotta/val1

    #print hive.lookup("security/sec1").get_string()
    #print hive.lookup("security/sec1").get_bool()

    #    print hive.lookup("toplevel_param1").get_string()
    #print hive.lookup("globals/workgroup").get_string()
    #print hive.get_string("globals/workgroup")

    #print hive.set_string("shares/tmp/nyfolder/nyparam", "newvalue")
#    print hive.set_string("shares/tmp/nyfolder/nyparam", "newvalue2")

    #hive.walk()

    
    #    print hive.lookup("globals/max log size").get_integer()
    #    print hive.lookup("globals/deadtime").get_float()
    #    print hive.lookup("globals/server string").get_binary()
    #    print hive.lookup("globals/boolean_list").get_bool_list()
    #    print hive.lookup("globals/integer_list").get_integer_list()
    #    print hive.lookup("globals/float_list").get_float_list()
    #    print hive.lookup("globals/interfaces").get_string_list()
    #    print hive.lookup("shares/tmp/public").get_bool()
    #    print hive.lookup("globals/hostkeys").get_binary_list()
    #

    #
    # Set tests. 
    #
##     hive.lookup("toplevel_param1").set_string("fff")
##     hive.lookup("shares/tmp/public").set_bool(0)
##     hive.lookup("globals/max log size").set_integer(222)
##     hive.lookup("globals/deadtime").set_float(12.3)
##     hive.lookup("globals/server string").set_binary("GNU") ## FEl!!!

##     hive.lookup("globals/interfaces").set_string_list(["a", "b"])
##     hive.lookup("globals/boolean_list").set_bool_list([1, 2, 3, 0])
##     hive.lookup("globals/integer_list").set_integer_list([1, 2, 3, 0])
##     hive.lookup("globals/float_list").set_float_list([1.2, 2.3])
##     hive.lookup("globals/hostkeys").set_binary_list(["aaa", "bbb"])

    #print hive.lookup("shares/tmp/bar/bbb").set_string("pppppp")
    #print hive.lookup("shares/tmp/bar")

    


main()
