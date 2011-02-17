import sys
import time
import uuid
import traceback
import threading
import math
import base64
from collections import defaultdict

from .terrainsync import TerrainSync

from b2rexpkg.siminfo import GridInfo
from b2rexpkg import IMMEDIATE, ERROR

from .tools.threadpool import ThreadPool, NoResultsPending

from .importer import Importer
from .exporter import Exporter
from .tools.terraindecoder import TerrainDecoder, TerrainEncoder

from .tools.simtypes import RexDrawType, AssetType, PCodeEnum

import bpy

ZERO_UUID_STR = '00000000-0000-0000-0000-000000000000'
priority_commands = ['pos', 'LayerData', 'LayerDataDecoded']

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
        self.command_queue = []
        self.wanted_workers = 1
        self.second_start = time.time()
        self.second_budget = 0
        self.pool = ThreadPool(1)
        self.workpool = ThreadPool(5)
        self.rawselected = set()
        self.simstats = None
        self.agent_id = ""
        self.loglevel = "standard"
        self.agent_access = ""
        self.rt_support = eventlet_present
        self.stats = [0,0,0,0,0,0,0,0,0,0,0,0,0]
        self.status = "b2rex started"
        self.selected = {}
        self.sim_selection = set()
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
        self._requested_urls = []
        self._agents = {}
        self.initializeCommands()
        Importer.__init__(self, self.gridinfo)
        Exporter.__init__(self, self.gridinfo)

    def registerTextureImage(self, image):
        if not image.opensim.uuid:
            image.opensim.uuid = str(uuid.uuid4())
        pass # register a texture with the sim
        return image.opensim.uuid

    def registerCommand(self, cmd, callback):
        self._cmd_matrix[cmd] = callback

    def initializeCommands(self):
        self._cmd_matrix = {}
        self.registerCommand('pos', self.processPosCommand)
        self.registerCommand('rot', self.processRotCommand)
        self.registerCommand('scale', self.processScaleCommand)
        self.registerCommand('props', self.processPropsCommand)
        self.registerCommand('delete', self.processDeleteCommand)
        self.registerCommand('msg', self.processMsgCommand)
        self.registerCommand('RexPrimData', self.processRexPrimDataCommand)
        self.registerCommand('LayerData', self.processLayerData)
        self.registerCommand('ObjectProperties', self.processObjectPropertiesCommand)
        self.registerCommand('CoarseLocationUpdate', self.processCoarseLocationUpdate)
        self.registerCommand('AssetUploadFinished', self.processAssetUploadFinished)
        self.registerCommand('connected', self.processConnectedCommand)
        self.registerCommand('meshcreated', self.processMeshCreated)
        self.registerCommand('capabilities', self.processCapabilities)
        self.registerCommand('InventorySkeleton', self.processInventorySkeleton)
        self.registerCommand('InventoryDescendents', self.processInventoryDescendents)
        self.registerCommand('SimStats', self.processSimStats)
        self.registerCommand('LayerDataDecoded', self.processLayerDataDecoded)
        self.registerCommand('RegionHandshake', self.processRegionHandshake)
        self.registerCommand('OnlineNotification',
                             self.processOnlineNotification)
        self.registerCommand('OfflineNotification',
                             self.processOfflineNotification)
        self.registerCommand('AgentMovementComplete',
                             self.processAgentMovementComplete)
        # internal
        self.registerCommand('mesharrived', self.processMeshArrived)
        self.registerCommand('materialarrived', self.processMaterialArrived)
        self.registerCommand('texturearrived', self.processTextureArrived)

    def processSimStats(self, X, Y, Flags, ObjectCapacity, *args):
        self.simstats = [X, Y, Flags, ObjectCapacity] + list(args)

    def processOnlineNotification(self, agentID):
        self._agents[agentID] = agentID

    def processOfflineNotification(self, agentID):
        pass # should get a kill..
        # self._agents[agentID] = agentID

    def processAgentMovementComplete(self, agentID, pos, lookat):
        agent = self.getAgent(agentID)
        agent.rotation_euler = lookat
        self.apply_position(agent, pos)

    def getAgent(self, agentID):
        agent = self.findWithUUID(agentID)
        if not agent:
            camera = bpy.data.cameras.new(agentID)
            agent = bpy.data.objects.new(agentID, camera)
            self.set_uuid(agent, agentID)
            self._agents[agentID] = agentID

            scene = self.get_current_scene()
            if agentID in self.positions:
                self.apply_position(agentID, self.positions[agentID], raw=True)
            scene.objects.link(agent)
            try:
                agent.show_name = True
                agent.show_x_ray = True
            except:
                pass # blender2.5 only
            if not agentID == self.agent_id:
                self.set_immutable(agent)
        return agent

    def processRegionHandshake(self, regionID, pars):
        print("REGION HANDSHAKE", pars)

    def processLayerData(self, layerType, b64data):
        self.workpool.addRequest(self.decodeTerrainBlock, [b64data],
                             self.terrainDecoded, self.default_error_db)


    def decodeTerrainBlock(self, b64data):
        data = base64.urlsafe_b64decode(b64data.encode('ascii'))
        terrpackets = TerrainDecoder.decode(data)
        return terrpackets
 
    def terrainDecoded(self, request, terrpackets):
        for header, layer in terrpackets:
            self.command_queue.append(['LayerDataDecoded', header, layer])

    def processLayerDataDecoded(self, header, layer):
        self.terrain.apply_patch(layer, header.x, header.y)

    def processInventoryDescendents(self, folder_id, folders, items):
        pass
        

    def processInventorySkeleton(self, inventory):
        pass

    def processCoarseLocationUpdate(self, agent_id, pos):
        #print("COARSE LOCATION UPDATE", agent_id, pos)
        pass

    def processConnectedCommand(self, agent_id, agent_access):
        self.agent_id = agent_id
        self.agent_access = agent_access
        print("CONNECTED AS", agent_id)

    def default_error_db(self, request, error):
        logger.warning("error downloading "+str(request)+": "+str(error))
        #traceback.print_tb(error[2])

    def addDownload(self, http_url, cb, cb_pars=(), error_cb=None, main=None):
        if http_url in self._requested_urls:
            return False
        self._requested_urls.append(http_url)
        if not error_cb:
            _error_cb = self.default_error_db
        else:
            def _error_cb(request, result):
                error_cb(result)
        def _cb(request, result):
            cb(result, *cb_pars)
        if not main:
            main = self.doDownload
        self.pool.addRequest(main, [[http_url, cb_pars]], _cb, _error_cb)
        return True

    def doDownload(self, pars):
        http_url, pars = pars
        req = urllib2.urlopen(http_url)
        return req.read()

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
        logger.info("reconnect to " + self._sim_url)
        self.gridinfo.connect('http://'+str(self._sim_ip)+':'+str(9000), username, password)
        self.sim.connect(self._sim_url)

    def onConnectAction(self):
        """
        Connect Action
        """
        self.terrain = TerrainSync(self, self.exportSettings.terrainLOD)
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
            logger.warning("no support for real time communications")

        self.connected = True
        self.addStatus("Connected to " + self.griddata['gridnick'])

    def addRtCheckBox(self):
        pass

    def onToggleRt(self, context=None):
        if context:
            self.exportSettings = context.scene.b2rex_props
        if self.rt_on:
            self.simrt.quit()
            self.rt_on = False
            self.simrt = None
        else:
            props = self.exportSettings
            region_uuid = list(self.regions.keys())[props.selected_region]
            region_name = self.regions[region_uuid]['name']
            firstline = 'Blender '+ self.getBlenderVersion()
            self.simrt = simrt.run_thread(self, self.exportSettings.server_url,
                                          self.exportSettings.username,
                                          self.exportSettings.password,
                                          region_name, firstline)
            self.simrt.Throttle(self.exportSettings.kbytesPerSecond*1024)
            if not context:
                Blender.Window.QAdd(Blender.Window.GetAreaID(),Blender.Draw.REDRAW,0,1)
            self.rt_on = True

    def redraw(self):
        if not self.stats[5]:
            # we're using the commands left stats to keep our counter
            self.stats[5] += 1
            self.queueRedraw(True)

    def processCommand(self, cmd, *args):
        self.stats[0] += 1
        cmdHandler = self._cmd_matrix.get(cmd, None)
        if cmdHandler:
            cmdHandler(*args)

    def processCapabilities(self, caps):
        self.caps = caps

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
            logger.warning("Could not find object for meshcreated")
        if foundmesh:
            foundmesh.opensim.uuid = asset_id
        else:
            logger.warning("Could not find mesh for meshcreated")

    def processDeleteCommand(self, objId):
        obj = self.findWithUUID(objId)
        if obj:
            print("DELETE FOR",objId)
            # delete from object cache
            if objId in self._total['objects']:
                del self._total['objects'][objId]
            # clear uuid
            obj.opensim.uuid = ""
            scene = self.get_current_scene()
            # unlink
            scene.objects.unlink(obj)
            self.queueRedraw()

    def processRexPrimDataCommand(self, objId, pars):
        self.stats[3] += 1
        meshId = pars["RexMeshUUID"]
        obj = self.findWithUUID(objId)
        if obj or not meshId:
            if obj:
                logger.warning(("Object already created", obj, meshId, objId))
            # XXX we dont update mesh for the moment
            return
        mesh = self.find_with_uuid(meshId, bpy.data.meshes, "meshes")
        if mesh:
            self.createObjectWithMesh(mesh, objId, meshId)
            self.queueRedraw()
        else:
            materials = []
            if "Materials" in pars:
                materials = pars["Materials"]
                for index, matId, asset_type in materials:
                    if not matId == ZERO_UUID_STR and asset_type == AssetType.OgreMaterial:
                        mat_url = self.caps["GetTexture"] + "?texture_id=" + matId
                        self.addDownload(mat_url, self.materialArrived, (objId,
                                                                         meshId,
                                                                         matId,
                                                                         asset_type,
                                                                         index))
                    else:
                        logger.warning("unhandled material of type " + str(asset_type))
            if meshId and not meshId == ZERO_UUID_STR:
                asset_type = pars["drawType"]
                if asset_type == RexDrawType.Mesh:
                    mesh_url = self.caps["GetTexture"] + "?texture_id=" + meshId
                    if not self.addDownload(mesh_url,
                                     self.meshArrived, 
                                     (objId, meshId, materials),
                                            main=self.doMeshDownloadTranscode):
                        self.add_mesh_callback(meshId,
                                               self.createObjectWithMesh,
                                               objId,
                                               meshId, materials)
                else:
                    logger.warning("unhandled rexdata of type " + str(asset_type))

    def processPropsCommand(self, objId, pars):
        if "PCode" in pars and pars["PCode"] == PCodeEnum.Avatar:
            agent = self.getAgent(objId) # creates the agent
            if "NameValues" in pars:
                props = pars["NameValues"]
                if "FirstName" in props and "LastName" in props:
                    agent.name = props['FirstName']+" "+props["LastName"]
                    self._total['objects'][objId] = agent.name
        else:
            if "ParentID" in pars:
                parentId = pars["ParentID"]
                parent = self.findWithUUID(objId)
                if parent:
                    pass # XXX apply parent
            self.processObjectPropertiesCommand(objId, pars)



    def processObjectPropertiesCommand(self, objId, pars):
        obj = self.find_with_uuid(str(objId), bpy.data.objects, "objects")
        if obj:
            self.applyObjectProperties(obj, pars)

    def applyObjectProperties(self, obj, pars):
        pass

    def materialArrived(self, data, objId, meshId, matId, assetType, matIdx):
        self.command_queue.append(["materialarrived", data, objId, meshId,
                                      matId, assetType, matIdx])

    def processMaterialArrived(self, data, objId, meshId, matId, assetType, matIdx):
        if assetType == AssetType.OgreMaterial:
            self.parse_material(matId, {"name":matId, "data":data}, meshId,
                                matIdx)

    def meshArrived(self, mesh, objId, meshId, materials):
        self.command_queue.append(["mesharrived", mesh, objId, meshId, materials])

    def processMeshArrived(self, mesh, objId, meshId, materials):
        self.stats[4] += 1
        obj = self.findWithUUID(objId)
        if obj:
            return
        new_mesh = self.create_mesh_fromomesh(meshId, "opensim", mesh, materials)
        if new_mesh:
            self.createObjectWithMesh(new_mesh, str(objId), meshId, materials)
            self.trigger_mesh_callbacks(meshId, new_mesh)
        else:
            print("No new mesh with processMeshArrived")

    def setMeshMaterials(self, mesh, materials):
        presentIds = list(map(lambda s: s.opensim.uuid, mesh.materials))
        for idx, matId, asset_type in materials:
            mat = self.find_with_uuid(matId, bpy.data.materials, 'materials')
            if mat and not matId in presentIds:
                mesh.materials.append(mat)

    def createObjectWithMesh(self, new_mesh, objId, meshId, materials=[]):
        obj = self.getcreate_object(objId, "opensim", new_mesh)
        self.setMeshMaterials(new_mesh, materials)
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
        selected = bpy.context.selected_objects
        if selected:
            # just the first for now
            selected = selected[0]
            if not selected.opensim.uuid:
                self.doRtObjectUpload(context, selected)
                return

    def doDelete(self):
        selected = self.getSelected()
        if selected:
            for obj in selected:
                if obj.opensim.uuid:
                    self.simrt.Delete(obj.opensim.uuid)

    def sendObjectClone(self, obj, materials):
        obj_name = obj.name
        mesh = obj.data
        if not obj.opensim.uuid:
            obj.opensim.uuid = str(uuid.uuid4())
        obj_uuid = obj.opensim.uuid
        mesh_name = mesh.name
        mesh_uuid = mesh.opensim.uuid
        pos, rot, scale = self.getObjectProperties(obj)
        
        self.simrt.Clone(obj_name, obj_uuid, mesh_name, mesh_uuid,
                           self.unapply_position(pos),
                           self.unapply_rotation(rot), list(scale), materials)
        
    def sendObjectUpload(self, obj, mesh, data, materials):
        b64data = base64.urlsafe_b64encode(data).decode('ascii')
        obj_name = obj.name
        obj_uuid = obj.opensim.uuid
        mesh_name = mesh.name
        mesh_uuid = mesh.opensim.uuid
        pos, rot, scale = self.getObjectProperties(obj)
        
        self.simrt.Create(obj_name, obj_uuid, mesh_name, mesh_uuid,
                           self.unapply_position(pos),
                           self.unapply_rotation(rot), list(scale), b64data,
                          materials)

    def doRtObjectUpload(self, context, obj):
        mesh = obj.data
        has_mesh_uuid = mesh.opensim.uuid
        if has_mesh_uuid:
            def finish_clone(materials):
                self.sendObjectClone(obj, materials)
            self.doExportMaterials(obj, cb=finish_clone)
            return
        def finish_upload(materials):
            def send_upload(data):
                self.sendObjectUpload(obj, mesh, data, materials)
            self.doAsyncExportMesh(context, obj, send_upload)
        self.doExportMaterials(obj, cb=finish_upload)
        # export mesh
        # upload prim
        # self.sendObjectUpload(selected, mesh, data)
        # send new prim

    def processMsgCommand(self, username, message):
        self.addStatus("message from "+username+": "+message)

    def findWithUUID(self, objId):
        obj = self.find_with_uuid(str(objId), bpy.data.objects, "objects")
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
        if obj_uuid:
            pos, rot, scale = self.getObjectProperties(obj)
            pos = list(pos)
            rot = list(rot)
            scale = list(scale)
            if not obj_uuid in self.rotations or not rot == self.rotations[obj_uuid]:
                self.stats[1] += 1
                print("sending object position", obj_uuid)
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


    def checkPool(self):
        # check thread pool size
        if self.wanted_workers != self.exportSettings.pool_workers:
            current_workers = self.wanted_workers
            wanted_workers = self.exportSettings.pool_workers
            if current_workers < wanted_workers:
                self.pool.createWorkers(wanted_workers-current_workers)
            else:
                self.pool.dismissWorkers(current_workers-wanted_workers)
            self.wanted_workers = self.exportSettings.pool_workers

    def processUpdates(self):
        starttime = time.time()
        framebudget = float(self.exportSettings.rt_budget)/1000.0
        try:
            self.pool.poll()
        except NoResultsPending:
            pass
        try:
            self.workpool.poll()
        except NoResultsPending:
            pass

        # check consistency
        self.checkUuidConsistency(set(self.getSelected()))

        # per second checks
        if time.time() - self.second_start > 1:
            self.checkPool()
            self.second_budget = 0
            self.second_start = time.time()

        # process command queue
        if time.time() - starttime < framebudget:
            self.processCommandQueue(starttime, framebudget)
        elif len(self.command_queue):
            self.queueRedraw()

    def processCommandQueue(self, starttime, budget):
        # the command queue can change while we execute here, but it should
        # be ok as long as things are just added at the end.
        # note if they are added at the beginning we would have problems
        # when deleting things after processing.
        self.command_queue += self.simrt.getQueue()
        cmds = self.command_queue
        second_budget = float(self.exportSettings.rt_sec_budget)/1000.0
        currbudget = 0
        self.stats[8] += 1
        if cmds:
            self.stats[2] += 1
            # first check the priority commands
            processed = []
            for idx, cmd in enumerate(cmds):
                currbudget = time.time()-starttime
                if currbudget < budget and self.second_budget+currbudget < second_budget:
                    if cmd[0] in priority_commands:
                        self.processCommand(*cmd)
                        processed.append(idx)
                else:
                    break
            # delete all processed elements. in reversed order
            # to avoid problems because of index changing
            for idx in reversed(processed):
                cmds.pop(idx)
            # now all other commands, note there should be no priority
            # commands so we just ignore they exist and process all commands.
            if time.time()-starttime < budget:
                processed = []
                for idx, cmd in enumerate(cmds):
                    currbudget = time.time()-starttime
                    if currbudget < budget and self.second_budget+currbudget < second_budget:
                        self.processCommand(*cmd)
                        processed.append(idx)
                    else:
                        break
                for idx in reversed(processed):
                    cmds.pop(idx)
        self.second_budget += currbudget
        self.stats[5] = len(self.command_queue)
        self.stats[6] = (currbudget)*1000 # processed
        self.stats[7] = threading.activeCount()-1

        # redraw if we have commands left
        if len(self.command_queue):
            self.queueRedraw()
            return
        self.checkTerrain()

    def checkTerrain(self, timebudget=20):
        updated_blocks = []

        if bpy.context.mode == 'EDIT_MESH' or bpy.context.mode == 'SCULPT':
            if bpy.context.scene.objects.active:
                if bpy.context.scene.objects.active.name == 'terrain':
                    self.terrain.set_dirty()
        elif self.terrain.is_dirty():
            start = time.time()
            while self.terrain.is_dirty() and time.time() - start < timebudget:
                updated_blocks.extend(self.terrain.check())

        self.sendTerrainBlocks(updated_blocks)

        if self.terrain.is_dirty() or updated_blocks:
            self.queueRedraw()

    def sendTerrainBlocks(self, updated_blocks):
        if not updated_blocks:
            return

        self.workpool.addRequest(self.encodeTerrainBlock, updated_blocks,
                             self.terrainEncoded, self.default_error_db)


    def encodeTerrainBlock(self, args):
        datablock, x, y = args
        bindata = TerrainEncoder.encode([[datablock, x, y]])
        b64data = base64.urlsafe_b64encode(bindata).decode('ascii')
        # send directly from the thread
        self.simrt.LayerData(x, y, b64data)
        return True

    def terrainEncoded(self, request, result):
        if result:
            pass

    def checkUuidConsistency(self, selected):
        # look for duplicates
        if self.rawselected == selected:
            return
        oldselected = self.selected
        newselected = {}
        isobjcopy = True
        for obj in selected:
            obj_uuid = obj.opensim.uuid
            if obj.type == 'MESH' and obj_uuid:
                mesh_uuid = obj.data.opensim.uuid
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
                else:
                    newselected[obj_uuid] = obj.as_pointer()
                    newselected[mesh_uuid] = obj.data.as_pointer()
        self.selected = newselected
        self.rawselected = selected

    def processView(self):
        self.stats[9] += 1

        selected = set(self.getSelected())
        all_selected = set()
        # changes in our own avatar
        agent = self.findWithUUID(self.agent_id)
        if agent:
            self.processUpdate(agent)
        # look for changes in objects
        for obj in selected:
            obj_id = self.get_uuid(obj)
            if obj_id in self.selected and obj.as_pointer() == self.selected[obj_id]:
                self.processUpdate(obj)
                all_selected.add(obj_id)
        # update selection
        if not all_selected == self.sim_selection:
            self.simrt.Select(*all_selected)
            self.sim_selection = all_selected

    def go(self):
        """
        Start the ogre interface system
        """
        self.screen.activate()

    def addRegionsPanel(self, regions, griddata):
        pass

    def queueRedraw(self, pars=None):
        pass



