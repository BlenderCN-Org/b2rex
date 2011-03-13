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

    def ensure_game_uuid(self, context, obj):
        """
        Ensure the uuid is set as a game object property.
        """
        if obj.opensim.uuid:
            if not self.has_game_uuid(obj):
                obj.select = True
                context.scene.objects.active = obj
                bpy.ops.object.game_property_new()
                # need to change type and then get the property otherwise
                # it will stay in the wrong class
                obj.game.properties[-1].type = 'STRING'
                prop = obj.game.properties[-1]
                prop.name = 'uuid'
                prop.value = obj.opensim.uuid
                obj.select = False

    def prepare_object(self, context, obj):
        """
        Prepare the given object for running inside the
        game engine.
        """
        self.ensure_game_uuid(context, obj)

    def start_game(self, context):
        """
        Start blender game engine, previously setting up game
        properties for opensim.
        """
        selected = list(context.selected_objects)
        for obj in selected:
            obj.select = False
        for obj in bpy.data.objects:
            self.prepare_object(context, obj)
        for obj in selected:
            obj.select = True
        bpy.ops.view3d.game_start()
