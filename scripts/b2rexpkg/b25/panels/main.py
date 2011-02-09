"""
 Main panel managing the connection.
"""

import bpy

from b2rexpkg.b25.ops import getLogLabel


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
    def __init__(self, context):
        bpy.types.Panel.__init__(self)
        # not the best place to set the loglevel :P
        bpy.ops.b2rex.loglevel(level=str(bpy.context.scene.b2rex_props.loglevel))
    def __del__(self):
        if bpy.b2rex_session.rt_on:
            bpy.b2rex_session.onToggleRt()
        print("byez!")

    def draw_callback_view(self, context):
        pass # we dont really want this callback, but keeps the object
        # from dying all the time so we keep it for now

    def draw(self, context):
        if self.cb_view == None:
            # callback is important so object doesnt die ?
            self.cb_view = context.region.callback_add(self.draw_callback_view, 
                                        (context, ),
                                        'POST_VIEW') # XXX POST_PIXEL ;)
        
        layout = self.layout
        props = context.scene.b2rex_props
        session = bpy.b2rex_session

        box = layout.box()
        if session.connected and session.rt_support:
            box_c = box.row()
            col = box_c.column()
            col.operator("b2rex.connect", text="Connect")
            col = box_c.column()
            col.alignment = 'RIGHT'
            if session.simrt and session.simrt.connected:
                col.operator("b2rex.toggle_rt", text="RT", icon='LAYER_ACTIVE')
            else:
                col.operator("b2rex.toggle_rt", text="RT", icon='LAYER_USED')
            if session.simrt:
                session.processView()
                bpy.ops.b2rex.processqueue()
            #col.prop(bpy.context.scene.b2rex_props, "rt_on", toggle=True)
        else:
            box.operator("b2rex.connect", text="Connect")
        box.operator("b2rex.export", text="Export")
        row = layout.row()
        row = box.row() 
        row.label(text="Status: "+session.status)
        if session.simrt:
            if session.agent_id:
                row = box.row() 
                row.label(text="agent: "+session.agent_id+" "+session.agent_access)



        if len(props.regions):
            row = layout.row() 
            row.template_list(props, 'regions', props, 'selected_region')
        if len(props.chat):
            row = layout.row() 
            row.label(text="Chat")
            row = layout.row() 
            row.template_list(props, 'chat', props, 'selected_chat',
                              rows=5)
            if props.next_chat:
                session.simrt.addCmd(["msg", props.next_chat])
                props.next_chat = ""
            row = layout.row()
            row.prop(props, 'next_chat')
        if props.selected_region > -1:
            box = layout.row()
            col = box.column()
            col.operator("b2rex.exportupload", text="Export/Upload")
            col = box.column()
            col.operator("b2rex.export", text="Upload")
            box = layout.row()
            col = box.column()
            col.operator("b2rex.export", text="Clear")
            col = box.column()
            col.operator("b2rex.check", text="Check")
            box = layout.row()
            col = box.column()
            col.operator("b2rex.sync", text="Sync")
            col = box.column()
            col.operator("b2rex.import", text="Import")

        row = layout.row()

        for k in session.region_report:
            row.label(text=k)
            row = layout.row()

        self.draw_stats(layout, session, props)
        self.draw_settings(layout, session, props)


    def draw_stats(self, layout, session, props):
        row = layout.row() 
        if not props.show_stats:
            row.prop(props,"show_stats", icon="TRIA_DOWN", text="Stats", emboss=False)
            box = layout.box()
            row = box.row() 
            row.label(text="cmds in: %d out: %d updates: %d"%tuple(session.stats[:3]))
            row = box.row() 
            row.label(text="http req: %d ok: %d"%tuple(session.stats[3:5]))
            row = box.row() 
            row.label(text="queue pending: %d last: %d workers: %d"%tuple(session.stats[5:8]))
            row = box.row() 
            row.label(text="updates cmd: %d view: %d"%tuple(session.stats[8:10]))
        else:
            row.prop(props,"show_stats", icon="TRIA_RIGHT", text="Stats", emboss=False)


    def draw_settings(self, layout, session, props):
        box = layout.row()
        row = layout.row()
        if not props.expand:
            row.prop(props,"expand", icon="TRIA_DOWN", text="Settings", emboss=False)
            for prop in ["pack", "path", "server_url", "username", "password",
                         "loc"]:
                row = layout.row()
                row.prop(props, prop)

            box = layout.row()
            col = box.column()
            col.prop(props,"regenMaterials")
            col = box.column()
            col.prop(props,"regenObjects")

            box = layout.row()
            col = box.column()
            col.prop(props,"regenTextures")
            col = box.column()
            col.prop(props,"regenMeshes")
            box = layout.row()
            box.operator_menu_enum("b2rex.loglevel", 'level', icon='INFO',
                                   text=getLogLabel(props.loglevel))
            box = layout.row()
            box.prop(props, "kbytesPerSecond")
            box = layout.row()
            box.prop(props, "rt_budget")
            box = layout.row()
            box.prop(props, "pool_workers")
        else:
            row.prop(props,"expand", icon="TRIA_RIGHT", text="Settings", emboss=False)
