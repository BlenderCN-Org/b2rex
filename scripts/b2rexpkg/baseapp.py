import time
import traceback

from b2rexpkg.siminfo import GridInfo
from b2rexpkg import IMMEDIATE, ERROR

from .importer import Importer
from .exporter import Exporter

import bpy

eventlet_present = True
try:
    import eventlet
    from b2rexpkg import simrt
except:
    from b2rexpkg import threadrt as simrt

import logging
logger = logging.getLogger('b2rex.baseapp')

class BaseApplication(Importer, Exporter):
    def __init__(self, title="RealXtend"):
        self.rt_support = eventlet_present
        self.stats = [0,0,0,0,0]
        self.status = "b2rex started"
        self.connected = False
        self.positions = {}
        self.rotations = {}
        self.scales = {}
        self.rt_on = False
        self.simrt = None
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

    def onToggleRt(self, context=None):
        if context:
            self.exportSettings = context.scene.b2rex_props
        if self.rt_on:
            self.simrt.addCmd(["quit"])
            self.rt_on = False
            self.simrt = None
        else:
            firstline = 'Blender '+ self.getBlenderVersion()
            self.simrt = simrt.run_thread(context, self.exportSettings.server_url,
                                          self.exportSettings.username,
                                          self.exportSettings.password,
                                          firstline)
            if not context:
                Blender.Window.QAdd(Blender.Window.GetAreaID(),Blender.Draw.REDRAW,0,1)
            self.rt_on = True

    def processCommand(self, cmd, *args):
        self.stats[0] += 1
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

    def findWithUUID(self, objId):
        obj = self.find_with_uuid(str(objId), bpy.data.objects, "objects")
        if not obj:
            obj = self.find_with_uuid(str(objId), bpy.data.meshes, "meshes")
        return obj

    def processPosCommand(self, objId, pos):
        obj = self.findWithUUID(objId)
        if obj:
            self.apply_position(obj, pos)
            self.positions[str(objId)] = list(obj.getLocation())
            self.queueRedraw()

    def processScaleCommand(self, objId, scale):
        obj = self.findWithUUID(objId)
        if obj:
            prev_scale = list(obj.getSize())
            if not prev_scale == scale:
                obj.setSize(*scale)
                self.scales[str(objId)] = list(obj.getSize())
                self.queueRedraw()


    def processRotCommand(self, objId, rot):
        obj = self.findWithUUID(objId)
        if obj:
            self.apply_rotation(obj, rot)
            self.rotations[str(objId)] = list(obj.getEuler())
            self.queueRedraw()

    def processUpdate(self, obj):
        obj_uuid = self.get_uuid(obj)
        if obj_uuid:
            pos, rot, scale = self.getObjectProperties(obj)
            pos = list(pos)
            rot = list(rot)
            scale = list(scale)
            if not obj_uuid in self.rotations or not rot == self.rotations[obj_uuid]:
                self.stats[1] += 1
                self.simrt.apply_position(obj_uuid,  self.unapply_position(pos), self.unapply_rotation(rot))
                self.rotations[obj_uuid] = rot
                self.positions[obj_uuid] = pos
            elif not obj_uuid in self.positions or not pos == self.positions[obj_uuid]:
                self.stats[1] += 1
                self.simrt.apply_position(obj_uuid, self.unapply_position(pos))
                self.positions[obj_uuid] = pos
            if not obj_uuid in self.scales or not scale == self.scales[obj_uuid]:
                self.stats[1] += 1
                self.simrt.apply_scale(obj_uuid, scale)
                self.scales[obj_uuid] = scale


    def processUpdates(self):
        cmds = self.simrt.getQueue()
        if cmds:
            self.stats[2] += 1
            for cmd in cmds:
                self.processCommand(*cmd)

    def processView(self):
        t = time.time()
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



