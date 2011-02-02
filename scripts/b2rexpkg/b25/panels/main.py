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
