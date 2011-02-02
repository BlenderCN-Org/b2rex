import traceback

from ..siminfo import GridInfo
from ..importer import Importer
from ..tools.logger import logger

class B2Rex(Importer):
    def __init__(self, context):
        self.region_report = ''
        self.gridinfo = GridInfo()
        Importer.__init__(self, self.gridinfo)

    def onConnect(self, context):
        self.connect(props.server_url, props.username, props.password)
        while(len(props.regions) > 0):
            props.regions.remove(0)
        for key, region in self.regions.items():
            props.regions.add()
            regionss = props.regions[-1]
            regionss.name = region['name']
#            regionss.description = region['id']

    def onCheck(self, context):
        props = context.scene.b2rex_props
        self.region_uuid = list(self.regions.keys())[props.selected_region]
        self.do_check()

    def onExport(self, context):
        self.export()

    def onImport(self, context):
        self.region_uuid = list(self.regions.keys())[props.selected_region]
        self._import()

    def onSettings(self, context):
        self.settings()

    def connect(self, base_url, username="", password=""):
   #     self.sim.connect(base_url)
        self.addStatus("Connecting to " + base_url, IMMEDIATE)
        self.gridinfo.connect(base_url, username, password)
        self.region_uuid = ''
        self.regionLayout = None
        try:
            self.regions = self.gridinfo.getRegions()
            self.griddata = self.gridinfo.getGridInfo()
        except:
            self.addStatus("Error: couldnt connect to " + base_url, ERROR)
            traceback.print_exc()
            return
#        self.addRegionsPanel(regions, griddata)
        # create the regions panel
        self.addStatus("Connected to " + self.griddata['gridnick'])
        logger.debug("conecttt")

    def _import(self):
