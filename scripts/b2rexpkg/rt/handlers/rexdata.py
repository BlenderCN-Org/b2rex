import uuid
import struct

from pyogp.lib.base.datatypes import UUID
from pyogp.lib.base.message.message import Message, Block

from simtypes import AssetType

from .base import Handler

class RexDataHandler(Handler):
    def onAgentConnected(self, agent):
        self.manager.register_generic_handler('RexPrimData', self.onRexPrimData)

    def onRexPrimData(self, packet):
        rexdata = packet[1]["Parameter"]
        if len(rexdata) < 102:
            rexdata = rexdata + ('\0'*(102-len(rexdata)))
        obj_uuid = UUID(packet[0]["Parameter"])
        obj_uuid_str = str(obj_uuid)

        client = self.manager.client
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
        obj = client.region.objects.get_object_from_store(FullID = obj_uuid)
        if obj:
            obj.rexdata = pars
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
        self.out_queue.put(['RexPrimData', obj_uuid_str, pars])
        if not len(rexdata) > pos:
            #self.logger.debug("RexPrimData: no more data")
            return
        idx = pos
        while rexdata[idx] != '\0':
              idx += 1
        RexClassName = rexdata[pos:idx+1]
        #self.logger.debug(" REXCLASSNAME: " + str(RexClassName))


    def sendRexPrimData(self, obj_uuid, args):
        client = self.manager.client
        agent_id = client.agent_id
        session_id = client.session_id
        t_id = uuid.uuid4()
        invoice_id = UUID()
        data = b''
        materials = []
        if "materials" in args:
            materials = args["materials"]
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
        client.region.enqueue_message(packet)


