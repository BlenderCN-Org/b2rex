import traceback
import math
import uuid
from io import StringIO

from ..siminfo import GridInfo
from ..compatibility import BaseApplication
from ..tools.logger import logger
#from .properties import B2RexObjectProps
#from .properties import B2RexProps
from .material import RexMaterialIO

from bpy.props import StringProperty, PointerProperty, IntProperty
from bpy.props import BoolProperty, FloatProperty, CollectionProperty
from bpy.props import FloatVectorProperty
from b2rexpkg.tools.passmanager import PasswordManager

from b2rexpkg import IMMEDIATE, ERROR

import bpy

class MyFancyObject(bpy.types.ID):
    pass

class B2Rex(BaseApplication):
    def __init__(self, context):
        self.credentials = PasswordManager('b2rex')
        self.region_report = ''
        self.cb_pixel = []
        BaseApplication.__init__(self)

    def onConnect(self, context):
        props = context.scene.b2rex_props
        #self.connect(props.server_url, props.username, props.password)
        self.exportSettings = props
        self.onConnectAction()
        if not self.connected:
            return False
        while(len(props.regions) > 0):
                props.regions.remove(0)
        for key, region in self.regions.items():
            props.regions.add()
            regionss = props.regions[-1]
            regionss.name = region['name']
#            regionss.description = region['id']

    def onCheck(self, context):
        self.onTest(context)
        return
        props = context.scene.b2rex_props
        self.exportSettings = props
        self.region_uuid = list(self.regions.keys())[props.selected_region]
        self.do_check()

    def onTest(self, context):
        print("export materials")
        props = context.scene.b2rex_props
        current = context.active_object
        if current:
            session = bpy.b2rex_session.doExportMaterials(current)
            return
            for mat in current.data.materials:
                face = None
                if current.data.uv_textures:
                    face = current.data.uv_textures[0].data[0]
                matio = RexMaterialIO(self, current.data, face,
                                     False)
                f = StringIO()
                matio.write(f)
                f.seek(0)
                print("MATERIAL", mat.opensim.uuid)
                print(f.read())

    def onProcessQueue(self, context):
        self.processUpdates()

    def onDelete(self, context):
        self.doDelete()

    def onDeRezObject(self):
        self.doDeRezObject()

    def onRezObject(self, item_id):
        location_to_rez_x = bpy.context.scene.cursor_location[0]
        location_to_rez_y = bpy.context.scene.cursor_location[1]
        location_to_rez_z = bpy.context.scene.cursor_location[2]
        location_to_rez = (location_to_rez_x, location_to_rez_y, location_to_rez_z)
        location_to_rez = self._unapply_position(location_to_rez)

        print("onRezObject", item_id, location_to_rez)
        self.simrt.RezObject(item_id, location_to_rez, location_to_rez)

    def onRemoveInventoryItem(self, item_id):
        self.simrt.RemoveInventoryItem(item_id)
 

    def onExport(self, context):
        props = context.scene.b2rex_props
        self.doExport(props, props.loc)

    def delete_connection(self, context):
        props = context.scene.b2rex_props
        print("no workie")

    def cancel_edit_connection(self, context):
        props = context.scene.b2rex_props
        props.connection.search = props.connection.list[0].name
        form = props.connection.form
        form.username = ""
        form.password = ""
        form.url = ""
        form.name = ""

    def create_connection(self, context):
        props = context.scene.b2rex_props
        form = props.connection.form
        con = props.connection.list[props.connection.search]
        form.url = ""
        form.name = ""
        form.username = ""
        props.connection.search = 'add'

    def edit_connection(self, context):
        props = context.scene.b2rex_props
        if "add" in props.connection.list:
            props.connection.list.remove(1)
        form = props.connection.form
        con = props.connection.list[props.connection.search]
        form.url = con.url
        form.name = con.name
        form.username = con.username
        props.connection.search = 'edit'

    def add_connection(self, context):
        props = context.scene.b2rex_props
        form = props.connection.form
        if form.name in props.connection.list:
            con = props.connection.list[form.name]
        else:
            props.connection.list.add()
            con = props.connection.list[-1]
        con.name = form.name
        con.username = form.username
        con.url = form.url
        form.name = ""
        form.url = ""
        form.username = ""
        props.connection.search = con.name
        self.credentials.set_credentials(con.url, con.username, form.password)
        form.password = ""

    def draw_callback_view(self, context):
        self.processView()
        bpy.ops.b2rex.processqueue()
        pass

    def register_draw_callbacks(self, context):
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    #if region.type == 'WINDOW': # gets updated every frame
                    if region.type == 'TOOL_PROPS': # gets updated when finishing and operation
                        self.cb_pixel.append(region.callback_add(self.draw_callback_view, 
                                        (context, ),
                                        'POST_PIXEL'))
    def unregister_draw_callbacks(self, context):
        for cb in self.cb_pixel:
            if context.region:
                context.region.callback_remove(cb)
        self.cb_pixel = []

    def onToggleRt(self, context=None):
        if not context:
            context = bpy.context
        BaseApplication.onToggleRt(self, context)
        if self.simrt:
            self.register_draw_callbacks(context)
        else:
            self.unregister_draw_callbacks(context)

    def onExportUpload(self, context):
        if self.simrt:
            self.doRtUpload(context)
        else:
            self.onExport(context)
            self.onUpload(context)

    def onUpload(self, context):
        self.doUpload()

    def onImport(self, context):
        props = context.scene.b2rex_props
        self.region_uuid = list(self.regions.keys())[props.selected_region]
        self._import()

    def onSettings(self, context):
        self.settings()

    def _import(self):
        print('importing..')
        text = self.import_region(self.region_uuid)
        self.addStatus("Scene imported " + self.region_uuid)

    def settings(self):
        print("conecttt")

    def do_check(self):
        print("do_check regionuuid" + self.region_uuid)
        self.region_report = self.check_region(self.region_uuid)

    def addStatus(self, status, level=0):
        self.status = status

    def getSelected(self):
        return bpy.context.selected_objects

    def get_uuid(self, obj):
        """
        Get the uuid from the given object.
        """
        obj_uuid = obj.opensim.uuid
        if obj_uuid:
            return obj_uuid

    def set_loading_state(self, obj, value):
        """
        Set the loading state for the given blender object.
        """
        obj.opensim.state = value

    def get_loading_state(self, obj):
        return str(obj.opensim.state)

    def set_uuid(self, obj, obj_uuid):
        """
        Set the uuid for the given blender object.
        """
        obj.opensim.uuid = obj_uuid

    def getBlenderVersion(self):
        return str(bpy.app.version_string)

    def getObjectProperties(self, obj):
        return (obj.location, obj.rotation_euler, obj.scale)

    def _processScaleCommand(self, obj, objId, scale):
        self.apply_scale(obj, scale)
        #prev_scale = list(obj.scale)
        #if not prev_scale == scale:
            #    obj.scale = scale
        self.scales[objId] = list(obj.scale)

    def _processPosCommand(self, obj, objId, pos):
        self.apply_position(obj, pos)
        self.positions[objId] = list(obj.location)

    def _processRotCommand(self, obj, objId, rot):
        if objId in self._agents:
            rot = obj.rotation_euler
            obj.rotation_euler = (rot[0]+math.pi/2.0, rot[1], rot[2]+math.pi/2.0)
        else:
            self.apply_rotation(obj, rot)
        self.rotations[objId] = list(obj.rotation_euler)

    def processMsgCommand(self, username, message):
        props = bpy.context.scene.b2rex_props
        props.chat.add()
        regionss = props.chat[-1]
        regionss.name = username+" "+message
        props.selected_chat = len(props.chat)-1

    def applyObjectProperties(self, obj, pars):
        for key, value in pars.items():
            if hasattr(obj.opensim, key):
                try:
                    setattr(obj.opensim, key, value)
                except:
                    print("cant set %s to %s"%(key, value))
                    pass # too bad :P
            else:
                prop = None
                if isinstance(value, str):
                    prop = StringProperty(name=key)
                elif isinstance(value, bool):
                    prop = BoolProperty(name=key)
                elif isinstance(value, dict):
                    self.applyObjectProperties(obj, value)
                elif isinstance(value, int):
                    prop = IntProperty(name=key)
                elif isinstance(value, float):
                    prop = FloatProperty(name=key)
                if prop:
                    setattr(bpy.types.B2RexObjectProps, key, prop)
                    setattr(obj.opensim, key, value)
        self.queueRedraw()


    def queueRedraw(self, immediate=False):
        screen = bpy.context.screen
        if screen and not immediate:
            bpy.ops.b2rex.redraw()
        else:
            # no context means we call a redraw for every
            # screen. this may be happening from a thread
            # and seems to be problematic.
            for screen in bpy.data.screens:
                self.queueRedrawScreen(screen)

    def queueRedrawScreen(self, screen):
        for area in screen.areas:
                area.tag_redraw()

    def update_folders(self, folders):
        props = bpy.context.scene.b2rex_props
        cached_folders = getattr(props, 'folders')
        cached_folders.clear()
        
        for folder in folders:
            expand_prop = "e_" + str(folder['FolderID']).split('-')[0]
            if not hasattr(bpy.types.B2RexProps, expand_prop):
                prop = BoolProperty(name="expand", default=False)
                setattr(bpy.types.B2RexProps, expand_prop, prop)

            descendents = -1
            if 'Descendents' in folder:
                descendents = folder['Descendents']
            elif folder['FolderID'] in cached_folders:
                if 'Descendents' in cached_folders[folder['FolderID']]:
                    cached_folder = cached_folders[folder['FolderID']]
                    descendents = cached_folder['Descendents'] 
            
            if descendents <= 0:
                setattr(props, expand_prop, False)

            folder['Descendents'] = descendents
            cached_folders[folder['FolderID']] = folder


    def update_items(self, items):
        props = bpy.context.scene.b2rex_props
        cached_items = getattr(props, '_items')
        cached_items.clear()
        for item in items:
            cached_items[item['ItemID']] = item

    def update_firstlevel(self):
        props = bpy.context.scene.b2rex_props
        cached_folders = getattr(props, 'folders')
        root_id = getattr(props, "root_folder")
        session = bpy.b2rex_session

        for folder_id, folder in cached_folders.items():
            if folder['ParentID'] == root_id:
                session.simrt.FetchInventoryDescendents(folder_id)

    def processInventoryDescendents(self, folder_id, folders, items):
        logger.debug("processInventoryDescendents")
        self.update_folders(folders)
        self.update_items(items)
           
    def processInventorySkeleton(self, inventory):
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
        
