import os
import shutil
from collections import defaultdict

class LibraryComponent(object):
    def __init__(self, name, path, component_type, dependencies,
                 comp_dependencies, attrs):
        self._name = name
        self._path = path
        self._type = component_type
        self._file_dependencies = dependencies
        self.dependencies = comp_dependencies
        self.attributes = attrs

    def pack(self, dest_dir):
        # XXX should create a subdirectory to avoid possible conflicts?
        shutil.copy(self._path, dest_dir)
        for dep in self._file_dependencies:
            shutil.copy(dep, dest_dir)

    def __repr__(self):
        return "LibraryComponent(%s, %s, %s)"%(self._name, self._path, self._type)

class Library(object):
    def __init__(self):
        self._paths = []
        self._components = defaultdict(dict)

    def add_path(self, path):
        if not path in self._paths:
            self._paths.append(path)
            self.scan_path(path)

    def scan_path(self, path):
        for f in os.listdir(path):
            if f.endswith(".js"):
                name = f[:-3]
                f_path = os.path.join(path, f)
                self.add_js_component(name, f_path)

    def find_paths(self, path, delim):
        f = open(path, 'r')
        data = f.read()
        f.close()
        paths = set()
        found = data.find(delim)
        while not found == -1:
            delimiter = data[found-1]
            if delimiter in ['"', "'"]:
                end = data.find(delimiter, found)
                paths.add(data[found:end].strip())
            else:
                end = found+1
            found = data.find(delim, end)
        return list(paths)

    def dereference_paths(self, paths, basepath):
        new_paths = []
        for path in paths:
            if path.startswith('local://'):
                new_paths.append(os.path.join(basepath, path[8:]))
            elif path.startswith('file://'):
                new_paths.append(os.path.join(basepath, path[7:]))
        return new_paths

    def add_js_component(self, name, path):
        paths = self.find_paths(path, 'local://')
        paths += self.find_paths(path, 'file://')
        paths = self.dereference_paths(paths, os.path.dirname(path))
        deps, attrs = self.find_component_deps_fromjs(path)
        self._components['jsscript'][name] = LibraryComponent(name,
                                                             path, 'js', paths,
                                                             deps, attrs)
    def find_component_deps_fromjs(self, path):
        f = open(path, 'r')
        data = f.read()
        f.close()
        deps = set()
        attrs = set()
        if 'me.dynamiccomponent' in data:
            deps.add('EC_DynamicComponent')
            pos = data.find('me.dynamiccomponent')
            linepos = data[:pos].rfind('\n')
            name = data[linepos: pos].split('=')[0].strip()
            key = name + '.GetAttribute('
            found = data.find(key)
            while not found == -1:
                delim = data[found+len(key)]
                end = data.find(delim, found+len(key)+2)
                attrs.add(data[found+len(key)+1:end])
                found = data.find(key, end)
        if 'me.animationcontroller' in data:
            deps.add('EC_AnimationController')
        return list(deps), list(attrs)

    def get_component(self, component_type, name):
        return self._components[component_type][name]

    def get_components(self, component_type):
        return self._components[component_type]

library = Library()
library.add_path('/home/caedes/SVN/REALXTEND/tundra/bin/scenes/Door')
library.add_path('/home/caedes/SVN/REALXTEND/tundra/bin/scenes/Avatar')

if __name__ == '__main__':
    l = Library()
    l.add_path('/home/caedes/SVN/REALXTEND/tundra/bin/scenes/Door')
    l.add_path('/home/caedes/SVN/REALXTEND/tundra/bin/scenes/Avatar')
    print(l.get_components('jsscript'))

