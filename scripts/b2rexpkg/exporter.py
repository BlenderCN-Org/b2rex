"""
Class holding all export modules.
"""

import os
import sys
import logging
import tempfile
import shutil
import b2rexpkg

from b2rexpkg.siminfo import GridInfo
from b2rexpkg.simconnection import SimConnection
if sys.version_info[0] == 2:
    from b2rexpkg.ogre_exporter import OgreExporter
    from .b24.hooks import reset_uuids
else:
    class DummyExporter():
        pass
    from b2rexpkg.b25.ogre_exporter import OgreExporter
    def reset_uuids(*args):
        pass

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

    def doExport(self, exportSettings, location):
        """
        Export Action
        """
        tempfile.gettempdir()
        self.exportSettings = exportSettings
        base_url = self.exportSettings.server_url
        pack_name = self.exportSettings.pack
        export_dir = self.getExportDir()

        self.addStatus("Exporting to " + export_dir, 'IMMEDIATE')

        destfolder = os.path.join(export_dir, 'b2rx_export')
        if not os.path.exists(destfolder):
            os.makedirs(destfolder)
        else:
            shutil.rmtree(destfolder)
            os.makedirs(destfolder)

        x, y, z = location

        self.export(destfolder, pack_name, [x, y, z], self.exportSettings)
        dest_file = os.path.join(export_dir, "world_pack.zip")
        self.packTo(destfolder, dest_file)

        self.addStatus("Exported to " + dest_file)

    def getExportDir(self):
        """
        Get export directory.
        """
        export_dir = self.exportSettings.path
        if not export_dir:
            export_dir = tempfile.tempdir
        return export_dir

    def packTo(self, from_path, to_zip):
        """
        Pack a directory to a file.
        """
        import zipfile
        zfile = zipfile.ZipFile(to_zip, "w", zipfile.ZIP_DEFLATED)
        for dirpath, dirnames, filenames in os.walk(from_path):
            for name in filenames:
                file_path = os.path.join(dirpath,  name)
                zfile.write(file_path, file_path[len(from_path+"/"):])
        zfile.close()

    def doUpload(self):
        """
        Upload Action
        """
        base_url = self.exportSettings.server_url
        pack_name = self.exportSettings.pack
        if not self.region_uuid:
            self.addStatus("Error: No region selected ", 'ERROR')
            return
        self.addStatus("Uploading to " + base_url, 'IMMEDIATE')
        export_dir = self.getExportDir()
        res = self.sim.sceneUpload(self.region_uuid,
                                                           pack_name,
                                   os.path.join(export_dir, "world_pack.zip"))
        if res.has_key('success') and res['success'] == True:
            self.addStatus("Uploaded to " + base_url)
        else:
            self.addStatus("Error: Something went wrong uploading", 'ERROR')


