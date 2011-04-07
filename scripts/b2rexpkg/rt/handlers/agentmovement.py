from .base import Handler

class AgentMovementHandler(Handler):
    def onRegionConnect(self, region):
        res = region.message_handler.register("AgentMovementComplete")
        res.subscribe(self.onAgentMovementComplete)

    def processWalk(self, walk = False):
        print("processWalk")
        agent = self.manager.client
        agent.walk(walk)

    def processWalkBackwards(self, walk = False):
        print("processWalkBackwards")
        agent = self.manager.client
        agent.walk_backwards(walk)

    def processBodyRotation(self, body_rotation):
        print("processBodyRotation")
        agent = self.manager.client
	print(body_rotation)
	print(type(body_rotation))
        agent.body_rotation(body_rotation)

    def processStop(self):
        print("processStop")
        agent = self.manager.client
        agent.stop()

    def processTurnLeft(self, turning = True):
        print("processTurnLeft")
        agent = self.manager.client
        agent.turn_left(turning)

    def processTurnRight(self, turning = True):
        print("processTurnRight")
        agent = self.manager.client
        agent.turn_right(turning)


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


