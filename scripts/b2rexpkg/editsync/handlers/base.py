"""
 Base class for editsync modules.
"""

import bpy

class SyncModule(object):
    _expand = False
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
    def expand(self, box):
        if self._expand:
            box.operator('b2rex.section', icon="TRIA_DOWN", text=self.getName(),
                     emboss=True).section = self.getName()
        else:
            box.operator("b2rex.section", icon="TRIA_RIGHT", text=self.getName(),
                     emboss=True).section = self.getName()
        return self._expand

    """
    The following can be defined for getting called in specific
    moments.

    def draw(self, layout, editor, props):
    def draw_object(self, layout, editor, obj):
    def check(self, starttime, budget):
    """

