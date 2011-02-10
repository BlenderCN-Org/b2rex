
import bpy

class TerrainSync(object):
    def __init__(self, app):
        self.app = app
        try:
            self.terrain = bpy.data.objects["terrain"]
        except:
            self.terrain = self.create_terrain()
    def create_terrain(self):
        mesh = bpy.data.meshes.new("terrain")
        newobj = bpy.data.objects.new("terrain", mesh)

        f = 256.0/float(16*16)

        layersize = 16*16
        layersize_f = layersize-1
        off_x = 128.0
        off_y = 128.0
        mesh.vertices.add(layersize*layersize)
        for j in range(layersize):
            for i in range(layersize):
                mesh.vertices[i + j*layersize].co = (i*f-off_x, j*f-off_y, 0)
        mesh.faces.add(layersize_f*layersize_f)
        for j in range(layersize_f):
            for i in range(layersize_f):
                v1 = i + (j*layersize)
                v2 = i + ((j+1)*layersize)
                v3 = i+1 + ((j+1)*layersize)
                v4 = i+1 + (j*layersize)
                face = [v1, v2, v3, v4]
                mesh.faces[i + (j*layersize_f)].vertices_raw = face

        
        """
        for j in range(15*15*16):
            for i in range(15*15*16):
        """
        scene = self.app.get_current_scene()
        scene.objects.link(newobj)
        #self.apply_patch(None, 10, 10)

    def apply_patch(self, data, x, y):
        patchsize = 16
        off_x = x*patchsize
        off_y = y*patchsize
        layersize = patchsize*patchsize
        mesh = bpy.data.objects["terrain"].data
        for j in range(patchsize):
            for i in range(patchsize):
                val = data[i+(j*patchsize)]
                i2 = off_x+i
                j2 = off_y+j
                mesh.vertices[i2 + (j2*layersize)].co.z = val-20.0
