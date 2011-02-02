# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

import traceback
#
#from b2rexpkg.settings import ExportSettings
from b2rexpkg.siminfo import GridInfo
#from b2rexpkg.tools.selectable import SelectablePack, SelectableRegion
from b2rexpkg.importer import Importer

ERROR = 0
OK = 1
IMMEDIATE = 2
import bpy

class B2RexRegions(bpy.types.IDPropertyGroup):
    pass
class B2Rex(Importer):
    
    
    def __init__(self, context):
        pass
        #BaseApplication.__init__(self)
        #self.addStatus("b2rex started")
        self.gridinfo = GridInfo()
        Importer.__init__(self, self.gridinfo)

    def connect(self, base_url, username="", password=""):
   #     self.sim.connect(base_url)
        self.addStatus("Connecting to " + base_url, IMMEDIATE)
        self.gridinfo.connect(base_url, username, password)
        self.region_uuid = ''
        self.regionLayout = None
        try:
            self.regions = self.gridinfo.getRegions()
            self.griddata = self.gridinfo.getGridInfo()
        except:
            self.addStatus("Error: couldnt connect to " + base_url, ERROR)
            traceback.print_exc()
            return
#        self.addRegionsPanel(regions, griddata)
        # create the regions panel
        self.addStatus("Connected to " + self.griddata['gridnick'])
     

        print("conecttt")
    def _import(self):
        text = self.import_region(self.region_uuid)
        self.addStatus("Scene imported " + self.region_uuid)
    def export(self):
        print("conecttt")
    def settings(self):
        print("conecttt")
    def addStatus(self, status, level=0):
        bpy.context.scene.b2rex_props.status = status

#        Blender.Draw.Draw()

        
#    def addStatus(self, text, level = OK)


bl_addon_info = {
    'name': 'b2rex',
    'author': 'Crouch, N.tox, PKHG, Campbell Barton, Dany Lebel',
    'version': (1, 4, 2),
    'blender': (2, 5, 6),
    'api': 33928,
    'location': 'Text window > Properties panel (ctrl+F) or '\
        'Console > Console menu',
    'warning': '',
    'description': 'Click an icon to display its name and copy it '\
        'to the clipboard',
    'wiki_url': 'http://wiki.blender.org/index.php/Extensions:2.5/'\
        'Py/Scripts/System/Display_All_Icons',
    'tracker_url': 'http://projects.blender.org/tracker/index.php?'\
        'func=detail&aid=22011&group_id=153&atid=469',
    'category': 'System'}


#from b2rexpkg.baseapp import BaseApplication
#from b2rexpkg.siminfo import GridInfo


def addProperties(B2RexProps):
    from bpy.props import StringProperty, PointerProperty, IntProperty, BoolProperty, FloatProperty, CollectionProperty
    bpy.types.Scene.b2rex_props = PointerProperty(type=B2RexProps, name="b2rex props")

    #B2RexProps.credentials = PasswordManager("b2rex")
    B2RexProps.path = StringProperty(name='path', default='')
    B2RexProps.pack = StringProperty(name='pack', default='pack')
    B2RexProps.username = StringProperty(name='username', default='invi invi')
    B2RexProps.password = StringProperty(name='password', default='invi')
    B2RexProps.server_url = StringProperty(name='server url', default='http://delirium:9000')
    B2RexProps.export_dir = StringProperty(name='login password', default='') 
    B2RexProps.locX = FloatProperty(name="X", description="loc X", default=128.0,min=-10000.0,max=10000.0)
    B2RexProps.locY = FloatProperty(name="Y", description="loc X", default=128.0,min=-10000.0,max=10000.0)
    B2RexProps.locZ = FloatProperty(name="Z", description="loc X", default=128.0,min=-10000.0,max=10000.0)
    B2RexProps.regenMaterials = BoolProperty(name="Regen Material", default=False)
    B2RexProps.regenObjects = BoolProperty(name="Regen Objects", default=False)
    B2RexProps.regenTextures = BoolProperty(name="Regen Textures", default=False)
    B2RexProps.regenMeshes = BoolProperty(name="Regen Meshes", default=False)
    B2RexProps.expand = BoolProperty(default=False, description="Expand, to diesply")
    B2RexProps.status = StringProperty(default="b2rex started", description="Expand, to diesply")
    B2RexProps.selected_region = IntProperty(default=0, description="Expand, to diesply")
    B2RexProps.regions = CollectionProperty(type=B2RexRegions, name='Regions', description='Sessions on Renderfarm.fi')
#    B2RexProps.regions.name = StringProperty(name='Name', description='Name of the session', maxlen=128, default='[session]')


def delProperties():
    del bpy.types.WindowManager.b2rex_props



class Connect(B2Rex, bpy.types.Operator):
    bl_idname = "b2rex.connect"
    bl_label = "Connect"
    def __init__(self, context):
        pass
    def execute(self, context):
        session = bpy.b2rex_session
        props = context.scene.b2rex_props
        session.connect(props.server_url, props.username, props.password)
        while(len(props.regions) > 0):
            props.regions.remove(0)
        for key, region in session.regions.items():
            props.regions.add()
            regionss = props.regions[-1]
            regionss.name = region['name']
        return {'FINISHED'}

class Export(B2Rex, bpy.types.Operator):
    bl_idname = "b2rex.export"
    bl_label = "export"

    def execute(self, context):
  
        self.export()
        return {'FINISHED'}

class Settings(B2Rex, bpy.types.Operator):
    bl_idname = "b2rex.settings"
    bl_label = "Settings"

    def execute(self, context):
        
        self.settings()
        return {'FINISHED'}


class OBJECT_PT_b2rex(B2Rex, bpy.types.Panel):
    
    bl_label = "b2rex" #baseapp.title
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"
    bl_idname = "b2rex"

#    bpy.types.Scene.b2rex_props = bpy.props.PointerProperty(type = B2RexProps)
#    B2RexProps.serverurl = bpy.props.StringProperty(description="url:serverurl")

#    def __init__(self, x):
#        self.serverurl = "localhost:9000"
#        self.amount = 10
#        self.icon_list = create_icon_list()
    

    def draw(self, context):
        
        print(context.__class__)
        
        layout = self.layout
        props = context.scene.b2rex_props

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
            print("selected")
        print(props.selected_region)

#        box = layout.row()
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
            col = box.column()
            col.prop(bpy.context.scene.b2rex_props,"locX")
            col = box.column()
            col.prop(bpy.context.scene.b2rex_props,"locY")
            col = box.column()
            col.prop(bpy.context.scene.b2rex_props,"locZ")

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
            

#REGISTER FUNCTIONS
def register():
    class B2RexProps(bpy.types.IDPropertyGroup):
        pass
    addProperties(B2RexProps)
    bpy.b2rex_session = B2Rex(bpy.context.scene)
#    register_keymaps()

def unregister():
#    unregister_keymaps()
    delProperties()
    del bpy.b2rex_session


if __name__ == "__main__":
    registe()
