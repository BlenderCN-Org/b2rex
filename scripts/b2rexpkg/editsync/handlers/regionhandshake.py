"""
 RegionHandshakeModule: Process RegionHandshake commands.
"""

from .base import SyncModule

import bpy

class RegionHandshakeModule(SyncModule):
    def register(self, parent):
        """
        Register this module with the editor
        """
        parent.registerCommand('RegionHandshake', self.processRegionHandshake)

    def unregister(self, parent):
        """
        Unregister this module from the editor
        """
        parent.unregisterCommand('RegionHandshake')

    def processRegionHandshake(self, regionID, pars):
        print("REGION HANDSHAKE", pars)


