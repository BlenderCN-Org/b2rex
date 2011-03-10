from .base import Handler

from pyogp.lib.base.datatypes import UUID
from pyogp.lib.base.message.message import Message, Block


class ScriptingHandler(Handler):
    def onRegionConnect(self, region):
        res = region.message_handler.register("ScriptRunningReply")
        res.subscribe(self.onScriptRunningReply)
        res = region.message_handler.register("ScriptQuestion")
        res.subscribe(self.onScriptQuestion)
        res = region.message_handler.register("ScriptSensorReply")
        res.subscribe(self.onScriptSensorReply)
        res = region.message_handler.register("LoadURL")
        res.subscribe(self.onScriptDialog)

    def onScriptSensorReply(self, packet):
        pass

    def onScriptQuestion(self, packet):
        pass

    def onScriptDialog(self, packet):
        pass

    def onLoadURL(self, packet):
        pass

    def processGetScriptRunning(self, obj_id, item_id):
        print("GetScriptRunning", obj_id, item_id)
        agent = self.manager.client
        packet = Message('GetScriptRunning',
                        Block('Script',
                                ObjectID = UUID(str(obj_id)),
                                ItemID = UUID(str(item_id))))
        agent.region.enqueue_message(packet)

    def processSetScriptRunning(self, obj_id, item_id, running):
        agent = self.manager.client
        print("SetScriptRunning", obj_id, item_id, running)
        packet = Message('SetScriptRunning',
                        Block('AgentData',
                                AgentID = agent.agent_id,
                                SessionID = agent.session_id),
                        Block('Script',
                                ObjectID = UUID(str(obj_id)),
                                ItemID = UUID(str(item_id)),
                                Running = running))
        agent.region.enqueue_message(packet)

    def processScriptReset(self, obj_id, item_id):
        agent = self.manager.client
        packet = Message('ScriptReset',
                        Block('AgentData',
                                AgentID = agent.agent_id,
                                SessionID = agent.session_id),
                        Block('Script',
                                ObjectID = UUID(str(obj_id)),
                                ItemID = UUID(str(item_id))))
        agent.region.enqueue_message(packet)

    def processScriptSensorRequest(self, obj_id, item_id, *args):
        agent = self.manager.client
        # XXX missing parameter setup
        packet = Message('ScriptSensorRequest',
                        Block('Requester',
                                SourceID = UUID(source_id),
                                RequestID = UUID(request_id),
                                SearchID = UUID(search_id),
                                SearchPos = Vector3(search_pos),
                                SearchDir = Quaternion(search_dir),
                                SearchName = search_name,
                                Type = _type,
                                Range = _range,
                                Arc = arc,
                                RegionHandle = region_handle,
                                SearchRegions = search_regions))
        agent.region.enqueue_message(packet)


    def onScriptRunningReply(self, packet):
        print("ScriptRunningReply", packet)
        for data in packet['Script']:
            objID = str(data['ObjectID'])
            itemID = str(data['ItemID'])
            running = data['Running']
            try:
                mono = data['Mono']
            except:
                mono = False
            self.out_queue.put(['ScriptRunningReply',
                                      objID, itemID,
                                      running, mono])

