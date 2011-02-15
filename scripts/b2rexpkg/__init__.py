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
    'category': 'B2Rex'}

import sys
import traceback
from .siminfo import GridInfo
from .importer import Importer
from .tools.logger import logger

ERROR = 0
OK = 1
IMMEDIATE = 2


if sys.version_info[0] == 2:
    import Blender
    from .b24 import hacks
else:
    from bpy.props import PointerProperty
    from .b25.ops import Connect, Export, Import, Settings, SetLogLevel, Redraw
    from .b25.ops import Upload, ExportUpload, Sync, Check, ProcessQueue
    from .b25.panels.main import ConnectionPanel
    from .b25.panels.menu import Menu
    from .b25.panels.object import ObjectPropertiesPanel
    from .b25.properties import B2RexRegions, B2RexProps
    from .b25.properties import B2RexObjectProps, B2RexMaterialProps
    from .b25.properties import B2RexMeshProps, B2RexTextureProps
    from .b25.properties import B2RexImageProps
    from .b25.app import B2Rex

import bpy

_oldheader_ = None

def register():
    global _oldheader_
    bpy.types.Scene.b2rex_props = PointerProperty(type=B2RexProps, name="b2rex props")
    bpy.types.Object.opensim = PointerProperty(type=B2RexObjectProps,
                                               name="b2rex object props")
    bpy.types.Mesh.opensim = PointerProperty(type=B2RexMeshProps,
                                               name="b2rex object props")
    bpy.types.Material.opensim = PointerProperty(type=B2RexMaterialProps,
                                               name="b2rex object props")
    bpy.types.Texture.opensim = PointerProperty(type=B2RexTextureProps,
                                               name="b2rex object props")
    bpy.types.Image.opensim = PointerProperty(type=B2RexImageProps,
                                               name="b2rex object props")
    bpy.b2rex_session = B2Rex(bpy.context.scene)
    if hasattr(bpy.types, 'INFO_HT_header'):
        _oldheader_ = bpy.types.INFO_HT_header
        bpy.types.unregister( bpy.types.INFO_HT_header )
    if hasattr(bpy.types, 'INFO_HT_myheader'):
       bpy.types.unregister( bpy.types.INFO_HT_myheader )


#    register_keymaps()

def unregister():
    logger.debug("byez!-")
    del bpy.types.Scene.b2rex_props
    del bpy.b2rex_session
    # XXX are we sure we want to do this?
    del bpy.types.Object.opensim
    del bpy.types.Mesh.opensim
    del bpy.types.Material.opensim
    del bpy.types.Texture.opensim
    del bpy.types.Image.opensim
    bpy.types.register( _oldheader_ )
    #testthread.running = False
#    unregister_keymaps()


if __name__ == "__main__":
    register()
