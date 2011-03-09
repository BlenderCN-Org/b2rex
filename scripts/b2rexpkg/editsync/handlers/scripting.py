"""
 OnlineModule: Manages agent online and offline messages from the simulator.
"""
import uuid

from .base import SyncModule
from b2rexpkg.tools.llsd_logic import generate_llsd, get_llsd_info

import bpy

LLSDText = 10

class ScriptingModule(SyncModule):
    def register(self, parent):
        """
        Register this module with the editor
        """
        parent.Asset.registerAssetType(LLSDText, self.create_llsd_script)
        return
        parent.registerCommand('OfflineNotification',
                             self.processOfflineNotification)
        parent.registerCommand('OnlineNotification',
                             self.processOnlineNotification)
    def unregister(self, parent):
        """
        Unregister this module from the editor
        """
        return
        parent.unregisterCommand('OfflineNotification')
        parent.unregisterCommand('OnlineNotification')

    def upload(self, name):
        editor = self._parent
        text_obj = bpy.data.texts[name]
        self.upload_text(text_obj)

    def find_text(self, text_uuid):
        editor = self._parent
        return editor.find_with_uuid(text_uuid, bpy.data.texts, 'texts')

    def create_llsd_script(self, assetID, assetType, data):
        print("AssetArrived")
        editor = self._parent
        text = data.decode('ascii')
        name = 'text'

        for item in editor.Inventory:
            if item['AssetID'] == assetID:
                name = item['Name']

        text_obj = bpy.data.texts.new(name)
        text_obj.write(text)
        text_obj.opensim.uuid = assetID
        

    def upload_text(self, text_obj):
        editor = self._parent
        text_data = ""
        # gather text data
        for line in text_obj.lines:
            text_data += line.body + "\n"
        # initialize object sim state
        name = text_obj.name
        desc = "test script"
        item_id = ""

        # asset uploaded callback
        def upload_finished(old_uuid, new_uuid, tr_uuid):
            text_obj.opensim.uuid = new_uuid
            text_obj.opensim.state = 'OK'
            self.simrt.CreateInventoryItem(tr_uuid,
                                           LLSDText,
                                           LLSDText,
                                           name,
                                           desc)
        def update_finished(old_uuid, new_uuid, tr_uuid):
            text_obj.opensim.uuid = new_uuid
            text_obj.opensim.state = 'OK'
            item = editor.Inventory[item_id]
            # XXX this should happen automatically?
            item['AssetID'] = new_uuid
            self.simrt.UpdateInventoryItem(item_id,
                                           tr_uuid,
                                           LLSDText,
                                           LLSDText,
                                           name,
                                           desc)

        if text_obj.opensim.uuid:
            for item in editor.Inventory:
                if item['AssetID'] == text_obj.opensim.uuid:
                    item_id = item['ItemID']

            cb = update_finished
        else:
            text_obj.opensim.uuid = str(uuid.uuid4())
            cb = upload_finished
        text_obj.opensim.state = 'UPLOADING'
        # start uploading
        editor.Asset.upload(text_obj.opensim.uuid, LLSDText,
                            text_data.encode('ascii'),
                            cb)

    def _add_state(self, context):
        editor = self._parent
        objs = editor.getSelected()
        for obj in objs:
            props = obj.opensim.fsm
            props.states.add()
            state = props.states[-1]
            if props.selected_state:
                state.name = props.selected_state
            else:
                state.name = 'default'
            props.selected_state = state.name

    def _add_sensor(self, context):
        fsm, state = self._get_fsm_state()
        sensor = state.sensors.add()
        sensor.name = sensor.type

    def _up_actuator(self, context):
        fsm, sensor = self._get_fsm_sensor()
        sel = fsm.selected_actuator
        sensor.actuators.move(sel, sel-1)
        fsm.selected_actuator -= 1

    def _get_fsm_state(self):
        editor = self._parent
        objs = editor.getSelected()
        obj = objs[0]
        fsm = obj.opensim.fsm
        state = fsm.states[fsm.selected_state]
        return fsm, state

    def _get_fsm_sensor(self):
        fsm, state = self._get_fsm_state()
        sensor = state.sensors[fsm.selected_sensor]
        return fsm, sensor

    def _down_actuator(self, context):
        fsm, sensor = self._get_fsm_sensor()
        sel = fsm.selected_actuator
        sensor.actuators.move(sel, sel+1)
        fsm.selected_actuator += 1

    def _add_actuator(self, context):
        fsm, sensor = self._get_fsm_sensor()
        actuator = sensor.actuators.add()
        actuator.name = actuator.type

    def _delete_state(self, context):
        print("delete_state!")

    def _delete_actuator(self, context):
        fsm, sensor = self._get_fsm_sensor()
        sensor.remove(fsm.selected_actuator)
        fsm.selected_actuator = 0

    def _generate_llsd(self, context):
        editor = self._parent
        obj = editor.getSelected()[0]
        fsm = obj.opensim.fsm
        print(generate_llsd(fsm, obj))

    def set_sensor_type(self, context, type):
        editor = self._parent
        obj = editor.getSelected()[0]
        fsm, sensor = self._get_fsm_sensor()
        sensor.type = type
        sensor.name = type

    def set_actuator_type(self, context, type):
        editor = self._parent
        obj = editor.getSelected()[0]
        fsm, sensor = self._get_fsm_sensor()
        actuator = sensor.actuators[fsm.selected_actuator]
        actuator.type = type
        actuator.name = type
        llsd_info = get_llsd_info()["Actuators"]
        act_info = llsd_info[actuator.type]
        pre = str(fsm.selected_actuator)
        for prop in act_info:
            name = list(prop.keys())[0]
            data = list(prop.values())[0]
            tmp_name = "tmp_" + pre + name
            if not tmp_name in obj:
                if 'default' in data:
                    val = data['default']
                elif data['type'] == 'integer':
                    val = 0
                elif data['type'] == 'string':
                    val = "bla"
                elif data['type'] == 'key':
                    val = "bla"
                elif data['type'] == 'float':
                    val = 0.0
                obj[tmp_name] = val

    def draw_object(self, box, editor, obj):
        if not self.expand(box):
            return False
        mainbox = box.box()
        box = mainbox.row()
        main_row = mainbox.row()
        #box = box.box()
        box.label("State")
        props = obj.opensim.fsm
        # draw state list
        row = box.row()
        if not props.states or (props.selected_state and not props.selected_state in props.states):
            row.operator('b2rex.fsm', text='', icon='ZOOMIN').action = '_add_state'
        elif props.states:
            row.operator('b2rex.fsm', text='', icon='ZOOMOUT').action = '_delete_state'
        row.prop_search(props, 'selected_state', props, 'states')

        # draw sensor list
        if not props.selected_state or not props.selected_state in props.states:
            return
        box = main_row.column()
        box.label("Sensors")
        currstate = props.states[props.selected_state]
        box.template_list(currstate,
                          'sensors',
                          props,
                          'selected_sensor')
        row = box.row()
        row.operator('b2rex.fsm', text='', icon='ZOOMIN').action = '_add_sensor'
        if currstate.sensors:
            row.operator('b2rex.fsm', text='', icon='ZOOMOUT').action = '_delete_sensor'
        if props.selected_sensor >= len(currstate.sensors):
            return
        #box = box.box()
        currsensor = currstate.sensors[props.selected_sensor]
        row = box.row()
        row.alignment = 'LEFT'
        row.label(text='Type:')
        row.operator_menu_enum('b2rex.fsm_sensortype',
                               'type',
                               text=currsensor.type, icon='BLENDER')

        box = main_row.column()
        box.label("Actions")
        # draw current sensor controls

        if currsensor.actuators:
            box.template_list(currsensor,
                          'actuators',
                          props,
                          'selected_actuator')

        row = box.row()
        row.operator('b2rex.fsm', text='', icon='ZOOMIN').action = '_add_actuator'
        if currsensor.actuators:
            row.operator('b2rex.fsm', text='', icon='ZOOMOUT').action = '_delete_actuator'
            if props.selected_actuator > 0:
                row.operator('b2rex.fsm', text='', icon='TRIA_UP').action = '_up_actuator'
            if props.selected_actuator < len(currsensor.actuators) -1:
                row.operator('b2rex.fsm', text='', icon='TRIA_DOWN').action = '_down_actuator'

        if props.selected_actuator >= len(currsensor.actuators):
            return

        curractuator = currsensor.actuators[props.selected_actuator]
        #box.prop(curractuator, 'name')
        row = box.row()
        row.alignment = 'LEFT'
        row.label(text='Type:')
        row.operator_menu_enum('b2rex.fsm_actuatortype',
                               'type',
                               text=curractuator.type, icon='BLENDER')

        llsd_info = get_llsd_info()["Actuators"]
        act_info = llsd_info[curractuator.type]
        pre = str(props.selected_actuator)
        for prop in act_info:
            name = list(prop.keys())[0]
            data = list(prop.values())[0]
            tmp_name = "tmp_" + pre + name
            if tmp_name in obj:
                box.prop(obj, '["'+tmp_name+'"]', text=name)
        # draw actuators one by one
        #for actuator in currstate.sensors[props.selected_sensor].actuators:
            #    box.label(text=str(actuator))
        mainbox.operator('b2rex.fsm', text='Generate', icon='SCRIPT').action = '_generate_llsd'


