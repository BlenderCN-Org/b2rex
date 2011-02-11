
import bpy

class TerrainSync(object):
    lodlevels = [1,2,4,8,16]
    def __init__(self, app, lod):
        self.lod = lod
        self.app = app
        self.nblocks = 16
        try:
            self.terrain = bpy.data.objects["terrain"]
        except:
            self.terrain = self.create_terrain()
    def create_terrain(self):
        mesh = bpy.data.meshes.new("terrain")
        newobj = bpy.data.objects.new("terrain", mesh)
        newobj.location = (0,0,-20)


        patchsize = int(16/self.lodlevels[self.lod])
        layersize = patchsize*self.nblocks
        layersize_f = layersize-1
        f = 256.0/float(layersize)
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
                face = [v1, v4, v3, v2]
                mesh.faces[i + (j*layersize_f)].use_smooth = True
                mesh.faces[i + (j*layersize_f)].vertices_raw = face

        scene = self.app.get_current_scene()
        scene.objects.link(newobj)
        mesh.calc_normals()

    def apply_patch(self, data, x, y):
        lod = self.lodlevels[self.lod]
        fullpatchsize = 16
        patchsize = int(fullpatchsize/lod)
        off_x = x*patchsize
        off_y = y*patchsize
        layersize = patchsize*self.nblocks
        mesh = bpy.data.objects["terrain"].data
        for j in range(patchsize):
            for i in range(patchsize):
                val = data[(i*lod)+(j*fullpatchsize)]
                i2 = off_x+i
                j2 = off_y+j
                mesh.vertices[i2 + (j2*layersize)].co.z = val
        mesh.calc_normals()
