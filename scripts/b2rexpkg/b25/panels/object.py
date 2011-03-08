"""
 Object tools panel.
"""

import bpy

col_enum_list = [("None", "None", ""), ("Transfer", "Transfer", "")]
mask_enum = {"Transfer" : 1 << 13,"Modify" : 1 << 14,"Copy" : 1 << 15,"Move" : 1 << 19,"Damage" : 1 << 20}


class ObjectPropertiesPanel(bpy.types.Panel):
    bl_label = "OpenSim" #baseapp.title
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_idname = "b2rex.panel.object"

    def draw_permissions_box(self, obj):
        if not hasattr(obj.opensim, 'EveryoneMask'):
            return
        layout = self.layout
        box = layout.box()
        row = box.row()
        expand = obj.opensim.everyonemask_expand
        if expand:
            row.prop(obj.opensim, 'everyonemask_expand', icon="TRIA_DOWN", text='Everyone Permissions', emboss=False)
            for perm, mask in mask_enum.items():
                row = box.row() 
                if getattr(obj.opensim, 'EveryoneMask') & mask: 
                    row.operator("b2rex.setmaskoff", text=perm, icon='LAYER_ACTIVE', emboss=False).mask = mask
                else:
                    row.operator("b2rex.setmaskon", text=perm, icon='LAYER_USED', emboss=False).mask = mask
        else:
            row.prop(obj.opensim, 'everyonemask_expand', icon="TRIA_RIGHT", text='Everyone Permissions', emboss=False)

    def draw(self, context):
        layout = self.layout
        props = context.scene.b2rex_props
        session = bpy.b2rex_session

        if not session.simrt:
            box = self.layout.box()
            box.label("Not connected yet")
            for obj in context.selected_objects:
                self.draw_prim(box, obj)
            return

        box = layout.box()
        for obj in context.selected_objects:
            if obj.name.startswith("terrain"):
                self.draw_terrain(box, obj)
            else:
                self.draw_object(box, obj)

    def draw_prim(self, box, obj):
        props = obj.data.opensim.prim
        box.label(text="Prim Parameters")
        box.prop(props, 'extrapolationType')
        box.prop(props, 'sides')
        box.prop(props, 'hollowSides')
        box.prop(props, 'hollow')
        row = box.row()
        row.prop(props, 'profile')
        row = box.row()
        row.prop(props, 'twist')
        row = box.row()
        row.prop(props, 'topShear')
        row = box.row()
        row.prop(props, 'pathCut')
        row = box.row()
        row.prop(props, 'taper')
        # row = box.row()
        # row.prop(props, 'dimpleBegin')
        # row.prop(props, 'dimpleEnd')
        if props.extrapolationType == 'CIRCULAR':
            box.prop(props, 'radius')
            box.prop(props, 'skew')
            row = box.row()
            row.prop(props, 'holeSize')
            box.prop(props, 'revolutions')
            box.prop(props, 'stepsPerRevolution')
        row = box.row()
        op = box.operator('b2rex.genprim')

    def draw_terrain(self, box, obj):
        terrain = bpy.b2rex_session.Terrain.terrain
        box.label(text="This is the region terrain.")
        box.label(text="Using lod %s with %s blocks"%(terrain.lod,
                                                      len(terrain.checksums)))

    def draw_object(self, box, obj):
        if obj.opensim.state == 'OK':
            box.label(text="%s"%(obj.opensim.name))
            if obj.type == 'MESH':
                box.label(text="  obj: %s"%(obj.opensim.uuid))
                box.label(text="  mesh: %s"%(obj.data.opensim.uuid))

            box.operator('b2rex.delete', text='Delete from simulator')
            box.operator('b2rex.derezobject', text='Take to inventory')

            self.draw_permissions_box(obj)

        elif obj.opensim.state == 'OFFLINE':
            box.operator('b2rex.exportupload', text='Upload to Sim')
        if not obj.opensim.state == 'OK':
            box.label(text='state: '+str(obj.opensim.state))


