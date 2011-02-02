"""
Class holding all export modules.
"""

import os
import sys
import logging
import b2rexpkg

from b2rexpkg.siminfo import GridInfo
from b2rexpkg.simconnection import SimConnection
if sys.version_info[0] == 2:
    from b2rexpkg.ogre_exporter import OgreExporter
    from .b24.hooks import reset_uuids
else:
    class DummyExporter():
        pass
    OgreExporter = DummyExporter

import bpy
logger = logging.getLogger('b2rex.exporter')

class Exporter(object):
    def __init__(self, gridinfo=None):
        # rest
        if gridinfo:
            self.gridinfo = gridinfo
        else:
            self.gridinfo = GridInfo()
        self.sim = SimConnection()
        self.ogre = OgreExporter()

    def connect(self, base_url, username="", password=""):
        """
        Connect to an opensim instance
        """
        self.gridinfo.connect(base_url, username, password)
        self.sim.connect(base_url)

    def test(self):
        """
        Api tests
        """
        logger.debug(self.gridinfo.getGridInfo()["gridnick"])
        regions = self.gridinfo.getRegions()
        for id in regions:
            region = regions[id]
            logger.debug((" *", region["name"], region["x"], region["y"], id))

        # xmlrpc
        logger.debug(self.sim.login("caedes", "caedes", "pass"))
        logger.debug(self.sim.sceneClear("d9d1b302-5049-452d-b176-3a9561189ca4",
                                         "cube"))
        logger.debug(self.sim.sceneUpload("d9d1b302-5049-452d-b176-3a9561189ca4",
                              "cube",
                              "/home/caedes/groupmembers.zip"))

    def export(self, path, pack_name, offset, exportSettings):
        """
        Export the scene to a zipfile.
        """
        b2rexpkg.start()
        if exportSettings.regenMaterials:
                reset_uuids(bpy.data.materials)
        if exportSettings.regenObjects:
                reset_uuids(bpy.data.objects)
        if exportSettings.regenTextures:
                reset_uuids(bpy.data.textures)
        if exportSettings.regenMeshes:
                reset_uuids(bpy.data.meshes)
        self.ogre.export(path, pack_name, offset)
        f = open(os.path.join(path, pack_name + ".uuids"), 'w')
        b2rexpkg.write(f)
        f.close()

