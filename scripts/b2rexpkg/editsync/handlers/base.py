import bpy

class SyncModule(object):
    def __init__(self, parent):
        self._parent = parent
    def getName(self):
        """
        Return the name under which this handler should be registered.
        """
        return self.__class__.__name__.replace("Module", "")
    def setProperties(self, props):
        self._props = props
    def onToggleRt(self, enabled):
        self._props = self._parent.exportSettings
        if enabled:
            self.simrt = self._parent.simrt
        else:
            self.simrt = None
    def check(self, starttime, budget):
        pass
    def register(self, parent):
        pass
    def unregister(self, parent):
        pass
    def draw(self, layout, session, props):
        pass
