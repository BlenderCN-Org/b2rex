from .base import Handler

class AgentMovementHandler(Handler):
    def onRegionConnect(self, region):
        res = region.message_handler.register("AgentMovementComplete")
        res.subscribe(self.onAgentMovementComplete)
    def onAgentMovementComplete(self, packet):
        # some region info
        AgentData = packet['AgentData'][0]
        Data = packet['Data'][0]
        pos = Data['Position']
        lookat = Data['LookAt']
        agent_id = str(AgentData['AgentID'])
        lookat = [lookat.X, lookat.Y, lookat.Z]
        pos = [pos.X, pos.Y, pos.Z]
        self.out_queue.put(["AgentMovementComplete", agent_id, pos, lookat])


