import bpy

class Connect(bpy.types.Operator):
    bl_idname = "b2rex.connect"
    bl_label = "Connect"
    def __init__(self, context):
        pass

    def execute(self, context):
        bpy.b2rex_session.onConnect(context)
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
        

