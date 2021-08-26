#!/usr/bin/python3
# -*-Python-*-

import os
import sys
import locale
import unittest

from unittest.mock import MagicMock, patch, ANY, call

def get_origin_dir():
    """Get program origin directory"""
    return os.path.dirname(os.path.realpath(__file__))

# Import what is needed from hiveconf before mocking it
hiveconfdir = os.path.realpath(os.path.join(get_origin_dir(), "../"))
sys.path.append(hiveconfdir)
from hiveconf import NotAParameterError

fakemods = [
    "hiveconf",
]

# Insert fake modules in the module hierarchy
sys.modules.update({ m: MagicMock(name=m) for m in fakemods if m not in sys.modules })
_mp = [ m.rsplit(".", 1) for m in fakemods if "." in m ]
[ __import__(p) for (p,m) in _mp if p not in fakemods ]
[ setattr(sys.modules[p], m, sys.modules["%s.%s" % (p,m)]) for (p, m) in
    _mp if not hasattr(sys.modules[p], m) ]

from importlib.machinery import SourceFileLoader
import importlib.util

script_path = os.path.join(get_origin_dir(), "..", "hivetool")
loader = SourceFileLoader("hivetool", script_path)
spec = importlib.util.spec_from_loader("hivetool", loader)
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)
sys.modules["hivetool"] = script

# FIXME: Add additional tests covering the missing parts.
# The current tests cover flags -i, -p, -?, -Ra and invalid flags, as
# well as setting a new parameter and updating a parameter value.

def script_main(*args):
    try:
        with patch("sys.argv", [ script_path ] + list(args)):
            script.main()
    except SystemExit as e:
        return e.code
    return 0

@patch("hiveconf.open_hive")
class ParameterTest(unittest.TestCase):
    @patch("hivetool.print")
    def test_handle_param_set_new_param(self, _print, hive):
        # Given
        hive().get_integer.return_value = None
        hive().set_integer.return_value = 1

        # When
        return_code = script_main("integer:/a=3")

        # Then
        self.assertEqual(return_code, 0)
        hive().set_integer.assert_called_once_with("/a", "3")
        _print.assert_called_once()
        self.assertIn("Created new", _print.call_args_list[0][0][0],
                      "Called incorrect print in handle_param()")

    @patch("hivetool.print")
    def test_handle_param_set_new_param_default_type(self, _print, hive):
        # Given
        mock_get = getattr(hive(), "get_%s" % script.DEFAULT_TYPE)
        mock_set = getattr(hive(), "set_%s" % script.DEFAULT_TYPE)
        mock_get.return_value = None
        mock_set.set_string.return_value = 1

        # When
        return_code = script_main("/a=3")

        # Then
        self.assertEqual(return_code, 0)
        hive().set_string.assert_called_once_with("/a", "3")
        _print.assert_called_once()
        self.assertIn("Created new", _print.call_args_list[0][0][0],
                      "Called incorrect print in handle_param()")

    @patch("hivetool.print")
    def test_handle_param_set_new_param_error(self, _print, hive):
        # Given
        hive().get_integer.return_value = None
        hive().set_integer.return_value = 0

        # When
        return_code = script_main("integer:/a=3")

        # Then
        self.assertEqual(return_code, 1)
        hive().set_integer.assert_called_once_with("/a", "3")
        _print.assert_called_once_with(ANY, ANY, file=sys.stderr)
        self.assertIn("Failed to set", _print.call_args_list[0][0][0],
                      "Called incorrect print in handle_param()")

    @patch("hivetool.print")
    def test_handle_param_update_param(self, _print, hive):
        # Given
        hive().get_integer.return_value = 4
        hive().set_integer.return_value = 1

        # When
        return_code = script_main("integer:/a=3")

        # Then
        self.assertEqual(return_code, 0)
        hive().set_integer.assert_called_once_with("/a", "3")
        _print.assert_not_called()

    @patch("hivetool.print")
    def test_handle_param_display_param(self, _print, hive):
        # Given
        hive().get_integer.return_value = 42

        # When
        return_code = script_main("integer:/a")

        # Then
        self.assertEqual(return_code, 0)
        _print.assert_called_once_with(42)

    @patch("hivetool.print")
    def test_handle_param_display_param_default_type(self, _print, hive):
        # Given
        mock_get = getattr(hive(), "get_%s" % script.DEFAULT_TYPE)
        mock_get.return_value = "42"

        # When
        return_code = script_main("/a")

        # Then
        self.assertEqual(return_code, 0)
        _print.assert_called_once_with("42")

    @patch("hivetool.print")
    def test_handle_param_display_param_error_NotAParameterError(self, _print, hive):
        # Given
        hive().get_integer.side_effect = NotAParameterError()

        # When
        return_code = script_main("integer:/a")

        # Then
        self.assertEqual(return_code, 1)
        _print.assert_called_once_with(ANY, file=sys.stderr)
        self.assertIn("No such parameter", _print.call_args_list[0][0][0],
                      "Called incorrect print in handle_param()")

    @patch("hivetool.print")
    def test_handle_param_display_param_error_no_such_param(self, _print, hive):
        # Given
        hive().get_integer.return_value = None

        # When
        return_code = script_main("integer:/a")

        # Then
        self.assertEqual(return_code, 1)
        _print.assert_called_once_with(ANY, file=sys.stderr)
        self.assertIn("No such parameter", _print.call_args_list[0][0][0],
                      "Called incorrect print in handle_param()")

    @patch("sys.stdout")
    @patch("hivetool.print")
    def test_handle_param_display_param_unprintable(self, _print, stdout, hive):
        # Given
        mock_get = getattr(hive(), "get_%s" % script.DEFAULT_TYPE)
        mock_get.return_value = "привет"
        stdout.encoding = "latin-1"

        # When
        return_code = script_main("/a")

        # Then
        self.assertEqual(return_code, 0)
        _print.assert_called_once_with("??????")

class WalkTest(unittest.TestCase):
    def reset_purge_params(self):
        # Reset purge_params in case other tests modified it
        script.purge_params = []

    def get_args_str(self, call_args_list):
        args_list = [x[0][0] for x in call_args_list]
        return "".join(args_list)

    @patch("hiveconf.open_hive")
    def test_purge_walk_param_on_toplevel(self, hive):
        # Given
        self.reset_purge_params()
        hive_purge = MagicMock()
        hive_reduced = MagicMock()
        def _open_hive(file, blacklist=None):
            if "purge_file" in file:
                return hive_purge
            else:
                return hive_reduced

        hive_purge.get_parameters.return_value = ["p1", "p2"]
        hive_reduced.lookup.side_effect = [None, MagicMock()]
        hive.side_effect = _open_hive

        # When
        return_code = script_main("-p", "purge_file")

        # Then
        self.assertEqual(return_code, 0)
        # Hiveconf handles the double slashes with _path2comps()
        hive_purge.delete.assert_called_once_with("//p2")
        hive_purge.get_parameters.assert_called_once_with("/")
        self.assertEqual(hive_reduced.lookup.call_args_list,
                         [ call("//p1"), call("//p2") ])

    @patch("hiveconf.open_hive")
    def test_purge_walk_param_in_folder(self, hive):
        # Given
        self.reset_purge_params()
        hive_purge = MagicMock()
        def _open_hive(file, blacklist=None):
            if "purge_file" in file:
                return hive_purge
            else:
                return hive

        hive_purge.get_parameters.side_effect = [[], ["p1", "p2"]]
        hive_purge.get_folders.side_effect = [["f1"], []]
        hive.lookup.side_effect = [None, MagicMock()]
        hive.side_effect = _open_hive

        # When
        return_code = script_main("-p", "purge_file")

        # Then
        self.assertEqual(return_code, 0)
        hive_purge.delete.assert_called_once_with("/f1/p2")
        self.assertEqual(hive_purge.get_parameters.call_args_list,
                         [ call("/"), call("/f1") ])
        self.assertEqual(hive_purge.get_folders.call_args_list,
                         [ call("/"), call("/f1") ])
        self.assertEqual(hive.lookup.call_args_list,
                         [ call("/f1/p1"), call("/f1/p2") ])

    @patch("hiveconf.open_hive")
    def test_imp_walk_param_on_toplevel(self, hive):
        # Given
        hive_import = MagicMock()
        def _open_hive(file):
            if "import_file" in file:
                return hive_import
            else:
                return hive

        hive_import.get_string.return_value = "v1"
        hive_import.get_parameters.return_value = ["p1"]
        hive_import.get_folders.return_value = []
        hive.side_effect = _open_hive

        # When
        return_code = script_main("-i", "import_file")

        # Then
        self.assertEqual(return_code, 0)
        # Hiveconf handles the double slashes with _path2comps()
        hive.set_string.assert_called_once_with("//p1", "v1")
        hive_import.get_string.assert_called_once_with("//p1")
        hive_import.get_parameters.assert_called_once_with("/")
        hive_import.get_folders.assert_called_once_with("/")

    @patch("hiveconf.open_hive")
    def test_imp_walk_param_in_folder(self, hive):
        # Given
        hive_import = MagicMock()
        def _open_hive(file):
            if "import_file" in file:
                return hive_import
            else:
                return hive

        hive_import.get_string.return_value = "v1"
        hive_import.get_parameters.side_effect = [[], ["p1"]]
        hive_import.get_folders.side_effect = [["f1"], []]
        hive.side_effect = _open_hive

        # When
        return_code = script_main("-i", "import_file")

        # Then
        self.assertEqual(return_code, 0)
        hive.set_string.assert_called_once_with("/f1/p1", "v1")
        hive_import.get_string.assert_called_once_with("/f1/p1")
        self.assertEqual(hive_import.get_parameters.call_args_list,
                         [ call("/"), call("/f1") ])
        self.assertEqual(hive_import.get_folders.call_args_list,
                         [ call("/"), call("/f1") ])

    @patch("hiveconf.open_hive")
    @patch("sys.stdout.write")
    # Our mocked folder's class need to match hiveconf.Folder
    @patch("hiveconf.Folder", MagicMock)
    def test_print_walk(self, write, open_hive):
        # Given
        hive = open_hive.return_value
        hive.get_string.return_value = "yay"
        hive.get_parameters.return_value = ["p"]
        hive.get_folders.return_value = []
        hive.lookup.side_effect = lambda p: MagicMock(sectionname=p.rstrip("/"))

        # When
        return_code = script_main("-a", "/")

        # Then
        write_args_str = self.get_args_str(write.call_args_list)
        self.assertEqual(write_args_str, "p = yay\n")
        hive.get_parameters.assert_called_once_with("/")
        hive.get_folders.assert_called_once_with("/")
        hive.get_string.assert_called_once_with("//p")

    @patch("hiveconf.open_hive")
    @patch("sys.stdout.write")
    # Our mocked folder's class need to match hiveconf.Folder
    @patch("hiveconf.Folder", MagicMock)
    def test_print_walk_recursive(self, write, open_hive):
        # Given
        hive = open_hive.return_value
        hive.get_string.return_value = "hurray"
        hive.get_parameters.side_effect = [[], ["p"]]
        hive.get_folders.side_effect = [["f2"], []]
        hive.lookup.side_effect = lambda p: MagicMock(sectionname=p.rstrip("/"))

        # When
        return_code = script_main("-Ra", "/")

        # Then
        write_args_str = self.get_args_str(write.call_args_list)
        self.assertEqual(write_args_str, "f2/\n    p = hurray\n")
        hive.get_string.assert_called_once_with("/f2/p")
        self.assertEqual(hive.get_parameters.call_args_list,
                         [ call("/"), call("/f2") ])
        self.assertEqual(hive.get_folders.call_args_list,
                         [ call("/"), call("/f2") ])

    @patch("hiveconf.open_hive")
    @patch("sys.stdout.write")
    # Our mocked folder's class need to match hiveconf.Folder
    @patch("hiveconf.Folder", MagicMock)
    def test_print_walk_ignore_slash_subfolders(self, write, open_hive):
        # Given
        hive = open_hive.return_value
        hive.get_parameters.return_value = []
        hive.get_folders.return_value = ["/"]
        hive.lookup.side_effect = lambda p: MagicMock(sectionname=p.rstrip("/"))

        # When
        return_code = script_main("-Ra", "/")

        # Then
        write.assert_not_called()

    @patch("hiveconf.open_hive")
    @patch("sys.stdout")
    # Our mocked folder's class need to match hiveconf.Folder
    @patch("hiveconf.Folder", MagicMock)
    def test_print_walk_unprintable_value(self, stdout, open_hive):
        # Given
        hive = open_hive.return_value
        hive.get_string.return_value = "привет"
        hive.get_parameters.return_value = ["p"]
        hive.get_folders.return_value = []
        hive.lookup.side_effect = lambda p: MagicMock(sectionname=p.rstrip("/"))
        stdout.encoding = "latin-1"

        # When
        return_code = script_main("-a", "/")

        # Then
        write_args_str = self.get_args_str(stdout.write.call_args_list)
        self.assertEqual(write_args_str, "p = ??????\n")
        hive.get_parameters.assert_called_once_with("/")
        hive.get_folders.assert_called_once_with("/")
        hive.get_string.assert_called_once_with("//p")

    @patch("hiveconf.open_hive")
    @patch("sys.stdout")
    # Our mocked folder's class need to match hiveconf.Folder
    @patch("hiveconf.Folder", MagicMock)
    def test_print_walk_unprintable_parameter(self, stdout, open_hive):
        # Given
        hive = open_hive.return_value
        hive.get_string.return_value = "hurray"
        hive.get_parameters.return_value = ["привет"]
        hive.get_folders.return_value = []
        hive.lookup.side_effect = lambda p: MagicMock(sectionname=p.rstrip("/"))
        stdout.encoding = "latin-1"

        # When
        return_code = script_main("-a", "/")

        # Then
        write_args_str = self.get_args_str(stdout.write.call_args_list)
        self.assertEqual(write_args_str, "?????? = hurray\n")
        hive.get_parameters.assert_called_once_with("/")
        hive.get_folders.assert_called_once_with("/")
        hive.get_string.assert_called_once_with("//привет")

    @patch("hiveconf.open_hive")
    @patch("sys.stdout")
    # Our mocked folder's class need to match hiveconf.Folder
    @patch("hiveconf.Folder", MagicMock)
    def test_print_walk_unprintable_folder(self, stdout, open_hive):
        # Given
        hive = open_hive.return_value
        hive.get_string.return_value = "hurray"
        hive.get_parameters.side_effect = [[], ["p"]]
        hive.get_folders.side_effect = [["привет"], []]
        hive.lookup.side_effect = lambda p: MagicMock(sectionname=p.rstrip("/"))
        stdout.encoding = "latin-1"

        # When
        return_code = script_main("-Ra", "/")

        # Then
        write_args_str = self.get_args_str(stdout.write.call_args_list)
        self.assertEqual(write_args_str, "??????/\n    p = hurray\n")
        hive.get_string.assert_called_once_with("/привет/p")
        self.assertEqual(hive.get_parameters.call_args_list,
                         [ call("/"), call("/привет") ])
        self.assertEqual(hive.get_folders.call_args_list,
                         [ call("/"), call("/привет") ])


class MainTest(unittest.TestCase):
    @patch("hivetool.print")
    def test_main_help_flag(self, _print):
        # When
        return_code = script_main("-?")

        # Then
        self.assertEqual(return_code, 0)
        _print.assert_called_once_with(ANY, file=sys.stderr)

    @patch("hivetool.print")
    def test_main_invalid_flag(self, _print):
        # When
        return_code = script_main("--invalid")

        # Then
        self.assertEqual(return_code, 2)
        _print.assert_called_once_with(ANY, file=sys.stderr)


if "__main__" == __name__:
    unittest.main()
