#
# Hiveconf configuration framework
#
# Copyright (C) 2003 Peter Astrand <peter@cendio.se>
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# as published by the Free Software Foundation; version 2.1
# of the License. 
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free
# Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# 02111-1307 USA

# -- API --
# The public API of this file is open_hive() which, in turn, gives
# a Folder. That means all non underscored Folder functions should
# be considered public.
# Folder.lookup() can return a Parameter. That means all non
# underscored Parameter functions should also be considered public.
# ---------

import sys
import os
import string
import glob
import getopt
import re
import urllib.parse
import binascii

class _DebugWriter:
    def __init__(self, debug):
        self.debug = debug
    
    def write(self, data):
        if self.debug:
            sys.stderr.write(data)

debugw = _DebugWriter(debug=0)


class _IndentPrinter:
    def __init__(self):
        self.indent = 0
        self.line_indented = 0

    def write(self, data):
        if self.indent and not self.line_indented:
            sys.stdout.write(" " * self.indent)
            self.line_indented = 1
        sys.stdout.write(data)
        if data.find("\n") != -1:
            self.line_indented = 0

    def change(self, val):
        self.indent += val
        

class Error(Exception): pass
class NoSuchParameterError(Error): pass
class NoSuchFolderError(Error): pass
class NoSuchObjectError(Error): pass
class ObjectExistsError(Error): pass
class InvalidObjectError(Error): pass
class NotAParameterError(Error): pass
class BadBoolFormat(Error): pass
class BadIntegerFormat(Error): pass
class BadFloatFormat(Error): pass
class BadBinaryFormat(Error): pass
class BadListFormat(Error): pass
class ReadOnlySource(Error): pass
class FolderNotEmpty(Error): pass
    
class SyntaxError(Error):
    def __init__(self, url, linenum):
        self.url = url
        self.linenum = linenum

    def __str__(self):
        return "Bad line %d in %s" % (self.linenum, self.url)

class UnicodeError(Error):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message

#
# Utility functions
#

def _path2comps(path):
    # Special case: root folder
    if path == "/":
        return ["/"]

    # Remove first slash
    if path.startswith("/"):
        path = path[1:]
    
    # Remove last slash
    if path.endswith("/"):
        path = path[:-1]
    
    return path.split("/")

def _comps2path(comps):
    result = ""
    for component in comps:
        result += "/" + component
    return result

def _get_cwd_url():
    """Get current working directory in URL format"""
    return "file://" + os.getcwd() + "/"

def _get_url_scheme(url):
    """Get URL scheme"""
    return urllib.parse.urlsplit(url)[0]

def _get_url_path(url):
    """Get URL path component"""
    return urllib.parse.urlsplit(url)[2]

def _fixup_sectionname(sn):
    """Add leading slash, remove trailing slash, if necessary"""
    if not sn.startswith("/"):
        sn = "/" + sn
    if sn.endswith("/"):
        sn = sn[:-1]
    return sn

def _check_write_access(url):
    if _get_url_scheme(url) == "file":
        path = _get_url_path(url)
        return os.access(path, os.W_OK)
    else:
        # Cannot write to other URLs, currently
        return 0

_glob_magic_check = re.compile('[*?[]')
def _has_glob_wildchars(s):
    return _glob_magic_check.search(s) is not None
    

#
# End of utility functions
#

class NamespaceObject:
    pass


class Parameter(NamespaceObject):
    def __init__(self, value, source, sectionname, paramname, write_target):
        # This parameters value, in the external string representation
        self._value = value
        # URL that this parameter was read from
        if not source:
            raise Error("Empty source file!")
        self.source = source
        self.sectionname = sectionname
        # FIXME: The class probably shouldn't know about it's own name.
        self.paramname = paramname
        self.write_target = write_target

    def __repr__(self):
        return "<Parameter: %s  value=%s  section=%s  source=%s  write_target=%s>" \
               % (self.paramname, self._value, self.sectionname, self.source,
                  self.write_target)

    def write_new(self):
        """Add a new parameter to the backend"""
        if not self.write_target:
            print("write_new(%s): no write_target" % self.paramname, file=debugw)
            return 0
        
        hfu = _HiveFileUpdater(self.write_target)
        hfu.add_parameter(self.sectionname, self.paramname, self._value)
        return 1

    def write_update(self, delete=0):
        """Change the value of a existing parameter in the backend"""
        if not self.write_target:
            print("write_update(%s): no write_target" % self.paramname, file=debugw)
            return 0
        
        if self.source != self.write_target:
            # If we should write to another file than the parameter
            # was read from, we should add, not change
            return self.write_new()
        else:
            hfu = _HiveFileUpdater(self.write_target)
            hfu.change_parameter(self.sectionname, self.paramname,
                                 self._value, delete_param=delete)

        return 1

    #
    # Primitive data types, get operations
    #
    def get_string(self):
        """Get value as string"""
        return self._value

    def get_bool(self):
        """Get boolean value"""
        try:
            return self._string2bool(self._value)
        except ValueError:
            raise BadBoolFormat()
    
    def get_integer(self):
        """Get integer value"""
        try:
            return int(self._value)
        except ValueError:
            raise BadIntegerFormat()

    def get_float(self):
        """Get float value"""
        try:
            return float(self._value)
        except ValueError:
            raise BadFloatFormat()

    def get_binary(self):
        """Get binary value"""
        try:
            return self._hexascii2bytes(self._value)
        except ValueError:
            raise BadBinaryFormat()

    #
    # Compound data types, get operations
    #
    def get_string_list(self):
        return self._value.split()

    def get_bool_list(self):
        return list(map(self._string2bool, self._value.split()))

    def get_integer_list(self):
        return list(map(int, self._value.split()))

    def get_float_list(self):
        return list(map(float, self._value.split()))

    def get_binary_list(self):
        return list(map(self._hexascii2bytes, self._value.split()))

    #
    # Primitive data types, set operations
    #
    def set_string(self, new_value):
        """Set string value"""
        self._value = new_value

    def set_bool(self, new_value):
        """Set bool value"""
        self._value = self._bool2string(new_value)

    def set_integer(self, new_value):
        """Set integer value"""
        self._value = str(new_value)

    def set_float(self, new_value):
        """Set float value"""
        self._value = str(new_value)

    def set_binary(self, new_value):
        """Set binary value"""
        self._value = self._bytes2hexascii(new_value)

    #
    # Compound data types, set operations
    #
    def set_string_list(self, new_value):
        """Set string list value"""
        self._value = " ".join(new_value)
    
    def set_bool_list(self, new_value):
        """Set bool list value"""
        self._value = " ".join(map(self._bool2string, new_value))

    def set_integer_list(self, new_value):
        """Set integer list value"""
        self._value = " ".join(map(str, new_value))

    def set_float_list(self, new_value):
        """Set float list value"""
        self._value = " ".join(map(str, new_value))

    def set_binary_list(self, new_value):
        """Set binary list value"""
        self._value = " ".join(map(self._bytes2hexascii, new_value))

    #
    # Internal methods
    #
    def _bool2string(self, value):
        """Convert a Python bool value to 'true' or 'false'"""
        return value and "true" or "false"
        
    def _bytes2hexascii(self, b):
        """Convert bytes to hexascii"""
        result = binascii.hexlify(b)
        return result.decode('ascii')

    def _hexascii2bytes(self, s):
        """Convert hexascii to bytes"""
        # Since Python 3.7 'fromhex' will ignore all ASCII whitespace, not just
        # spaces. To support Python < 3.7 we have to manually split first.
        s = "".join(s.split())
        return bytes.fromhex(s)

    def _string2bool(self, s):
        lcase = s.lower()
        if lcase == "true" \
           or lcase == "yes" \
           or lcase == "1":
            return 1
        elif lcase == "false" \
             or lcase == "no" \
             or lcase == "0":
            return 0
        else:
            raise ValueError()
            

class Folder(NamespaceObject):
    """A folder. Does not contain the name of the folder itself."""
    def __init__(self, source, write_target, sectionname):
        self._folders = {}
        self._parameters = {}
        # List of URLs that has contributed to this Folder.
        self.sources = []
        # URL to write to when adding new folder objects.
        self.write_target = None
        self._update_write_target(write_target)
        self.sectionname = _fixup_sectionname(sectionname)
        self._update(source)

    def __repr__(self):
        return "<Folder: sources=%s  write_target=%s  sectionname=%s>" \
               % (",".join(self.sources), self.write_target, self.sectionname)

    def _update(self, source):
        if source:
            self.sources.append(source)
            self._update_write_target(source)

    def _update_write_target(self, write_target):
        if not self.write_target \
               and write_target \
               and _check_write_access(write_target):
            self.write_target = write_target

    def _write_new_section(self):
        hfu = _HiveFileUpdater(self.write_target)
        hfu.add_section(self.sectionname)

    def _write_delete_section(self):
        hfu = _HiveFileUpdater(self.write_target)
        return hfu.delete_section(self.sectionname)

    def _addobject(self, obj, objname):
        if self._exists(objname):
            raise ObjectExistsError

        if isinstance(obj, Parameter):
            print("Adding parameter", objname, file=debugw)
            self._parameters[objname] = obj
        elif isinstance(obj, Folder):
            print("Adding folder", objname, file=debugw)
            self._folders[objname] = obj
        else:
            raise InvalidObjectError

    def _get_object(self, objname):
        return self._folders.get(objname) or self._parameters.get(objname)
        
    def _exists(self, objname):
        return objname in self._folders or objname in self._parameters

    #
    # Get methods
    #
    def get_folders(self, folderpath, default=None):
        """Get folder names in folder"""
        if default == None:
            default = []

        folder = self.lookup(folderpath)

        if not folder:
            return default
        else:
            return list(folder._folders.keys())

    def get_parameters(self, folderpath, default=None):
        """Get parameter names in this folder"""
        if default == None:
            default = []

        folder = self.lookup(folderpath)
        if not folder:
            return default
        else:
            return list(folder._parameters.keys())

    def delete(self, path, recursive=0):
        obj = self.lookup(path)

        if not obj:
            return 0

        comps = _path2comps(path)

        if [] != comps[:-1]:
            parentfolder = self._lookup_list(comps[:-1])
        else:
            parentfolder = self

        if isinstance(obj, Parameter):
            return parentfolder._delete_param(comps[-1])
        else:
            subfolders = list(obj._folders.keys())
            subparams = list(obj._parameters.keys())

            if ([] != subfolders or [] != subparams) and not recursive:
                raise FolderNotEmpty

            return parentfolder._delete_folder(comps[-1])

    def _delete_folder(self, foldername):
        print(self, "_delete_folder(\"%s\")" % foldername, file=debugw)
        folder = self._folders[foldername]
        for (subfoldername, subfolder) in list(folder._folders.items()):
            if "/" == subfoldername:
                continue
            folder._delete_folder(subfoldername)
        for (subparamname, subparam) in list(folder._parameters.items()):
            folder._delete_param(subparamname)

        self._folders[foldername]._write_delete_section()
        del self._folders[foldername]
        return 1

    def _delete_param(self, paramname):
        print(self, "_delete_param(\"%s\")" % paramname, file=debugw)
        self._parameters[paramname].write_update(delete=1)
        del self._parameters[paramname]
        return 1

    def _get_value(self, parampath, default, method):
        param = self.lookup(parampath)

        if not param:
            return default
        else:
            # Check if param really is a Parameter
            if not isinstance(param, Parameter):
                raise NotAParameterError()
            return method(param)

    def get_string(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_string)

    def get_bool(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_bool)

    def get_integer(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_integer)

    def get_float(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_float)

    def get_binary(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_binary)

    def get_string_list(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_string_list)

    def get_bool_list(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_bool_list)

    def get_integer_list(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_integer_list)

    def get_float_list(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_float_list)
    
    def get_binary_list(self, parampath, default=None):
        return self._get_value(parampath, default, Parameter.get_binary_list)
    
    #
    # Set methods
    #
    def _set_value(self, parampath, value, method):
        comps = _path2comps(parampath)
        folder_comps = comps[:-1]
        if folder_comps:
            folder = self._lookup_list(folder_comps, autocreate=1)
        else:
            folder = self
        paramname = comps[-1]
        param = folder.lookup(paramname)
        if not param:
            # Create new parameter
            param = Parameter(None, folder.write_target,
                              folder.sectionname, paramname, folder.write_target)
            # Set the value
            method(param, value)
            folder._addobject(param, paramname)
            # Write new parameter to disk
            return param.write_new()
        else:
            # Update existing parameter
            method(param, value)
            return param.write_update()

    def set_string(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_string)
        
    def set_bool(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_bool)
        
    def set_integer(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_integer)
        
    def set_float(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_float)
        
    def set_binary(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_binary)
        
    def set_string_list(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_string_list)

    def set_bool_list(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_bool_list)

    def set_integer_list(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_integer_list)

    def set_float_list(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_float_list)

    def set_binary_list(self, parampath, value):
        return self._set_value(parampath, value, Parameter.set_binary_list)

    def lookup(self, objpath, autocreate=0):
        """Lookup an object. objname is like global/settings/background
        Returns None if object is not found.
        """
        comps = _path2comps(objpath)
        return self._lookup_list(comps, autocreate)

    def _lookup_list(self, comps, autocreate=0, sectionname=""):
        """Lookup an object. comps is like
        ["global", "settings", "background"]
        Returns None if object is not found.

        If autocreate is in use, leading paths will be created in memory.
        The last component will be recognized as a Folder, and it will be
        created and written to disk. 
        """
        print("_lookup_list with components:", repr(comps), file=debugw)

        obj_name = comps[0]
        rest_comps = comps[1:]
        sectionname = os.path.join(sectionname, obj_name)
        
        obj = self._get_object(obj_name)

        create_folder = not obj and autocreate
        if create_folder:
            obj = Folder(None, self.write_target,
                         os.path.join(self.sectionname, obj_name))
            self._addobject(obj, obj_name)

        if not obj:
            return

        if len(comps) == 1:
            # Last step in recursion
            if create_folder:
                # Last component, sync to disk
                obj._write_new_section()
                # Set source
                obj._update(obj.write_target)
            
            return obj
        else:
            # Recursive call with rest of component list
            if not isinstance(obj, Folder):
                raise ObjectExistsError

            return obj._lookup_list(rest_comps, autocreate, sectionname)

    def walk(self, recursive=1, indent=None):
        def _unicode_to_print(*args, **kwargs):
            try:
                print(*args, file=kwargs["file"])
            except UnicodeEncodeError:
                if len(self.sources) > 0:
                    raise UnicodeError("Characters in [%s] in %s cannot be printed." \
                                       % (self.sectionname, self.sources[0]))
                else:
                    raise UnicodeError("Characters in [%s] cannot be printed." \
                                       % (self.sectionname))

        if not indent:
            indent = _IndentPrinter()
            # Print root folder in debug mode
            if debugw.debug:
                _unicode_to_print("/", str(self), file=indent)

        # Print Parameters and values
        for (paramname, param) in self._parameters.items():
            if not debugw.debug:
                _unicode_to_print(paramname, "=", param.get_string(), file=indent)
            else:
                _unicode_to_print(paramname, param, file=indent)

        # Print Foldernames and their contents
        for (foldername, folder) in self._folders.items():
            if foldername == "/":
                continue

            if not debugw.debug:
                _unicode_to_print(foldername + "/ ", file=indent)
            else:
                _unicode_to_print(foldername + "/", str(folder), file=indent)
            indent.change(4)
            if recursive:
                folder.walk(recursive, indent)
            indent.change(-4)


def open_hive(url, blacklist=None):
    # Relative URLs should be resolved relative to _get_cwd_url().
    hfp = _HiveFileParser(urllib.parse.urljoin(_get_cwd_url(), url), blacklist)
    return hfp.parse()


class _HiveFileParser:
    def __init__(self, url, blacklist):
        # URL to entry hive
        self.url = url
        if blacklist is None:
            self.blacklist = []
        else:
            self.blacklist = blacklist

    def parse(self, url=None, rootfolder=None):
        """Open and parse a hive file. Returns a folder"""
        if not url:
            url = self.url
        
        print("Opening URL", url, file=debugw)
        try:
            if _get_url_scheme(url) == "file" or _get_url_scheme(url) == "":
                file = open(_get_url_path(url), "r", encoding="UTF-8")
            else:
                # FIXME: Url:s have broken unicode handling - we can't know the encoding
                return
        except OSError: # We could not read a file. Just return, this is part
            # of the Hiveconf specification.
            return

        if not rootfolder:
            rootfolder = Folder(url, url, "/")
            rootfolder._addobject(rootfolder, "/")
        curfolder = rootfolder
        linenum = 0
        sectionname = ""

        # Section [/] is implicit
        self.handle_section(rootfolder, "/", url)

        # Read & parse entire hive file
        while True:
            try:
                line = file.readline()
            except UnicodeDecodeError:
                raise UnicodeError("File %s contains non UTF-8 characters." % (url))
            linenum += 1

            if not line:
                break

            line = line.strip()

            if line.startswith("#") or line.startswith(";") or not line:
                continue

            if line.startswith("["):
                # Folder
                if not line.endswith("]"):
                    print("%s: line %d: Syntax error: line does not end with ]" \
                          % (url, linenum), file=sys.stderr)
                    continue

                sectionname = line[1:-1]
                print("Read section line", sectionname, file=debugw)
                curfolder = self.handle_section(rootfolder, sectionname, url)

            elif line.startswith("%"):
                # Directive
                fields = line.split()
                directive = fields[0]
                args = fields[1:]

                # %mount
                if directive == "%mount":
                    self.mount_directive(args, curfolder, url, linenum, sectionname)
                else:
                    print("%s: line %d: unknown directive" % (url, linenum), file=sys.stderr)

            elif line.find("=") != -1:
                # Parameter
                (paramname, paramvalue) = line.split("=", 1)
                paramname = paramname.strip()
                paramvalue = paramvalue.strip()
                print("Read parameter line", paramname, file=debugw)
                if _check_write_access(url):
                    write_target = url
                else:
                    write_target = curfolder.write_target
                try:
                    curfolder._addobject(Parameter(paramvalue, url, sectionname, paramname, write_target), paramname)
                except ObjectExistsError:
                    print("Object '%s' already exists" % paramname, file=debugw)
            else:
                raise SyntaxError(url, linenum)

        return rootfolder


    def handle_section(self, rootfolder, sectionname, source):
        print("handle_section for section", sectionname, file=debugw)
        comps = _path2comps(sectionname)

        folder = rootfolder._lookup_list(comps)
        if folder:
            # Folder already exists. Update with new information. 
            folder._update(source)
        else:
            folder = self._create_folders(rootfolder, comps, source)

        return folder


    # Create folder in memory. Not for external use.
    # The external function should also write folder to disk. 
    def _create_folders(self, folder, comps, source, sectionname=""):
        obj_name = comps[0]
        rest_comps = comps[1:]
        sectionname = os.path.join(sectionname, obj_name)

        obj = folder._get_object(obj_name)
        if not obj:
            # Create folder
            # If we have a source file and it's writable, make this
            # the write_target. Otherwise, inherit. 
            if source and _check_write_access(source):
                write_target = source
            else:
                write_target = folder.write_target

            if len(comps) == 1:
                # last step
                obj = Folder(source, write_target, sectionname)
            else:
                obj = Folder(None, write_target, sectionname)
                
            folder._addobject(obj, obj_name)

        if len(comps) == 1:
            # Last step in recursion
            return obj
        else:
            # Recursive call with rest of component list
            if not isinstance(obj, Folder):
                raise ObjectExistsError

            return self._create_folders(obj, rest_comps, source, sectionname)
                                        

    def mount_directive(self, args, curfolder, url, linenum, sectionname):
        try:
            opts, args = getopt.getopt(args, "t:a:")
        except getopt.GetoptError:
            print("%s: line %d: invalid syntax" % (url, linenum), file=sys.stderr)
            return

        backend = "hivefile"
        backend_args = ""
        for o, a in opts:
            if o == "-t":
                backend = a
            if o == "-a":
                backend_args = a

        if not len(args) == 1:
            print("%s: line %d: invalid syntax" % (url, linenum), file=sys.stderr)
            return

        # Resolve URL, relative to the doc base URL
        mnturl = urllib.parse.urljoin(url, args[0])
        del args

        for mount_url in self._get_urls_to_mount(mnturl):
            if backend == "hivefile":
                self.parse(mount_url, curfolder)

            elif backend == "filesystem": # FIXME: Separate function/module/library
                paramname = "default" # FIXME

                # Parse specific options
                for backend_arg in backend_args.split(","):
                    try:
                        (name, value) = backend_arg.split("=")
                    except ValueError:
                        continue
                    
                    if name == "name":
                        paramname = value

                paramvalue = open(mount_url, "r", encoding="UTF-8").read()
                curfolder._addobject(Parameter(paramvalue, mount_url, "", paramname, mount_url), paramname)

            else:
                print("%s: line %d: unsupported backend" % (url, linenum), file=sys.stderr)
                continue


    def _get_urls_to_mount(self, mnturl):
        if _get_url_scheme(mnturl) == "file":
            # Strip file://
            mntpath = _get_url_path(mnturl)
            # Expand ~
            mntpath = os.path.expanduser(mntpath)
            # Glob local files
            urls_to_mount =[]
            print("Globbing path", mntpath, file=debugw)
            glob_result = glob.glob(mntpath)
            if glob_result:
                glob_result.sort()
                for file_to_mount in glob_result:
                    for bl_file in self.blacklist:
                        if os.path.samefile(file_to_mount, bl_file):
                            break
                    else:
                        urls_to_mount.append("file://" + file_to_mount)
            else:
                # No files found. Create file if the path had no wildcards
                if not _has_glob_wildchars(mntpath):
                    try:
                        # Touch
                        with open(mntpath, "w", encoding="UTF-8"):
                            pass
                    except OSError:
                        print("Couldn't create", mntpath, file=debugw)
                    else:
                        # Successfully created file
                        urls_to_mount.append("file://" + mntpath)
                
        else:
            urls_to_mount = [mnturl]

        return urls_to_mount
        

class _HiveFileUpdater:
    # FIXME: Broken for parameter files. 
    def __init__(self, source):
        self.source = source

        (scheme, netloc, self.filename, query, fragment) = urllib.parse.urlsplit(self.source)
        if not scheme == "file":
            # Only able to write to local files right now
            raise ReadOnlySource()

    def change_parameter(self, sectionname, paramname, value, new_param=0,
                         delete_param=0):
        """Change existing parameter line in file"""
        # FIXME: Use file locking
        with open(self.filename, "r+", encoding="UTF-8") as f:
            parameter_offset = self._find_offset(f, sectionname, paramname, new_param)
            rest_data = f.read()

            if parameter_offset == None:
                # The parameter was not found!
                # If we are adding a parameter to a section that is not
                # in this file, we should create the section.
                if new_param:
                    self.add_section(sectionname)
                    # Now we can add the parameter at the end.
                    f.seek(0, 2)
                    parameter_offset = f.tell()
                else:
                    raise NoSuchParameterError()

            # Seek to parameter offset, and write new value
            f.seek(parameter_offset)
            if not delete_param:
                print(paramname + "=" + value, file=f)

            # Write rest
            f.write(rest_data)
            f.truncate()

    def add_parameter(self, sectionname, paramname, value):
        self.change_parameter(sectionname, paramname, value, new_param=1)

    def delete_section(self, sectionname):
        with open(self.filename, "r+", encoding="UTF-8") as f:
            section_offset = self._find_offset(f, sectionname, None, get_section=1)
            # FIXME: the readline() below looks weird. Currently this will
            #        remove the section-line AND the next line.
            #        Either remove only the section-line or the entire
            #        section including all parameters (and subsections?).
            #        See https://www.cendio.com/bugzilla/show_bug.cgi?id=6122
            f.readline()
            rest_data = f.read()
            f.seek(section_offset)
            f.write(rest_data)
            f.truncate()

    def _find_offset(self, f, sectionname, paramname, new_param=0,
                     get_section=0):
        correct_section = 0 

        # If this parameter is at top level, we are already in the
        # correct section when we start parsing.
        # FIXME: This is not very clean. We should probably push "[/]"
        # into the file stream some way, instead
        if sectionname == "":
            correct_section = 1
        if correct_section and new_param:
            return f.tell()

        print("_find_offset, sectionname:", sectionname, file=debugw)

        while True:
            line_offset = f.tell()
            line = f.readline()
            print("Read line:", line.strip(), file=debugw)

            if not line:
                break

            line = line.strip()
            
            if line.startswith("#") or line.startswith(";") or not line:
                continue

            if line.startswith("["):
                # Section
                if not line.endswith("]"):
                    # Ignore invalid section lines
                    continue

                correct_section = (sectionname == line[1:-1])
                if correct_section and get_section:
                    return line_offset
                elif correct_section and new_param:
                    # If we have found the correct section,
                    # we should add new parameters just below it.
                    return f.tell()
                
            elif correct_section and line.find("=") != -1:
                (line_paramname, line_paramvalue) = line.split("=", 1)
                line_paramname = line_paramname.strip()
                if paramname == line_paramname:
                    return line_offset

        return None


    def add_section(self, sectionname):
        """Add new section to end of file"""
        with open(self.filename, "a", encoding="UTF-8") as f:
            print("", file=f)
            print("[%s]" % sectionname, file=f)
