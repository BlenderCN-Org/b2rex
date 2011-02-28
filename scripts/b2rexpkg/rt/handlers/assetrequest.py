from array import array
import base64
import time
from eventlet import api

from pyogp.lib.base.datatypes import UUID
from pyogp.lib.base.message.message import Message, Block

from .base import Handler

class AssetRequest(Handler):
    def __init__(self, parent):
        Handler.__init__(self, parent)
        self._request_queue = []
        self._requesting = {}
        self.timeout = 30

    def onAgentConnected(self, agent):
        self._asset_manager = agent.asset_manager

    #def onRegionConnect(self, region):
        #    api.spawn(self._start_timer)

    def _start_timer(self):
        ev =  self.manager.client.region.message_handler.register('TransferPacket').event
        while True:
            api.sleep(5)
            currtime = time.time()
            for key, reqdata in list(self._requesting.items()):
                reqtime, reqtype = reqdata
                if reqtime + self.timeout < currtime:
                    print(key, "passed its time rescheduling ASSET TIMER")
                    self._requesting.pop(key)
                    self._request_queue.append((key, reqtype))
                    self.processAssetRequest(*self._request_queue.pop(0))

            print("ASSET TIMER CHECKING!!!", len(ev.subscribers))

    def processAssetRequest(self, assetID, assetType):
        print("Request Asset", assetID)
        def finish(assetID, is_ok):
            print("Asset Arrived", is_ok)
            if is_ok:
                data = self._asset_manager.get_asset(assetID).data
                b64data = base64.urlsafe_b64encode(data).decode('ascii')

                self.out_queue.put(["AssetArrived", str(assetID), b64data])

            if str(assetID) in self._requesting:
                reqtime, reqtype = self._requesting.pop(str(assetID))
                if not is_ok:
                    self._request_queue.append((str(assetID), reqtype))
            if self._request_queue:
                self.processAssetRequest(*self._request_queue.pop(0))
            ev = self.manager.client.region.message_handler.register('TransferPacket').event
            print(len(ev.subscribers), len(self._request_queue))

        if len(self._requesting) > 15:
            self._request_queue.append((assetID, assetType))
            return
        self._requesting[assetID] = (time.time(), assetType)
        self._asset_manager.request_asset(UUID(assetID), assetType, True, finish)


