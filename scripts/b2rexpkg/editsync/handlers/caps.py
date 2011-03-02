from .base import SyncModule

import bpy

class CapsModule(SyncModule):
    def register(self, parent):
        parent.registerCommand('capabilities', self.processCapabilities)

    def unregister(self, parent):
        parent.unregisterCommand('capabilities')

    def processCapabilities(self, caps):
        self._parent.caps = caps


