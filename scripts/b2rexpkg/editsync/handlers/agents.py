"""
 AgentsModule. Will appear under the editor as editor.Agents, and
 keeps track of agents in our connection.

 The module can be used as a dictionary per agentID.
"""

from .base import SyncModule

import bpy

class AgentsModule(SyncModule):
    _agents = {}
    def register(self, parent):
        """
        Register this module with the editor
        """
        parent.registerCommand('AgentMovementComplete',
                             self.processAgentMovementComplete)

    def unregister(self, parent):
        """
        Unregister this module from the editor
        """
        parent.unregisterCommand('AgentMovementComplete')

    def processAgentMovementComplete(self, agentID, pos, lookat):
        """
        An AgentMovementComplete message arrived from the agent.
        """
        agent = self.getAgent(agentID)
        agent.rotation_euler = lookat
        self._parent.apply_position(agent, pos)

    def __getitem__(self, agentID):
        """
        Get the agent with the specified uuid, will be created
        if it doesnt exist.
        """
        return self.getAgent(agentID)

    def __setitem__(self, agentID, value):
        """
        Set an agent as available.
        """
        self._agents[agentID] = value

    def __iter__(self):
        """
        Get an iterator over all available agent uuids.
        """
        return iter(self._agents)

    def getAgent(self, agentID):
        """
        Get the agent with the specified uuid, will be created
        if it doesnt exist.
        """
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


