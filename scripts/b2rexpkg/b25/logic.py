import os
import bpy

from bpy.props import StringProperty, PointerProperty, IntProperty
from bpy.props import BoolProperty, FloatProperty, CollectionProperty
from bpy.props import FloatVectorProperty, EnumProperty

from ..tools.llsd_logic import parse_llsd_data

from ..tools import rexio

# Helpers
sensors, actuators = parse_llsd_data()
components = ()
# the following shouldnt be done on module import but on registering
# to blender or even later if possible...
for name in rexio.get_component_info():
    components += ((name, name.replace('EC_', ''), name),)

# Operators
class EntityAction(bpy.types.Operator):
    bl_idname = "b2rex.entity"
    bl_label = "entity action"
    action = StringProperty(name="action",default='add_component')
    def execute(self, context):
        getattr(bpy.b2rex_session.RexLogic, self.action)(context)
        return {'FINISHED'}

class ComponentTypeTypeAction(bpy.types.Operator):
    bl_idname = "b2rex.component_type"
    bl_label = "component type"
    type = EnumProperty(items=components, description='')
    def execute(self, context):
        bpy.b2rex_session.RexLogic.set_component_type(context, self.type)
        return {'FINISHED'}




class FsmAction(bpy.types.Operator):
    bl_idname = "b2rex.fsm"
    bl_label = "fsmaction"
    action = StringProperty(name="action",default='add_state')
    def execute(self, context):
        getattr(bpy.b2rex_session.Scripting, self.action)(context)
        return {'FINISHED'}

class FsmActuatorTypeAction(bpy.types.Operator):
    bl_idname = "b2rex.fsm_actuatortype"
    bl_label = "actuatortype"
    type = EnumProperty(items=actuators, description='')
    def execute(self, context):
        bpy.b2rex_session.Scripting.set_actuator_type(context, self.type)
        return {'FINISHED'}

class FsmSensorTypeAction(bpy.types.Operator):
    bl_idname = "b2rex.fsm_sensortype"
    bl_label = "sensortype"
    type = EnumProperty(items=sensors, description='')
    def execute(self, context):
        bpy.b2rex_session.Scripting.set_sensor_type(context, self.type)
        return {'FINISHED'}


#
# Model
class B2RexActuator(bpy.types.IDPropertyGroup):
    id = IntProperty()
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

class B2RexComponent(bpy.types.IDPropertyGroup):
    id = IntProperty()
    type = EnumProperty(items=components, description='')
