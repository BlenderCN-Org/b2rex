"""
 Main panel managing the connection.
"""

import bpy

from ..properties import B2RexObjectProps

from bpy.props import StringProperty, PointerProperty, IntProperty
from bpy.props import BoolProperty, FloatProperty, CollectionProperty
from bpy.props import FloatVectorProperty

handled_props = [StringProperty, IntProperty, BoolProperty, FloatProperty]

class ObjectPropertiesPanel(bpy.types.Panel):
    bl_label = "OpenSim" #baseapp.title
    bl_space_type = "VIEW_3D"
    #bl_space_type = "PROPERTIES"
    #bl_region_type = "WINDOW"
    bl_region_type = "UI"
    #bl_region_type = "TOOL_PROPS"
    #bl_context = "scene"
    bl_idname = "b2rex.panel.object"
    cb_pixel = None
    cb_view = None

    def draw(self, context):
        layout = self.layout
        props = context.scene.b2rex_props
        session = bpy.b2rex_session

        box = layout.box()
        for obj in context.selected_objects:
            row = box.row() 
            row.label(text="obj: %s"%(obj.opensim.uuid))
            if obj.type == 'MESH':
                row = box.row() 
                row.label(text="  mesh: %s"%(obj.data.opensim.uuid))

            for propname in set(dir(B2RexObjectProps)):
                aprop = getattr(B2RexObjectProps, propname)
                if propname.startswith("__"):
                    continue
                elif aprop.__class__ == tuple and aprop[0] in handled_props:
                    row = box.row()
                    row.prop(obj.opensim, propname)

        if session.simrt:
            row = box.row() 
            row.label(text="Updates: in:%d out:%d fin:%d"%tuple(session.stats[:3]))


