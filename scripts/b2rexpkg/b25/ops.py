import bpy
from bpy.props import StringProperty, PointerProperty, IntProperty

from bpy.props import StringProperty, PointerProperty, IntProperty
from bpy.props import BoolProperty, FloatProperty, CollectionProperty
from bpy.props import FloatVectorProperty, EnumProperty

import logging

log_levels = ((str(logging.ERROR), 'Standard', 'standard level, show only errors'),
              (str(logging.CRITICAL), 'Critical', 'show only critical errors (least info)'),
              (str(logging.WARNING), 'Warning', 'show warnings or errors'),
              (str(logging.INFO), 'Info', 'show info or errors'),
              (str(logging.DEBUG), 'Debug', 'debug log level'))

def getLogLabel(level):
    level = str(level)
    loglevel = list(filter(lambda s: s[0] == level, log_levels))
    if loglevel:
        return loglevel[0][1]
    else:
        return log_levels[0][1]


class SetLogLevel(bpy.types.Operator):
    bl_idname = "b2rex.loglevel"
    bl_label = "LogLevel"
    level = EnumProperty(items=log_levels,
                         name='level',
                         default=str(logging.ERROR))
    def __init__(self, context):
        pass

    def getLabel(self):
        return getLogLabel(self.level)

    def execute(self, context):
        if not self.level:
            self.level = logging.ERROR
        context.scene.b2rex_props.loglevel = int(self.level)
        logging.getLogger('root').setLevel(int(self.level))
        for logger in logging.getLogger('root').manager.loggerDict.values():
            logger.setLevel(int(self.level))
        return {'FINISHED'}

class AddConnection(bpy.types.Operator):
    bl_idname = "b2rex.addconnection"
    bl_label = "Add"
    bl_description = "Perform an action on a connection"
    action = StringProperty(name="action",default='add')
    def __init__(self, context):
        pass
    def draw(self, context):
        self.bl_description = self.action+" the current connection"
        self.description = self.action+" the current connection"

    def execute(self, context):
        if self.action == 'add':
            bpy.b2rex_session.add_connection(context)
        elif self.action == 'edit':
            bpy.b2rex_session.edit_connection(context)
        elif self.action == 'cancel':
            bpy.b2rex_session.cancel_edit_connection(context)
        elif self.action == 'create':
            bpy.b2rex_session.create_connection(context)
        elif self.action == 'delete':
            bpy.b2rex_session.delete_connection(context)

        return {'FINISHED'}


class Connect(bpy.types.Operator):
    bl_idname = "b2rex.connect"
    bl_label = "connect"
    def __init__(self, context):
        pass

    def execute(self, context):
        bpy.b2rex_session.onconnect(context)
        return {'FINISHED'}

class Redraw(bpy.types.Operator):
    bl_idname = "b2rex.redraw"
    bl_label = "redraw"

    def invoke(self, context, event):
        for area in context.screen.areas:
            if area.type == 'INFO':
                area.tag_redraw()
        return {'RUNNING_MODAL'}
    def check(self, context):
        return True
    def execute(self, context):
        if not context.screen:
            print("not redrawing")
            return {'FINISHED'}
        for scene in bpy.data.scenes:
            # what is the best way to trigger a redraw?
            # only the stuff below the return doesnt seem
            # to always work.
            scene.name = scene.name
            return {'FINISHED'}
        return
        if context and context.screen:
            for area in context.screen.areas:
                if area.type in ['INFO', 'VIEW_3D']:
                    area.tag_redraw()
            return {'FINISHED'}
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == 'INFO':
                    area.tag_redraw()
        return {'FINISHED'}



class ToggleRt(bpy.types.Operator):
    bl_idname = "b2rex.toggle_rt"
    bl_label = "RT"

    def execute(self, context):
        bpy.b2rex_session.onToggleRt(context)
        return {'FINISHED'}

class Export(bpy.types.Operator):
    bl_idname = "b2rex.export"
    bl_label = "export"

    def execute(self, context):
        bpy.b2rex_session.onExport(context)
        return {'FINISHED'}

class ProcessQueue(bpy.types.Operator):
    bl_idname = "b2rex.processqueue"
    bl_label = "processqueue"

    def execute(self, context):
        bpy.b2rex_session.onProcessQueue(context)
        return {'FINISHED'}

class Delete(bpy.types.Operator):
    bl_idname = "b2rex.delete"
    bl_label = "delete"

    def execute(self, context):
        bpy.b2rex_session.onDelete(context)
        return {'FINISHED'}


class Upload(bpy.types.Operator):
    bl_idname = "b2rex.upload"
    bl_label = "upload"

    def execute(self, context):
        bpy.b2rex_session.onUpload(context)
        return {'FINISHED'}

class ExportUpload(bpy.types.Operator):
    bl_idname = "b2rex.exportupload"
    bl_label = "export+upload"

    def execute(self, context):
        bpy.b2rex_session.onExportUpload(context)
        return {'FINISHED'}

class Import(bpy.types.Operator):
    bl_idname = "b2rex.import"
    bl_label = "import"

    def execute(self, context):
        print('exec import')
        bpy.b2rex_session.onImport(context)
        return {'FINISHED'}

class Check(bpy.types.Operator):
    bl_idname = "b2rex.check"
    bl_label = "Check"

    def execute(self, context):
        bpy.b2rex_session.onCheck(context)
        return {'FINISHED'}

class Sync(bpy.types.Operator):
    bl_idname = "b2rex.sync"
    bl_label = "Sync"

    def execute(self, context):
        bpy.b2rex_session.onSync(context)
        return {'FINISHED'}

class Settings(bpy.types.Operator):
    bl_idname = "b2rex.settings"
    bl_label = "Settings"

    def execute(self, context):
        bpy.b2rex_session.onSettings(context)
        return {'FINISHED'}
        
class SetMaskOn(bpy.types.Operator):
    bl_idname = "b2rex.setmaskon"
    bl_label = "SetMaskOn"
    mask = bpy.props.IntProperty(name="Mask")
    def execute(self, context):
        simrt = bpy.b2rex_session.simrt
        for obj in context.selected_objects:
            simrt.UpdatePermissions(obj.opensim.uuid, self.mask, 1)
        
        return {'FINISHED'}
        
class SetMaskOff(bpy.types.Operator):
    bl_idname = "b2rex.setmaskoff"
    bl_label = "SetMaskOff"
    mask = bpy.props.IntProperty(name="Mask")

    def execute(self, context):
        simrt = bpy.b2rex_session.simrt
        for obj in context.selected_objects:
            simrt.UpdatePermissions(obj.opensim.uuid, self.mask, 0)
 
        return {'FINISHED'}
   

class FolderStatus(bpy.types.Operator):
    bl_idname = "b2rex.folder"
    bl_label = "Folder"
    expand = bpy.props.BoolProperty(name="Expand")
    folder_id = bpy.props.StringProperty(name="Folder ID")

    def execute(self, context):
        setattr(context.scene.b2rex_props, "e_" + self.folder_id.split('-')[0], self.expand)
        if self.expand == True:
            bpy.b2rex_session.simrt.FetchInventoryDescendents(self.folder_id)

        return {'FINISHED'}

class DeRezObject(bpy.types.Operator):
    bl_idname = "b2rex.derezobject"
    bl_label = "Take item to inventory"

    def execute(self, context):
        bpy.b2rex_session.onDeRezObject()
        bpy.b2rex_session.update_firstlevel()

        print("Execute")
        return {'FINISHED'}

class RezObject(bpy.types.Operator):
    bl_idname = "b2rex.rezobject"
    bl_label = "Take item from inventory"

    item_id = StringProperty(name="item_id")

    def execute(self, context):
        bpy.b2rex_session.onRezObject(self.item_id)
        return {'FINISHED'}

class RemoveInventoryItem(bpy.types.Operator):
    bl_idname = "b2rex.removeinventoryitem"
    bl_label = "Remove item from inventory"

    item_id = StringProperty(name="item_id")

    def execute(self, context):
        bpy.b2rex_session.onRemoveInventoryItem(self.item_id)
        return {'FINISHED'}

class LocalView(bpy.types.Operator):
    bl_idname = "b2rex.localview"
    bl_label = "Item local view"

    item_id = StringProperty(name="item_id")

    def execute(self, context):
        obj = bpy.b2rex_session.findWithUUID(self.item_id)
        bpy.ops.object.select_all(action="DESELECT")
        bpy.ops.object.select_name(name=obj.name, extend=False)
        
        #bpy.ops.view3d.localview()
    
        return {'FINISHED'}

