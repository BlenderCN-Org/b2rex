"""
Classes managing the ogre tools from blender 2.5
"""

import bpy
import addon_ogreDotScene

# export meshes
class OgreExporter(object):
    def export(self, path, pack_name, offset):
        """
        Export whole scene, including scene info and mesh info.
        """
        bpy.ops.ogre.export(filepath="/tmp/bla.zip")


