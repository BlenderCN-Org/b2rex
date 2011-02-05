import traceback

from ..siminfo import GridInfo
from ..compatibility import BaseApplication
from ..tools.logger import logger

from b2rexpkg import IMMEDIATE, ERROR

import bpy

class B2Rex(BaseApplication):
    def __init__(self, context):
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
        props = context.scene.b2rex_props
        self.region_uuid = list(self.regions.keys())[props.selected_region]
        self.do_check()

    def onProcessQueue(self, context):
        self.processUpdates()

    def onExport(self, context):
        props = context.scene.b2rex_props
        self.doExport(props, props.loc)

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
        prev_scale = list(obj.scale)
        if not prev_scale == scale:
            obj.scale = scale
            self.scales[objId] = list(obj.scale)
            self.queueRedraw()

    def _processPosCommand(self, obj, objId, pos):
        self.apply_position(obj, pos)
        self.positions[objId] = list(obj.location)
        self.queueRedraw()

    def _processRotCommand(self, obj, objId, rot):
        self.apply_rotation(obj, rot)
        self.rotations[objId] = list(obj.rotation_euler)
        self.queueRedraw()

    def processMsgCommand(self, username, message):
        props = bpy.context.scene.b2rex_props
        props.chat.add()
        regionss = props.chat[-1]
        regionss.name = username+" "+message
        props.selected_chat = len(props.chat)-1
