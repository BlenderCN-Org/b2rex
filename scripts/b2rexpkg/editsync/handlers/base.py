"""
 Base class for editsync modules.
"""

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
        """
        Called when setting the module properties
        """
        self._props = props
    def onToggleRt(self, enabled):
        """
        Called when agent is enabled or disabled.
        """
        self._props = self._parent.exportSettings
        if enabled:
            self.simrt = self._parent.simrt
            self.workpool = self._parent.workpool
        else:
            self.simrt = None
            self.workpool = None
    def register(self, parent):
        """
        Called when the module is registered with the system.
        """
        pass
    def unregister(self, parent):
        """
        Called when the module is unregistered from the system:
        """
        pass
    """
    The following can be defined for getting called in specific
    moments.

    def draw(self, layout, session, props):
    def check(self, starttime, budget):
    """

