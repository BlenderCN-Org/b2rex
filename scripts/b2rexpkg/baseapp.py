import traceback

from b2rexpkg.siminfo import GridInfo
from b2rexpkg import IMMEDIATE, ERROR

from .importer import Importer
from .exporter import Exporter

eventlet_present = False
try:
    import eventlet
    from b2rexpkg import simrt
    eventlet_present = True
except:
    pass

import logging
logger = logging.getLogger('b2rex.baseapp')

class BaseApplication(Importer, Exporter):
    def __init__(self, title="RealXtend"):
        self.rt_support = eventlet_present
        self.connected = False
        self.positions = {}
        self.rotations = {}
        self.scales = {}
        self.rt_on = False
        self.screen = self
        self.gridinfo = GridInfo()
        self.buttons = {}
        self.settings_visible = False
        Importer.__init__(self, self.gridinfo)
        Exporter.__init__(self, self.gridinfo)

    def addStatus(self, text, priority=0):
        pass

    def initGui(self, title):
        pass

    def connect(self, base_url, username="", password=""):
        """
        Connect to an opensim instance
        """
        self.gridinfo.connect(base_url, username, password)
        #self.sim.connect(base_url)

    def onConnectAction(self):
        """
        Connect Action
        """
        base_url = self.exportSettings.server_url
        self.addStatus("Connecting to " + base_url, IMMEDIATE)
        self.connect(base_url, self.exportSettings.username,
                     self.exportSettings.password)
        self.region_uuid = ''
        self.regionLayout = None
        try:
            regions = self.gridinfo.getRegions()
            griddata = self.gridinfo.getGridInfo()
        except:
            self.addStatus("Error: couldnt connect to " + base_url, ERROR)
            traceback.print_exc()
            return
        # create the regions panel
        self.addRegionsPanel(regions, griddata)
        if eventlet_present:
            self.addRtCheckBox()
        else:
            logger.debug("no support for real time communications")

        self.connected = True
        self.addStatus("Connected to " + griddata['gridnick'])

    def addRtCheckBox(self):
        pass

    def onToggleRt(self):
        if self.rt_on:
            self.simrt.addCmd("quit")
            self.rt_on = False
        else:
            firstline = 'Blender '+ self.getBlenderVersion()
            self.simrt = simrt.run_thread(self.exportSettings.server_url,
                                          self.exportSettings.username,
                                          self.exportSettings.password,
                                          firstline)
            Blender.Window.QAdd(Blender.Window.GetAreaID(),Blender.Draw.REDRAW,0,1)
            self.rt_on = True

    def processCommand(self, cmd, *args):
        if cmd == 'pos':
            self.processPosCommand(*args)
        elif cmd == 'rot':
            self.processRotCommand(*args)
        elif cmd == 'scale':
            self.processScaleCommand(*args)
        elif cmd == 'msg':
            self.processMsgCommand(*args)

    def processMsgCommand(self, username, message):
        self.addStatus("message from "+username+": "+message)

    def findWithUUID(self):
        obj = self.find_with_uuid(str(objId), bpy.data.objects, "objects")
        if not obj:
            obj = self.find_with_uuid(str(objId), bpy.data.meshes, "meshes")
        return obj

    def processPosCommand(self, objId, pos):
        obj = self.findWithUUID()
        if obj:
            self.apply_position(obj, [pos.X, pos.Y, pos.Z])
            self.positions[str(objId)] = list(obj.getLocation())
            self.queueRedraw()
            logger.debug(("IN_CMDS",pos.X,obj))

    def processScaleCommand(self, objId, scale):
        obj = self.findWithUUID()
        if obj:
            prev_scale = list(obj.getSize())
            if not prev_scale == scale:
                obj.setSize(scale.X, scale.Y, scale.Z)
                self.scales[str(objId)] = list(obj.getSize())
                self.queueRedraw()


    def processRotCommand(self, objId, rot):
        obj = self.findWithUUID()
        if obj:
            self.apply_rotation(obj, [rot.X, rot.Y, rot.Z, rot.W])
            self.rotations[str(objId)] = list(obj.getEuler())
            self.queueRedraw()

    def processUpdate(self, obj):
        obj_uuid = self.get_uuid(obj)
        if obj_uuid:
            pos, rot, scale = self.getObjectProperties(obj)
            if not obj_uuid in self.rotations or not rot == self.rotations[obj_uuid]:
                self.simrt.apply_position(obj_uuid,  self.unapply_position(pos), self.unapply_rotation(rot))
                self.rotations[obj_uuid] = rot
                self.positions[obj_uuid] = pos
            elif not obj_uuid in self.positions or not pos == self.positions[obj_uuid]:
                self.simrt.apply_position(obj_uuid, self.unapply_position(pos))
                self.positions[obj_uuid] = pos
            if not obj_uuid in self.scales or not scale == self.scales[obj_uuid]:
                self.simrt.apply_scale(obj_uuid, scale)


    def processUpdates(self):
        selected = self.getSelected()
        for obj in selected:
            self.processUpdate(obj)

    def go(self):
        """
        Start the ogre interface system
        """
        self.screen.activate()

    def addRegionsPanel(self, regions, griddata):
        pass

    def queueRedraw(self, pars=None):
        pass

    def getObjectProperties(self, obj):
        return (obj.location, obj.rotation_euler, obj.scale)

    def getBlenderVersion(self):
        return str(bpy.app.version_string)


