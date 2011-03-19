"""
 RexLogicModule: Support for rex logic system
"""
from .base import SyncModule

from b2rexpkg.tools import rexio

#from .props.rexlogic import RexLogicProps

import bpy

class RexComponent(object):
    def __init__(self, obj):
        self._obj = obj
    def _get_attribute_names(self):
        return self._attribute_names
    attribute_names = property(_get_attribute_names)

class NameComponent(RexComponent):
    type = 'EC_Name'
    _attribute_names = ['name', 'description']
    def _get_name(self):
        return self._obj.name
    name = property(_get_name)
    def _get_description(self):
        return 'blender object'
    description = property(_get_description)

class RexLogicModule(SyncModule):
    def register(self, parent):
        """
        Register this module with the editor
        """
        setattr(bpy.types.B2RexObjectProps, 'components',
                property(self.get_entity_components))

    def unregister(self, parent):
        """
        Unregister this module from the editor
        """
        if hasattr(bpy.types.B2RexObjectProps, 'components'):
            delattr(bpy.types.B2RexObjectProps, 'components')

    def find_components(self, obj):
        return [NameComponent(obj)]

    def get_entity_components(self, opensim_data):
        if not opensim_data.uuid:
            return []
        obj = self._parent.findWithUUID(opensim_data.uuid)
        return self.find_components(obj)
    #parent.registerCommand('CoarseLocationUpdate', self.processCoarseLocationUpdate)


