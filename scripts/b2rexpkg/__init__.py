# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

bl_addon_info = {
    'name': 'b2rex',
    'author': 'Invi, Caedes',
    'version': (0, 7, 8),
    'blender': (2, 5, 6),
    'api': 33928,
    'location': 'Text window > Properties panel (ctrl+F) or '\
        'Console > Console menu',
    'warning': '',
    'description': 'Click an icon to display its name and copy it '\
        'to the clipboard',
    'wiki_url': 'http://wiki.blender.org/index.php/Extensions:2.5/'\
        'Py/Scripts/System/Display_All_Icons',
    'tracker_url': 'http://projects.blender.org/tracker/index.php?'\
        'func=detail&aid=22011&group_id=153&atid=469',
    'category': 'System'}

import sys
import traceback
from .siminfo import GridInfo
from .importer import Importer
from .tools.logger import logger

if sys.version_info[0] == 2:
    import Blender
    from .b24.hooks import start, write
    from .b24 import hacks
else:
    from bpy.props import PointerProperty
    from .b25.ops import Connect, Export, Import, Settings
    from .b25.panels.main import ConnectionPanel
    from .b25.properties import B2RexRegions, B2RexProps

ERROR = 0
OK = 1
IMMEDIATE = 2
import bpy

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
        logger.debug('importing..')
        text = self.import_region(self.region_uuid)
        self.addStatus("Scene imported " + self.region_uuid)
    def export(self):
        logger.debug("export clicked")
    def settings(self):
        logger.debug("settings clicked")
    def do_check(self):
        logger.debug("do_check regionuuid" + self.region_uuid)
        self.region_report = self.check_region(self.region_uuid)
    def addStatus(self, status, level=0):
        bpy.context.scene.b2rex_props.status = status

def register():
    bpy.types.Scene.b2rex_props = PointerProperty(type=B2RexProps, name="b2rex props")
    bpy.b2rex_session = B2Rex(bpy.context.scene)
#    register_keymaps()

def unregister():
    logger.debug("byez!-")
    del bpy.types.Scene.b2rex_props
    del bpy.b2rex_session
    #testthread.running = False
#    unregister_keymaps()


if __name__ == "__main__":
    register()
