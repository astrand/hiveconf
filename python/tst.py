#!/usr/bin/env python2

import hiveconf



def main():
    hive = hiveconf.open_hive("tst.hive")

    print "Walking, ROOT folder:"
    hive.walk()

    print "================="

    #print hive.lookup("security/sec1").get_string()
    #print hive.lookup("security/sec1").get_bool()

    print hive.lookup("toplevel_param1").get_string()
    print hive.lookup("globals/workgroup").get_string()
    print hive.lookup("globals/max log size").get_integer()
    print hive.lookup("globals/deadtime").get_float()
    print hive.lookup("globals/server string").get_binary()
    print hive.lookup("globals/boolean_list").get_bool_list()
    print hive.lookup("globals/integer_list").get_integer_list()
    print hive.lookup("globals/float_list").get_float_list()
    print hive.lookup("globals/interfaces").get_string_list()
    print hive.lookup("shares/tmp/public").get_bool()
    print hive.lookup("globals/hostkeys").get_binary_list()


main()
