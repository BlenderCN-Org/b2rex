"""
 Main panel managing the connection.
"""

import bpy
import testthread

class ConnectionPanel(bpy.types.Panel):
    bl_label = "b2rex" #baseapp.title
    #bl_space_type = "VIEW_3D"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    #bl_region_type = "UI"
    bl_context = "scene"
    bl_idname = "b2rex"
    cb_pixel = None
    cb_view = None
#    bpy.types.Scene.b2rex_props = bpy.props.PointerProperty(type = B2RexProps)
#    B2RexProps.serverurl = bpy.props.StringProperty(description="url:serverurl")

#    def __init__(self, x):
#        self.serverurl = "localhost:9000"
#        self.amount = 10
#        self.icon_list = create_icon_list()
    
    def __del__(self):
        testthread.running = False
        print("byez!")

    def draw_callback_view(self, context):
        pass # we dont really want this callback, but keeps the object
        # from dying all the time so we keep it for now

    def draw(self, context):
        if self.cb_pixel == None:
            # callback is important so object doesnt die ?
            self.cb_view = context.region.callback_add(self.draw_callback_view, 
                                        (context, ),
                                        'POST_VIEW') # XXX POST_PIXEL ;)
        
        layout = self.layout
        props = context.scene.b2rex_props
        session = bpy.b2rex_session

        box = layout.box()
        box.operator("b2rex.connect", text="Connect")
        box.operator("b2rex.export", text="Export")
        row = layout.row()
        row = box.row() 
        row.label(text="Status: "+bpy.context.scene.b2rex_props.status)
        row = layout.row() 

        if len(props.regions):
            row.template_list(props, 'regions', props, 'selected_region', rows=2)
        if props.selected_region > -1:
            box = layout.row()
            col = box.column()
            col.operator("b2rex.export", text="Export/Upload")
            col = box.column()
            col.operator("b2rex.export", text="Upload")
            box = layout.row()
            col = box.column()
            col.operator("b2rex.export", text="Clear")
            col = box.column()
            col.operator("b2rex.check", text="Check")
            box = layout.row()
            col = box.column()
            col.operator("b2rex.import", text="Sync")
            col = box.column()
            col.operator("b2rex.import", text="Import")

        row = layout.row()

        for k in session.region_report:
            row.label(text=k)
            row = layout.row()

        box = layout.row()
        row = layout.row()
        if not bpy.context.scene.b2rex_props.expand:
            row.prop(bpy.context.scene.b2rex_props,"expand", icon="TRIA_DOWN", text="Settings", emboss=False)
            row = layout.row()
            row.operator("b2rex.export", text="Export")
            row = layout.row()
            row.prop(bpy.context.scene.b2rex_props,"pack")
            row = layout.row()
            row.prop(bpy.context.scene.b2rex_props,"path")
            row = layout.row()
            row.prop(bpy.context.scene.b2rex_props,"server_url")
            row = layout.row()
            row.prop(bpy.context.scene.b2rex_props,"username")
            row = layout.row()
            row.prop(bpy.context.scene.b2rex_props,"password")
            box = layout.row()
            box.prop(bpy.context.scene.b2rex_props,"loc")

            box = layout.row()
            col = box.column()
            col.prop(bpy.context.scene.b2rex_props,"regenMaterials")
            col = box.column()
            col.prop(bpy.context.scene.b2rex_props,"regenObjects")

            box = layout.row()
            col = box.column()
            col.prop(bpy.context.scene.b2rex_props,"regenTextures")
            col = box.column()
            col.prop(bpy.context.scene.b2rex_props,"regenMeshes")
            
        else:
            row.prop(bpy.context.scene.b2rex_props,"expand", icon="TRIA_RIGHT", text="Settings", emboss=False)
