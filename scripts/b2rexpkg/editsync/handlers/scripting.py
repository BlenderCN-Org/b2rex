"""
 OnlineModule: Manages agent online and offline messages from the simulator.
"""
import uuid

from .base import SyncModule

import bpy

LLSDText = 10

class ScriptingModule(SyncModule):
    def register(self, parent):
        """
        Register this module with the editor
        """
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
        if text_obj.opensim.uuid:
            self.upload_text(text_obj)
        else:
            self.update_text(text_obj)

    def update_text(self, text_obj):
        print("update text")

    def upload_text(self, text_obj):
        text_obj.opensim.uuid = str(uuid.uuid4())
        text_data = ""
        for line in text_obj.lines:
            text_data += line + "\n"
        encoded = base64.urlsafe_b64encode(text_data).decode('ascii')
        self.simrt.UploadAsset(text_obj.opensim.uuid, LLSDText, encoded)

