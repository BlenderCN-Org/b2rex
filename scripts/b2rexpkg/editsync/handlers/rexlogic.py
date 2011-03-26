"""
 RexLogicModule: Support for rex logic system
"""
import math
import os
import uuid

from .base import SyncModule

import b2rexpkg.tools.rexio.export
from b2rexpkg.tools import rexio
from b2rexpkg.b25.material import RexMaterialIO

#from .props.rexlogic import RexLogicProps

import bpy

class RexComponent(object):
    def __init__(self, obj):
        self._obj = obj
    def _get_dummy(self):
        return ""
    def _get_attribute_names(self):
        return self._attribute_names
    attribute_names = property(_get_attribute_names)

class NameComponent(RexComponent):
    type = 'EC_Name'
    _attribute_names = ['name', 'description']
    def _get_name(self):
        return self._obj.name
    name = property(_get_name)
    def _get_description(self):
        return 'blender object'
    description = property(_get_description)

class MeshComponent(RexComponent):
    type = 'EC_Mesh'
    _attribute_names = ['Transform', 'Mesh ref', 'Skeleton ref',
                        'Mesh materials', 'Draw distance', 'Cast shadows']
    def _get_dummy(self):
        return ""
    def _get_transform(self):
        return "0,0,0,90,0,180,1,1,1"
    def _get_mesh_ref(self):
        return "file://"+self._obj.data.name+".mesh"
    def _get_mesh_materials(self):
        return "file://"+self._obj.data.name+".material"
    transform = property(_get_transform) # 0,0,0,90,0,180,1,1,1
    mesh_ref = property(_get_mesh_ref) # file://crab_stand_swim.mesh
    skeleton_ref = property(_get_dummy) # file://crab_stand_swim.skeleton
    mesh_materials = property(_get_mesh_materials) # file://crab.material
    draw_distance = property(_get_dummy) # 0
    cast_shadows = property(_get_dummy) # false

class PlaceableComponent(RexComponent):
    type = 'EC_Placeable'
    def _get_dummy(self):
        return ""
    _attribute_names = ['Transform', 'Show bounding box']
    def _get_transform(self):
        editor = bpy.b2rex_session
        pos, rot, scale = editor.getObjectProperties(self._obj)
        r = 180.0/math.pi
        # XXX convert angle to degrees?
        if self._obj.parent:
            pos = editor.unapply_position(self._obj, pos,0,0,0)
        else:
            pos = editor.unapply_position(self._obj, pos)
            rot = list(map(lambda s: s*r, rot))
            # rot = editor.unapply_rotation(rot) - asks for euler?
        scale = editor.unapply_scale(self._obj, scale)
        tr = map(lambda s: str(s), pos + rot + scale)
        return ",".join(tr)
    transform = property(_get_transform) # -68,-4.32,80,0,0,0,2,2,2
    show_bounding_box = property(_get_dummy) # false

class ScriptComponent(RexComponent):
    type = 'EC_Script'
    def _get_dummy(self):
        return ""
    _attribute_names = ['js', 'Run on load', 'Script ref']
    js = property(_get_dummy) # js
    run_on_load = property(_get_dummy) # true
    script_ref = property(_get_dummy) # C:\Script\js\testanimation.js


class RexLogicModule(SyncModule):
    def register(self, parent):
        """
        Register this module with the editor
        """
        setattr(bpy.types.B2RexObjectProps, 'components',
                property(self.get_entity_components))

    def export(self, context):
        """
        Export and pack the scene to rex logic format.
        """
        editor = self._parent
        editor.exportSettings = context.scene.b2rex_props
        dest = editor.ensureDestinationDir(delete=True)

        # export materials
        for ob in bpy.context.scene.objects:
            self.export_materials(ob, dest)

        # export ogre data
        editor.onExport(context, delete=False)

        # export rex data
        dest_tundra = os.path.join(dest, editor.exportSettings.pack + '.txml')
        e = rexio.export.RexSceneExporter()
        e.export(context.scene, dest_tundra)

    def export_materials(self, obj, dest):
        editor = self._parent
        mesh = obj.data
        faces = editor._getFaceRepresentatives(mesh)
        f = open(os.path.join(dest, mesh.name + '.material'), 'w')
        for face in faces:
            bmat = editor._getFaceMaterial(mesh, face)
            if not bmat.opensim.uuid:
                bmat.opensim.uuid = str(uuid.uuid4())
                bmat.name = bmat.opensim.uuid
            matio = RexMaterialIO(editor, mesh, face, bmat)
            matio.write(f)
        f.write('\n\n')
        f.close()

    def unregister(self, parent):
        """
        Unregister this module from the editor
        """
        if hasattr(bpy.types.B2RexObjectProps, 'components'):
            delattr(bpy.types.B2RexObjectProps, 'components')

    def find_components(self, obj):
        return [NameComponent(obj), PlaceableComponent(obj), MeshComponent(obj)]

    def get_entity_components(self, opensim_data):
        if not opensim_data.uuid:
            return []
        obj = self._parent.findWithUUID(opensim_data.uuid)
        return self.find_components(obj)
    #parent.registerCommand('CoarseLocationUpdate', self.processCoarseLocationUpdate)


