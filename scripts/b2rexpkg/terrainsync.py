"""
Maintains a terrain mesh in blender and synchronizes it with height data
arriving in blocks.
"""

import bpy

class TerrainSync(object):
    lodlevels = [1,2,4,8,16]
    def __init__(self, app, lod):
        self.lod = lod
        self.app = app
        self.nblocks = 16
        self.nextcheck = 0
        self.terraindirty = False
        try:
            self.terrain = bpy.data.objects["terrain"]
        except:
            self.terrain = self.create_terrain()
        self.checksums = [0] * self.nblocks * self.nblocks

    def set_dirty(self):
        """
        Set the dirty flag so the terrain will do a scan for changes.
        """
        self.terraindirty = True
        self.nextcheck = 0

    def is_dirty(self):
        """
        Check if the Terrain needs to be checked.
        """
        return self.terraindirty

    def check(self):
        """
        Check some blocks and return changed arrays.
        """
        output = []
        for i in range(8):
            res = self.check_next()
            if res:
                output.append(res)
        return output

    def check_next(self):
        """
        Check the next block to see if it needs updating, and
        unsets dirty state if this is the last block.
        """
        if self.lod > 0:
            # doesnt work with lod yet...
            self.terraindirty = False
            return
        if not self.terraindirty:
            return

        res = None
        x = self.nextcheck % self.nblocks
        y = int(self.nextcheck / self.nblocks)

        if self.patch_changed(x, y):
            res = [self.patch_array(x, y), x, y]

        self.nextcheck += 1
        if self.nextcheck >= self.nblocks*self.nblocks:
            self.nextcheck = 0
            self.terraindirty = False

        return res

    def create_terrain(self):
        """
        Creates the terrain mesh.
        """
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

    def patch_changed(self, x, y):
        """
        Checks to see if given patch changed by calculating
        a checksum.
        """
        mesh = bpy.data.objects["terrain"].data
        lod = self.lodlevels[self.lod]
        fullpatchsize = 16
        patchsize = int(fullpatchsize/lod)
        off_x = x*patchsize
        off_y = y*patchsize
        layersize = patchsize*self.nblocks
        checksum = 0.0
        for j in range(patchsize):
            for i in range(patchsize):
                i2 = off_x+i
                j2 = off_y+j
                val = mesh.vertices[i2 + (j2*layersize)].co.z
                checksum += val
        idx = x + int(self.nblocks * y)

        changed = abs(checksum - self.checksums[idx]) > 1.0
        if changed:
            self.checksums[idx] = checksum
            self.constrain_patch(x, y)
        return changed

    def constrain_patch(self, x, y):
        """
        Set all vertices in given patch to their lawful x, y coordinates.
        """
        fullpatchsize = 16
        patchsize = int(fullpatchsize/self.lodlevels[self.lod])
        layersize = patchsize*self.nblocks
        layersize_f = layersize-1
        f = 256.0/float(layersize)
        loff_x = 128.0
        loff_y = 128.0
        mesh = bpy.data.objects["terrain"].data
        lod = self.lodlevels[self.lod]
        off_x = x*patchsize
        off_y = y*patchsize
        layersize = patchsize*self.nblocks
        checksum = 0.0
        for j in range(patchsize):
            for i in range(patchsize):
                i2 = off_x+i
                j2 = off_y+j
                zval = val = mesh.vertices[i2 + (j2*layersize)].co.z
                mesh.vertices[i2 + (j2*layersize)].co = (i2*f-loff_x, j2*f-loff_y,
                                                        zval)

    def patch_array(self, x, y):
        """
        Return the patch array for given coordinates.
        """
        mesh = bpy.data.objects["terrain"].data
        # XXX check for lod
        fullpatchsize = 16
        patchsize = int(fullpatchsize/self.lodlevels[self.lod])
        layersize = patchsize*self.nblocks
        off_x = x*patchsize
        off_y = y*patchsize
        output = list(range(fullpatchsize*fullpatchsize))
        for j in range(fullpatchsize):
            for i in range(fullpatchsize):
                i2 = off_x+i
                j2 = off_y+j
                output[j * fullpatchsize + i] = mesh.vertices[i2 + j2*layersize].co.z
        return output

    def apply_patch(self, data, x, y):
        """
        Apply a set of data to a patch of land
        """
        lod = self.lodlevels[self.lod]
        fullpatchsize = 16
        patchsize = int(fullpatchsize/lod)
        off_x = x*patchsize
        off_y = y*patchsize
        layersize = patchsize*self.nblocks
        mesh = bpy.data.objects["terrain"].data
        checksum = 0.0
        for j in range(patchsize):
            for i in range(patchsize):
                val = data[(i*lod)+(j*fullpatchsize)]
                i2 = off_x+i
                j2 = off_y+j
                mesh.vertices[i2 + (j2*layersize)].co.z = val
                checksum += val
        self.checksums[x + self.nblocks * y] = checksum
        mesh.calc_normals()
