from .base import SyncModule

import bpy

class OnlineModule(SyncModule):
    def register(self, parent):
        parent.registerCommand('OfflineNotification',
                             self.processOfflineNotification)
        parent.registerCommand('OnlineNotification',
                             self.processOnlineNotification)
    def unregister(self, parent):
        parent.unregisterCommand('OfflineNotification')
        parent.unregisterCommand('OnlineNotification')

    def processOnlineNotification(self, agentID):
        self.Agents[agentID] = agentID

    def processOfflineNotification(self, agentID):
        pass # should get a kill..
        # self._agents[agentID] = agentID


