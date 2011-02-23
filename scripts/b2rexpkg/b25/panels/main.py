"""
 Main panel managing the connection.
"""

import bpy
import uuid

from b2rexpkg.b25.ops import getLogLabel
#from ..properties import B2RexProps

simstats_labels = ["X", "Y", "Flags", "ObjectCapacity", "TimeDilation",
                   "SimFPS", "PhysicsFPS", "AgentUpdates", "Agents",
                   "ChildAgents", "TotalPrim", "ActivePrim", "FrameMS", "NetMS",
                  "PhysicsMS", "ImageMS", "OtherMS", "InPacketsPerSecond",
                   "OutPacketsPerSecond", "UnAckedBytes", "AgentMS",
                   "PendingDownloads", "PendingUploads", "ActiveScripts",
                   "ScriptLinesPerSecond"]

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

    def draw_connection_panel(self, layout, session, props):
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
            if session.simrt and False: # now done on menu
                session.processView()
                bpy.ops.b2rex.processqueue()
            #col.prop(bpy.context.scene.b2rex_props, "rt_on", toggle=True)
        else:
            box.operator("b2rex.connect", text="Connect")
        box.operator("b2rex.export", text="Export")

        box.label(text="Status: "+session.status)

    def draw_chat(self, layout, session, props):
        if not len(props.chat):
            return
        row = layout.column()
        if props.chat_expand:
            row.prop(props, 'chat_expand', icon="TRIA_DOWN", text="Chat")
        else:
            row.prop(props, 'chat_expand', icon="TRIA_RIGHT", text="Chat")
            return

        row = layout.row() 
        row.label(text="Chat")
        row = layout.row() 
        row.template_list(props, 'chat', props, 'selected_chat',
                          rows=5)
        row = layout.row()
        row.prop(props, 'next_chat')

    def draw_connections(self, layout, session, props):
        box = layout.box()
        row = box.row()
        if len(props.connection.list):
            row.prop_search(props.connection, 'search', props.connection,
                            'list', icon='SCRIPTWIN',text='connection')
            if props.connection.search in ['add', 'edit']:
                pass
            else:
                row.operator("b2rex.addconnection", text="", icon='SETTINGS',
                             emboss=False).action = "edit"
                row.operator("b2rex.addconnection", text="", icon='ZOOMOUT',
                             emboss=False).action = "delete"
                row.operator("b2rex.addconnection", text="", icon='ZOOMIN',
                             emboss=False).action = "create"
                if props.connection.search and props.connection.search in props.connection.list:
                    col = row.column()
                    col.alignment = 'RIGHT'
                    if session.simrt:
                        if session.simrt.connected:
                            col.operator("b2rex.toggle_rt", text="RT",
                                         icon='PMARKER_ACT')
                        else:
                            col.operator("b2rex.toggle_rt", text="RT",
                                         icon='PMARKER_SEL')
                    else:
                        col.operator("b2rex.toggle_rt", text="RT", icon='PMARKER')

        if not len(props.connection.list) or props.connection.search in ['add', 'edit']:
            if not len(props.connection.list):
                row.label("New connection")
            box_c = box.box()
            form = props.connection.form
            box_c.prop(form, "name")
            box_c.prop(form, "url")
            box_c.prop(form, "username")
            box_c.prop(form, "password")
            if form.url and form.username and form.password:
                if form.name in props.connection.list:
                    text = "Save"
                else:
                    text = "Add"
                box_c.operator("b2rex.addconnection", text=text, icon='FILE_TICK').action = "add"
            if len(props.connection.list):
                box_c.operator("b2rex.addconnection", text="Cancel",
                               icon='CANCEL').action = "cancel"
        box.label(text="Status: "+session.status)

            #row.prop_enum(props.connection, 'list')
            #           row.template_list(props.connection, 'list', props.connection,
            #                 'selected', type='COMPACT')


    def draw_regions(self, layout, session, props):
        row = layout.column()
        if not len(props.regions):
            return
        if props.regions_expand:
            row.prop(props, 'regions_expand', icon="TRIA_DOWN", text="Regions")
        else:
            row.prop(props, 'regions_expand', icon="TRIA_RIGHT", text="Regions")
            return

        row = layout.row() 
        row.template_list(props, 'regions', props, 'selected_region')
        if props.selected_region > -1:
            col = layout.column_flow(0)
            col.operator("b2rex.exportupload", text="Export/Upload")
            col.operator("b2rex.export", text="Upload")
            col.operator("b2rex.export", text="Clear")
            col.operator("b2rex.check", text="Check")
            col.operator("b2rex.sync", text="Sync")
            col.operator("b2rex.import", text="Import")

        row = layout.column()
        for k in session.region_report:
            row.label(text=k)


    def draw(self, context):
        if self.cb_view == None:
            # callback is important so object doesnt die ?
            self.cb_view = context.region.callback_add(self.draw_callback_view, 
                                        (context, ),
                                        'POST_VIEW') # XXX POST_PIXEL ;)
        
        layout = self.layout
        props = context.scene.b2rex_props
        session = bpy.b2rex_session

        #self.draw_connection_panel(layout, session, props)
        self.draw_connections(layout, session, props)

        self.draw_chat(layout, session, props)
        self.draw_inventory(layout, session, props)
        self.draw_regions(layout, session, props)

        self.draw_stats(layout, session, props)
        self.draw_settings(layout, session, props)

    def draw_folder(self, folder_id, indent):
 
        props = bpy.context.scene.b2rex_props
    
        folders = dict()
        items = dict()
        if hasattr(bpy.types.B2RexProps, 'folders'):
            folders = getattr(props, 'folders')

        if hasattr(bpy.types.B2RexProps, '_items'):
            items = getattr(props, '_items')

        folder = folders[folder_id]

        session = bpy.b2rex_session
        row = self.layout.row()

        for i in range(indent):
            row.separator()

        if folder['Descendents'] > -1:
            name = folder['Name'] + " (" + str(folder['Descendents']) + " children)"
        elif folder['Descendents'] == 0:
            name = folder['Name'] + " (empty)"
        elif folder['Descendents'] == -1:
            name = folder['Name'] + " (? children)"

        folder_expand = "e_" +  str(folder_id).split('-')[0]
        if hasattr(bpy.types.B2RexProps, folder_expand):
            if folder['Descendents'] == 0: 
                oper = row.operator('b2rex.folder', text=name, icon='RIGHTARROW_THIN', emboss=False)
                oper.expand = False
                return
            if not getattr(props, folder_expand):
                oper = row.operator('b2rex.folder', text=name, icon='TRIA_RIGHT', emboss=False)
                oper.expand = True
            else:
                oper = row.operator('b2rex.folder', text=name, icon='TRIA_DOWN', emboss=False)
                count = 0
                for _id,_folder in folders.items():
                    if _folder['ParentID'] == folder_id:
                        count += 1
                        self.draw_folder(_id, indent + 1) 
                for i_if,item in items.items():
                    if item['FolderID'] == folder_id:
                        count += 1
                        row = self.layout.row()
                        for i in range(indent + 1):
                            row.separator()
                        if item['InvType'] == 6:
                            row.label(text=item['Name'], icon='OBJECT_DATA')
                            row.operator('b2rex.rezobject', text="", icon='PARTICLE_DATA', emboss=True).item_id=str(item['ItemID']) 
                        else:
                            row.label(text=item['Name'] + str(item['InvType']))
      
                
                if count < folder['Descendents'] or folder['Descendents'] == -1:
                    row = self.layout.row()
                    for i in range(indent + 1):
                        row.separator()
                    row.label(text="Loading...")
  
                oper.expand = False

            oper.folder_id = folder_id
        else:
            row.label(text="Loading.......")
        
    def draw_inventory(self, layout, session, props):
        row = layout.column()
        row.alignment = 'CENTER'
        if not hasattr(session, 'inventory'):
            return
        if props.inventory_expand:
            row.prop(props, 'inventory_expand', icon="TRIA_DOWN", text="Inventory")
        else:
            row.prop(props, 'inventory_expand', icon="TRIA_RIGHT", text="Inventory")
            return
            
        try:
            inventory = session.inventory
        except:
            row = layout.column()
            row.label(text='Inventory not loaded')
            return

        
        if hasattr(bpy.types.B2RexProps, "root_folder"): 
            root_folder = getattr(props, "root_folder")
            self.draw_folder(root_folder, 0)

    def draw_stats(self, layout, session, props):
        row = layout.row() 
        if props.show_stats:
            row.prop(props,"show_stats", icon="TRIA_DOWN", text="Stats",
                     emboss=True)
            box = layout.box()
            if session.simrt:
                if session.agent_id:
                    box.label(text="agent: "+session.agent_id+" "+session.agent_access)

            box.label(text="cmds in: %d out: %d updates: %d"%tuple(session.stats[:3]))
            box.label(text="http requests: %d ok: %d"%tuple(session.stats[3:5]))
            box.label(text="queue pending: %d last time: %d"%tuple(session.stats[5:7])+" last sec: "+str(session.second_budget))
            box.label(text="threads workers: "+str(session.stats[7]))
            box.label(text="updates cmd: %d view: %d"%tuple(session.stats[8:10]))
            if session.simstats:
                for idx, a in enumerate(session.simstats):
                    box.label(text=simstats_labels[idx]+": "+str(a))
        else:
            row.prop(props,"show_stats", icon="TRIA_RIGHT", text="Stats",
                     emboss=True)


    def draw_settings(self, layout, session, props):
        row = layout.row()
        if props.expand:
            row.prop(props,"expand", icon="TRIA_DOWN", text="Settings",
                     emboss=True)
            for prop in ['agent_libs_path',"pack", "path", "loc"]: #"server_url", "username", "password",
                row = layout.row()
                row.prop(props, prop)

            col = layout.column_flow()
            col.prop(props,"regenMaterials")
            col.prop(props,"regenObjects")

            col.prop(props,"regenTextures")
            col.prop(props,"regenMeshes")

            box = layout.row()
            box.operator_menu_enum("b2rex.loglevel", 'level', icon='INFO',
                                   text=getLogLabel(props.loglevel))
            box = layout.row()
            box.prop(props, "kbytesPerSecond")
            box = layout.row()
            box.prop(props, "rt_budget")
            box = layout.row()
            box.prop(props, "rt_sec_budget")
            box = layout.row()
            box.prop(props, "pool_workers")
            box = layout.row()
            box.prop(props, "terrainLOD")
        else:
            row.prop(props,"expand", icon="TRIA_RIGHT", text="Settings",
                     emboss=True)
