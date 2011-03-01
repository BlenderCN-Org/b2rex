import base64

from .base import SyncModule

import bpy

class AssetModule(SyncModule):
    _requested_llassets = {}
    def register(self, parent):
        parent.registerCommand('AssetArrived', self.processAssetArrived)

    def unregister(self, parent):
        parent.unregisterCommand('AssetArrived')

    def processAssetArrived(self, assetId, b64data):
        data = base64.urlsafe_b64decode(b64data.encode('ascii'))
        cb, cb_pars, main = self._requested_llassets['lludp:'+assetId]
        def _cb(request, result):
            if 'lludp:'+assetId in self._requested_llassets:
                cb(result, *cb_pars)
            else:
                print("asset arrived but no callback! "+assetId)
        if main:
            self.workpool.addRequest(main,
                                 [[assetId, cb_pars, data]],
                                 _cb,
                                 self._parent.default_error_db)
        else:
            cb(data, *cb_pars)

    def downloadAsset(self, assetId, assetType, cb, pars, main=None):
        if "GetTexture" in self._parent.caps:
            asset_url = self._parent.caps["GetTexture"] + "?texture_id=" + assetId
            return self._parent.addDownload(asset_url, cb, pars, extra_main=main)
        else:

            if 'lludp:'+assetId in self._requested_llassets:
                return False
            self._requested_llassets['lludp:'+assetId] = (cb, pars, main)
            self.simrt.AssetRequest(assetId, assetType)
            return True


