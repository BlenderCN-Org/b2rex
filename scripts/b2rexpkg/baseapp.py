import sys
import time
import uuid
import traceback
import base64
from collections import defaultdict

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
        self.selected = set()
        self.agent_id = ""
        self.agent_access = ""
        self.rt_support = eventlet_present
        self.stats = [0,0,0,0,0,0,0,0]
        self.status = "b2rex started"
        self.selected = {}
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
            self.simrt.addCmd(["throttle", self.exportSettings.kbytesPerSecond*1024])
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
        elif cmd == 'delete':
            self.processDeleteCommand(*args)
        elif cmd == 'msg':
            self.processMsgCommand(*args)
        elif cmd == 'RexPrimData':
            self.processRexPrimDataCommand(*args)
        elif cmd == 'ObjectProperties':
            self.processObjectPropertiesCommand(*args)
        elif cmd == 'connected':
            self.agent_id = args[0]
            self.agent_access = args[1]
        elif cmd == 'meshcreated':
            self.processMeshCreated(*args)

    def processMeshCreated(self, obj_uuid, mesh_uuid, new_obj_uuid, asset_id):
        foundobject = False
        foundmesh = False
        for obj in self.getSelected():
            if obj.type == 'MESH' and obj.opensim.uuid == obj_uuid:
                foundobject = obj
            if obj.type == 'MESH' and obj.data.opensim.uuid == mesh_uuid:
                foundmesh = obj.data

        if not foundmesh:
            foundmesh = self.find_with_uuid(mesh_uuid,
                                              bpy.data.meshes, "meshes")
        if not foundobject:
            foundobject = self.find_with_uuid(obj_uuid,
                                              bpy.data.objects, "objects")
        if foundobject:
            foundobject.opensim.uuid = new_obj_uuid
        else:
            print("Could not find object for meshcreated")
        if foundmesh:
            foundmesh.opensim.uuid = asset_id
        else:
            print("Could not find mesh for meshcreated")

    def processDeleteCommand(self, objId):
        obj = self.findWithUUID(objId)
        if obj:
            obj.opensim.uuid = ""
            self.queueRedraw()

    def processRexPrimDataCommand(self, objId, pars):
        #print("ReXPrimData for ", pars["MeshUrl"])
        self.stats[3] += 1
        meshId = pars["RexMeshUUID"]
        obj = self.findWithUUID(objId)
        if obj:
            # XXX we dont update mesh for the moment
            return
        mesh = self.find_with_uuid(meshId, bpy.data.meshes, "meshes")
        if mesh:
            self.createObjectWithMesh(mesh, objId, meshId)
            self.queueRedraw()
        else:
            if not meshId == '00000000-0000-0000-0000-000000000000':
                self.addDownload(objId, meshId, pars["MeshUrl"], self.meshArrived)

    def processObjectPropertiesCommand(self, objId, pars):
        #print("ObjectProperties for", objId, pars)
        obj = self.find_with_uuid(str(objId), bpy.data.objects, "objects")
        if obj:
            print("Found obj!")
            self.applyObjectProperties(obj, pars)
        self.stats[5] += 1

    def applyObjectProperties(self, obj, pars):
        pass

    def meshArrived(self, objId, meshId, data):
        self.stats[4] += 1
        obj = self.findWithUUID(objId)
        if obj:
            return
        new_mesh = self.create_mesh_frombinary(meshId, "opensim", data)
        if new_mesh:
            self.createObjectWithMesh(new_mesh, objId, meshId)

    def createObjectWithMesh(self, new_mesh, objId, meshId):
        obj = self.getcreate_object(objId, "opensim", new_mesh)
        if objId in self.positions:
            pos = self.positions[objId]
            self.apply_position(obj, pos, raw=True)
        if objId in self.rotations:
            rot = self.rotations[objId]
            self.apply_rotation(obj, rot, raw=True)
        if objId in self.scales:
            scale = self.scales[objId]
            self.apply_scale(obj, scale)
        self.set_uuid(obj, objId)
        self.set_uuid(new_mesh, meshId)
        scene = self.get_current_scene()
        if not obj.name in scene.objects:
            scene.objects.link(obj)
            new_mesh.update()


    def doRtUpload(self, context):
        #print("doRtUpload")
        selected = bpy.context.selected_objects
        if selected:
            # just the first for now
            selected = selected[0]
            if not selected.opensim.uuid:
                self.doRtObjectUpload(context, selected)
                return

    def doDelete(self):
        #print("doDelete")
        selected = self.getSelected()
        if selected:
            for obj in selected:
                if obj.opensim.uuid:
                    self.simrt.addCmd(['delete', obj.opensim.uuid])

    def sendObjectClone(self, obj):
        obj_name = obj.name
        mesh = obj.data
        if not obj.opensim.uuid:
            obj.opensim.uuid = str(uuid.uuid4())
        obj_uuid = obj.opensim.uuid
        mesh_name = mesh.name
        mesh_uuid = mesh.opensim.uuid
        pos, rot, scale = self.getObjectProperties(obj)
        
        self.simrt.addCmd(['clone', obj_name, obj_uuid, mesh_name, mesh_uuid,
                           self.unapply_position(pos),
                           self.unapply_rotation(rot), list(scale)])

    def sendObjectUpload(self, obj, mesh, data):
        b64data = base64.urlsafe_b64encode(data).decode('ascii')
        obj_name = obj.name
        obj_uuid = obj.opensim.uuid
        mesh_name = mesh.name
        mesh_uuid = mesh.opensim.uuid
        print("finishing upload for", obj_uuid, mesh_uuid)
        pos, rot, scale = self.getObjectProperties(obj)
        
        self.simrt.addCmd(['create', obj_name, obj_uuid, mesh_name, mesh_uuid,
                           self.unapply_position(pos),
                           self.unapply_rotation(rot), list(scale), b64data])

    def doRtObjectUpload(self, context, obj):
        mesh = obj.data
        has_mesh_uuid = mesh.opensim.uuid
        if has_mesh_uuid:
            self.sendObjectClone(obj)
            return
        def finish_upload(data):
            self.sendObjectUpload(obj, mesh, data)
        # export mesh
        self.doAsyncExportMesh(context, obj, finish_upload)
        # upload prim
        # self.sendObjectUpload(selected, mesh, data)
        # send new prim

    def processMsgCommand(self, username, message):
        self.addStatus("message from "+username+": "+message)

    def findWithUUID(self, objId):
        obj = self.find_with_uuid(str(objId), bpy.data.objects, "objects")
        if not obj:
            obj = self.find_with_uuid(str(objId), bpy.data.meshes, "meshes")
        return obj

    def processPosCommand(self, objId, pos, rot=None):
        obj = self.findWithUUID(objId)
        if obj:
            self._processPosCommand(obj, objId, pos)
            if rot:
                self._processRotCommand(obj, objId, rot)
        else:
            self.positions[str(objId)] = self._apply_position(pos)
            if rot:
                self.rotations[str(objId)] = self._apply_rotation(rot)

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
            self.rotations[str(objId)] = self._apply_rotation(rot)
            
    def processUpdate(self, obj):
        obj_uuid = self.get_uuid(obj)
        #print("process update for ", obj_uuid)
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
            return obj_uuid


    def processUpdates(self):
        try:
            self.pool.poll()
        except NoResultsPending:
            pass
        self.checkUuidConsistency(self.getSelected())
        cmds = self.simrt.getQueue()
        if cmds:
            self.stats[2] += 1
            for cmd in cmds:
                self.processCommand(*cmd)

    def checkUuidConsistency(self, selected):
        # look for duplicates
        selected = set(self.getSelected())
        oldselected = self.selected
        newselected = {}
        isobjcopy = True
        for obj in selected:
            obj_uuid = obj.opensim.uuid
            if obj.type == 'MESH' and obj_uuid:
                mesh_uuid = obj.data.opensim.uuid
                newselected[obj_uuid] = obj.as_pointer()
                newselected[mesh_uuid] = obj.data.as_pointer()
                if obj.opensim.uuid in oldselected and not oldselected[obj_uuid] == obj.as_pointer():
                    # copy or clone
                    if obj.data.opensim.uuid in oldselected and not oldselected[mesh_uuid] == obj.data.as_pointer():
                        # copy
                        ismeshcopy = True
                        obj.data.opensim.uuid = ""
                    else:
                        # clone
                        pass
                    obj.opensim.uuid = ""
        self.selected = newselected
        return

        uuids = map(lambda s: s.opensim.uuid, selected)
        uuids = list(filter(lambda s: s, uuids))
        uuids_set = set(uuids)
        if len(uuids) == len(uuids_set):
            return
        seen = []
        seen_meshes = {}
        for obj in selected:
            obj_uuid = obj.opensim.uuid
            if obj_uuid and obj_uuid not in seen:
                # didnt see this obj uuid, so just add to cache
                seen.append(obj_uuid)
            elif obj_uuid:
                # mark the object as unsynced
                obj.opensim.uuid = ""
            if obj.type == 'MESH':
                mesh_uuid = obj.data.opensim.uuid
                if mesh_uuid:
                    if mesh_uuid in seen_meshes:
                        if obj.data.as_pointer() != seen_meshes[mesh_uuid]:
                            obj.data.opensim.uuid = ""
                    else:
                        seen_meshes[mesh_uuid] = obj.data.as_pointer()

                    seen_meshes[mesh_uuid] = obj.data.as_pointer()

    def processView(self):
        t = time.time()
        selected = self.getSelected()
        all_selected = set()
        # look for changes in objects
        for obj in selected:
            if obj.opensim.uuid in self.selected and obj.as_pointer() == self.selected[obj.opensim.uuid]:
                obj_id = self.processUpdate(obj)
                if obj_id:
                    all_selected.add(obj_id)
        if not all_selected == self.selected:
            self.simrt.addCmd(["select"]+list(all_selected))

    def go(self):
        """
        Start the ogre interface system
        """
        self.screen.activate()

    def addRegionsPanel(self, regions, griddata):
        pass

    def queueRedraw(self, pars=None):
        pass



