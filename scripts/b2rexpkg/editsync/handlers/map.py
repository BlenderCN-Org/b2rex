from .base import SyncModule

import bpy

class MapModule(SyncModule):
    def register(self, parent):
        parent.registerCommand('CoarseLocationUpdate', self.processCoarseLocationUpdate)

    def unregister(self, parent):
        parent.unregisterCommand('CoarseLocationUpdate')

    def processCoarseLocationUpdate(self, agent_id, pos):
        #print("COARSE LOCATION UPDATE", agent_id, pos)
        pass

