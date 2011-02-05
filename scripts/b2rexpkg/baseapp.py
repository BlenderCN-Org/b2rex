import sys
import time
import traceback

from b2rexpkg.siminfo import GridInfo
from b2rexpkg import IMMEDIATE, ERROR

from .tools.threadpool import ThreadPool, NoResultsPending

from .importer import Importer
from .exporter import Exporter

import bpy

if sys.version_info[0] == 3:
        import urllib.request as urllib2
else:
        import urllib2


eventlet_present = False
try:
    import eventlet
    try:
        from b2rexpkg import simrt
        eventlet_present = True
    except:
        traceback.print_exc()
except:
    from b2rexpkg import threadrt as simrt
    eventlet_present = True

import logging
logger = logging.getLogger('b2rex.baseapp')

class BaseApplication(Importer, Exporter):
    def __init__(self, title="RealXtend"):
        self.rt_support = eventlet_present
        self.stats = [0,0,0,0,0]
        self.status = "b2rex started"
        self.pool = ThreadPool(10)
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

        #self.pool.addRequest(self.start_thread, range(100), self.print_thread,
        #                 self.error_thread)


    def default_error_db(self, request, error):
        logger.error("error downloading "+str(request)+": "+str(error))

    def addDownload(self, objId, meshId, http_url, cb, error_cb=None):
        if not error_cb:
            _error_cb = self.default_error_db
        else:
            def _error_cb(request, result):
                error_cb(result)
        def _cb(request, result):
            cb(objId, meshId, result)
        self.pool.addRequest(self.doDownload, [http_url], _cb, _error_cb)

    def doDownload(self, http_url):
        req = urllib2.urlopen(http_url)
        return req.read()

    def start_thread(self, bla):
        time.sleep(10)

    def print_thread(self, request, result):
        print(result)

    def error_thread(self, request, error):
        print(error)

    def addStatus(self, text, priority=0):
        pass

    def initGui(self, title):
        pass

    def connect(self, base_url, username="", password=""):
        """
        Connect to an opensim instance
        """
        self.sim.connect(base_url+'/xml-rpc.php')
        firstname, lastname = username.split()
        coninfo = self.sim.login(firstname, lastname, password)
        self._sim_port = coninfo['sim_port']
        self._sim_ip = coninfo['sim_ip']
        self._sim_url = 'http://'+str(self._sim_ip)+':'+str(self._sim_port)
        print("reconnect to", self._sim_url)
        self.gridinfo.connect('http://'+str(self._sim_ip)+':'+str(9000), username, password)
        self.sim.connect(self._sim_url)

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
            self.regions = self.gridinfo.getRegions()
            self.griddata = self.gridinfo.getGridInfo()
        except:
            self.addStatus("Error: couldnt connect to " + base_url, ERROR)
            traceback.print_exc()
            return
        # create the regions panel
        self.addRegionsPanel(self.regions, self.griddata)
        if eventlet_present:
            self.addRtCheckBox()
        else:
            logger.debug("no support for real time communications")

        self.connected = True
        self.addStatus("Connected to " + self.griddata['gridnick'])

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
        elif cmd == 'RexPrimData':
            self.processRexPrimDataCommand(*args)

    def processRexPrimDataCommand(self, objId, pars):
        print("ReXPrimData for ", pars["MeshUrl"])
        self.stats[3] += 1
        self.addDownload(objId, pars["RexMeshUUID"], pars["MeshUrl"], self.meshArrived)

    def meshArrived(self, objId, meshId, data):
        self.stats[4] += 1
        obj = self.findWithUUID(objId)
        if obj:
            return
        new_mesh = self.create_mesh_frombinary(meshId, "opensim", data)
        if new_mesh:
            obj = self.getcreate_object(objId, "opensim", new_mesh)
            if objId in self.positions:
                pos = self.positions[objId]
                self.apply_position(obj, pos)
            if objId in self.rotations:
                rot = self.rotations[objId]
                self.apply_rotation(obj, rot)
            if objId in self.scales:
                scale = self.scales[objId]
                self.apply_scale(obj, scale)
            self.set_uuid(obj, objId)
            self.set_uuid(new_mesh, meshId)
            scene = self.get_current_scene()
            scene.objects.link(obj)
            new_mesh.update()

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
            self._processPosCommand(obj, objId, pos)
        else:
            self.positions[str(objId)] = pos

    def processScaleCommand(self, objId, scale):
        obj = self.findWithUUID(objId)
        if obj:
            self._processScaleCommand(obj, objId, scale)
        else:
            self.scales[str(objId)] = scale

    def processRotCommand(self, objId, rot):
        obj = self.findWithUUID(objId)
        if obj:
            self._processRotCommand(obj, objId, rot)
        else:
            self.rotations[str(objId)] = rot
            
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
                self.positions[obj_uuid] = pos
                self.rotations[obj_uuid] = rot
            elif not obj_uuid in self.positions or not pos == self.positions[obj_uuid]:
                self.stats[1] += 1
                self.simrt.apply_position(obj_uuid, self.unapply_position(pos))
                self.positions[obj_uuid] = pos
            if not obj_uuid in self.scales or not scale == self.scales[obj_uuid]:
                self.stats[1] += 1
                self.simrt.apply_scale(obj_uuid, scale)
                self.scales[obj_uuid] = scale


    def processUpdates(self):
        try:
            self.pool.poll()
        except NoResultsPending:
            pass
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



