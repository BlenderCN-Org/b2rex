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

    def onExport(self, context):
        props = context.scene.b2rex_props
        self.doExport(props, props.loc)

    def draw_callback_view(self, context):
        self.processUpdates()

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
        logger.debug("conecttt")

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

