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

import sys
import urllib2
import urlparse
import os
import string
import glob
import getopt
import re

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
    
class SyntaxError(Error):
    def __init__(self, linenum):
        self.linenum = linenum

    def __str__(self):
        return "Bad line %d" % self.linenum

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
    return urlparse.urlsplit(url)[0]

def _get_url_path(url):
    """Get URL path component"""
    return urlparse.urlsplit(url)[2]

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

def _check_create_possible(file):
    """Check if it's possible to create this file"""
    directory = os.path.dirname(file)
    return os.access(dirname, W_OK)

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
            raise "No source!" # FIXME
        self.source = source
        self.sectionname = sectionname
        # FIXME: The class probably shouldn't know about it's own name.
        self.paramname = paramname
        self.write_target = write_target

    def __repr__(self):
        return "<Parameter: %s  value=%s  section=%s  source=%s  write_target=%s>" \
               % (self.paramname, self._value, self.sectionname, self.source,
                  self.write_target)

    def _be_add_param(self):
        """Add a new parameter to the backend"""
        if not self.write_target:
            print >>debugw, "_be_add_param(%s): no write_target" % self.paramname
            return 0
        
        hfu = _HiveFileUpdater(self.write_target)
        hfu.add_parameter(self.sectionname, self.paramname, self._value)
        return 1

    def _be_change_param(self):
        """Change the value of a existing parameter in the backend"""
        if not self.write_target:
            print >>debugw, "_be_change_param(%s): no write_target" % self.paramname
            return 0
        
        if self.source != self.write_target:
            # If we should write to another file than the parameter
            # was read from, we should add, not change
            return self._be_add_param()
        else:
            hfu = _HiveFileUpdater(self.write_target)
            hfu.change_parameter(self.sectionname, self.paramname, self._value)

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
            return self._hexascii2string(self._value)
        except ValueError:
            raise BadBinaryFormat()

    #
    # Compound data types, get operations
    #
    def get_string_list(self):
        return self._value.split()

    def get_bool_list(self):
        return map(self._string2bool, self._value.split())

    def get_integer_list(self):
        return map(int, self._value.split())

    def get_float_list(self):
        return map(float, self._value.split())

    def get_binary_list(self):
        return map(self._hexascii2string, self._value.split())
    
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
        self._value = self._string2hexascii(new_value)

    #
    # Compound data types, set operations
    #
    def set_string_list(self, new_value):
        """Set string list value"""
        self._value = string.join(new_value)
    
    def set_bool_list(self, new_value):
        """Set bool list value"""
        self._value = string.join(map(self._bool2string, new_value))

    def set_integer_list(self, new_value):
        """Set integer list value"""
        self._value = string.join(map(str, new_value))

    def set_float_list(self, new_value):
        """Set float list value"""
        self._value = string.join(map(str, new_value))

    def set_binary_list(self, new_value):
        """Set binary list value"""
        self._value = string.join(map(self._string2hexascii, new_value))

    #
    # Internal methods
    #
    def _bool2string(self, value):
        """Convert a Python bool value to 'true' or 'false'"""
        return value and "true" or "false"
        
    def _string2hexascii(self, s):
        """Convert string to hexascii"""
        result = ""
        for char in s:
            result += "%02x" % ord(char)
        return result

    def _hexascii2string(self, s):
        """Convert hexascii to string"""
        # Remove all whitespace from string
        s = s.translate(string.maketrans("", ""), string.whitespace)
        result = ""
        for x in range(len(s)/2):
            pair = s[x*2:x*2+2]
            val = int(pair, 16)
            result += chr(val)
        return result

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
               % (string.join(self.sources, ","), self.write_target, self.sectionname)

    def _update(self, source):
        if source:
            self.sources.append(source)
            self._update_write_target(source)

    def _update_write_target(self, write_target):
        if not self.write_target \
               and write_target \
               and _check_write_access(write_target):
            self.write_target = write_target

    def _be_write_section(self):
        hfu = _HiveFileUpdater(self.write_target)
        hfu.add_section(self.sectionname)

    def _addobject(self, obj, objname):
        if self._exists(objname):
            raise ObjectExistsError

        if isinstance(obj, Parameter):
            print >>debugw, "Adding parameter", objname
            self._parameters[objname] = obj
        elif isinstance(obj, Folder):
            print >>debugw, "Adding folder", objname
            self._folders[objname] = obj
        else:
            raise InvalidObjectError

    def _get_object(self, objname):
        return self._folders.get(objname) or self._parameters.get(objname)
        
    def _exists(self, objname):
        return self._folders.has_key(objname) or self._parameters.has_key(objname)

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
            return folder._folders.keys()
        
    def get_parameters(self, folderpath, default=None):
        """Get parameter names in this folder"""
        if default == None:
            default = []

        folder = self.lookup(folderpath)
        if not folder:
            return default
        else:
            return folder._parameters.keys()

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
            return param._be_add_param()
        else:
            # Update existing parameter
            method(param, value)
            return param._be_change_param()

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
        print >>debugw, "_lookup_list with components:", repr(comps)
        
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
                obj._be_write_section()
                # Set source
                obj._update(obj.write_target)
            
            return obj
        else:
            # Recursive call with rest of component list
            if not isinstance(obj, Folder):
                raise ObjectExistsError
            
            return obj._lookup_list(rest_comps, autocreate, sectionname)

    def walk(self, recursive=1, indent=None):
        if not indent:
            indent = _IndentPrinter()
            # Print root folder in debug mode
            if debugw.debug:
                print >>indent, "/", str(self)

        # Print Parameters and values
        for (paramname, param) in self._parameters.items():
            if not debugw.debug:
                print >> indent, paramname, "=", param.get_string()
            else:
                print >> indent, paramname, param

        # Print Foldernames and their contents
        for (foldername, folder) in self._folders.items():
            if foldername == "/":
                continue
            
            if not debugw.debug:
                print >>indent, foldername + "/ "
            else:
                print >>indent, foldername + "/", str(folder)
            indent.change(4)
            if recursive:
                folder.walk(recursive, indent)
            indent.change(-4)
            

def open_hive(url):
    # Relative URLs should be resolved relative to _get_cwd_url().
    hfp = _HiveFileParser(urlparse.urljoin(_get_cwd_url(), url))
    return hfp.parse()


class _HiveFileParser:
    def __init__(self, url):
        # URL to entry hive
        self.url = url

    def parse(self, url=None, rootfolder=None):
        """Open and parse a hive file. Returns a folder"""
        if not url:
            url = self.url
        
        print >>debugw, "Opening URL", url
        file = urllib2.urlopen(url) 

        if not rootfolder:
            rootfolder = Folder(url, url, "/")
            rootfolder._addobject(rootfolder, "/")
        curfolder = rootfolder
        linenum = 0
        sectionname = ""

        # Section [/] is implicit
        self.handle_section(rootfolder, "/", url)

        # Read & parse entire hive file
        while 1:
            line = file.readline()
            linenum += 1

            if not line:
                break

            line = line.strip()

            if line.startswith("#") or line.startswith(";") or not line:
                continue

            if line.startswith("["):
                # Folder
                if not line.endswith("]"):
                    raise SyntaxError

                sectionname = line[1:-1]
                print >>debugw, "Read section line", sectionname
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
                    print >> sys.stderr, "%s: line %d: unknown directive" % (url, linenum)

            elif line.find("=") != -1:
                # Parameter
                (paramname, paramvalue) = line.split("=", 1)
                paramname = paramname.strip()
                paramvalue = paramvalue.strip()
                print >>debugw, "Read parameter line", paramname
                try:
                    if _check_write_access(url):
                        write_target = url
                    else:
                        write_target = curfolder.write_target
                    curfolder._addobject(Parameter(paramvalue, url, sectionname, paramname, write_target), paramname)
                except ObjectExistsError:
                    print >>debugw, "Object '%s' already exists" % paramname
            else:
                raise SyntaxError(linenum)

        return rootfolder


    def handle_section(self, rootfolder, sectionname, source):
        print >>debugw, "handle_section for section", sectionname
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
            if len(comps) == 1:
                # last step
                # If we have a source file and it's writable, make this
                # the write_target. Otherwise, inherit. 
                if source and _check_write_access(source):
                    write_target = source
                else:
                    write_target = folder.write_target
                obj = Folder(source, write_target, sectionname)
            else:
                obj = Folder(None, folder.write_target, sectionname)

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
            print >> sys.stderr, "%s: line %d: invalid syntax" % (url, linenum)
            return

        backend = "hivefile"
        backend_args = ""
        for o, a in opts:
            if o == "-t":
                backend = a
            if o == "-a":
                backend_args = a

        if not len(args) == 1:
            print >> sys.stderr, "%s: line %d: invalid syntax" % (url, linenum)
            return

        # Resolve URL, relative to the doc base URL
        mnturl = urlparse.urljoin(url, args[0])
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

                paramvalue = urllib2.urlopen(mount_url).read()
                curfolder._addobject(Parameter(paramvalue, mount_url, "", paramname, mount_url), paramname)

            else:
                print >> sys.stderr, "%s: line %d: unsupported backend" % (url, linenum)
                continue


    def _get_urls_to_mount(self, mnturl):
        if _get_url_scheme(mnturl) == "file":
            # Strip file://
            mntpath = _get_url_path(mnturl)
            # Expand ~
            mntpath = os.path.expanduser(mntpath)
            # Glob local files
            urls_to_mount =[]
            print >>debugw, "Globbing path", mntpath
            glob_result = glob.glob(mntpath)
            if glob_result:
                glob_result.sort()
                for file_to_mount in glob_result:
                    urls_to_mount.append("file://" + file_to_mount)
            else:
                # No files found. Create file if the path had no wildcards
                if not _has_glob_wildchars(mntpath):
                    try:
                        # Touch
                        open(mntpath, "w")
                    except IOError:
                        print >>debugw, "Couldn't create", mntpath
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

        (scheme, netloc, self.filename, query, fragment) = urlparse.urlsplit(self.source)
        if not scheme == "file":
            # Only able to write to local files right now
            raise ReadOnlySource()

    def change_parameter(self, sectionname, paramname, value, new_param=0):
        """Change existing parameter line in file"""
        # FIXME: Use file locking
        f = open(self.filename, "r+")
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
        print >> f, paramname + "=" + value

        # Write rest
        f.write(rest_data)
        f.truncate()

    def add_parameter(self, sectionname, paramname, value):
        self.change_parameter(sectionname, paramname, value, new_param=1)

    def _find_offset(self, f, sectionname, paramname, new_param=0):
        correct_section = 0 

        # If this parameter is at top level, we are already in the
        # correct section when we start parsing.
        # FIXME: This is not very clean. We should probably push "[/]"
        # into the file stream some way, instead
        if sectionname == "":
            correct_section = 1
        if correct_section and new_param:
            return f.tell()

        while 1:
            line_offset = f.tell()
            line = f.readline()

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
                if correct_section and new_param:
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
        f = open(self.filename, "a")
        print >> f
        print >> f, "[%s]" % sectionname

