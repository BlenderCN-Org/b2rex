from .base import SyncModule

import bpy

class AgentsModule(SyncModule):
    _agents = {}
    def register(self, parent):
        parent.registerCommand('AgentMovementComplete',
                             self.processAgentMovementComplete)

    def unregister(self, parent):
        parent.unregisterCommand('AgentMovementComplete')

    def processAgentMovementComplete(self, agentID, pos, lookat):
        agent = self.getAgent(agentID)
        agent.rotation_euler = lookat
        self._parent.apply_position(agent, pos)

    def __getitem__(self, agentID):
        return self.getAgent(agentID)

    def __setitem__(self, agentID, value):
        self._agents[agentID] = value

    def __iter__(self):
        return iter(self._agents)

    def getAgent(self, agentID):
        editor = self._parent
        agent = editor.findWithUUID(agentID)
        if not agent:
            camera = bpy.data.cameras.new(agentID)
            agent = bpy.data.objects.new(agentID, camera)
            editor.set_uuid(agent, agentID)
            self._agents[agentID] = agentID

            scene = editor.get_current_scene()
            if agentID in editor.positions:
                editor.apply_position(agent, editor.positions[agentID], raw=True)
            scene.objects.link(agent)
            try:
                agent.show_name = True
                agent.show_x_ray = True
            except:
                pass # blender2.5 only
            if not agentID == self._parent.agent_id:
                editor.set_immutable(agent)
        return agent


