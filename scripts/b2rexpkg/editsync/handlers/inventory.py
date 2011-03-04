"""
 InventoryModule: Manages inventoy inside the editor and provides operations
 for putting items in and out of inventory.
"""
import uuid
import logging

import bpy
from bpy.props import BoolProperty

from .base import SyncModule


logger = logging.getLogger('b2rex.InventoryModule')

class InventoryModule(SyncModule):
    def register(self, parent):
        """
        Register this module with the editor
        """
        parent.registerCommand('InventorySkeleton', self.processInventorySkeleton)
        parent.registerCommand('InventoryDescendents', self.processInventoryDescendents)

    def unregister(self, parent):
        """
        Unregister this module from the editor
        """
        parent.unregisterCommand('InventorySkeleton')
        parent.unregisterCommand('InventoryDescendents')

    def update_folders(self, folders):
        """
        Update the available folders with the given folder dict.
        """
        props = bpy.context.scene.b2rex_props
        cached_folders = getattr(props, 'folders')
        cached_folders.clear()
        
        for folder in folders:
            expand_prop = "e_" + str(folder['FolderID']).split('-')[0]
            if not hasattr(bpy.types.B2RexProps, expand_prop):
                prop = BoolProperty(name="expand", default=False)
                setattr(bpy.types.B2RexProps, expand_prop, prop)

            if folder['Descendents'] < 1:
                setattr(props, expand_prop, False)

            cached_folders[folder['FolderID']] = folder

    def update_items(self, items):
        """
        Update the available items from the fiven item dict.
        """
        props = bpy.context.scene.b2rex_props
        cached_items = props._items
        cached_items.clear()
        for item in items:
            cached_items[item['ItemID']] = item

    def processInventoryDescendents(self, folder_id, folders, items):
        """
        Inventory descendents arrived from the sim.
        """
        logger.debug("processInventoryDescendents")
        self.update_folders(folders)
        self.update_items(items)

    def __iter__(self):
        props = bpy.context.scene.b2rex_props
        return iter(props._items.values())

    def __contains__(self, itemID):
        props = bpy.context.scene.b2rex_props
        return itemID in props._items

    def __getitem__(self, itemID):
        props = bpy.context.scene.b2rex_props
        return props._items[itemID]

    def processInventorySkeleton(self, inventory):
        """
        Inventory skeleton arrived from the sim.
        """
        logger.debug("processInventorySkeleton")

        props = bpy.context.scene.b2rex_props
        session = bpy.b2rex_session
        B2RexProps = bpy.types.B2RexProps

        if not hasattr(B2RexProps, 'folders'):
            setattr(B2RexProps, 'folders',  dict())
        if not hasattr(B2RexProps, '_items'):
            setattr(B2RexProps, '_items', dict())

        for inv in inventory:
            session.simrt.FetchInventoryDescendents(inv['folder_id'])
            if uuid.UUID(inv['parent_id']).int == 0:
                if not hasattr(B2RexProps, "root_folder"):
                    setattr(B2RexProps, "root_folder", inv['folder_id'])
                setattr(props, "root_folder", inv['folder_id'])


        session.inventory = inventory

    def draw(self, layout, session, props):
        """
        Draw the inventory panel into the given layout.
        """
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
            self.draw_folder(layout, root_folder, 0)

    def draw_folder(self, layout, folder_id, indent):
        """
        Draw an inventory folder into the given layout.
        """
 
        props = bpy.context.scene.b2rex_props
    
        folders = dict()
        items = dict()
        if hasattr(bpy.types.B2RexProps, 'folders'):
            folders = getattr(props, 'folders')

        if hasattr(bpy.types.B2RexProps, '_items'):
            items = getattr(props, '_items')

        if not folder_id in folders:
            return

        folder = folders[folder_id]

        session = bpy.b2rex_session
        row = layout.row()

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
                        self.draw_folder(layout, _id, indent + 1) 
                for i_if,item in items.items():
                    if item['FolderID'] == folder_id:
                        count += 1
                        row = layout.row()
                        for i in range(indent + 1):
                            row.separator()
                        if item['InvType'] == 6:
                            row.label(text=item['Name'], icon='OBJECT_DATA')
                            row.operator('b2rex.localview', text="", icon='MUTE_IPO_OFF', emboss=False).item_id=str(item['ItemID']) 
                            row.operator('b2rex.rezobject', text="", icon='PARTICLE_DATA', emboss=False).item_id=str(item['ItemID']) 
                            row.operator('b2rex.removeinventoryitem', text="", icon='ZOOMOUT', emboss=False).item_id=str(item['ItemID']) 
                        elif item['InvType'] == 10:
                            row.label(text=item['Name'], icon='WORDWRAP_ON')
                            if not session.Scripting.find_text(item['ItemID']):
                                op = row.operator('b2rex.requestasset', text="",
                                             icon='PARTICLE_DATA',
                                             emboss=False)
                                op.asset_id=str(item['AssetID'])
                                op.asset_type = 10 # LLSD Script
                            #row.label(text=item['Name'], icon='SCRIPT')
                        else:
                            row.label(text=item['Name'] + str(item['InvType']))
      
                
                if count < folder['Descendents'] or folder['Descendents'] == -1:
                    row = layout.row()
                    for i in range(indent + 1):
                        row.separator()
                    row.label(text="Loading...")
  
                oper.expand = False

            oper.folder_id = folder_id
        else:
            row.label(text="Loading.......")
 
