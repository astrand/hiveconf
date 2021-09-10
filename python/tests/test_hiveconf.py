#! /usr/bin/env python3
# -*-mode: python; coding: utf-8 -*-
#
# Copyright 2020 Samuel Mannehed for Cendio AB.
# For more information, see http://www.cendio.com
import os
import sys
import unittest
import getopt

from unittest import mock

def get_origin_dir():
    """Get program origin directory"""
    return os.path.dirname(os.path.realpath(__file__))

modules_path = os.path.abspath(os.path.join(get_origin_dir(), "../"))
sys.path = [modules_path] + sys.path

import hiveconf

class HiveconfDebugWriterTest(unittest.TestCase):
    @mock.patch('hiveconf.sys')
    def test_debugwriter_write(self, sys):
        # Given
        dw = hiveconf._DebugWriter("foo")
        # When
        dw.write("bär")
        # Then
        sys.stderr.write.assert_called_with("bär")


class HiveconfUtilitiesTest(unittest.TestCase):
    def test_path2comps_root(self):
        # Given
        p = "/"
        # When
        r = hiveconf._path2comps(p)
        # Then
        self.assertEqual(r, ["/"])

    def test_path2comps_slashstart(self):
        # Given
        p = "/tmp/foo"
        # When
        r = hiveconf._path2comps(p)
        # Then
        self.assertEqual(r, ["tmp", "foo"])

    def test_path2comps_slashend(self):
        # Given
        p = "tmp/bar/"
        # When
        r = hiveconf._path2comps(p)
        # Then
        self.assertEqual(r, ["tmp", "bar"])

    def test_path2comps_non_ascii(self):
        # Given
        p = "tämp/bår/"
        # When
        r = hiveconf._path2comps(p)
        # Then
        self.assertEqual(r, ["tämp", "bår"])

    def test_comps2path(self):
        # Given
        c = ["a", "b", "c"]
        # When
        r = hiveconf._comps2path(c)
        # Then
        self.assertEqual(r, "/a/b/c")

    def test_comps2path_non_ascii(self):
        # Given
        c = ["å", "ß", "c"]
        # When
        r = hiveconf._comps2path(c)
        # Then
        self.assertEqual(r, "/å/ß/c")

    @mock.patch('os.getcwd')
    def test_get_cwd_url(self, getcwd):
        # When
        r = hiveconf._get_cwd_url()
        # Then
        getcwd.assert_called_once()
        self.assertTrue(r.beginsWith("file://"))

    @mock.patch('hiveconf.urllib.parse')
    def test_get_url_scheme(self, urlparse):
        # Given
        urlparse.urlsplit.return_value = ['a', 'b', 'c']
        # When
        r = hiveconf._get_url_scheme("hej")
        # Then
        urlparse.urlsplit.assert_called_with("hej")
        self.assertEqual(r, "a")

    @mock.patch('hiveconf.urllib.parse')
    def test_get_url_path(self, urlparse):
        # Given
        urlparse.urlsplit.return_value = ['a', 'b', 'c']
        # When
        r = hiveconf._get_url_path("hej")
        # Then
        urlparse.urlsplit.assert_called_with("hej")
        self.assertEqual(r, "c")

    def test_fixup_sectionname_no_leading_slash(self):
        # Given
        sn = "a"
        # When
        r = hiveconf._fixup_sectionname(sn)
        # Then
        self.assertEqual(r, "/a")

    def test_fixup_sectionname_trailing_slash(self):
        # Given
        sn = "/a/"
        # When
        r = hiveconf._fixup_sectionname(sn)
        # Then
        self.assertEqual(r, "/a")

    @mock.patch('hiveconf.os.access', return_value=2)
    @mock.patch('hiveconf.urllib.parse.urlsplit',
                mock.MagicMock(return_value=["file", "", "path"]))
    def test_check_write_access_returns_access_ok(self, access):
        # When
        r = hiveconf._check_write_access("url")
        # Then
        access.assert_called_once()
        path_arg = access.call_args_list[0][0][0]
        self.assertTrue(isinstance(path_arg, str))
        self.assertEqual(r, 2)

    @mock.patch('hiveconf.urllib.parse.urlsplit', mock.MagicMock(return_value=["other"]))
    def test_check_write_access_non_file(self):
        # When
        r = hiveconf._check_write_access("url")
        # Then
        self.assertEqual(r, 0)

    def test_has_glob_wildchars_yes(self):
        # When
        r = hiveconf._has_glob_wildchars("a*c")
        # Then
        self.assertEqual(r, True)

    def test_has_glob_wildchars_no(self):
        # When
        r = hiveconf._has_glob_wildchars("abc")
        # Then
        self.assertEqual(r, False)


class HiveconfParameterTest(unittest.TestCase):
    def test_constructor_empty_source(self):
        with self.assertRaises(hiveconf.Error):
            hiveconf.Parameter("val", "", "section1", "param1", "file1")

    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater.add_parameter")
    def test_write_new(self, add_parameter, hivefileupdater):
        p = hiveconf.Parameter("val", "file1", "section1", "param1", "file://file1")
        # When
        r = p.write_new()
        # Then
        self.assertEqual(r, 1)
        add_parameter.assert_called_once_with("section1", "param1", "val")

    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater.add_parameter")
    def test_write_new_non_ascii(self, add_parameter, hivefileupdater):
        p = hiveconf.Parameter("væl", "fïl€1", "sêctioŋ1", "pä®am1", "file://fîłe1")
        # When
        r = p.write_new()
        # Then
        self.assertEqual(r, 1)
        add_parameter.assert_called_once_with("sêctioŋ1", "pä®am1", "væl")

    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_write_new_no_write_target(self, hivefileupdater):
        p = hiveconf.Parameter("val", "file1", "section1", "param1", "")
        # When
        r = p.write_new()
        # Then
        self.assertEqual(r, 0)
        hivefileupdater.assert_not_called()

    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater.change_parameter")
    def test_write_update(self, change_parameter, hivefileupdater):
        p = hiveconf.Parameter("val", "file1", "section1", "param1", "file1")
        # When
        r = p.write_update()
        # Then
        self.assertEqual(r, 1)
        change_parameter.assert_called_once_with("section1", "param1", "val", delete_param=0)

    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater.change_parameter")
    def test_write_update_non_ascii(self, change_parameter, hivefileupdater):
        p = hiveconf.Parameter("väl", "fiłë1", "säƈtioñ1", "pªr@m1", "fiłë1")
        # When
        r = p.write_update()
        # Then
        self.assertEqual(r, 1)
        change_parameter.assert_called_once_with("säƈtioñ1", "pªr@m1", "väl", delete_param=0)

    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater.add_parameter")
    def test_write_update_new(self, add_parameter, hivefileupdater):
        p = hiveconf.Parameter("val", "file2", "section1", "param1", "file1")
        # When
        r = p.write_update()
        # Then
        self.assertEqual(r, 1)
        add_parameter.assert_called_once_with("section1", "param1", "val")

    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_write_update_no_write_target(self, hivefileupdater):
        p = hiveconf.Parameter("val", "file2", "section1", "param1", "")
        # When
        r = p.write_update()
        # Then
        self.assertEqual(r, 0)
        hivefileupdater.assert_not_called()

    def test_get_string(self):
        # Given
        p = hiveconf.Parameter("val", "file1", "section1", "param1", "file1")
        # When
        r = p.get_string()
        # Then
        self.assertEqual(r, "val")

    def test_get_bool_true(self):
        # Given
        p = hiveconf.Parameter("1", "file1", "section1", "param1", "file1")
        # When
        r = p.get_bool()
        # Then
        self.assertEqual(r, 1)

    def test_get_bool_false(self):
        # Given
        p = hiveconf.Parameter("false", "file1", "section1", "param1", "file1")
        # When
        r = p.get_bool()
        # Then
        self.assertEqual(r, 0)

    def test_get_bool_badbool(self):
        # Given
        p = hiveconf.Parameter("foo", "file1", "section1", "param1", "file1")
        # Then
        self.assertRaises(hiveconf.BadBoolFormat, p.get_bool)

    def test_get_integer(self):
        # Given
        p = hiveconf.Parameter(" 5", "file1", "section1", "param1", "file1")
        # When
        r = p.get_integer()
        # Then
        self.assertEqual(r, 5)

    def test_get_integer_badinteger(self):
        # Given
        p = hiveconf.Parameter("bar", "file1", "section1", "param1", "file1")
        # Then
        self.assertRaises(hiveconf.BadIntegerFormat, p.get_integer)

    def test_get_float(self):
        # Given
        p = hiveconf.Parameter("4.4", "file1", "section1", "param1", "file1")
        # When
        r = p.get_float()
        # Then
        self.assertEqual(r, 4.4)

    def test_get_float_badfloat(self):
        # Given
        p = hiveconf.Parameter("foo 1.0", "file1", "section1", "param1", "file1")
        # Then
        self.assertRaises(hiveconf.BadFloatFormat, p.get_float)

    def test_get_binary(self):
        # Given
        p = hiveconf.Parameter("414243", "file1", "section1", "param1", "file1")
        # When
        r = p.get_binary()
        # Then
        self.assertEqual(r, b"ABC")

    def test_get_binary_with_whitespaces(self):
        # Given
        p = hiveconf.Parameter("   41 42 \n    43  \t", "file1",
                               "section1", "param1", "file1")
        # When
        r = p.get_binary()
        # Then
        self.assertEqual(r, b"ABC")

    def test_get_binary_badbinary(self):
        # Given
        p = hiveconf.Parameter("foox", "file1", "section1", "param1", "file1")
        # Then
        self.assertRaises(hiveconf.BadBinaryFormat, p.get_binary)

    def test_get_string_list(self):
        # Given
        p = hiveconf.Parameter("a b c", "file1", "section1", "param1", "file1")
        # When
        r = p.get_string_list()
        # Then
        self.assertEqual(r, ["a", "b", "c"])

    def test_get_bool_list(self):
        # Given
        p = hiveconf.Parameter("1 true no yes FALSE 0", "file1", "section1", "param1", "file1")
        # When
        r = p.get_bool_list()
        # Then
        self.assertEqual(r, [1, 1, 0, 1, 0, 0])

    def test_get_integer_list(self):
        # Given
        p = hiveconf.Parameter("00 33 -1", "file1", "section1", "param1", "file1")
        # When
        r = p.get_integer_list()
        # Then
        self.assertEqual(r, [0, 33, -1])

    def test_get_float_list(self):
        # Given
        p = hiveconf.Parameter("0.0 3.3 -1.6", "file1", "section1", "param1", "file1")
        # When
        r = p.get_float_list()
        # Then
        self.assertEqual(r, [0, 3.3, -1.6])

    def test_get_binary_list(self):
        # Given
        p = hiveconf.Parameter("41 6969 7b", "file1", "section1", "param1", "file1")
        # When
        r = p.get_binary_list()
        # Then
        self.assertEqual(r, [b"A", b"ii", b"{"])

    def test_set_string(self):
        # Given
        p = hiveconf.Parameter("foo", "file1", "section1", "param1", "file1")
        # When
        p.set_string("bar")
        # Then
        self.assertEqual(p._value, "bar")

    def test_set_bool(self):
        # Given
        p = hiveconf.Parameter("True", "file1", "section1", "param1", "file1")
        # When
        p.set_bool(False)
        # Then
        self.assertEqual(p._value, "false")

    def test_set_integer(self):
        # Given
        p = hiveconf.Parameter("1", "file1", "section1", "param1", "file1")
        # When
        p.set_integer(3)
        # Then
        self.assertEqual(p._value, '3')

    def test_set_float(self):
        # Given
        p = hiveconf.Parameter("1000", "file1", "section1", "param1", "file1")
        # When
        p.set_float(9.999)
        # Then
        self.assertEqual(p._value, '9.999')

    def test_set_binary(self):
        # Given
        p = hiveconf.Parameter("50", "file1", "section1", "param1", "file1")
        # When
        p.set_binary(b"Z")
        # Then
        self.assertEqual(p._value, "5a")

    def test_set_binary_more_than_one_byte(self):
        # Given
        p = hiveconf.Parameter("50", "file1", "section1", "param1", "file1")
        # When
        p.set_binary(b".\xf0\xf1\xf2")
        # Then
        self.assertEqual(p._value, "2ef0f1f2")

    def test_set_string_list(self):
        # Given
        p = hiveconf.Parameter("A B C D E F G H", "file1", "section1", "param1", "file1")
        # When
        p.set_string_list(['X', 'Y', 'Z'])
        # Then
        self.assertEqual(p._value, "X Y Z")

    def test_set_bool_list(self):
        # Given
        p = hiveconf.Parameter("true", "file1", "section1", "param1", "file1")
        # When
        p.set_bool_list([0, False, True])
        # Then
        self.assertEqual(p._value, "false false true")

    def test_set_integer_list(self):
        # Given
        p = hiveconf.Parameter("1 2 3", "file1", "section1", "param1", "file1")
        # When
        p.set_integer_list([4, 5])
        # Then
        self.assertEqual(p._value, "4 5")

    def test_set_float_list(self):
        # Given
        p = hiveconf.Parameter("1.0 2.1 3.6", "file1", "section1", "param1", "file1")
        # When
        p.set_float_list([4.4])
        # Then
        self.assertEqual(p._value, "4.4")

    def test_set_binary_list(self):
        # Given
        p = hiveconf.Parameter("9a9b9c 8b 7c", "file1", "section1", "param1", "file1")
        # When
        p.set_binary_list([b"FOO", b"BAR"])
        # Then
        self.assertEqual(p._value, "464f4f 424152")


class HiveconfFolderTest(unittest.TestCase):
    # -- Help Functions --
    def get_args_str(self, call_args_list):
        args_list = [x[0][0] for x in call_args_list]
        return "".join(args_list)

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_folders_existing(self, lookup, check_write_access):
        # Given
        root = hiveconf.Folder("file1", "file1", "/")
        root._folders = { "subfolderA": None,
                          "subfolderB": None }
        lookup.return_value = root
        # When
        r = root.get_folders("/")
        # Then
        expected = ['subfolderA', 'subfolderB']
        # Sort since the order doesn't matter
        self.assertEqual(sorted(r), sorted(expected))

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_folders_existing_non_ascii(self, lookup, check_write_access):
        # Given
        root = hiveconf.Folder("fiłë1", "fiłë1", "/")
        root._folders = { "sübfolderÅ": None,
                          "sûbfolderß": None }
        lookup.return_value = root
        # When
        r = root.get_folders("/")
        # Then
        expected = ['sübfolderÅ', 'sûbfolderß']
        # Sort since the order doesn't matter
        self.assertEqual(sorted(r), sorted(expected))

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup", return_value=[])
    def test_get_folders_default(self, lookup, check_write_access):
        # Given
        f = hiveconf.Folder("file1", "file1", "")
        # When
        r = f.get_folders("/", ["foo"])
        # Then
        self.assertEqual(r, ["foo"])

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_folders_empty(self, lookup, check_write_access):
        # Given
        f = hiveconf.Folder("file1", "file1", "sectionA")
        lookup.return_value = f
        # When
        r = f.get_folders("/")
        # Then
        self.assertEqual(r, [])

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_parameters_existing(self, lookup, check_write_access):
        # Given
        f = hiveconf.Folder("file1", "file1", "/")
        f._parameters = { "a": "1",
                          "b": "2" }
        lookup.return_value = f
        # When
        r = f.get_parameters("/")
        # Then
        expected = ['a', 'b']
        # Sort since the order doesn't matter
        self.assertEqual(sorted(r), sorted(expected))

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_parameters_existing_non_ascii(self, lookup, check_write_access):
        # Given
        f = hiveconf.Folder("fîłé1", "fîłé1", "/")
        f._parameters = { "ä": "1",
                          "ß": "2" }
        lookup.return_value = f
        # When
        r = f.get_parameters("/")
        # Then
        expected = ['ä', 'ß']
        # Sort since the order doesn't matter
        self.assertEqual(sorted(r), sorted(expected))

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup", return_value=[])
    def test_get_parameters_default(self, lookup, check_write_access):
        # Given
        f = hiveconf.Folder("file1", "file1", "/")
        # When
        r = f.get_parameters("/", ["foo"])
        # Then
        self.assertEqual(r, ["foo"])

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_parameters_empty(self, lookup, check_write_access):
        # Given
        f = hiveconf.Folder("file1", "file1", "sectionA")
        lookup.return_value = f
        # When
        r = f.get_parameters("sectionA")
        # Then
        self.assertEqual(r, [])

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Folder._lookup_list")
    @mock.patch("hiveconf.urllib.parse.urlsplit", return_value=("file", "n", "f", "q", "f"))
    @mock.patch("hiveconf.Parameter.write_update")
    def test_delete_param(self, write_update, urlsplit, lookup_list, lookup, check_write_access):
        # Given
        child = hiveconf.Parameter("val1", "file1", "r/p", "c", "file1")
        parent = hiveconf.Folder("file1", "file1", "r/p")
        parent._parameters = { 'c': child }
        root = hiveconf.Folder("file1", "file1", "r")
        root._folders = { 'p': parent }
        lookup.return_value = child
        lookup_list.return_value = parent
        # When
        r = root.delete("r/p/c")
        # Then
        self.assertEqual(r, 1)
        write_update.assert_called_with(delete=1)

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Folder._lookup_list")
    @mock.patch("hiveconf.urllib.parse.urlsplit", return_value=("file", "n", "f", "q", "f"))
    @mock.patch("hiveconf.Parameter.write_update")
    @mock.patch("hiveconf._HiveFileUpdater.delete_section")
    def test_delete_param_recursive(self, delete_section, write_update, urlsplit,
                                    lookup_list, lookup, check_write_access):
        # Given
        child = hiveconf.Parameter("val1", "file1", "r/p", "c", "file1")
        parent = hiveconf.Folder("file1", "file1", "r/p")
        parent._parameters = { 'c': child }
        root = hiveconf.Folder("file1", "file1", "r")
        root._folders = { 'p': parent }
        lookup.return_value = parent
        lookup_list.return_value = root
        # When
        r = root.delete("r/p", recursive=1)
        # Then
        self.assertEqual(r, 1)
        write_update.assert_called_once_with(delete=1)
        delete_section.assert_called_once_with("/r/p")

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Folder._lookup_list")
    @mock.patch("hiveconf.urllib.parse.urlsplit", return_value=("file", "n", "f", "q", "f"))
    @mock.patch("hiveconf.Parameter.write_update")
    @mock.patch("hiveconf._HiveFileUpdater.delete_section")
    def test_delete_param_recursive_non_ascii(self, delete_section, write_update, urlsplit,
                                              lookup_list, lookup, check_write_access):
        # Given
        child = hiveconf.Parameter("val1", "file1", "я/þ", "¢", "file1")
        parent = hiveconf.Folder("file1", "file1", "я/þ")
        parent._parameters = { '¢': child }
        root = hiveconf.Folder("file1", "file1", "r")
        root._folders = { 'þ': parent }
        lookup.return_value = parent
        lookup_list.return_value = root
        # When
        r = root.delete("я/þ", recursive=1)
        # Then
        self.assertEqual(r, 1)
        write_update.assert_called_once_with(delete=1)
        delete_section.assert_called_once_with("/я/þ")

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Folder._lookup_list")
    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater.delete_section")
    def test_delete_folder(self, delete_section, hivefileupdater, lookup_list,
                           lookup, check_write_access):
        # Given
        child = hiveconf.Folder("file1", "file1", "r/p/c")
        parent = hiveconf.Folder("file1", "file1", "r/p")
        parent._folders = { 'c': child }
        root = hiveconf.Folder("file1", "file1", "r")
        root._folders = { 'p': parent }
        lookup.return_value = child
        lookup_list.return_value = parent
        # When
        r = root.delete("r/p/c")
        # Then
        self.assertEqual(r, 1)
        delete_section.assert_called_with(child.sectionname)

    @mock.patch("hiveconf.Folder._lookup_list")
    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater.delete_section")
    def test_delete_folder_no_parent(self, delete_section, hivefileupdater, lookup_list):
        # Given
        root = hiveconf.Folder("file1", "file1", "/")
        root._addobject(root, "/") # special setup for rootfolder
        lookup_list.return_value = root
        # When
        r = root.delete("/", recursive=1) # recursive since it has itself as subfolder
        # Then
        self.assertEqual(r, 1)
        delete_section.assert_called_with(root.sectionname)

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Folder._lookup_list")
    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater.delete_section")
    def test_delete_folder_recursive(self, delete_section, hivefileupdater,
                                     lookup_list, lookup, check_write_access):
        # Given
        child = hiveconf.Folder("file1", "file1", "r/p/c")
        parent = hiveconf.Folder("file1", "file1", "r/p")
        parent._folders = { 'c': child }
        root = hiveconf.Folder("file1", "file1", "r")
        root._folders = { 'p': parent }
        lookup.return_value = parent
        lookup_list.return_value = root
        # When
        r = root.delete("r/p", recursive=1)
        # Then
        self.assertEqual(r, 1)
        self.assertEqual(delete_section.call_count, 2)
        delete_section.assert_any_call(child.sectionname)
        delete_section.assert_any_call(parent.sectionname)

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Folder._lookup_list")
    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater.delete_section")
    def test_delete_folder_recursive_non_ascii(self, delete_section, hivefileupdater,
                                               lookup_list, lookup, check_write_access):
        # Given
        child = hiveconf.Folder("file1", "file1", "я/þ/¢")
        parent = hiveconf.Folder("file1", "file1", "я/þ")
        parent._folders = { '¢': child }
        root = hiveconf.Folder("file1", "file1", "я")
        root._folders = { 'þ': parent }
        lookup.return_value = parent
        lookup_list.return_value = root
        # When
        r = root.delete("я/þ", recursive=1)
        # Then
        self.assertEqual(r, 1)
        self.assertEqual(delete_section.call_count, 2)
        delete_section.assert_any_call(child.sectionname)
        delete_section.assert_any_call(parent.sectionname)

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder._lookup_list")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_delete_folder_nonrecursive_subfolders(self, hivefileupdater, lookup_list,
                                                   check_write_access):
        # Given
        child = hiveconf.Folder("file1", "file1", "r/p/c")
        parent = hiveconf.Folder("file1", "file1", "r/p")
        parent._folders = { 'c': child }
        root = hiveconf.Folder("file1", "file1", "r")
        root._folders = { 'p': parent }
        lookup_list.return_value = parent
        # When/Then
        self.assertRaises(hiveconf.FolderNotEmpty, root.delete, "/r/p")
        hivefileupdater.assert_not_called()

    @mock.patch("hiveconf.Folder.lookup", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_delete_folder_no_obj(self, hivefileupdater, lookup):
        # Given
        f = hiveconf.Folder("file1", "file1", "")
        # When
        r = f.delete("foo")
        # Then
        self.assertEqual(r, 0)
        hivefileupdater.assert_not_called()

    @mock.patch("hiveconf.Parameter.get_bool")
    @mock.patch("hiveconf.Folder.lookup", return_value=None)
    def test_get_value_default(self, lookup, p_get_bool):
        # Given
        f = hiveconf.Folder("file1", "file1", "/")
        # When
        r = f.get_bool("/p", default="bar")
        # Then
        self.assertEqual(r, "bar")
        p_get_bool.assert_not_called()

    @mock.patch("hiveconf.Parameter.get_bool")
    @mock.patch("hiveconf.Folder.lookup", return_value=None)
    def test_get_value_default_non_ascii(self, lookup, p_get_bool):
        # Given
        f = hiveconf.Folder("file1", "file1", "/")
        # When
        r = f.get_bool("/p", default="bær")
        # Then
        self.assertEqual(r, "bær")
        p_get_bool.assert_not_called()

    @mock.patch("hiveconf.Parameter.get_binary_list")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_value_bad_param(self, lookup, p_get_binary_list):
        # Given
        f = hiveconf.Folder("file1", "file1", "/")
        lookup.return_value = f
        # When/Then
        self.assertRaises(hiveconf.NotAParameterError, f.get_bool, "/f")

    @mock.patch("hiveconf.Parameter.get_string")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_string(self, lookup, p_get_string):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_string.return_value = "foo"
        # When
        r = f.get_string("/p")
        # Then
        self.assertEqual(r, "foo")
        p_get_string.assert_called_with(p)

    @mock.patch("hiveconf.Parameter.get_bool")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_bool(self, lookup, p_get_bool):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_bool.return_value = "1"
        # When
        r = f.get_bool("p")
        # Then
        self.assertEqual(r, "1")
        p_get_bool.assert_called_with(p)

    @mock.patch("hiveconf.Parameter.get_integer")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_integer(self, lookup, p_get_integer):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_integer.return_value = "5"
        # When
        r = f.get_integer("/f/p")
        # Then
        self.assertEqual(r, "5")
        p_get_integer.assert_called_with(p)

    @mock.patch("hiveconf.Parameter.get_float")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_float(self, lookup, p_get_float):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_float.return_value = "1.3"
        # When
        r = f.get_float("/p")
        # Then
        self.assertEqual(r, "1.3")
        p_get_float.assert_called_with(p)

    @mock.patch("hiveconf.Parameter.get_binary")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_binary(self, lookup, p_get_binary):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_binary.return_value = "ff"
        # When
        r = f.get_binary("/p")
        # Then
        self.assertEqual(r, "ff")
        p_get_binary.assert_called_with(p)

    @mock.patch("hiveconf.Parameter.get_string_list")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_string_list(self, lookup, p_get_string_list):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_string_list.return_value = "a bc defghåäö"
        # When
        r = f.get_string_list("/p")
        # Then
        self.assertEqual(r, "a bc defghåäö")
        p_get_string_list.assert_called_with(p)

    @mock.patch("hiveconf.Parameter.get_bool_list")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_bool_list(self, lookup, p_get_bool_list):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_bool_list.return_value = "1 0"
        # When
        r = f.get_bool_list("/p")
        # Then
        self.assertEqual(r, "1 0")
        p_get_bool_list.assert_called_with(p)

    @mock.patch("hiveconf.Parameter.get_integer_list")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_integer_list(self, lookup, p_get_integer_list):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_integer_list.return_value = "9 8 7 5555"
        # When
        r = f.get_integer_list("/p")
        # Then
        self.assertEqual(r, "9 8 7 5555")
        p_get_integer_list.assert_called_with(p)

    @mock.patch("hiveconf.Parameter.get_float_list")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_float_list(self, lookup, p_get_float_list):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_float_list.return_value = "1.1 2.22 3.333"
        # When
        r = f.get_float_list("/p")
        # Then
        self.assertEqual(r, "1.1 2.22 3.333")
        p_get_float_list.assert_called_with(p)

    @mock.patch("hiveconf.Parameter.get_binary_list")
    @mock.patch("hiveconf.Folder.lookup")
    def test_get_binary_list(self, lookup, p_get_binary_list):
        # Given
        p = hiveconf.Parameter("val1", "file1", "/f", "p", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'p': p }
        lookup.return_value = p
        p_get_binary_list.return_value = "10 bc ff"
        # When
        r = f.get_binary_list("/p")
        # Then
        self.assertEqual(r, "10 bc ff")
        p_get_binary_list.assert_called_with(p)

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup", return_value=None)
    @mock.patch("hiveconf.Parameter.write_new")
    def test_set_value_create_shortpath(self, write_new, lookup, check_write_access):
        # Given
        f2 = hiveconf.Folder("file1", "file1", "/f1/f2")
        f1 = hiveconf.Folder("file1", "file1", "/f1")
        f1._folders = { 'f2': f2 }
        # When
        f2.set_integer("myint", "9999")
        # Then
        write_new.assert_called_once()

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup", return_value=None)
    @mock.patch("hiveconf.Parameter.write_new")
    def test_set_value_create_shortpath_non_ascii(self, write_new, lookup,
                                                  check_write_access):
        # Given
        f2 = hiveconf.Folder("file1", "file1", "/ḟ1/ḟ2")
        f1 = hiveconf.Folder("file1", "file1", "/ḟ1")
        f1._folders = { 'ḟ2': f2 }
        # When
        f2.set_integer("m¥int", "9999")
        # Then
        write_new.assert_called_once()

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder._lookup_list")
    @mock.patch("hiveconf.Folder.lookup", return_value=None)
    @mock.patch("hiveconf.Parameter.write_new")
    def test_set_value_create_fullpath(self, write_new, lookup, lookup_list,
                                       check_write_access):
        # Given
        f2 = hiveconf.Folder("file1", "file1", "/f1/f2")
        f1 = hiveconf.Folder("file1", "file1", "/f1")
        f1._folders = { 'f2': f2 }
        lookup_list.return_value = f2
        # When
        f2.set_string("/f1/f2/biip", "boop")
        # Then
        write_new.assert_called_once()

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Parameter.write_update")
    def test_set_value_update(self, write_update, lookup, check_write_access):
        # Given
        p = hiveconf.Parameter("0", "file1", "/f", "pineapplegoesonpizza", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'pineapplegoesonpizza': p }
        lookup.return_value = p
        # When
        f.set_bool("pineapplegoesonpizza", "1")
        # Then
        write_update.assert_called_once()

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Parameter.write_update")
    def test_set_value_update_non_ascii(self, write_update, lookup, check_write_access):
        # Given
        p = hiveconf.Parameter("0", "file1", "/f", "ßαηαηαgoeson℘☤ℨℨα", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'ßαηαηαgoeson℘☤ℨℨα': p }
        lookup.return_value = p
        # When
        f.set_bool("ßαηαηαgoeson℘☤ℨℨα", "1")
        # Then
        self.assertEqual(p.paramname, "ßαηαηαgoeson℘☤ℨℨα")
        write_update.assert_called_once()

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Parameter.write_update")
    def test_set_value_update_no_write_target(self, write_update, lookup,
                                              check_write_access):
        # Given
        p = hiveconf.Parameter("0", "file1", "/f", "param", "")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'param': p }
        lookup.return_value = p
        # When
        f.set_integer("param", "888")
        # Then
        write_update.assert_called_once()

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf.Parameter.write_update")
    def test_set_value_update_write_target_different_from_source(self, write_update,
                                                                 lookup, check_write_access):
        # Given
        p = hiveconf.Parameter("0", "file1", "/f", "tacofredag", "1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'tacofredag': p }
        lookup.return_value = p
        # When
        f.set_integer("tacofredag", "77")
        # Then
        write_update.assert_called_once()

    # Lookup doesn't find it, but parameter already exists
    @mock.patch("hiveconf.Folder.lookup", return_value=None)
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    @mock.patch("hiveconf._check_write_access", return_value=True)
    def test_set_value_existing(self, check_write_access, hivefileupdater, lookup):
        # Given
        p = hiveconf.Parameter("hejsan", "file1", "/f", "svejsan", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'hejsan': p }
        # When / Then
        with self.assertRaises(hiveconf.ObjectExistsError):
            f.set_string("hejsan", "MrAstrand")

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder.lookup", return_value=None)
    @mock.patch("hiveconf.isinstance", return_value=False)
    def test_set_value_invalid_type(self, isinstance, lookup, check_write_access):
        # Given
        f = hiveconf.Folder("file1", "file1", "/f")
        # When / Then
        with self.assertRaises(hiveconf.InvalidObjectError):
            f.set_string("hejsan", "MrAstrand")

    @mock.patch("hiveconf.Parameter.set_string")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_string(self, hivefileupdater, lookup, p_set_string):
        # Given
        p = hiveconf.Parameter("hejsan", "file1", "/f", "svejsan", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'hejsan': p }
        lookup.return_value = p
        # When
        f.set_string("hejsan", "MrAstrand")
        # Then
        p_set_string.assert_called_with(p, "MrAstrand")

    @mock.patch("hiveconf.Parameter.set_bool")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_bool(self, hivefileupdater, lookup, p_set_bool):
        # Given
        p = hiveconf.Parameter("1", "file1", "/f", "peoplewithbeardsarecool", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'peoplewithbeardsarecool': p }
        lookup.return_value = p
        # When
        f.set_bool("peoplewithbeardsarecool", False)
        # Then
        p_set_bool.assert_called_with(p, False)

    @mock.patch("hiveconf.Parameter.set_integer")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_integer(self, hivefileupdater, lookup, p_set_integer):
        # Given
        p = hiveconf.Parameter("7", "file1", "/f", "numberofbugsinthecode", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'numberofbugsinthecode': p }
        lookup.return_value = p
        # When
        f.set_integer("numberofbugsinthecode", 8)
        # Then
        p_set_integer.assert_called_with(p, 8)

    @mock.patch("hiveconf.Parameter.set_float")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_float(self, hivefileupdater, lookup, p_set_float):
        # Given
        p = hiveconf.Parameter("0.0", "file1", "/f", "WeAllFloatDownHere", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'WeAllFloatDownHere': p }
        lookup.return_value = p
        # When
        f.set_float("WeAllFloatDownHere", 0.0)
        # Then
        p_set_float.assert_called_with(p, 0.0)

    @mock.patch("hiveconf.Parameter.set_binary")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_binary(self, hivefileupdater, lookup, p_set_binary):
        # Given
        p = hiveconf.Parameter("f9", "file1", "/f", "thinlincMenuKey", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'thinlincMenuKey': p }
        lookup.return_value = p
        # When
        f.set_binary("thinlincMenuKey", "f8")
        # Then
        p_set_binary.assert_called_with(p, "f8")

    @mock.patch("hiveconf.Parameter.set_string_list")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_string_list(self, hivefileupdater, lookup, p_set_string_list):
        # Given
        p = hiveconf.Parameter("obviously the answer is J", "file1", "/f",
                               "gifOrJif", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'gifOrJif': p }
        lookup.return_value = p
        # When
        f.set_string_list("gifOrJif", ["graphical", "has", "a", "hard g"])
        # Then
        p_set_string_list.assert_called_with(p, ["graphical", "has", "a", "hard g"])

    @mock.patch("hiveconf.Parameter.set_bool_list")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_bool_list(self, hivefileupdater, lookup, p_set_bool_list):
        # Given
        p = hiveconf.Parameter("1 1 1 0 0 0 1 1 1", "file1", "/f", "sos", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'sos': p }
        lookup.return_value = p
        # When
        f.set_bool_list("sos", ["0", "0", "0", "1", "1", "1", "0", "0", "0"])
        # Then
        p_set_bool_list.assert_called_with(p, ["0", "0", "0", "1", "1", "1", "0", "0", "0"])

    @mock.patch("hiveconf.Parameter.set_integer_list")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_integer_list(self, hivefileupdater, lookup, p_set_integer_list):
        # Given
        p = hiveconf.Parameter("1 2 3 4 5 6 7 8 9", "file1", "/f", "iCanCount", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'iCanCount': p }
        lookup.return_value = p
        # When
        f.set_integer_list("iCanCount", ["9", "8", "7", "6", "5", "4", "3", "2", "1"])
        # Then
        p_set_integer_list.assert_called_with(p, ["9", "8", "7", "6", "5", "4", "3", "2", "1"])

    @mock.patch("hiveconf.Parameter.set_float_list")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_float_list(self, hivefileupdater, lookup, p_set_float_list):
        # Given
        p = hiveconf.Parameter("1.9 2.8 3.7 4.6 5.5 6.4 7.3 8.2 9.1", "file1", "/f",
                               "floaters", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'floaters': p }
        lookup.return_value = p
        # When
        f.set_float_list("floaters", ["9.87654321"])
        # Then
        p_set_float_list.assert_called_with(p, ["9.87654321"])

    @mock.patch("hiveconf.Parameter.set_binary_list")
    @mock.patch("hiveconf.Folder.lookup")
    @mock.patch("hiveconf._HiveFileUpdater", autospec=True)
    def test_set_binary_list(self, hivefileupdater, lookup, p_set_binary_list):
        # Given
        p = hiveconf.Parameter("f1 f2 f3 f4", "file1", "/f", "b", "file1")
        f = hiveconf.Folder("file1", "file1", "/f")
        f._parameters = { 'b': p }
        lookup.return_value = p
        # When
        f.set_binary_list("b", ["11", "12", "13"])
        # Then
        p_set_binary_list.assert_called_with(p, ["11", "12", "13"])

    def test_lookup(self):
        # Given
        p = hiveconf.Parameter("amazing", "file1", "f1/f2", "s", "file1")
        f2 = hiveconf.Folder("file1", "file1", "f1/f2")
        f2._parameters = { 's': p }
        f1 = hiveconf.Folder("file1", "file1", "f1")
        f1._folders = { 'f2': f2 }
        # When
        r = f1.lookup("/f2/s")
        # Then
        self.assertEqual(r, p)

    def test_lookup_non_ascii(self):
        # Given
        p = hiveconf.Parameter("αღ@ℨ☤ᾔℊ", "fiłé1", "ƒ☺ℓⅾ℮ґ1/ƒ☺ℓⅾ℮ґ2", "$", "fiłé1")
        f2 = hiveconf.Folder("fiłé1", "fiłé1", "ƒ☺ℓⅾ℮ґ1/ƒ☺ℓⅾ℮ґ2")
        f2._parameters = { '$': p }
        f1 = hiveconf.Folder("fiłé1", "fiłé1", "ƒ☺ℓⅾ℮ґ1")
        f1._folders = { 'ƒ☺ℓⅾ℮ґ2': f2 }
        # When
        r = f1.lookup("/ƒ☺ℓⅾ℮ґ2/$")
        # Then
        self.assertEqual(r, p)

    @mock.patch("hiveconf._HiveFileUpdater.add_section")
    @mock.patch("hiveconf._HiveFileUpdater.__init__", return_value=None)
    def test_lookup_autocreate(self, hivefileupdater, add_section):
        # Given
        f1 = hiveconf.Folder("file1", "file1", "f1")
        # When
        r = f1.lookup("f2", autocreate=1)
        # Then
        self.assertTrue(isinstance(r, hiveconf.Folder))
        add_section.assert_called_with("/f1/f2")

    def test_lookup_no_obj(self):
        # Given
        f1 = hiveconf.Folder("file1", "file1", "f1")
        # When
        r = f1.lookup("somethingelse")
        # Then
        self.assertEqual(r, None)

    def test_lookup_not_a_folder(self):
        # Given
        p = hiveconf.Parameter("notafolder", "file1", "f", "param", "file1")
        f = hiveconf.Folder("file1", "file1", "folder")
        f._parameters = {'param': p}
        # When/Then
        self.assertRaises(hiveconf.ObjectExistsError, f.lookup, "param/folder")


class OpenHiveTest(unittest.TestCase):
    @mock.patch("hiveconf.open", new_callable=mock.mock_open, read_data="")
    def test_open_hive(self, mock_open):
        # When
        r = hiveconf.open_hive("/")
        # Then
        self.assertTrue(isinstance(r, hiveconf.Folder))


class HiveFileParserTest(unittest.TestCase):

    # When verifying the type of a mocked folder we need to
    # compare with something, we create a special mock for that
    class FolderMockClass(mock.MagicMock):
        """
        Mock class to handle tests for _HiveFileParser.
        """
        calls = []

        def __init__(self, *args, **kwargs):
            mock.MagicMock.__init__(self)
            HiveFileParserTest.FolderMockClass.calls.append(mock.call(*args, **kwargs))

        def _get_child_mock(self, **kwargs):
            foldermock = mock.MagicMock(**kwargs)
            foldermock._isFolderMockChild = True
            return foldermock


    # -- Help Functions --
    def mock_folder__update(self, folder, source):
        if source:
            folder.sources.append(source)

    def mock__addobject(self, folder, obj, objname):
        folder._folders[objname] = obj


    # -- Tests --
    def test_constructor_blacklist_is_none(self):
        # Given
        url = "url"

        # When
        parser_obj = hiveconf._HiveFileParser(url, None)

        # Then
        self.assertTrue(isinstance(parser_obj, hiveconf._HiveFileParser))
        self.assertEqual(parser_obj.blacklist, [])

    def test_constructor_blacklist_is_not_none(self):
        # Given
        url = "url"
        blacklist = ["blacklist"]

        # When
        parser_obj = hiveconf._HiveFileParser(url, blacklist)

        # Then
        self.assertTrue(isinstance(parser_obj, hiveconf._HiveFileParser))
        self.assertEqual(parser_obj.blacklist, blacklist)

    def test_constructor_blacklist_is_not_none_non_ascii(self):
        # Given
        url = "υяł"
        blacklist = ["♭ℓα¢кłїṧ⊥"]

        # When
        parser_obj = hiveconf._HiveFileParser(url, blacklist)

        # Then
        self.assertTrue(isinstance(parser_obj, hiveconf._HiveFileParser))
        self.assertEqual(parser_obj.blacklist, blacklist)


    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open, read_data="")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    def test_parse_with_default_args_empty_file(self, mock_handle_section,
                                                mock_open, mock_folder):
        # Given
        url = "url"
        parser = hiveconf._HiveFileParser(url, None)

        # When
        result = parser.parse()

        # Then
        self.assertTrue(isinstance(result, mock_folder.__class__))
        mock_folder.assert_called_once_with(url, url, "/")

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open,
                read_data="# line 1\n; line 2\n  \n")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    def test_parse_file_with_lines_to_skip(self, mock_handle_section, mock_open,
                                           mock_folder):
        # Given
        url = "url"
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When
        result = parser.parse(url, mock_folder)

        # Then
        self.assertEqual(result, mock_folder)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open,
                read_data="[sec_name]\n")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    def test_parse_file_with_sectionname(self, mock_handle_section, mock_open,
                                         mock_folder):
        # Given
        url = "url"
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When
        result = parser.parse(url, mock_folder)

        # Then
        self.assertEqual(result, mock_folder)
        mock_handle_section.assert_called_with(mock_folder, "sec_name", url)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open,
                read_data="[ṧε¢▁name]\n")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    def test_parse_file_with_sectionname_non_ascii(self, mock_handle_section,
                                                   mock_open, mock_folder):
        # Given
        url = "ʊґł"
        parser = hiveconf._HiveFileParser("parser_ʊґł", None)

        # When
        result = parser.parse(url, mock_folder)

        # Then
        expected = "ṧε¢▁name"
        self.assertEqual(result, mock_folder)
        mock_handle_section.assert_called_with(mock_folder, expected, url)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open, read_data="[missing_end_bracket\n")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    @mock.patch("sys.stderr", mock.MagicMock()) # Suppressing stderr prints
    def test_parse_file_with_sectionname_missing_end_bracket(self, mock_handle_section,
                                                             mock_open, mock_folder):
        # Given
        url = "url"
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When
        result = parser.parse(url, mock_folder)

        # Then
        self.assertEqual(result, mock_folder)

        # mock_handle_section should not have been called with these arguments
        # if endbracket is missing
        uncalled_call_object = mock.call(mock_folder, "missing_end_bracket", url)
        self.assertTrue(uncalled_call_object not in mock_handle_section.call_args_list)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open,
                read_data="%mount arg1 arg2")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    @mock.patch("hiveconf._HiveFileParser.mount_directive")
    def test_parse_file_with_mount_directive(self, mock_mount_directive, mock_handle_section,
                                             mock_open, mock_folder):
        # Given
        url = "url"
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When
        result = parser.parse(url, mock_folder)

        # Then
        self.assertEqual(result, mock_folder)
        mock_mount_directive.assert_called_once_with(["arg1", "arg2"], mock_folder,
                                                     url, mock.ANY, "")

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open,
                read_data="%invalid_directive\n")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    @mock.patch("hiveconf._HiveFileParser.mount_directive")
    @mock.patch("sys.stderr", mock.MagicMock()) # Suppressing stderr prints
    def test_parse_file_with_invalid_directive(self, mock_mount_directive, mock_handle_section,
                                               mock_open, mock_folder):
        # Given
        url = "url"
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When
        result = parser.parse(url, mock_folder)

        # Then
        self.assertEqual(result, mock_folder)
        mock_mount_directive.assert_not_called()

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.Parameter", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open, read_data="name=xyz\n")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    @mock.patch("hiveconf._check_write_access", return_value=True)
    def test_parse_file_with_parameter_has_write_access(self, mock_c_w_a, mock_handle_section,
                                                        mock_open, mock_parameter, mock_folder):
        # Given
        url = "url"
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When
        result = parser.parse(url, mock_folder)

        # Then
        self.assertEqual(result, mock_folder)
        mock_parameter.assert_called_once_with("xyz", url, "", "name", url)

        parameter_arg = mock_folder._addobject.call_args_list[0][0][0]
        self.assertTrue(isinstance(parameter_arg, hiveconf.Parameter.__class__))
        mock_folder._addobject.assert_called_once_with(parameter_arg, "name")

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.Parameter", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open, read_data="ᾔαмℯ=✖⑂ℨ")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    @mock.patch("hiveconf._check_write_access", return_value=True)
    def test_parse_file_with_parameter_non_ascii(self, mock_c_w_a, mock_handle_section,
                                                 mock_open, mock_parameter, mock_folder):
        # Given
        url = "υґℓ"
        paramname = "ᾔαмℯ"
        paramvalue = "✖⑂ℨ"
        parser = hiveconf._HiveFileParser("parser_υґℓ", None)

        # When
        result = parser.parse(url, mock_folder)

        # Then
        self.assertEqual(result, mock_folder)
        mock_parameter.assert_called_once_with(paramvalue, url, "", paramname, url)

        parameter_arg = mock_folder._addobject.call_args_list[0][0][0]
        self.assertTrue(isinstance(parameter_arg, hiveconf.Parameter.__class__))
        mock_folder._addobject.assert_called_once_with(parameter_arg, paramname)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.Parameter", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open, read_data="name=xyz\n")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    @mock.patch("hiveconf._check_write_access", return_value=False)
    def test_parse_file_with_parameter_not_write_access(self, mock_c_w_a, mock_handle_section,
                                                        mock_open, mock_parameter, mock_folder):
        # Given
        url = "url"
        write_target = "w_target"
        mock_folder.write_target = write_target
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When
        result = parser.parse(url, mock_folder)

        # Then
        self.assertEqual(result, mock_folder)
        mock_parameter.assert_called_once_with("xyz", url, "", "name", write_target)

        parameter_arg = mock_folder._addobject.call_args_list[0][0][0]
        self.assertTrue(isinstance(parameter_arg, hiveconf.Parameter.__class__))
        mock_folder._addobject.assert_called_once_with(parameter_arg, "name")

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.Parameter", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open, read_data="name=xyz\n")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    @mock.patch("hiveconf._check_write_access", return_value=False)
    @mock.patch("sys.stderr")
    def test_parse_file_with_parameter_already_exists(self, mock_stderr, mock_c_w_a,
                                                      mock_handle_section, mock_open,
                                                      mock_parameter, mock_folder):
        """
        The parameter in the file already exists as a parameter of mock_folder.
        """
        # Given
        url = "url"
        write_target = "w_target"

        mock_folder.write_target = write_target
        mock_folder._addobject.side_effect = hiveconf.ObjectExistsError()
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When
        try:
            result = parser.parse(url, mock_folder)

        # Then
        except:
            self.fail("No exception should be thrown when adding an existing parameter.")

        self.assertEqual(result, mock_folder)
        mock_stderr.assert_not_called()

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open,
                read_data="invalid syntax\n# valid syntax\n")
    @mock.patch("hiveconf._HiveFileParser.handle_section")
    def test_parse_file_with_invalid_syntax(self, mock_handle_section, mock_open,
                                            mock_folder):
        # Given
        url = "url"
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When / Then
        with self.assertRaises(hiveconf.SyntaxError):
            parser.parse(url, mock_folder)

    @mock.patch("hiveconf.open", new_callable=mock.mock_open)
    def test_parse_file_with_incorrect_encoding(self, mock_open):
        """
        Hiveconf can call open() on a file which is not in UTF-8, but if the file
        contains non-ASCII characters a UnicodeDecodeError will be cast when calling
        readline() on the file.
        """
        # Given
        url = "url"
        mock_open.return_value.readline.side_effect = UnicodeDecodeError("", b"", 0, 0, "")
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When / Then
        with self.assertRaises(hiveconf.UnicodeError):
            parser.parse(url)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.open", new_callable=mock.mock_open)
    def test_parse_file_with_invalid_url(self, mock_open, mock_folder):
        # Given
        url = "https://url.se/home" # Hiveconf only supports local files
        parser = hiveconf._HiveFileParser("parser_url", None)

        # When
        parser.parse(url, mock_folder)

        # Then
        mock_open.assert_not_called()

    @mock.patch("hiveconf._HiveFileParser._parse_file")
    @mock.patch("hiveconf.open", new_callable=mock.mock_open)
    def test_parse_OSError(self, mock_open, mock_parse_file):
        # Given
        url = "url"
        mock_open.side_effect = OSError()
        parser = hiveconf._HiveFileParser(url, None)

        # When
        try:
            result = parser.parse()

        # Then
        except OSError:
            self.fail("Failed to catch OSError.")

        mock_open.return_value.readline.assert_not_called()


    @mock.patch("hiveconf.Folder", autospec=True)
    def test_handle_section_folder_contains_list(self, mock_folder):
        # Given
        source = "src"
        comps_path = "shortpath"
        parser = hiveconf._HiveFileParser("url", None)

        folder = mock.MagicMock(spec=hiveconf.Folder)
        folder.sources = []
        folder._update.side_effect = self.mock_folder__update(folder, source)
        rootfolder = mock_folder
        rootfolder._lookup_list.return_value = folder

        # When
        result = parser.handle_section(rootfolder, comps_path, source)

        # Then
        self.assertEqual(result, folder)

    @mock.patch("hiveconf.Folder", autospec=True)
    def test_handle_section_folder_contains_list_non_ascii(self, mock_folder):
        # Given
        source = "﹩ґḉ"
        comps_path = "shortρ@☂ℌ"
        parser = hiveconf._HiveFileParser("üґʟ", None)

        folder = mock.MagicMock(spec=hiveconf.Folder)
        folder.sources = []
        folder._update.side_effect = self.mock_folder__update(folder, source)
        rootfolder = mock_folder
        rootfolder._lookup_list.return_value = folder

        # When
        result = parser.handle_section(rootfolder, comps_path, source)

        # Then
        self.assertEqual(result, folder)

    @mock.patch("hiveconf.Folder", autospec=True)
    def test_handle_section_create_folders_obj_exists_short_path(self, mock_folder):
        """
        Handles the scenario where rootfolder does not contain a list, but contains
        an object. Comps path is 'short', i.e. does not contain any slashes.
        """
        # Given
        source = "src"
        comps_path = "shortpath"
        parser = hiveconf._HiveFileParser("url", None)

        folder = mock.MagicMock(spec = hiveconf.Folder)
        rootfolder = mock_folder
        rootfolder._lookup_list.return_value = None
        rootfolder._get_object.return_value = folder

        # When
        result = parser.handle_section(rootfolder, comps_path, source)

        # Then
        self.assertEqual(result, folder)

    def test_handle_section_create_folders_obj_exists_long_path(self):
        """
        Handles the scenario where rootfolder does not contain a list, but contains
        an object. Comps path is 'long', i.e. contains slashes.
        """
        # Given
        source = "src"
        comps_path = "bin/longerpath"
        parser = hiveconf._HiveFileParser("url", None)

        subfolder = mock.MagicMock(spec = hiveconf.Folder)
        folder = mock.MagicMock(spec = hiveconf.Folder)
        folder._get_object.return_value = subfolder

        rootfolder = mock.MagicMock(spec = hiveconf.Folder)
        rootfolder._lookup_list.return_value = None
        rootfolder._get_object.return_value = folder

        # When
        result = parser.handle_section(rootfolder, comps_path, source)

        # Then
        self.assertEqual(result, subfolder)

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder", autospec=True)
    def test_handle_section_create_folders_obj_not_exists_short_path_writable(self, mock_folder,
                                                                              mock__c_w_a):
        """
        Handles the scenario where rootfolder neither contains a list or an object.
        Comps path is 'short', i.e. does not contain any slashes, and we have
        write access at the provided source.
        """
        # Given
        source = "src"
        comps_path = "shortpath"
        parser = hiveconf._HiveFileParser("url", None)

        rootfolder = mock_folder
        rootfolder._lookup_list.return_value = None
        rootfolder._get_object.return_value = None
        rootfolder._folders = {}
        rootfolder._addobject.side_effect = self.mock__addobject(rootfolder, "obj", "objname")

        # When
        result = parser.handle_section(rootfolder, comps_path, source)

        # Then
        self.assertTrue(isinstance(result, hiveconf.Folder.__class__))
        self.assertEqual(len(rootfolder._folders), 1)
        mock_folder.assert_called_once_with(source, source, comps_path)

    @mock.patch("hiveconf._check_write_access", return_value=True)
    @mock.patch("hiveconf.Folder", autospec=True)
    def test_handle_section_create_folders_obj_not_exists_short_path_non_ascii(self, mock_folder,
                                                                               mock__c_w_a):
        """
        Handles the scenario where rootfolder neither contains a list or an object.
        Comps path is 'short', i.e. does not contain any slashes, and we have
        write access at the provided source. Input is non ASCII.
        """
        # Given
        source = "﹩я¢"
        comps_path = "short℘α☂♄"
        parser = hiveconf._HiveFileParser("üґʟ", None)

        rootfolder = mock_folder
        rootfolder._lookup_list.return_value = None
        rootfolder._get_object.return_value = None
        rootfolder._folders = {}
        rootfolder._addobject.side_effect = self.mock__addobject(rootfolder, "◎ßʝ", "◎ßʝname")

        # When
        result = parser.handle_section(rootfolder, comps_path, source)

        # Then
        self.assertTrue(isinstance(result, hiveconf.Folder.__class__))
        self.assertEqual(len(rootfolder._folders), 1)
        mock_folder.assert_called_once_with(source, source, comps_path)

    @mock.patch("hiveconf._check_write_access", return_value=False)
    def test_handle_section_create_folders_obj_not_exists_long_path_non_writable(self,
                                                                                 mock__c_w_a):
        """
        Handles the scenario where rootfolder neither contains a list or an object.
        Comps path is 'long', i.e. contains slashes, and we do not have write access
        at the provided source.
        """
        # Given
        self.FolderMockClass.calls = [] # Reset call list
        source = "src"
        write_target = "w_target"
        comps_path = "bin/longerpath"
        comps_path_list = comps_path.split("/")
        parser = hiveconf._HiveFileParser("url", None)

        rootfolder = mock.MagicMock()
        rootfolder._lookup_list.return_value = None
        rootfolder._get_object.return_value = None
        rootfolder.write_target = write_target
        rootfolder._folders = {}
        rootfolder._addobject.side_effect = self.mock__addobject(rootfolder, "obj", "longerpath")

        # When
        with mock.patch("hiveconf.Folder", self.FolderMockClass) as mock_folder:
            result = parser.handle_section(rootfolder, comps_path, source)

        # Then
        self.assertTrue(result._isFolderMockChild)
        self.assertEqual(len(rootfolder._folders), 1)
        self.assertEqual(self.FolderMockClass.calls, [mock.call(None, write_target, comps_path_list[0])])

    @mock.patch("hiveconf._check_write_access", return_value=False)
    def test_handle_section_create_folders_obj_not_exists_long_path_non_ascii(self, mock__c_w_a):
        """
        Handles the scenario where rootfolder neither contains a list or an object.
        Comps path is 'long', i.e. contains slashes, and we do not have write access
        at the provided source. Input is non ASCII.
        """
        # Given
        self.FolderMockClass.calls = [] # Reset call list
        source = "ṧґ¢"
        write_target = "ẘ_тαя❡ℯ☂"
        comps_path = "♭☤η/longerραт♄"
        comps_path_list = comps_path.split("/")
        parser = hiveconf._HiveFileParser("url", None)

        rootfolder = mock.MagicMock()
        rootfolder._lookup_list.return_value = None
        rootfolder._get_object.return_value = None
        rootfolder.write_target = write_target
        rootfolder._folders = {}
        rootfolder._addobject.side_effect = self.mock__addobject(rootfolder, "øßנ", "longerραт♄")

        # When
        with mock.patch("hiveconf.Folder", self.FolderMockClass) as mock_folder:
            result = parser.handle_section(rootfolder, comps_path, source)

        # Then
        self.assertTrue(result._isFolderMockChild)
        self.assertEqual(len(rootfolder._folders), 1)
        self.assertEqual(self.FolderMockClass.calls,
                         [mock.call(None, write_target, comps_path_list[0])])

    def test_handle_section_create_folders_ObjectExistsError(self):
        """
        Handles the scenario where rootfolder does not contain a list, but contains
        a string. However, since string is not a valid type, an error is thrown.
        """
        # Given
        source = "src"
        comps_path = "bin/longerpath"
        parser = hiveconf._HiveFileParser("url", None)

        rootfolder = mock.MagicMock(spec = hiveconf.Folder)
        rootfolder._lookup_list.return_value = None
        rootfolder._get_object.return_value = "str"

        # When / Then
        with self.assertRaises(hiveconf.ObjectExistsError):
            parser.handle_section(rootfolder, comps_path, source)


    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.urllib.parse.urljoin")
    @mock.patch("hiveconf._HiveFileParser.parse")
    @mock.patch("glob.glob")
    def test_mount_directive_hivefile_backend_valid_mnturl(self, mock_glob, mock_parse,
                                                           mock_urljoin, mock_folder):
        # Given
        file = "file.hconf"
        args = ["-a", "name=xyz", file]
        mnturl = "file://path/" + file
        parser = hiveconf._HiveFileParser("url", None)

        mock_urljoin.return_value = mnturl
        mock_glob.return_value = [file]

        # When
        result = parser.mount_directive(args, mock_folder, "url", 1, "sectionname")

        # Then
        mock_parse.assert_called_once_with("file://" + file, mock_folder)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.urllib.parse.urljoin")
    @mock.patch("hiveconf._HiveFileParser.parse")
    @mock.patch("glob.glob")
    def test_mount_directive_hivefile_backend_valid_mnturl_non_ascii(self, mock_glob,
                                                                     mock_parse, mock_urljoin,
                                                                     mock_folder):
        # Given
        file = "ḟḯℓ℮.hconf"
        args = ["-a", "η@me=✄¥ℨ", file]
        mnturl = "file://path/" + file
        parser = hiveconf._HiveFileParser("ʊґℓ", None)

        mock_urljoin.return_value = mnturl
        mock_glob.return_value = [file]

        # When
        result = parser.mount_directive(args, mock_folder, "ʊґℓ", 1, "ṧε¢tionname")

        # Then
        mock_parse.assert_called_once_with("file://" + file, mock_folder)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.urllib.parse.urljoin")
    @mock.patch("hiveconf._HiveFileParser.parse")
    @mock.patch("glob.glob")
    @mock.patch("os.path.samefile", return_value=True)
    def test_mount_directive_hivefile_backend_blacklisted_mnturl(self, mock_os_path_samefile,
                                                                 mock_glob, mock_parse,
                                                                 mock_urljoin, mock_folder):
        # Given
        file = "file.hconf"
        mnturl = "file://path/" + file
        args = ["-a", "name=xyz", file]
        parser = hiveconf._HiveFileParser("url", [file]) # blacklisting file

        mock_urljoin.return_value = mnturl
        mock_glob.return_value = [file]

        # When
        result = parser.mount_directive(args, mock_folder, "url", 1, "sectionname")

        # Then
        mock_os_path_samefile.assert_called_once_with(file, file)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.urllib.parse.urljoin")
    @mock.patch("hiveconf._HiveFileParser.parse")
    @mock.patch("glob.glob")
    @mock.patch("os.path.samefile", return_value=True)
    def test_mount_directive_hivefile_backend_blacklisted_mnturl_non_ascii(self, mock_os_path_samefile,
                                                                           mock_glob, mock_parse,
                                                                           mock_urljoin, mock_folder):
        # Given
        file = "ḟ☤ℓ℮.hconf"
        mnturl = "file://path/" + file
        args = ["-a", "naмℯ=x¥ẕ", file]
        parser = hiveconf._HiveFileParser("ʊяł", [file]) # blacklisting file

        mock_urljoin.return_value = mnturl
        mock_glob.return_value = [file]

        # When
        result = parser.mount_directive(args, mock_folder, "ʊяł", 1, "ṧ℮¢tionname")

        # Then
        mock_os_path_samefile.assert_called_once_with(file, file)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf._DebugWriter")
    @mock.patch("hiveconf.urllib.parse.urljoin")
    @mock.patch("hiveconf._HiveFileParser.parse")
    @mock.patch("glob.glob", return_value=None)
    @mock.patch("hiveconf.open")
    def test_mount_directive_hivefile_backend_could_not_create_mntpath(self, mock_open, mock_glob,
                                                                       mock_parse, mock_urljoin,
                                                                       mock_debugwriter, mock_folder):
        # Given
        file = "file.hconf"
        mnturl = "file://path/" + file
        args = ["-a", "name=xyz", file]
        parser = hiveconf._HiveFileParser("url", None)

        mock_urljoin.return_value = mnturl
        mock_open.side_effect = OSError()

        # When
        try:
            result = parser.mount_directive(args, mock_folder, "url", 1, "sectionname")

        # Then
        except OSError:
            self.fail("Failed to catch OSError when opening an invalid file path.")

        mock_parse.assert_not_called()


    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.Parameter", autospec=True)
    @mock.patch("hiveconf.urllib.parse.urljoin")
    @mock.patch("hiveconf.open", new_callable=mock.mock_open, read_data="value")
    def test_mount_directive_filesystem_backend_not_file_mnturl(self, mock_open, mock_urljoin,
                                                                mock_parameter, mock_folder):
        """
        Tests when mnturl does not start with 'file://'.
        """
        # Given
        mnturl = "path/file.hconf"
        paramname = "xyz"
        args = ["-a", "name=%s" % (paramname), "-t", "filesystem", "file"]
        parser = hiveconf._HiveFileParser("url", None)

        mock_urljoin.return_value = mnturl

        # When
        result = parser.mount_directive(args, mock_folder, "url", 1, "sectionname")

        # Then
        parameter_arg = mock_folder._addobject.call_args_list[0][0][0]
        self.assertTrue(isinstance(parameter_arg, hiveconf.Parameter.__class__))
        mock_folder._addobject.assert_called_once_with(parameter_arg, paramname)
        mock_parameter.assert_called_once_with("value", mnturl, "", paramname, mnturl)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.Parameter", autospec=True)
    @mock.patch("hiveconf.urllib.parse.urljoin")
    @mock.patch("hiveconf.open", new_callable=mock.mock_open,
                read_data="\xe2\x88\x9a\xce\xb1\xc5\x82\xcf\x85\xe2\x84\xaf")
    def test_mount_directive_filesystem_backend_nonfile_mnturl_non_ascii(self, mock_open, mock_urljoin,
                                                                         mock_parameter, mock_folder):
        """
        Tests when mnturl does not start with 'file://' for non ASCII values.
        """
        # Given
        mnturl = "℘αth/fiℓℯ.hconf" # mnturl does not contain 'file://'
        paramname = "✖yℨ"
        args = ["-a", "name=%s" % (paramname), "-t", "filesystem", "fiℓℯ"]
        parser = hiveconf._HiveFileParser("url", None)

        mock_urljoin.return_value = mnturl

        # When
        result = parser.mount_directive(args, mock_folder, "ʊяł", 1, "ṧ℮ḉtionname")

        # Then
        parameter_arg = mock_folder._addobject.call_args_list[0][0][0]
        self.assertTrue(isinstance(parameter_arg, hiveconf.Parameter.__class__))
        mock_folder._addobject.assert_called_once_with(parameter_arg, paramname)
        mock_parameter.assert_called_once_with("\xe2\x88\x9a\xce\xb1\xc5\x82\xcf\x85\xe2\x84\xaf",
                                               mnturl, "", paramname, mnturl)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.Parameter", autospec=True)
    @mock.patch("hiveconf.urllib.parse.urljoin")
    @mock.patch("hiveconf.open", new_callable=mock.mock_open, read_data="value")
    def test_mount_directive_filesystem_backend_invalid_arg_format(self, mock_open, mock_urljoin,
                                                                   mock_parameter, mock_folder):
        # Given
        mnturl = "path/file.hconf"
        paramname = "default"
        args = ["-a", "=invalid=argument=", "-t", "filesystem", "file"]
        parser = hiveconf._HiveFileParser("url", None)

        mock_urljoin.return_value = mnturl

        # When
        result = parser.mount_directive(args, mock_folder, "url", 1, "sectionname")

        # Then
        parameter_arg = mock_folder._addobject.call_args_list[0][0][0]
        self.assertTrue(isinstance(parameter_arg, hiveconf.Parameter.__class__))
        mock_folder._addobject.assert_called_once_with(parameter_arg, paramname)
        mock_parameter.assert_called_once_with("value", mnturl, "", paramname, mnturl)

    @mock.patch("hiveconf.Folder", autospec=True)
    @mock.patch("hiveconf.urllib.parse.urljoin")
    @mock.patch("glob.glob", return_value=None)
    @mock.patch("hiveconf.open")
    @mock.patch("hiveconf._HiveFileParser.parse")
    @mock.patch("hiveconf.Folder._addobject")
    @mock.patch("sys.stderr", mock.MagicMock()) # Suppressing stderr prints
    def test_mount_directive_invalid_backend(self, mock__addobject, mock_parse,
                                             mock_open, mock_glob, mock_urljoin,
                                             mock_folder):
        # Given
        mnturl = "file://path/file.hconf"
        args = ["-t", "invalid_backend", "file"]
        parser = hiveconf._HiveFileParser("url", None)

        mock_urljoin.return_value = mnturl

        # When
        result = parser.mount_directive(args, mock_folder, "url", 1, "sectionname")

        # Then
        mock__addobject.assert_not_called()
        mock_parse.assert_not_called()

    @mock.patch("getopt.getopt", side_effect = getopt.GetoptError(""))
    @mock.patch("hiveconf._HiveFileParser.parse")
    @mock.patch("hiveconf.Folder._addobject")
    @mock.patch("sys.stderr", mock.MagicMock()) # Suppressing stderr prints
    def test_mount_directive_GetoptError(self, mock__addobject, mock_parse, mock_getopt):
        # Given
        args = ["-invalid_flag"]
        parser = hiveconf._HiveFileParser("url", None)

        # When
        try:
            result = parser.mount_directive(args, "curfolder", "url", 1, "sectionname")

        # Then
        except getopt.GetoptError:
            self.fail("Failed to catch GetoptError.")

        mock_parse.assert_not_called()
        mock__addobject.assert_not_called()

    @mock.patch("getopt.getopt")
    @mock.patch("hiveconf._HiveFileParser.parse")
    @mock.patch("hiveconf.Folder._addobject")
    @mock.patch("sys.stderr", mock.MagicMock()) # Suppressing stderr prints
    def test_mount_directive_too_few_args(self, mock_parse, mock__addobject, mock_getopt):
        # Given
        args = []
        parser = hiveconf._HiveFileParser("url", None)
        mock_getopt.return_value = [[], args]

        # When
        result = parser.mount_directive(args, "curfolder", "url", 1, "sectionname")

        # Then
        mock_parse.assert_not_called()
        mock__addobject.assert_not_called()

    @mock.patch("getopt.getopt")
    @mock.patch("hiveconf._HiveFileParser.parse")
    @mock.patch("hiveconf.Folder._addobject")
    @mock.patch("sys.stderr", mock.MagicMock()) # Suppressing stderr prints
    def test_mount_directive_too_many_args(self, mock__addobject, mock_parse, mock_getopt):
        # Given
        args = ["file1", "file2"]
        parser = hiveconf._HiveFileParser("url", None)
        mock_getopt.return_value = [[], args]

        # When
        result = parser.mount_directive(args, "curfolder", "url", 1, "sectionname")

        # Then
        mock_parse.assert_not_called()
        mock__addobject.assert_not_called()


class HiveFileUpdaterTest(unittest.TestCase):
    test_filename = "test_file"

    def setUp(self):
        # Creates empty file if it doesnt exist
        self._clear_test_file("UTF-8")

    def tearDown(self):
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)


    # -- Help functions --
    def _clear_test_file(self, enc):
        with open(self.test_filename, "w", encoding=enc) as f:
            f.write("")

    def _set_up_test_file(self, content_list, enc):
        with open(self.test_filename, "a", encoding=enc) as f:
            for line in content_list:
                f.write(line + "\n")

    def _content_list_to_string(self, content_list):
        # Convert content list to format of file.read()
        output = ""
        for line in content_list:
            output = output + line + "\n"
        return output


    # -- Tests --
    def test_constructor_source_scheme_is_file(self):
        # Given
        filename = "/file.hconf"
        source = "file://path" + filename

        # When
        updater_obj = hiveconf._HiveFileUpdater(source)

        # Then
        self.assertTrue(isinstance(updater_obj, hiveconf._HiveFileUpdater))
        self.assertEqual(updater_obj.source, source)
        self.assertEqual(updater_obj.filename, filename)

    def test_constructor_source_scheme_is_file_non_ascii(self):
        # Given
        filename = "/ƒїl℮.hconf"
        source = "file://℘@тh" + filename

        # When
        updater_obj = hiveconf._HiveFileUpdater(source)

        # Then
        self.assertTrue(isinstance(updater_obj, hiveconf._HiveFileUpdater))
        self.assertEqual(updater_obj.source, source)
        self.assertEqual(updater_obj.filename, filename)

    def test_constructor_source_is_read_only(self):
        # Given
        filename = "/file.hconf"
        source = "path" + filename

        # When / Then
        with self.assertRaises(hiveconf.ReadOnlySource):
            hiveconf._HiveFileUpdater(source)


    def test_change_parameter_set_new_value(self):
        # Given
        encoding = "UTF-8"
        sectionname = "section_1"
        paramname = "name"
        new_value = "xyz"
        content_list = ["[%s]" % (sectionname),
                        "%s=a" % paramname,
                        "rest of file"]
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")

        self._clear_test_file(encoding)
        self._set_up_test_file(content_list, encoding)
        updater_obj.filename = self.test_filename

        updated_content_list = ["[%s]" % (sectionname),
                                "%s=%s" % (paramname, new_value),
                                "rest of file"]
        updated_content = self._content_list_to_string(updated_content_list)

        # When
        updater_obj.change_parameter(sectionname, paramname, new_value)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, updated_content)

    def test_change_parameter_set_new_value_non_ascii(self):
        # Given
        encoding = "UTF-8"
        sectionname = "sêctioŋ_↓µ"
        paramname = "ᾔaღe"
        new_value = "✖¥ẕ"
        content_list = ["[%s]" % (sectionname),
                        "%s=a" % paramname,
                        "rest of ƒїl℮"]
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")
        updater_obj.filename = self.test_filename

        expected_content_list = ["[%s]" % (sectionname),
                                 "%s=%s" % (paramname, new_value),
                                 "rest of ƒїl℮"]
        expected_content = self._content_list_to_string(expected_content_list)

        self._clear_test_file(encoding)
        self._set_up_test_file(content_list, encoding)

        # When
        updater_obj.change_parameter(sectionname, paramname, new_value)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, expected_content)

    def test_change_parameter_delete_parameter(self):
        # Given
        encoding = "UTF-8"
        sectionname = "section_1"
        paramname = "name"
        content_list = ["[%s]" % (sectionname),
                        "%s=a" % paramname,
                        "rest of file"]
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")

        self._clear_test_file(encoding)
        self._set_up_test_file(content_list, encoding)
        updater_obj.filename = self.test_filename

        updated_content_list = ["[%s]" % (sectionname),
                                "rest of file"]
        updated_content = self._content_list_to_string(updated_content_list)

        # When
        updater_obj.change_parameter(sectionname, paramname, "value", delete_param=1)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, updated_content)

    def test_change_parameter_new_parameter_section_exists(self):
        # Given
        encoding = "UTF-8"
        sectionname = "section_1"
        paramname = "name"
        paramvalue = "xyz"
        content_list = ["[%s]" % (sectionname),
                        "rest of file"]
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")

        self._clear_test_file(encoding)
        self._set_up_test_file(content_list, encoding)
        updater_obj.filename = self.test_filename

        updated_content_list = ["[%s]" % (sectionname),
                                "%s=%s" % (paramname, paramvalue),
                                "rest of file"]
        updated_content = self._content_list_to_string(updated_content_list)

        # When
        updater_obj.change_parameter(sectionname, paramname, paramvalue, new_param=1)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, updated_content)

    def test_change_parameter_new_parameter_no_section_name(self):
        # Given
        encoding = "UTF-8"
        sectionname = ""
        paramname = "name"
        paramvalue = "xyz"
        content_list = ["rest of file"]
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")

        self._clear_test_file(encoding)
        self._set_up_test_file(content_list, encoding)
        updater_obj.filename = self.test_filename

        updated_content_list = ["%s=%s" % (paramname, paramvalue),
                                "rest of file"]
        updated_content = self._content_list_to_string(updated_content_list)

        # When
        updater_obj.change_parameter(sectionname, paramname, paramvalue, new_param=1)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, updated_content)

    def test_change_parameter_new_parameter_section_not_found(self):
        # Given
        encoding = "UTF-8"
        sectionname = "section_1"
        paramname = "name"
        paramvalue = "xyz"
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")

        self._clear_test_file(encoding)
        updater_obj.filename = self.test_filename

        # When
        updater_obj.change_parameter(sectionname, paramname, paramvalue, new_param=1)

        # Then
        expected_content = "\n[%s]\n%s=%s" % (sectionname, paramname, paramvalue) + "\n"
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, expected_content)

    @mock.patch("hiveconf._HiveFileUpdater.add_section")
    def test_change_parameter_NoSuchParameterError(self, mock_add_section):
        # Given
        encoding = "UTF-8"
        sectionname = "section_1"
        paramname = "name"
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")

        self._clear_test_file(encoding) # Empty file
        updater_obj.filename = self.test_filename

        # When / Then
        with self.assertRaises(hiveconf.NoSuchParameterError):
            updater_obj.change_parameter(sectionname, paramname, "value")

        mock_add_section.assert_not_called()


    @mock.patch("hiveconf._HiveFileUpdater.change_parameter")
    def test_add_parameter(self, mock_change_parameter):
        # Given
        sectionname = "sec_name"
        paramname = "name"
        value = "xyz"
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")

        # When
        updater_obj.add_parameter(sectionname, paramname, value)

        # Then
        mock_change_parameter.assert_called_once_with(sectionname, paramname,
                                                      value, new_param=1)

    @mock.patch("hiveconf._HiveFileUpdater.change_parameter")
    def test_add_parameter_non_ascii(self, mock_change_parameter):
        # Given
        sectionname = "ṧ℮¢_name"
        paramname = "ηαღ℮"
        value = "✖¥ℨ"
        updater_obj = hiveconf._HiveFileUpdater("file://pa☂н/ḟ☤łε.hconf")

        # When
        updater_obj.add_parameter(sectionname, paramname, value)

        # Then
        mock_change_parameter.assert_called_once_with(sectionname, paramname,
                                                      value, new_param=1)


    def test_delete_section_file_contains_section(self):
        # FIXME: This test is disabled since delete_section() is broken,
        #        see https://www.cendio.com/bugzilla/show_bug.cgi?id=6122
        # The test below is written according to this broken behaviour.
        self.skipTest("delete_section is broken.")

        # Given
        encoding = "UTF-8"
        sectionname = "section_1"
        content_list = ["[%s]" % (sectionname), "section content", "rest of file"]
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")
        updater_obj.filename = self.test_filename

        expected_content_list = ["rest of file"]
        expected_content = self._content_list_to_string(expected_content_list)

        self._clear_test_file(encoding)
        self._set_up_test_file(content_list, encoding)

        # When
        updater_obj.delete_section(sectionname)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, expected_content)

    def test_delete_section_file_contains_section_non_ascii(self):
        # FIXME: This test is disabled since delete_section() is broken,
        #        see https://www.cendio.com/bugzilla/show_bug.cgi?id=6122
        # The test below is written according to this broken behaviour.
        self.skipTest("delete_section is broken.")

        # Given
        encoding = "UTF-8"
        sectionname = "secti☺η_←æ"
        content_list = ["[%s]" % (sectionname), "sectiøn日cöntent", "rëst of ḟḯʟℯ"]
        updater_obj = hiveconf._HiveFileUpdater("file://path//食パン.hconf")
        updater_obj.filename = self.test_filename

        expected_content_list = ["rëst of ḟḯʟℯ"]
        expected_content = self._content_list_to_string(expected_content_list)

        self._clear_test_file(encoding)
        self._set_up_test_file(content_list, encoding)

        # When
        updater_obj.delete_section(sectionname)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, expected_content)

    def test_delete_section_file_with_lines_to_skip(self):
        # FIXME: This test is disabled since delete_section() is broken,
        #        see https://www.cendio.com/bugzilla/show_bug.cgi?id=6122
        # The test below is written according to this broken behaviour.
        self.skipTest("delete_section is broken.")

        # Given
        encoding = "UTF-8"
        sectionname = "section_1"
        content_list = ["# line 1", "; line 2", "  ", "[%s]" % (sectionname), "remove", "rest of file"]
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")
        updater_obj.filename = self.test_filename

        expected_content_list = ["# line 1", "; line 2", "  ", "rest of file"]
        expected_content = self._content_list_to_string(expected_content_list)

        self._clear_test_file(encoding)
        self._set_up_test_file(content_list, encoding)

        # When
        updater_obj.delete_section(sectionname)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, expected_content)

    def test_delete_section_file_with_invalid_section(self):
        # FIXME: This test is disabled since delete_section() is broken,
        #        see https://www.cendio.com/bugzilla/show_bug.cgi?id=6122
        # The test below is written according to this broken behaviour.
        self.skipTest("delete_section is broken.")

        # Given
        encoding = "UTF-8"
        sectionname = "section_1"
        content_list = ["[missing_end_bracket",
                        "[%s]" % (sectionname),
                        "this line is removed",
                        "this is not removed"]
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")
        updater_obj.filename = self.test_filename

        # This is how it works... yep.
        expected_content_list = ["[missing_end_bracket", "this is not removed"]
        expected_content = self._content_list_to_string(expected_content_list)

        self._clear_test_file(encoding)
        self._set_up_test_file(content_list, encoding)

        # When
        updater_obj.delete_section(sectionname)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, expected_content)


    def test_add_section(self):
        # Given
        encoding = "UTF-8"
        sectionname = "sec_name"
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")

        self._clear_test_file(encoding)
        updater_obj.filename = self.test_filename

        # When
        updater_obj.add_section(sectionname)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, "\n[%s]\n" % (sectionname))

    def test_add_section_non_ascii(self):
        # Given
        encoding = "UTF-8"
        sectionname = "$ε¢_ᾔαme"
        updater_obj = hiveconf._HiveFileUpdater("file://path/file.hconf")
        updater_obj.filename = self.test_filename

        self._clear_test_file(encoding)

        # When
        updater_obj.add_section(sectionname)

        # Then
        with open(self.test_filename, "r", encoding=encoding) as file:
            file_content = file.read()
            self.assertEqual(file_content, "\n[%s]\n" % (sectionname))

class HiveconfIntegrationTest(unittest.TestCase):
    test_top_filename = "top.hconf"
    test_mounted_filename = "mounted.hconf"
    test_latin1_filename = "latin1.hconf"

    def setUp(self):
        # Creates empty file if it doesnt exist
        with open(self.test_top_filename, "w", encoding="UTF-8") as f:
            f.write("%mount mounted.hconf\n")

        with open(self.test_mounted_filename, "w", encoding="UTF-8") as f:
            f.write("[/sub2]\n")
            f.write("int1 = 3\n")

    def tearDown(self):
        if os.path.exists(self.test_top_filename):
            os.remove(self.test_top_filename)
        if os.path.exists(self.test_mounted_filename):
            os.remove(self.test_mounted_filename)
        if os.path.exists(self.test_latin1_filename):
            os.remove(self.test_latin1_filename)

    @mock.patch("hiveconf.print", mock.MagicMock()) # Suppressing stdout prints
    def test_root(self):
        """Tests parameters that are in the hive root"""
        # When
        self.hive = hiveconf.open_hive(self.test_top_filename)
        self.hive.set_integer("/int2", 5)
        # Then
        r = self.hive.get_integer("/int2")
        self.assertEqual(r, 5)

    def test_mount(self):
        """Tests parameters that are mounted through a %mount command"""
        self.hive = hiveconf.open_hive(self.test_top_filename)
        self.assertEqual(self.hive.get_integer("/sub2/int1"), 3)


if "__main__" == __name__:
    unittest.main()
