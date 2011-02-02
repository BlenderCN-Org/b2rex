"""
Class to get grid info from opensim
"""

import urllib
import xml.etree.ElementTree as ET
#XXX
from b2rexpkg.tools.restconnector import RestConnector
#from tools.restconnector import RestConnector


class GridInfo(RestConnector):
    def __init__(self):
        RestConnector.__init__(self)
        self._regions = {}

    def getGridInfo(self):
        """
        Get general grid information.
        """
        try:
            self.gridinfo = self.httpObjGet("/get_grid_info")
        except:
            self.gridinfo = {"gridname":"", "gridnick":"region", "mode":"standalone"}
        return self.gridinfo

    def getRegions(self):
        """
        Get grid regions.
        """
        xmldata = self.httpXmlGet("/admin/regions/")
        for uuid in xmldata.findall('uuid'):
            print(uuid.text)
            region = self.httpObjGet("/admin/regions/"+uuid.text, "region_")
            self._regions[region['id']] = region
            map_url = self._url + "/index.php?method=regionImage"+region['id'].replace('-','')
            self._regions[region['id']]['map'] = map_url
        return self._regions

    def getAsset(self, uuid):
        return self.httpObjGet("/admin/assets/"+uuid)

if __name__ == '__main__':
    base_url = "http://delirium:9000"
    gridinfo = GridInfo()
    gridinfo.connect(base_url, "invi invi", "invi")
#    print(gridinfo.httpXmlGet("//0a1b14b9-ca02-481d-bf77-9cbeca1ab050"))
#    print(gridinfo.getGridInfo()["gridnick"])
    regions = gridinfo.getRegions()
    for id in regions:
        region = regions[id]
        print(" *", region["name"], region["x"], region["y"], id)
#    asset = gridinfo.getAsset("68e2f587-4bbd-4ec7-8e1f-8b03601d218e")
#    print(asset["name"])
#    import tools.oimporter
    #tools.oimporter.parse(asset["data"])
    #   print struct.unpack_from(">H",asset["data"])

