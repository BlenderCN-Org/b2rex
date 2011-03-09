"""
 OnlineModule: Manages agent online and offline messages from the simulator.
"""
import uuid

from .base import SyncModule
from b2rexpkg.tools.llsd_logic import generate_llsd

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
        editor = self._parent
        objs = editor.getSelected()
        for obj in objs:
            props = obj.opensim.fsm
            state = props.states[props.selected_state]
            state.sensors.add()
            sensor = state.sensors[-1]
            sensor.name = 'newsensor'

    def _add_actuator(self, context):
        editor = self._parent
        objs = editor.getSelected()
        for obj in objs:
            props = obj.opensim.fsm
            state = props.states[props.selected_state]
            sensor = state.sensors[props.selected_sensor]
            sensor.actuators.add()
            actuator = sensor.actuators[-1]
            actuator.name = 'newactuator'


    def _delete_state(self, context):
        print("delete_state!")


    def _generate_llsd(self, context):
        editor = self._parent
        obj = editor.getSelected()[0]
        fsm = obj.opensim.fsm
        print(generate_llsd(fsm))
        return
        for state in fsm.states:
            print(state.name)
            print("{")
            for sensor in state.sensors:
                pars = 'integer num_detected'
                print('  '+sensor.type+'('+pars+')')
                print("  {")
                for actuator in sensor.actuators:
                    print("    "+actuator.type+'()')
                print("  }")
            print("}")

    def draw_object(self, box, editor, obj):
        mainbox = box
        box = box.box()
        box.label("States")
        props = obj.opensim.fsm
        # draw state list
        row = box.row()
        row.prop_search(props, 'selected_state', props, 'states')
        if not props.states or (props.selected_state and not props.selected_state in props.states):
            row.operator('b2rex.fsm', text='', icon='ZOOMIN').action = '_add_state'
        if props.states:
            row.operator('b2rex.fsm', text='', icon='ZOOMOUT').action = '_delete_state'
        # draw sensor list
        if not props.selected_state or not props.selected_state in props.states:
            return
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
        box = box.box()
        # draw current sensor controls
        currsensor = currstate.sensors[props.selected_sensor]
        box.prop(currsensor, 'name')
        box.prop(currsensor, 'type')

        row = box.row()
        row.operator('b2rex.fsm', text='', icon='ZOOMIN').action = '_add_actuator'
        if currsensor.actuators:
            row.operator('b2rex.fsm', text='', icon='ZOOMOUT').action = '_delete_actuator'

            box.template_list(currsensor,
                          'actuators',
                          props,
                          'selected_actuator')

        if props.selected_actuator >= len(currsensor.actuators):
            return

        curractuator = currsensor.actuators[props.selected_actuator]
        box.prop(curractuator, 'name')
        box.prop(curractuator, 'type')
        # draw actuators one by one
        #for actuator in currstate.sensors[props.selected_sensor].actuators:
            #    box.label(text=str(actuator))
        mainbox.operator('b2rex.fsm', text='Generate').action = '_generate_llsd'


