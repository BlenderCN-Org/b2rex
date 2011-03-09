import os
import bpy

from bpy.props import StringProperty, PointerProperty, IntProperty
from bpy.props import BoolProperty, FloatProperty, CollectionProperty
from bpy.props import FloatVectorProperty, EnumProperty

from ..tools.llsd_logic import parse_llsd_data

# Helpers
sensors, actuators = parse_llsd_data()

# Operators
class FsmAction(bpy.types.Operator):
    bl_idname = "b2rex.fsm"
    bl_label = "connect"
    action = StringProperty(name="action",default='add_state')
    def execute(self, context):
        getattr(bpy.b2rex_session.Scripting, self.action)(context)
        return {'FINISHED'}

class FsmActuatorTypeAction(bpy.types.Operator):
    bl_idname = "b2rex.fsm_actuatortype"
    bl_label = "connect"
    type = EnumProperty(items=actuators, description='')
    def execute(self, context):
        bpy.b2rex_session.Scripting.set_actuator_type(context, self.type)
        return {'FINISHED'}

#
# Model
class B2RexActuator(bpy.types.IDPropertyGroup):
    type = EnumProperty(items=actuators, description='')

class B2RexSensor(bpy.types.IDPropertyGroup):
    actuators = CollectionProperty(type=B2RexActuator)
    type = EnumProperty(items=sensors, description='')

class B2RexState(bpy.types.IDPropertyGroup):
    name = StringProperty(default='default')
    sensors = CollectionProperty(type=B2RexSensor)

class B2RexFsm(bpy.types.IDPropertyGroup):
    selected_state = StringProperty()
    selected_sensor = IntProperty()
    selected_actuator = IntProperty()
    states = CollectionProperty(type=B2RexState)


