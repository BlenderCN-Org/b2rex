try:
    from simtypes import AssetType
except:
    from b2rexpkg.tools.simtypes import AssetType

import uuid
import math
import struct
import base64
from collections import defaultdict

from pyogp.lib.client.enums import PCodeEnum

from pyogp.lib.base.datatypes import UUID, Vector3, Quaternion
from pyogp.lib.base.message.message import Message, Block
from pyogp.lib.client.namevalue import NameValueList

from ..tools import v3_to_list, q_to_list, uuid_combine, uuid_to_s
from ..tools import unpack_v3, unpack_q, b_to_s, prepare_server_name

from .base import Handler

class ObjectHandler(Handler):
    _eatupdates = defaultdict(int)
    _next_create = 1000
    _creating_cb = {}
    def onRegionConnect(self, region):
        res = region.message_handler.register("ObjectPermissions")
        res.subscribe(self.onObjectPermissions)
        res = region.message_handler.register("ObjectProperties")
        res.subscribe(self.onObjectProperties)

        res = region.message_handler.register("ImprovedTerseObjectUpdate")
        res.subscribe(self.onImprovedTerseObjectUpdate)
        res = region.objects.message_handler.register("ObjectUpdate")
        res.subscribe(self.onObjectUpdate)

        # we pre-hook KillObject in a special way because we need to use the
        # cache one last time
        objects = self.client.region.objects
        self.old_kill_object = objects.onKillObject
        objects.onKillObject = self.onKillObject

    def onAgentConnected(self, agent):
        self.client = agent
        self.rexdata = self.manager.rexdata

    def onKillObject(self, packet):
        objects = self.manager.client.region.objects
        localID = packet["ObjectData"][0]["ID"]
        obj = objects.get_object_from_store(LocalID = localID)
        if not obj:
            obj = objects.get_avatar_from_store(LocalID = localID)
        if obj:
            self.out_queue.put(["delete", str(obj.FullID)])
        self.old_kill_object(packet)

    def sendCreateObject(self, objId, pos, rot, scale, tok):
        RayTargetID = UUID()
        RayTargetID.random()

        client = self.manager.client
        client.region.objects.object_add(client.agent_id, client.session_id,
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


    def onImprovedTerseObjectUpdate(self, packet):
        client = self.manager.client
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
                obj = client.region.objects.get_avatar_from_store(LocalID = localID)
                if not obj:
                    print("cant find avatar!!")
            else:
                obj = client.region.objects.get_object_from_store(LocalID = localID)
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

    def processCreate(self, obj_name, obj_uuid_str, mesh_name, mesh_uuid_str, pos, rot,
                     scale, b64data, materials):
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
                        "RexIsVisible": True,
                        "materials": materials}
                #self.processPos(obj_uuid_str, pos, rot)
                self.rexdata.sendRexPrimData(real_uuid, args)
                self.out_queue.put(["meshcreated", obj_uuid_str, mesh_uuid_str,
                                    str(real_uuid), str(asset_id)])
            self._creating_cb[obj_idx] = finish_creating
            self.sendCreateObject(obj_uuid, pos, rot, scale, obj_idx)

        # send the asset data and wait for ack from the uploader
        assetID = self.manager.uploader.uploadAsset(AssetType.OgreMesh, data, finishupload)

    def processClone(self, obj_name, obj_uuid_str, mesh_name, mesh_uuid_str, pos, rot,
                     scale, materials):
        # create asset
        obj_uuid = UUID(obj_uuid_str)
        self._next_create = (self._next_create + 1) % (256*256)
        obj_idx = self._next_create

        tok = UUID(str(uuid.uuid4()))
        def finish_creating(real_uuid):
            del self._creating_cb[obj_idx]
            args = {"RexMeshUUID": mesh_uuid_str,
                    "materials": materials,
                    "RexIsVisible": True}
            self.out_queue.put(["meshcreated", obj_uuid_str, mesh_uuid_str,
                                str(real_uuid), mesh_uuid_str])
            self.rexdata.sendRexPrimData(real_uuid, args)
        self._creating_cb[obj_idx] = finish_creating
        self.sendCreateObject(obj_uuid, pos, rot, scale, obj_idx)

    def onObjectPermissions(self, packet):
        self.logger.debug("PERMISSIONS!!!")

    def onObjectProperties(self, packet):
        client = self.manager.client
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
            obj = client.region.objects.get_object_from_store(FullID=obj_uuid)
            if obj:
                obj.props = pars
            self.out_queue.put(["ObjectProperties", obj_uuid, pars])

    def processDelete(self, obj_id, destination = 6):
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
                                 Destination = destination,
                                 DestinationID = UUID(),
                                 TransactionID = tr_id,
                                 PacketCount = 1,
                                 PacketNumber = 0),
                        Block('ObjectData',
                                ObjectLocalID = obj.LocalID))
        # send
        self.client.region.enqueue_message(packet)

    def processDeRezObject(self, obj_id):
        self.processDelete(obj_id, 4)


    def processScale(self, objId, scale):
        client = self.client
        cmd_type = 12
        obj = client.region.objects.get_object_from_store(FullID=objId)
        if obj:
            data = scale
            self._eatupdates[obj.LocalID] += 1
            client.region.objects.send_ObjectPositionUpdate(client, client.agent_id,
                                      client.session_id,
                                      obj.LocalID, data, cmd_type)

    def processUpdatePermissions(self, objId, mask, value):
        client = self.client
        obj = client.region.objects.get_object_from_store(FullID=objId)
        if obj:
            self.updatePermissions(obj, mask, value)

    def processPos(self, objId, pos, rot=None):
        client = self.client
        obj = client.region.objects.get_object_from_store(FullID=objId)
        if not obj:
            obj = client.region.objects.get_avatar_from_store(FullID=UUID(objId))
            if obj:
                self.manager.misc.sendLocalTeleport(obj, pos)
                return
        if obj:
            pos = pos
            rot = rot
            self.sendPositionUpdate(obj, pos, rot)

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
        client = self.client
        obj.update_object_permissions(client, 0x08, val, mask)

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

