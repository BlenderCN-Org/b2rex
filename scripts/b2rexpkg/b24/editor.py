
import bpy
import Blender

class ProxyObject(object):
    def __init__(self, obj, parent=None):
        self._obj = obj
        self._parent = None
    def __getattr__(self, name):
        return getattr(self._obj, name)
    def __hasattr__(self, name):
        return hasattr(self._obj, name)

class EditorFace(ProxyObject):
    def get_smooth(self):
        return self._obj.smooth
    def set_smooth(self, value):
        self._obj.smooth = int(value)
    def get_vertices_raw(self):
        pass
    def set_vertices_raw(self, values):
        mesh = self._parent
        indices = map(lambda s: mesh.verts[s], values)
        self._obj.verts = indices
        
    use_smooth = property(get_smooth, set_smooth)
    vertices_raw = property(get_vertices_raw, set_vertices_raw)

class FaceList(ProxyObject):
    def __getitem__(self, idx):
        return EditorFace(self._obj[idx], self._parent)
    def add(self, nfaces):
        for a in xrange(nfaces):
            self._obj.extend([0,0,0], ignoreDups=True)

class VertexList(FaceList):
    def add(self, nfaces):
        for a in xrange(nfaces):
            self._obj.extend(0.0,0.0,0.0)

class EditorMesh(ProxyObject):
    def __init__(self, bmesh):
        ProxyObject.__init__(self, bmesh)
        self.vertices = VertexList(bmesh.verts, bmesh)
        self.faces = FaceList(bmesh.faces, bmesh)
    def calc_normals(self):
        pass

class EditorObject(object):
    def __init__(self, bobj):
        self._bobj = bobj
        self.data = EditorMesh(bobj.data)
    def link(self, data):
        self._bobj.link(data._bobj)
    def set_location(self, value):
        self._bobj.setLocation(*value)
    def get_location(self):
        self._bobj.getLocation()
    def get_unimplemented(self):
        pass
    def set_unimplemented(self, value):
        pass
    def __getattr__(self, name):
        return getattr(self._bobj, name)
    def __hasattr__(self, name):
        return hasattr(self._bobj, name)
    location = property(get_location, set_location)
    lock_location = property(get_unimplemented, set_unimplemented)
    lock_scale = property(get_unimplemented, set_unimplemented)
    lock_rotation = property(get_unimplemented, set_unimplemented)
    lock_rotations_4d = property(get_unimplemented, set_unimplemented)
    lock_rotation_w = property(get_unimplemented, set_unimplemented)

class EditorMeshes(ProxyObject):
    def __init__(self):
        ProxyObject.__init__(self, bpy.data.meshes)

    def new(self, name):
        return EditorMesh(bpy.data.meshes.new(name))

    def __getitem__(self, name):
        return EditorMesh(bpy.data.meshes[name])


class EditorObjects(ProxyObject):
    def __init__(self):
        ProxyObject.__init__(self, bpy.data.objects)

    def new(self, name, mesh_data):
        obj = Blender.Object.New("Mesh", name)
        if isinstance(mesh_data, EditorMesh):
            obj.link(mesh_data._obj)
        else:
            obj.link(mesh_data)
        return EditorObject(obj)

    def __getitem__(self, name):
        return EditorObject(bpy.data.objects[name])

class EditorData(object):
    def __init__(self):
        self.meshes = EditorMeshes()
        self.textures = bpy.data.textures
        self.objects = EditorObjects()
        self.materials = bpy.data.materials


data = EditorData()
