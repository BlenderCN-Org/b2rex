from .base import SyncModule

import bpy

class RegionHandshakeModule(SyncModule):
    def register(self, parent):
        parent.registerCommand('RegionHandshake', self.processRegionHandshake)

    def unregister(self, parent):
        parent.unregisterCommand('RegionHandshake')

    def processRegionHandshake(self, regionID, pars):
        print("REGION HANDSHAKE", pars)


