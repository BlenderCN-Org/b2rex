# standard
import re
import uuid
import getpass, sys, logging
import time
from array import array
import math
from hashlib import md5
import popen2
import base64
import struct
import urlparse
from collections import defaultdict
from threading import Thread
#from terraindecoder import TerrainDecoder

# related
import eventlet
from eventlet import api
from eventlet import Queue
try:
    from jsonsocket import JsonSocket
    from simtypes import RegionFlags, SimAccess, LayerTypes, AssetType
except:
    from b2rexpkg.tools.jsonsocket import JsonSocket
    from b2rexpkg.tools.simtypes import RegionFlags, SimAccess, LayerTypes
    from b2rexpkg.tools.simtypes import AssetType
import socket

# pyogp
from pyogp.lib.base.exc import LoginError
from pyogp.lib.base.helpers import Helpers
from pyogp.lib.base.datatypes import UUID, Vector3, Quaternion

from pyogp.lib.client.agent import Agent
from pyogp.lib.client.settings import Settings
from pyogp.lib.client.enums import PCodeEnum
from pyogp.lib.client.namevalue import NameValueList
from pyogp.lib.base.message.message import Message, Block

import pyogp.lib.client.inventory
from pyogp.lib.client.inventory import UDP_Inventory
# Extra asset and inventory types for rex
import pyogp.lib.client.enums

def v3_to_list(v3):
    return [v3.X, v3.Y, v3.Z]
def q_to_list(q):
    return [q.X, q.Y, q.Z, q.W]
def b_to_s(b):
    return b.decode('utf-8')
def uuid_to_s(b):
    return str(b)
def unpack_q(data, offset):
    min = -1.0
    max = 1.0
    q = Quaternion(X=Helpers.packed_u16_to_float(data, offset,
                                                     min, max),
                        Y=Helpers.packed_u16_to_float(data, offset+2,
                                                     min, max),
                        Z=Helpers.packed_u16_to_float(data, offset+4,
                                                     min, max),
                        W=Helpers.packed_u16_to_float(data, offset+6,
                                                     min, max))
    return q

def unpack_v3(data, offset, min, max):
    vector3 = Vector3(X=Helpers.packed_u16_to_float(data, offset,
                                                     min, max),
                        Y=Helpers.packed_u16_to_float(data, offset+2,
                                                     min, max),
                        Z=Helpers.packed_u16_to_float(data, offset+4,
                                                     min, max))
    return vector3

def uuid_combine(uuid_one, uuid_two):
    return UUID(bytes=md5(uuid_one.uuid.bytes+uuid_two.uuid.bytes).digest())

class XferUploader(object):
    def __init__(self, data, cb):
        self.cb = cb
        self.data = data
        self.total = len(data)/1024
        self.first = True
        self.nseq = 1
        self.xferID = None
    def getNextPacket(self):
        if not len(self.data):
            return
        if len(self.data) <= 1024:
            nextdata = self.data
            self.data = b''
            ongoing = 0x80000000 # last packet
        else:
            nextdata = self.data[:1024]
            self.data = self.data[1024:]
            ongoing = 0x00000000 # last packet
        if self.first:
            nextdata = b'\0\0\0\0' + nextdata
            self.first = False

        packet = Message('SendXferPacket',
                        Block('XferID',
                                ID = self.xferID,
                                Packet = ongoing|self.nseq),
                         # first packet needs 4 bytes padding if we dont
                         # bootstrap some data ???
                        Block('DataPacket', Data=array('c',nextdata)))
        self.nseq += 1
        return packet

class XferUploadManager(object):
    def __init__(self, agent):
        self._agent = agent
        region = agent.region
        self._uploaders = {}
        res = region.message_handler.register("AssetUploadComplete")
        res.subscribe(self.onAssetUploadComplete)
        res = region.message_handler.register("ConfirmXferPacket")
        res.subscribe(self.onConfirmXferPacket)
        res = region.message_handler.register("RequestXfer")
        res.subscribe(self.onRequestXfer)

    def uploadAsset(self, assetType, data, cb):
        """
        Request an asset upload from the simulator
        """
        tr_uuid = UUID()
        tr_uuid.random()
        init_data = None
        if len(data) < 1024:
            init_data = array('c', data)
        else:
            assetID = uuid_combine(tr_uuid, self._agent.secure_session_id)
            newuploader = XferUploader(data, cb)
            self._uploaders[str(assetID)] = newuploader

        self._agent.asset_manager.upload_asset(tr_uuid,
                                               assetType,
                                               False, # tempfile
                                               True, # storelocal
                                               init_data) # asset_data
        return  assetID

    def onRequestXfer(self, packet):
        """
        Confirmation for our asset upload. Now send data.
        """
        xfer_id = packet["XferID"][0]["ID"]
        vfile_id = packet["XferID"][0]["VFileID"] # key and uuid of new asset
        if str(vfile_id) in self._uploaders:
            uploader = self._uploaders[str(vfile_id)]
            self._uploaders[xfer_id] = uploader
            uploader.xferID = xfer_id
            packet = uploader.getNextPacket()
            self._agent.region.enqueue_message(packet)
        else:
            print("NO UPLOAD FOR TRANSFER REQUEST!!", vfile_id,
                  self._uploaders.keys())

    def onConfirmXferPacket(self, packet):
        """
        Confirmation for one of our upload packets.
        """
        xfer_id = packet["XferID"][0]["ID"]
        if xfer_id in self._uploaders:
            uploader = self._uploaders[xfer_id]
            print("ConfirmXferPacket", packet["XferID"][0]["Packet"],
                  uploader.total)
            packet = uploader.getNextPacket()
            if packet:
                self._agent.region.enqueue_message(packet)

    def onAssetUploadComplete(self, packet):
        """
        Confirmation for completion of the asset upload.
        """
        assetID = packet['AssetBlock'][0]['UUID']
        if str(assetID) in self._uploaders:
            print("AssetUploadComplete Go On", assetID)
            self._uploaders[str(assetID)].cb(assetID)
            xfer_id = self._uploaders[str(assetID)].xferID
            del self._uploaders[xferID]
            del self._uploaders[str(assetID)]
        else:
            print("NO UPLOAD FOR ASSET UPLOAD COMPLETE!!", assetID,
                  self._uploaders.keys())




class BlenderAgent(object):
    do_megahal = False
    verbose = True
    def __init__(self, in_queue, out_queue):
        self.inventory = None
        self.nlayers = 0
        self._creating_cb = {}
        self._next_create = 1000
        self._eatupdates = defaultdict(int)
        self.client = None
        self.bps = 100*1024 # bytes per second
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.initialize_logger()

    def bootstrapClient(self):
        print("BOOTSTRAP CLIENT")
        for obj in self.client.region.objects.object_store:
            obj_uuid = str(obj.FullID)
            if hasattr(obj, "pos") and hasattr(obj, "rot"):
                self.out_queue.put(['pos', obj_uuid, obj.pos, obj.rot])
            if hasattr(obj, "scale"):
                self.out_queue.put(['scale', obj_uuid, obj.scale])
            if hasattr(obj, "rexdata"):
                self.out_queue.put(['RexPrimData', obj_uuid, obj.rexdata])
            if hasattr(obj, "props"):
                self.out_queue.put(["ObjectProperties", obj_uuid, obj.props])

    def onKillObject(self, packet):
        localID = packet["ObjectData"][0]["ID"]
        obj = self.client.region.objects.get_object_from_store(LocalID = localID)
        if not obj:
            obj = self.client.region.objects.get_avatar_from_store(LocalID = localID)
        if obj:
            self.out_queue.put(["delete", str(obj.FullID)])
        self.old_kill_object(packet)

    def setThrottle(self, bps):
        if not bps == self.bps:
            self.bps = bps
            client = self.client
            if client and client.connected and client.region.connected:
                self.sendThrottle(bps)

    def sendThrottle(self, bps=None):
        if not bps:
            bps = self.bps
        bps = bps*8 # we use bytes per second :)
        data = b''
        data += struct.pack('<f', bps*0.1) # resend
        data += struct.pack('<f', bps*0.1) # land
        data += struct.pack('<f', bps*0.2) # wind
        data += struct.pack('<f', bps*0.2) # cloud
        data += struct.pack('<f', bps*0.25) # task
        data += struct.pack('<f', bps*0.26) # texture
        data += struct.pack('<f', bps*0.25) # asset
        counter = 0
        packet = Message('AgentThrottle',
                        Block('AgentData',
                                AgentID = self.client.agent_id,
                                SessionID = self.client.session_id,
                             CircuitCode = self.client.circuit_code),
                        Block('Throttle',
                              GenCounter=counter,
                              Throttles=data))
        self.client.region.enqueue_message(packet)

    def sendCreateObject(self, objId, pos, rot, scale, tok):
        RayTargetID = UUID()
        RayTargetID.random()
        print("CREATE OBJECT WITH UUID", RayTargetID)

        self.client.region.objects.object_add(self.client.agent_id, self.client.session_id,
                        PCodeEnum.Primitive,
                        Material = 3, AddFlags = 2, PathCurve = 16,
                        ProfileCurve = 1, PathBegin = 0, PathEnd = 0,
                        PathScaleX = 100, PathScaleY = 100, PathShearX = 0,
                        PathShearY = 0, PathTwist = 0, PathTwistBegin = 0,
                        PathRadiusOffset = 0, PathTaperX = 0, PathTaperY = 0,
                        PathRevolutions = 0, PathSkew = 0, ProfileBegin = 0,
                        ProfileEnd = 0, ProfileHollow = tok, BypassRaycast = 1,
                        RayStart = pos, RayEnd = pos,
                        RayTargetID = RayTargetID, RayEndIsIntersection = 0,
                        Scale = scale, Rotation = rot,
                        State = 0)

    def onAgentMovementComplete(self, packet):
        # some region info
        AgentData = packet['AgentData'][0]
        Data = packet['Data'][0]
        self.logger.debug(packet)
        pos = Data['Position']
        lookat = Data['LookAt']
        agent_id = str(AgentData['AgentID'])
        lookat = [lookat.X, lookat.Y, lookat.Z]
        pos = [pos.X, pos.Y, pos.Z]
        self.out_queue.put(["AgentMovementComplete", agent_id, pos, lookat])

    def sendLayerData(self, x, y, b64data):
        bindata = base64.urlsafe_b64decode(b64data.encode('ascii'))
        packet = Message('LayerData',
                        Block('LayerID',
                                Type = LayerTypes.LayerLand),
                        Block('LayerData',
                              Data=bindata))
        self.client.region.enqueue_message(packet)

    def onLayerData(self, packet):
        data = packet["LayerData"][0]["Data"]
        layerType = struct.unpack("<B", data[3])[0]
        if layerType == LayerTypes.LayerLand or True:
            b64data = base64.urlsafe_b64encode(data).decode('ascii')
            self.out_queue.put(["LayerData", layerType, b64data])

    def decompressLand(self, data, stride, patchSize):
        return TerrainDecoder.decode(data, stride, patchSize)

    def onParcelOverlay(self, packet):
        # some region info
        self.logger.debug(packet)

    def sendRexPrimData(self, obj_uuid, args):
        agent_id = self.client.agent_id
        session_id = self.client.session_id
        t_id = uuid.uuid4()
        invoice_id = UUID()
        data = b''
        materials = []
        if "materials" in args:
            materials=args["materials"]
        # drawType (1 byte)
        if 'drawType' in args:
            data += struct.pack('<b', args['drawType'])
        else:
            data += struct.pack('<b', 1) # where is this 1 coming from ??
        # bool properties
        for prop in ['RexIsVisible', 'RexCastShadows',
                     'RexLightCreatesShadows', 'RexDescriptionTexture',
                     'RexDescriptionTexture']:
            if prop in args:
                data += struct.pack('<?', args[prop])
            else:
                data += struct.pack('<?', False)

        # float properties
        for prop in ['RexDrawDistance', 'RexLOD']:
            if prop in args:
                data += struct.pack('<f', args[prop])
            else:
                data += struct.pack('<f', 0.0)

        # uuid properties
        for prop in ['RexMesh', 'RexCollisionMesh',
                     'RexParticleScript', 'RexAnimationPackage']:
            prop = prop+'UUID'
            if prop in args:
                data += bytes(UUID(args[prop]).data().bytes)
            else:
                data += bytes(UUID().data().bytes)

        data += b'\0' # empty animation name
        data += struct.pack("<f", 0) # animation rate

        data += struct.pack("<b", len(materials)) # materials count
        for idx, matID in enumerate(materials):
            data += struct.pack('<b', AssetType.OgreMaterial)
            data += bytes(UUID(matID).data().bytes)
            data += struct.pack('<b', idx)

        data += b'\0'*(200-len(data)) # just in case :P
        # prepare packet
        packet = Message('GenericMessage',
                        Block('AgentData',
                                AgentID = agent_id,
                                SessionID = session_id,
                             TransactionID = t_id),
                        Block('MethodData',
                                Method = 'RexPrimData',
                                Invoice = invoice_id),
                        Block('ParamList', Parameter=str(obj_uuid)),
                        Block('ParamList', Parameter=data))
        # send
        self.client.region.enqueue_message(packet)

    def onRexPrimData(self, packet):
        rexdata = packet[1]["Parameter"]
        if len(rexdata) < 102:
            rexdata = rexdata + ('\0'*(102-len(rexdata)))
        obj_uuid = UUID(packet[0]["Parameter"])
        obj_uuid_str = str(obj_uuid)
        pars = {}
        pars["drawType"] = struct.unpack("<b", rexdata[0])[0]

        pars["RexIsVisible"]= struct.unpack("<?", rexdata[1])[0]
        pars["RexCastShadows"]= struct.unpack("<?", rexdata[2])[0]
        pars["RexLightCreatesShadows"]= struct.unpack("<?", rexdata[3])[0]
        pars["RexDescriptionTexture"] = struct.unpack("<?", rexdata[4])[0]
        pars["RexScaleToPrim"]= struct.unpack("<?", rexdata[5])[0]
        pars["RexDrawDistance"]= struct.unpack("<f", rexdata[6:6+4])[0]
        pars["RexLOD"]= struct.unpack("<f", rexdata[10:10+4])[0]
        pars["RexMeshUUID"]= str(UUID(bytes=rexdata[14:14+16]))
        pars["RexCollisionMeshUUID"]= str(UUID(bytes=rexdata[30:30+16]))
        pars["RexParticleScriptUUID"]= str(UUID(bytes=rexdata[46:46+16]))
        pars["RexAnimationPackageUUID"]= str(UUID(bytes=rexdata[62:62+16]))
        obj = self.client.region.objects.get_object_from_store(FullID = obj_uuid)
        if obj:
            obj.rexdata = pars
        self.out_queue.put(['RexPrimData', obj_uuid_str, pars])
        # animation
        animname = ""
        idx = 78
        while rexdata[idx] != '\0':
            idx += 1
        animname = rexdata[78:idx+1]
        pos = idx+1
        RexAnimationRate = struct.unpack("<f", rexdata[pos:pos+4])[0]
        # materials
        materialsCount = struct.unpack("<b", rexdata[pos+4])[0]
        pos = pos+5
        materials = []
        for i in range(materialsCount):
            assettype = struct.unpack("<b", rexdata[pos])[0]
            matuuid_b = rexdata[pos+1:pos+1+16]
            matuuid = UUID(bytes=matuuid_b)
            matindex = struct.unpack("<b", rexdata[pos+17])[0]
            materials.append([matindex, str(matuuid), assettype])
            pos = pos + 18
        pars["Materials"] = materials
        if not len(rexdata) > pos:
            #self.logger.debug("RexPrimData: no more data")
            return
        idx = pos
        while rexdata[idx] != '\0':
              idx += 1
        RexClassName = rexdata[pos:idx+1]
        #self.logger.debug(" REXCLASSNAME: " + str(RexClassName))

    def onGenericMessage(self, packet):
        if packet["MethodData"][0]["Method"] == "RexPrimData":
            self.onRexPrimData(packet["ParamList"])
        else:
            self.logger.debug("unrecognized generic message"+packet["MethodData"][0]["Method"])
            print(packet)

    def onImprovedTerseObjectUpdate(self, packet):
        for packet_ObjectData in packet['ObjectData']:
            data = packet_ObjectData['Data']
            localID = struct.unpack("<I", data[0:4])[0]
            naaliProto = False
            if len(data) == 30:
                is_avatar = True
                naaliProto = True
                idx = 4
            else:
                attachPoint = struct.unpack("<b", data[4])[0]
                is_avatar = struct.unpack("<?", data[5])[0]
                idx = 6
                if is_avatar:
                    collisionPlane = Quaternion(data[idx:idx+16])
                    idx += 16
                minlen = idx+12+6+6+6+8
                if is_avatar:
                    minlen += 16
                if len(data) < minlen:
                    data = data + ('\0'*(minlen-len(data)))
            pos = Vector3(data[idx:idx+12])
            idx += 12
            vel = unpack_v3(data, idx, -128.0, 128.0)
            idx += 6
            if not naaliProto:
                accel = unpack_v3(data, idx, -64.0, 64.0)
                idx += 6
            rot = unpack_q(data, idx)
            idx += 8
            if not naaliProto:
                angular_vel = unpack_v3(data, idx, -64.0, 64.0)
            if is_avatar:
                obj = self.client.region.objects.get_avatar_from_store(LocalID = localID)
                if not obj:
                    print("cant find avatar!!")
            else:
                obj = self.client.region.objects.get_object_from_store(LocalID = localID)
            # print("onImprovedTerseObjectUpdate", localID, pos, vel, accel, obj)
            if obj:
                if self._eatupdates[obj.LocalID]:
                    self._eatupdates[obj.LocalID]-= 1
                    return
                obj_uuid = str(obj.FullID)
                obj.pos = v3_to_list(pos)
                obj.rot = q_to_list(rot)
                self.out_queue.put(['pos', obj_uuid, v3_to_list(pos), q_to_list(rot)])
            else:
                print("cant find object")

    def sendLocalTeleport(self, agent, pos):
        if not agent.FullID == self.agent_id:
            print("Trying to move an agent for other user")
        t_id = uuid.uuid4()
        client = self.client
        invoice_id = UUID()
        self.client.teleport(region_handle=client.region.RegionHandle, 
                             position=Vector3(X=pos[0], Y=pos[1], Z=pos[2]))

    def sendAutopilot(self, agent, pos):
        packet = Message('GenericMessage',
                        Block('AgentData',
                                AgentID = client.agent_id,
                                SessionID = client.session_id,
                             TransactionID = t_id),
                        Block('MethodData',
                                Method = 'autopilot',
                                Invoice = invoice_id),
                        Block('ParamList', Parameter=data_x),
                        Block('ParamList', Parameter=data_y),
                        Block('ParamList', Parameter=data_z))
        self.client.region.enqueue_message(packet)

    def onObjectPermissions(self, packet):
        self.logger.debug("PERMISSIONS!!!")

    def onObjectProperties(self, packet):
        self.logger.debug("ObjectProperties!!!")
        pars = {}
        value_pars = ['CreationDate', 'EveryoneMask', 'BaseMask',
                      'OwnerMask', 'GroupMask' , 'NextOwnerMask',
                      'OwnershipCost', 'SaleType', 'SalePrice',
                      'AggregatePerms', 'AggregatePermTextures',
                      'AggregatePermTexturesOwner', 'Category',
                      'InventorySerial', 'Name', 'Description', 'TouchName',
                      'SitName', 'TextureID']
        uuid_pars = ['ObjectID', 'CreatorID', 'OwnerID', 'GroupID', 'ItemID',
                     'FolderID', 'FromTaskID', 'LastOwnerID']
        for block in packet["ObjectData"]:
            for par in value_pars:
                pars[par] = block[par]
            for par in uuid_pars:
                pars[par] = str(block[par])
            obj_uuid = str(pars['ObjectID'])
            obj = self.client.region.objects.get_object_from_store(FullID=obj_uuid)
            if obj:
                obj.props = pars
            self.out_queue.put(["ObjectProperties", obj_uuid, pars])

    def deleteObject(self, obj_id):
        obj = self.client.region.objects.get_object_from_store(FullID=obj_id)
        # SaveToExistingUserInventoryItem = 0,
        # TakeCopy = 1,
        # Take = 4,
        # GodTakeCopy = 5,
        # Delete = 6,
        # Return = 9
        tr_id = UUID(str(uuid.uuid4()))
        packet = Message('DeRezObject',
                        Block('AgentData',
                                AgentID = self.client.agent_id,
                                SessionID = self.client.session_id),
                        Block('AgentBlock',
                                 GroupID = UUID(),
                                 Destination = 6,
                                 DestinationID = UUID(),
                                 TransactionID = tr_id,
                                 PacketCount = 1,
                                 PacketNumber = 0),
                        Block('ObjectData',
                                ObjectLocalID = obj.LocalID))
        # send
        self.client.region.enqueue_message(packet)

    def createObject(self, obj_name, obj_uuid_str, mesh_name, mesh_uuid_str, pos, rot,
                     scale, b64data):
        # create asset
        obj_uuid = UUID(obj_uuid_str)
        data = base64.urlsafe_b64decode(b64data.encode('ascii'))
        self._next_create = (self._next_create + 1) % (256*256)
        obj_idx = self._next_create
        def finishupload(asset_id):
            # asset uploaded, we have its uuid and can proceed now
            tok = UUID(str(uuid.uuid4()))
            def finish_creating(real_uuid):
                # object finished creating and here we get its real uuid and can
                # confirm creation to the client sending the new uuids.
                del self._creating_cb[obj_idx]
                args = {"RexMeshUUID": str(asset_id),
                        "RexIsVisible": True}
                self.sendRexPrimData(real_uuid, args)
                self.out_queue.put(["meshcreated", obj_uuid_str, mesh_uuid_str,
                                    str(real_uuid), str(asset_id)])
            self._creating_cb[obj_idx] = finish_creating
            self.sendCreateObject(obj_uuid, pos, rot, scale, obj_idx)

        # send the asset data and wait for ack from the uploader
        assetID = self.uploader.uploadAsset(AssetType.OgreMesh, data, finishupload)

    def cloneObject(self, obj_name, obj_uuid_str, mesh_name, mesh_uuid_str, pos, rot,
                     scale):
        # create asset
        obj_uuid = UUID(obj_uuid_str)
        self._next_create = (self._next_create + 1) % (256*256)
        obj_idx = self._next_create

        tok = UUID(str(uuid.uuid4()))
        def finish_creating(real_uuid):
            del self._creating_cb[obj_idx]
            args = {"RexMeshUUID": mesh_uuid_str,
                    "RexIsVisible": True}
            self.out_queue.put(["meshcreated", obj_uuid_str, mesh_uuid_str,
                                str(real_uuid), mesh_uuid_str])
            self.sendRexPrimData(real_uuid, args)
        self._creating_cb[obj_idx] = finish_creating
        self.sendCreateObject(obj_uuid, pos, rot, scale, obj_idx)

    def onCoarseLocationUpdate(self, packet):
        #print("COARSE LOCATION UPDATE")
        #print(packet)
        for i, block in enumerate(packet["Location"]):
            X = block['X']
            Y = block['Y']
            Z = block['Z']
            agent = packet["AgentData"][i]["AgentID"]

            self.out_queue.put(["CoarseLocationUpdate", str(agent), (X, Y, Z)])

    def onOnlineNotification(self, packet):
        self.out_queue.put(["OnlineNotification",
                            str(packet["AgentBlock"][0]["AgentID"])])

    def onOfflineNotification(self, packet):
        self.out_queue.put(["OfflineNotification",
                            str(packet["AgentBlock"][0]["AgentID"])])

    def onRegionHandshake(self, packet):
        regionInfo = packet["RegionInfo"][0]

        pars = {}

        for prop in ['RegionFlags', 'SimAccess', 'SimName', 'WaterHeight',
                     'BillableFactor', 'TerrainStartHeight00',
                     'IsEstateManager',
                     'TerrainStartHeight01', 'TerrainStartHeight10',
                     'TerrainStartHeight11', 'TerrainHeightRange00',
                     'TerrainHeightRange01', 'TerrainHeightRange10',
                     'TerrainHeightRange11']:
            pars[prop] = regionInfo[prop]

        for prop in ["SimOwner", 'CacheID', 'TerrainBase0', 'TerrainBase1',
                     'TerrainBase2', 'TerrainDetail0', 'TerrainDetail1',
                     'TerrainDetail2', 'TerrainDetail3']:
            pars[prop] = str(regionInfo[prop])

        pars["RegionID"] = str(packet["RegionInfo2"][0]["RegionID"])
        pars["CPUClassID"] = packet["RegionInfo3"][0]["CPUClassID"]
        pars["CPURatio"] = packet["RegionInfo3"][0]["CPURatio"]

        self.out_queue.put(["RegionHandshake", pars["RegionID"], pars])

    def login(self, server_url, username, password, regionname, firstline=""):
        """ login an to a login endpoint """ 
        in_queue = self.in_queue
        out_queue = self.out_queue

        client = self.initialize_agent()
        self.inventory = UDP_Inventory(client)
        # Now let's log it in
        region = regionname
        firstname, lastname = username.split(" ", 1)
        parsed_url = urlparse.urlparse(server_url)
        split_netloc = parsed_url.netloc.split(":")
        if len(split_netloc) == 2:
            server_name, port = split_netloc
        else:
            server_name = parsed_url.netloc
            port = None
        try:
            # reconstruct the url with the ip to avoid problems
            res_server_name = socket.gethostbyname(server_name)
            if res_server_name == '::1': # :-P
                res_server_name = '127.0.0.1'
                #if res_server_name in ['127.0.01', '::1']:
            server_name = res_server_name
        except:
            pass
        if port:
            server_name = server_name + ":" + port
        else:
            server_name = server_name + '/xml-rpc.php'
        server_url = parsed_url.scheme + '://' + server_name
        #if not server_url.endswith("/"):
            #    server_url = server_url + "/"
        loginuri = server_url
        api.spawn(client.login, loginuri, firstname, lastname, password,
                  start_location = region, connect_region = True)

        client.sit_on_ground()

        # wait for the agent to connect to it's region
        while client.connected == False:
            api.sleep(0)

        # inform our client of connection success
        out_queue.put(["connected", str(client.agent_id),
                             str(client.agent_access)])
 
        # we pre-hook KillObject in a special way because we need to use the
        # cache one last time
        self.old_kill_object = self.client.region.objects.onKillObject
        self.client.region.objects.onKillObject = self.onKillObject
        #res = client.region.message_handler.register("KillObject")
        #res.subscribe(self.onKillObject)

        self.inventory.enable_callbacks()
        self.uploader = XferUploadManager(self.client)

        res = client.region.message_handler.register("OnlineNotification")
        res.subscribe(self.onOnlineNotification)
        res = client.region.message_handler.register("OfflineNotification")
        res.subscribe(self.onOfflineNotification)

        res = client.region.message_handler.register("RegionHandshake")
        res.subscribe(self.onRegionHandshake)
        res = client.region.message_handler.register("CoarseLocationUpdate")
        res.subscribe(self.onCoarseLocationUpdate)
        res = client.region.message_handler.register("ImprovedTerseObjectUpdate")
        res.subscribe(self.onImprovedTerseObjectUpdate)
        res = client.region.message_handler.register("GenericMessage")
        res.subscribe(self.onGenericMessage)
        res = client.region.message_handler.register("ParcelOverlay")
        res.subscribe(self.onParcelOverlay)
        res = client.region.message_handler.register("AgentMovementComplete")
        res.subscribe(self.onAgentMovementComplete)
        res = client.region.message_handler.register("LayerData")
        res.subscribe(self.onLayerData)
        res = client.region.message_handler.register("ChatFromSimulator")
        res.subscribe(self.onChatFromViewer)
        res = client.region.objects.message_handler.register("ObjectUpdate")
        res.subscribe(self.onObjectUpdate)
        res = client.region.message_handler.register("SimStats")
        res.subscribe(self.onSimStats)
        res = client.region.message_handler.register("RexPrimData")
        res.subscribe(self.onRexPrimData)
        res = client.region.message_handler.register("ObjectPermissions")
        res.subscribe(self.onObjectPermissions)
        res = client.region.message_handler.register("ObjectProperties")
        res.subscribe(self.onObjectProperties)
        res = client.region.objects.message_handler.register("RexPrimData")
        res.subscribe(self.onRexPrimData)
        res = client.region.message_handler.register("InventoryDescendents")
        res.subscribe(self.onInventoryDescendents)

        caps_sent = False
        caps = {}

        # wait until the client is connected
        while client.region.connected == False:
            # look for GetTexture and send to client as soon as possible
            if not caps_sent and "GetTexture" in client.region.capabilities:
                for cap in client.region.capabilities:
                    caps[cap] = client.region.capabilities[cap].public_url
                self.out_queue.put(["capabilities", caps])
                caps_sent = True
            api.sleep(0)


        print("connected")
        f = open("/home/caedes/Firefox_wallpaper.png", "rb")
        data = f.read()
        f.close
        def uploadcheck(*blah):
            print("XFER: UploadDone!!", blah)
        print("Sending xfer")
        self.uploader.uploadAsset(0, data, uploadcheck)
        print("Sending xfer sent")


        self.sendThrottle()
        api.sleep(100.3)

        # speak up the first line
        client.say(str(firstline))

       # send inventory skeleton
        if hasattr(self.client, 'login_response') and 'inventory-skeleton' in self.client.login_response:
            out_queue.put(["InventorySkeleton",  self.client.login_response['inventory-skeleton']])

        self.inventory._parse_folders_from_login_response()    

        # main loop for the agent
        selected = set()
        while client.running == True:
            api.sleep()
            cmd = in_queue.get()
            cmd_type = 9 # 1-pos, 2-rot, 3-rotpos 4,20-scale, 5-pos,scale,
            #   # 10-rot
            if cmd[0] == "quit":
                continue # ignore
                out_queue.put(["quit"])
                client.logout()
                return
            elif cmd[0] == "throttle":
                self.setThrottle(*cmd[1:])
            elif cmd[0] == "bootstrap":
                self.bootstrapClient()
            elif cmd[0] == "create":
                self.createObject(*cmd[1:])
            elif cmd[0] == "delete":
                self.deleteObject(*cmd[1:])
            elif cmd[0] == "clone":
                self.cloneObject(*cmd[1:])
            elif cmd[0] == "select":
                selected_cmd = set(cmd[1:])
                newselected = selected_cmd.difference(selected)
                deselected = selected.difference(selected_cmd)
                for obj_id in newselected:
                    obj = client.region.objects.get_object_from_store(FullID=obj_id)
                    if obj:
                        obj.select(client)
                    else:
                        print("cant find "+obj_id)
                for obj_id in deselected:
                    obj = client.region.objects.get_object_from_store(FullID=obj_id)
                    if obj:
                        obj.deselect(client)
                selected = selected_cmd
            elif cmd[0] == "msg":
                client.say(cmd[1])
            elif cmd[0] == "scale":
                cmd_type = 12
                obj = client.region.objects.get_object_from_store(FullID=cmd[1])
                if obj:
                    data = cmd[2]
                    self._eatupdates[obj.LocalID] += 1
                    client.region.objects.send_ObjectPositionUpdate(client, client.agent_id,
                                              client.session_id,
                                              obj.LocalID, data, cmd_type)
            elif cmd[0] == "pos":
                obj = client.region.objects.get_object_from_store(FullID=cmd[1])
                if not obj:
                    obj = client.region.objects.get_avatar_from_store(FullID=UUID(cmd[1]))
                    if obj:
                        self.sendLocalTeleport(obj, cmd[2])
                        continue
                if obj:
                    pos = cmd[2]
                    rot = cmd[3]
                    self.sendPositionUpdate(obj, pos, rot)
            elif cmd[0] == "updatepermissions":
                obj = client.region.objects.get_object_from_store(FullID=cmd[1])
                if obj:
                    mask = cmd[2]
                    val = cmd[3]
                    self.updatePermissions(obj, mask, val)
            elif cmd[0] == "LayerData":
                self.sendLayerData(*cmd[1:])
            elif cmd[0] == "sendFetchInventoryDescendentsRequest":
                func = getattr(self.inventory, cmd[0])
                func(*cmd[1:])

    def onInventoryDescendents(self, packet):
        folder_id = packet['AgentData'][0]['FolderID']
        folders = [{'Name' : member.Name, 'ParentID' : str(member.ParentID), 'FolderID' : str(member.FolderID)} for member in self.inventory.folders if str(member.ParentID) == str(folder_id)]
        return # needs update on pyogp
        items =  [{'Name' : member.Name, 'FolderID' : str(member.FolderID), 'ItemID' : str(member.ItemID)} for member in self.inventory.items if str(member.FolderID) == str(folder_id)] 

        self.out_queue.put(['InventoryDescendents', str(folder_id), folders, items])

    def sendPositionUpdate(self, obj, pos, rot):
        cmd_type = 9 # 1-pos, 2-rot, 3-rotpos 4,20-scale, 5-pos,scale,
        client = self.client
        if rot:
            X = rot[0]
            Y = rot[1]
            Z = rot[2]
            W = rot[3]
            norm = math.sqrt((X*X)+(Y*Y)+(Z*Z)+(W*W))
            if norm == 0:
                data = [pos[0], pos[1], pos[2]]
            else:
                norm = 1.0 / norm
                if W < 0:
                    X = -X
                    Y = -Y
                    Z = -Z
                data = [pos[0], pos[1], pos[2],
                        #0.0,0.0,0.0,
                        #0.0,0.0,0.0,
                        X*norm, Y*norm, Z*norm]
                cmd_type = 11 # PrimGroupRotation
        else:
            data = [pos[0], pos[1], pos[2]]
        self._eatupdates[obj.LocalID] += 1
        client.region.objects.send_ObjectPositionUpdate(client, client.agent_id,
                                  client.session_id,
                                  obj.LocalID, data, cmd_type)
    def updatePermissions(self, obj, mask, val):
        
        if self.verbose:
            print("updatePermissions:", obj, mask, val)

        client = self.client
        obj.update_object_permissions(client, 0x08, val, mask)


    def initialize_logger(self):
        self.logger = logging.getLogger("b2rex.simrt")

        if self.verbose:
            console = logging.StreamHandler()
            console.setLevel(logging.DEBUG) # seems to be a no op, set it for the logger
            formatter = logging.Formatter('%(asctime)-30s%(name)-30s: %(levelname)-8s %(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)

            # setting the level for the handler above seems to be a no-op
            # it needs to be set for the logger, here the root logger
            # otherwise it is NOTSET(=0) which means to log nothing.
            logging.getLogger('').setLevel(logging.DEBUG)

    def initialize_agent(self):
        # let's disable inventory handling for this example
        settings = Settings()
        settings.ENABLE_INVENTORY_MANAGEMENT = False
        settings.ENABLE_EQ_LOGGING = False
        settings.ENABLE_CAPS_LOGGING = False
        settings.ENABLE_REGION_EVENT_QUEUE = False
        settings.REGION_EVENT_QUEUE_POLL_INTERVAL = 1

        #First, initialize the agent
        client = Agent(settings = settings, handle_signals=False)
        self.client = client
        self.do_megahal = False
        if self.do_megahal:
            megahal_r, megahal_w = popen2.popen2("/usr/bin/megahal-personal -p -b -w -d /home/caedes/bots/lorea/.megahal")
            firstline = megahal_r.readline()
        return client

    def onSimStats(self, packet):
        return
        for stat in packet["Stat"]:
            self.logger.debug(str(stat["StatID"]) + " " + str(stat["StatValue"]))
        self.logger.debug("received sim stats!"+str(packet))

    def onObjectUpdate(self, packet):
        out_queue = self.out_queue
        for ObjectData_block in packet['ObjectData']:
           if ObjectData_block['ProfileHollow'] in self._creating_cb:
               # we use ProfileHollow as a key for our object creation since
               # its the only way I found to keep some transaction id around and
               # we dont use the value anyways.
               self._creating_cb[ObjectData_block["ProfileHollow"]](ObjectData_block["FullID"])
               return

           objdata = ObjectData_block["ObjectData"]
           obj_uuid = uuid_to_s(ObjectData_block["FullID"])
           obj = self.client.region.objects.get_object_from_store(FullID=obj_uuid)
           if obj and self._eatupdates[obj.LocalID]:
               self._eatupdates[obj.LocalID]-= 1
               return
           pars = { "OwnerID": str(ObjectData_block["OwnerID"]),
                    "PCode":ObjectData_block["PCode"] }
           parent_id = ObjectData_block["ParentID"]
           if parent_id:
               parent =  self.client.region.objects.get_object_from_store(LocalID=parent_id)
               if parent:
                   pars["ParentID"] = str(parent.FullID)
           namevalue = NameValueList(ObjectData_block['NameValue'])
           if namevalue._dict:
               pars['NameValues'] = namevalue._dict
           out_queue.put(['props', obj_uuid, pars])
           if "Scale" in ObjectData_block.var_list:
               scale = ObjectData_block["Scale"]
               if obj:
                  obj.scale = v3_to_list(scale)
               out_queue.put(['scale', obj_uuid,
                                     v3_to_list(scale)])
           if len(objdata) == 48:
               pos_vector = Vector3(objdata)
               vel = Vector3(objdata[12:])
               acc = Vector3(objdata[24:])
               rot = Quaternion(objdata[36:])
               if obj:
                   obj.pos = v3_to_list(pos_vector)
                   obj.rot = q_to_list(rot)
               out_queue.put(['pos', obj_uuid, v3_to_list(pos_vector),
                              q_to_list(rot)])
           elif len(objdata) == 12:
               if True:
                   # position only packed as 3 floats
                   pos = Vector3(objdata)
                   if obj:
                      obj.pos = v3_to_list(pos)
                   out_queue.put(['pos', obj_uuid, v3_to_list(pos)])
               elif ObjectData_block.Type in [4, 20, 12, 28]:
                   # position only packed as 3 floats
                   scale = Vector3(objdata)
                   out_queue.put(['scale', obj_uuid, v3_to_list(scale)])
               elif ObjectData_block.Type in [2, 10]:
                   # rotation only packed as 3 floats
                   rot = Quaternion(objdata)
                   out_queue.put(['rot', obj_uuid, q_to_list(rot)])
         
           else:
                # missing sizes: 28, 40, 44, 64
                self.logger.debug("Unparsed update of size "+str(len(objdata)))

    def onChatFromViewer(self, packet):
        client = self.client
        out_queue = self.out_queue
        fromname = packet["ChatData"][0]["FromName"].split(" ")[0]
        message = packet["ChatData"][0]["Message"]
        out_queue.put(['msg',fromname, message])
        if message.startswith("#"):
            return
        if fromname.strip() == client.firstname:
            return
        elif message == "quit":
            if self.do_megahal:
                megahal_w.write("#QUIT\n\n")
                megahal_w.flush()
            client.say("byez!")
            api.sleep(10)
            if self.do_megahal:
                megahal_r.close()
                megahal_w.close()
            client.logout()
            api.sleep(50)
            #while client.connected:
                #    api.sleep(0)
        elif message == "sit":
            client.fly(False)
            client.sit_on_ground()
        elif message == "stand":
            client.fly(False)
            client.stand()
        elif message == "fly":
            client.fly()
        elif message == "+q":
            if fromname not in queue:
                queue.append(fromname)
                client.say(str(queue))
        elif message == "-q":
            if fromname in queue:
                queue.remove(fromname)
                client.say(str(queue))
        else:
            if self.do_megahal:
                megahal_w.write(message+"\n\n")
                megahal_w.flush()
                client.say(str(megahal_r.readline()))
        self.logger.debug("chat:"+packet["ChatData"][0]["Message"])
        self.logger.debug("chat:"+packet["ChatData"][0]["FromName"])


class GreenletsThread(Thread):
    def __init__ (self, server_url, username, password, region, firstline="Hello"):
        self.running = True
        self.agent = True
        self.cmd_out_queue = []
        self.cmd_in_queue = []
        self.out_queue = Queue()
        self.in_queue = Queue()
        self.server_url = server_url
        self.regionname = region
        self.username = username
        self.password = password
        self.firstline = firstline
        Thread.__init__(self)

    def apply_position(self, obj_uuid, pos, rot=None):
        cmd = ['pos', obj_uuid, pos, rot]
        self.addCmd(cmd)

    def apply_scale(self, obj_uuid, scale):
        cmd = ['scale', obj_uuid, scale]
        self.addCmd(cmd)

    def run(self):
        agent = BlenderAgent(self.in_queue,
                   self.out_queue)
        agent.login(self.server_url,
                    self.username,
                    self.password,
                    self.regionname,
                    self.firstline)
        agent.logger.debug("Quitting")
        self.agent = agent
        self.running = False

    def addCmd(self, cmd):
        self.in_queue.put(cmd)

    def getQueue(self):
        out_queue = []
        while self.out_queue.qsize():
            out_queue.append(self.out_queue.get())
        return out_queue

running = False

def run_thread(context, server_url, username, password, region, firstline):
    global running
    running = GreenletsThread(server_url, username, password, region, firstline)
    running.start()
    return running

def stop_thread():
    global running
    running.stop()
    running = None


# the following is to run in stand alone mode
class ClientHandler(object):
    def __init__(self):
        self.current = None
        self.deferred_cmds = []
    def read_client(self, json_socket, pool):
        global running
        while True:
            data = json_socket.recv()
            if not data:
                # client disconnected, bail out
                self.current.out_queue.put(["quit"])
                break
            if data[0] == 'connect':
                if not running:
                    # initial connect command
                    running = GreenletsThread(*data[1:])
                    self.current = running
                    pool.spawn_n(running.run)
                    for cmd in self.deferred_cmds:
                        running.addCmd(cmd)
                    self.deferred_cmds = []
                    json_socket.send(["hihi"])
                else:
                    running.addCmd(["bootstrap"])
            elif self.current:
                # forward command
                self.current.addCmd(data)
            else:
                if data[0] in ["throttle"]:
                    self.deferred_cmds.append(data)
        print("exit read client")
        # exit
        self.connected = False
    def handle_client(self, json_socket, pool):
        global running
        global run_main
        self.connected = True
        pool.spawn_n(self.read_client, json_socket, pool)
        if running:
            json_socket.send(["state", "connected"])
        else:
            json_socket.send(["state", "idle"])
        starttime = time.time()
        while self.connected:
            if self.current:
                cmd = self.current.out_queue.get()
                if cmd[0] == "quit":
                    print("quit on handle client")
                    break;
                else:
                    json_socket.send(cmd)
                #for cmd in self.current.queue.get():
                    #    json_socket.send(cmd)
                    #api.sleep(0)
            else:
                api.sleep(0)
        json_socket.close()
        if running:
            running.addCmd(["quit"])
            running = None
            # run_main = False
        # live..
        #raise eventlet.StopServe

run_main = True
def main():
    server = eventlet.listen(('0.0.0.0', 11112))
    pool = eventlet.GreenPool(1000)
    while run_main:
         new_sock, address = server.accept()
         client_handler = ClientHandler()
         pool.spawn_n(client_handler.handle_client, JsonSocket(new_sock), pool)
         api.sleep(0)

    #current = GreenletsThread(cmd_queue)
    #current.start()
    #while current.isAlive():
        #    time.sleep(1)

if __name__=="__main__":
    main()


