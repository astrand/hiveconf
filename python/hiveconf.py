#
# Copyright (C) 2003 by Cendio Systems
# Author: Peter Astrand <peter@cendio.se>
# 
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy,
# modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import urllib2
import urlparse
import os

class DebugWriter:
    def __init__(self, debug):
        self.debug = debug
    
    def write(self, data):
        if self.debug:
            sys.stderr.write(data)

debugw = DebugWriter(debug=0)


class IndentPrinter:
    def __init__(self):
        self.indent = 0
        self.line_indented = 0

    def write(self, data):
        if self.indent and not self.line_indented:
            sys.stderr.write(" " * self.indent)
            self.line_indented = 1
        sys.stderr.write(data)
        if data.find("\n") != -1:
            self.line_indented = 0

    def change(self, val):
        self.indent += val
        

class Error(Exception): pass
class NoSuchKeyError(Error): pass
class NoSuchFolderError(Error): pass
class ObjectExistsError(Error): pass
class InvalidObjectError(Error): pass
class BadBoolFormat(Error): pass
class BadIntegerFormat(Error): pass
class BadFloatFormat(Error): pass
class BadBinaryFormat(Error): pass
class BadListFormat(Error): pass
    
class SyntaxError(Error):
    def __init__(self, linenum):
        self.linenum = linenum

    def __str__(self):
        return "Bad line %d" % self.linenum

#
# Utils
#

def path2comps(path):
    # Remove first slash
    if path[0] == "/":
        path = path[1:]
    
    return path.split("/")

def comps2path(comps):
    result = ""
    for component in comps:
        result += "/" + component
    return result


class NamespaceObject:
    pass


class Parameter(NamespaceObject):
    # Innehåller textsträngsvärdet "value"; men oparsat, dvs ej försökt översätta till
    # någon speciell datatyp. 
    def __init__(self, value, source):
        self.value = value
        # URL that this parameter was read from
        self.source = source

    #
    # Primitive data types
    #
    def get_string(self):
        """Get value as string"""
        return self.value

    def get_bool(self):
        """Get boolean value"""
        try:
            return self._string2bool(self.value)
        except ValueError:
            raise BadBoolFormat()
    
    def get_integer(self):
        """Get integer value"""
        try:
            return int(self.value)
        except ValueError:
            raise BadIntegerFormat()

    def get_float(self):
        """Get float value"""
        try:
            return float(self.value)
        except ValueError:
            raise BadFloatFormat()

    def get_binary(self):
        """Get binary value"""
        try:
            self._hexascii2string(self.value)
        except ValueError:
            raise BadBinaryFormat()

    #
    # Compound data types
    #
    def get_string_list(self):
        return self.value.split()

    def get_bool_list(self):
        return map(self._string2bool, self.value.split())

    def get_integer_list(self):
        return map(int, self.value.split())

    def get_float_list(self):
        return map(float, self.value.split())

    def get_binary_list(self):
        return map(self._hexascii2string, self.value.split())
        
    def _string2hexascii(self, s):
        """Convert string to hexascii"""
        result = ""
        for char in s:
            result += "%02x" % ord(char)
            return result

    def _hexascii2string(self, s):
        """Convert hexascii to string"""
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
    def __init__(self):
        self.folders = {}
        self.parameters = {}

    def addobject(self, obj, objname):
        if self.exists(objname):
            raise ObjectExistsError

        if isinstance(obj, Parameter):
            print >>debugw, "Adding parameter", objname
            self.parameters[objname] = obj
        elif isinstance(obj, Folder):
            print >>debugw, "Adding folder", objname
            self.folders[objname] = obj
        else:
            raise InvalidObjectError

    def get(self, objname):
        return self.folders.get(objname) or self.parameters.get(objname)
        
    def exists(self, objname):
        return self.folders.has_key(objname) or self.parameters.has_key(objname)

    def lookup(self, objpath, autocreate=0):
        """Lookup an object. objname is like global/settings/background
        Returns None if object is not found."""
        comps = path2comps(objpath)
        return self._lookup_list(comps, autocreate)

    def _lookup_list(self, comps, autocreate=0):
        """Lookup an object. comps is like
        ["global", "settings", "background"]
        Returns None if object is not found. 
        """
        print >>debugw, "_lookup_list with components:", repr(comps)
        
        first_comp = comps[0]
        rest_comps = comps[1:] 
        
        obj = self.get(first_comp)
        if not obj and autocreate:
            # Create folder
            obj = Folder()
            self.addobject(obj, first_comp)

        if len(comps) == 1:
            # Last step in recursion
            return obj
        else:
            # Recursive call with rest of component list
            if not isinstance(obj, Folder):
                raise ObjectExistsError
            
            return obj._lookup_list(rest_comps, autocreate)

    def walk(self, indent=None):
        if not indent:
            indent = IndentPrinter()

        # Print Parameters and values
        print >>indent, "Parameters:"
        for (paramname, param) in self.parameters.items():
            indent.change(4)
            print >> indent, paramname, "=", param.get_string()
            indent.change(-4)

        # Print Foldernames and their contents
        for (foldername, folder) in self.folders.items():
            print >>indent, "Folder:", foldername
            indent.change(4)
            folder.walk(indent)
            indent.change(-4)


def fixup_url(url):
    """Change url slightly, so that urllib can be used for POSIX paths"""
    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    if not scheme:
        scheme = "file"

    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))


def open_hive(url):
    """Open and parse a hive file. Returns a folder"""
    url = fixup_url(url)
    file = urllib2.urlopen(url)
    
    rootfolder = Folder()
    curfolder = rootfolder
    linenum = 0

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

            foldername = line[1:-1]
            print >>debugw, "Read folder line", foldername
            curfolder = rootfolder.lookup(foldername, autocreate=1)
        elif line.find("=") != -1:
            # Parameter
            (paramname, paramvalue) = line.split("=")
            paramname = paramname.strip()
            paramvalue = paramvalue.strip()
            print >>debugw, "Read parameter line", paramname
            curfolder.addobject(Parameter(paramvalue, url), paramname)
        else:
            raise SyntaxError(linenum)

    return rootfolder
 
