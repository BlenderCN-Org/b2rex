import bpy

class Connect(bpy.types.Operator):
    bl_idname = "b2rex.connect"
    bl_label = "Connect"
    def __init__(self, context):
        pass

    def execute(self, context):
        bpy.b2rex_session.onConnect(context)
        return {'FINISHED'}

class Export(bpy.types.Operator):
    bl_idname = "b2rex.export"
    bl_label = "export"

    def execute(self, context):
        bpy.b2rex_session.onExport(context)
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


class Settings(bpy.types.Operator):
    bl_idname = "b2rex.settings"
    bl_label = "Settings"

    def execute(self, context):
        bpy.b2rex_session.onSettings(context)
        return {'FINISHED'}
        

