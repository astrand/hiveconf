#!/usr/bin/env python2

import hiveconf


def main():
    hive = hiveconf.open_hive("tst.hconf")

    print hive.get_string("/folder1/string_param")

    

if __name__ == "__main__":
    main()
