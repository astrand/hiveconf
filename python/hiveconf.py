#
# Copyright (C) 2003  Peter Åstrand <astrand@lysator.liu.se>
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

import posixpath
import sys
import types

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
# FIXME: Should contain at least line number
class SyntaxError(Error): pass

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
    def __init__(self, value):
        self.value = value

    def get_string(self):
        """Get value as string"""
        return self.value


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
        
        print >>indent, "Parameters:", self.parameters.keys()
        for (foldername, folder) in self.folders.items():
            print >>indent, "Folder:", foldername
            indent.change(4)
            folder.walk(indent)
            indent.change(-4)


    def get_string(self, key):
        # Hämta ett parametervärde, relativt en folder. 
        # Implementation:  dela upp "key" i komponenter. Utgå ifrån
        # "folder" och sök upp parameter-objektet. Hämta värdet från parametern via
        # parameter.get().
        pass



def open_hive(filename):
    """Open and parse a hive file. Returns a folder"""
    file = open(filename)
    rootfolder = Folder()
    curfolder = rootfolder

    # Read & parse entire hive file
    while 1:
        line = file.readline()

        if not line:
            break

        line = line.strip()
        
        if line.startswith("#") or not line:
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
            print >>debugw, "Read parameter line", paramname
            curfolder.addobject(Parameter(paramvalue), paramname)
        else:
            raise SyntaxError

    return rootfolder
 
