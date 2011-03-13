"""
 GameModule: Functionality related to starting up or running in game engine
 mode.
"""
from .base import SyncModule

import bpy

class GameModule(SyncModule):
    def has_game_uuid(self, obj):
        """
        Returns true if the object has the uuid game property.
        """
        for prop in obj.game.properties:
            if prop.name == 'uuid':
                return True
    def prepare_object(self, obj):
        """
        Prepare the given object for running inside the
        game engine.
        """
        if obj.opensim.uuid:
            if not self.has_game_uuid(obj):
                obj.select = True
                bpy.ops.object.game_property_new()
                # need to change type and then get the property otherwise
                # it will stay in the wrong class
                obj.game.properties[-1].type = 'STRING'
                prop = obj.game.properties[-1]
                prop.name = 'uuid'
                prop.value = obj.opensim.uuid
            else:
                print(obj.game.properties[-1])
    def start_game(self, context):
        """
        Start blender game engine, previously setting up game
        properties for opensim.
        """
        selected = list(context.selected_objects)
        for obj in selected:
            obj.select = False
        for obj in bpy.data.objects:
            self.prepare_object(obj)
        for obj in selected:
            obj.select = True
        bpy.ops.view3d.game_start()
