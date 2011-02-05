"""
Import sim data into Blender.
"""

import sys
import logging

logger = logging.getLogger("b2rex.importer")

from .siminfo import GridInfo
from .simconnection import SimConnection

import xml.parsers.expat

if sys.version_info[0] == 2:
    import httplib
    import urllib2
    import Blender
    from urllib2 import HTTPError, URLError
    from Blender import Mathutils as mathutils
    bversion = 2
    def bytes(text):
        return text
else:
    import http.client as httplib
    import urllib.request as urllib2
    from urllib.error import HTTPError, URLError
    import mathutils
    bversion = 3

import struct
import subprocess
import math
from .tools.oimporter.otypes import VES_POSITION, VES_NORMAL, VES_TEXTURE_COORDINATES
from .tools.oimporter.util import arr2float, parse_vector, get_vertex_legend
from .tools.oimporter.util import get_nor, get_uv, mat_findtextures, get_vcoords
from .tools.oimporter.omaterial import OgreMaterial
from .tools import oimporter

import socket
import traceback

import bpy

CONNECTION_ERRORS = (HTTPError, URLError, httplib.BadStatusLine,
                                     xml.parsers.expat.ExpatError)

default_timeout = 10

socket.setdefaulttimeout(default_timeout)

class Importer25(object):
    def import_submesh(self, new_mesh, vertex, vbuffer, indices, materialName):
        """
        Import submesh info and fill blender face and vertex information.
        """
        logger.debug("import_submesh")
        vertex_legend = get_vertex_legend(vertex)
        pos_offset = vertex_legend[VES_POSITION][1]
        no_offset = vertex_legend[VES_NORMAL][1]
        bmat = None
        image = None
        logger.debug("looking for image "+materialName)
        if materialName in self._imported_materials:
            bmat = self._imported_materials[materialName]
        if materialName in self._imported_ogre_materials:
            ogremat = self._imported_ogre_materials[materialName]
            if ogremat.btex and ogremat.btex.image:
                image = ogremat.btex.image
            if image:
                logger.debug("found image")
        if VES_TEXTURE_COORDINATES in vertex_legend:
            uvco_offset = vertex_legend[VES_TEXTURE_COORDINATES][1]
        vertmaps = {}
        indices_map = []
        # vertices
        for idx in range(max(indices)+1):
            coords = get_vcoords(vbuffer, idx, pos_offset)
            if coords:
                if not coords in vertmaps:
                    new_mesh.vertices.add(1)
                    new_mesh.vertices[len(new_mesh.vertices)-1].co = coords
                    vertmaps[coords] = len(new_mesh.vertices)-1
                indices_map.append(vertmaps[coords])
            else:
                new_mesh.vertices.add(1)
                new_mesh.vertices[len(new_mesh.vertices)-1].co = (0.0,0.0,0.0)
                indices_map.append(len(new_mesh.vertices)-1)
        if not len(new_mesh.vertices):
            logger.debug("mesh with no vertex!!")
        start_face = len(new_mesh.faces)
        # faces
        for idx in range(int(len(indices)/3)):
            idx = idx*3
            #new_mesh.vertexUV = False
            #face = [new_mesh.verts[indices_map[indices[idx]]],
            #                    new_mesh.verts[indices_map[indices[idx+1]]],
            #                    new_mesh.verts[indices_map[indices[idx+2]]]]
            face = [indices_map[indices[idx]],
                                indices_map[indices[idx+1]],
                                indices_map[indices[idx+2]]]
            new_mesh.faces.add(1)
            new_mesh.faces[len(new_mesh.faces)-1].vertices = face
            #new_mesh.faces.extend(face, ignoreDups=True)
            if len(new_mesh.faces) == 0:
                logger.debug("Degenerate face!")
                continue
            face = new_mesh.faces[len(new_mesh.faces)-1]

            continue
            try:
                no1 = get_nor(indices[idx], vbuffer, no_offset)
            except:
                no1 = [0.0,0.0,0.0]
            try:
                no2 = get_nor(indices[idx+1], vbuffer, no_offset)
            except:
                no2 = [0.0,0.0,0.0]
            try:
                no3 = get_nor(indices[idx+2], vbuffer, no_offset)
            except:
                no3 = [0.0,0.0,0.0]
            if VES_TEXTURE_COORDINATES in vertex_legend:
                uv1 = get_uv(indices[idx], vbuffer, uvco_offset)
                uv2 = get_uv(indices[idx+1], vbuffer, uvco_offset)
                uv3 = get_uv(indices[idx+2], vbuffer, uvco_offset)

                blender_tface = uvtex.data[len(new_mesh.faces)-1]
                blender_tface.uv1 = uv1
                blender_tface.uv2 = uv2
                blender_tface.uv3 = uv3
                if image:
                    blender_tface.image = image
        # UV
        if VES_TEXTURE_COORDINATES in vertex_legend:
            if image:
                logger.debug("setting image on material")
            if not len(new_mesh.uv_textures):
                uvtex = new_mesh.uv_textures.new()
                new_mesh.uv_textures.active = uvtex
            else:
                uvtex = new_mesh.uv_textures.active
            for idx in range(int(len(indices)/3)):
                fidx = idx*3
                uv1 = get_uv(indices[fidx], vbuffer, uvco_offset)
                uv2 = get_uv(indices[fidx+1], vbuffer, uvco_offset)
                uv3 = get_uv(indices[fidx+2], vbuffer, uvco_offset)

                blender_tface = uvtex.data[start_face+idx]
                blender_tface.uv1 = uv1
                blender_tface.uv2 = uv2
                blender_tface.uv3 = uv3
                if image:
                    blender_tface.image = image
                    blender_tface.use_image = True

        if not len(new_mesh.faces):
            logger.debug("mesh with no faces!!")
        sys.stderr.write("*")
        sys.stderr.flush()
        return new_mesh

    def apply_position(self, obj, pos, offset_x=128.0, offset_y=128.0,
                       offset_z=20.0):
        obj.location = (pos[0]-offset_x, pos[1]-offset_y, pos[2]-offset_z)

    def apply_scale(self, obj, scale):
        obj.scale = (scale[0], scale[1], scale[2])

    def unapply_position(self, pos, offset_x=128.0, offset_y=128.0,
                       offset_z=20.0):
        return [pos[0]+offset_x, pos[1]+offset_y, pos[2]+offset_z]


    def unapply_rotation(self, euler):
        #r = 180.0/math.pi
        r = 1.0
        euler = mathutils.Euler([-euler[0]*r, -euler[1]*r,
                                        (euler[2]*r)+math.pi])
        q = euler.to_quat()
        return [q.x, q.y, q.z, q.w]
        
    def apply_rotation(self, obj, rot):
        b_q = mathutils.Quaternion((rot[3], rot[0], rot[1],
                                           rot[2]))
        r = 1.0
        #r = math.pi/180.0;
        if b_q:
            b_q = mathutils.Quaternion((b_q.w, b_q.x, b_q.y, b_q.z))
            euler = b_q.to_euler()
            obj.rotation_euler = (-euler[0]*r, -euler[1]*r, (euler[2]-math.pi)*r)

    def getcreate_object(self, obj_uuid, name, mesh_data):
        logger.debug("create object")
        obj = self.find_with_uuid(obj_uuid, bpy.data.objects,
                             "objects")
        if not obj:
            obj = bpy.data.objects.new(name, mesh_data)
        return obj

    def create_texture(self, name, filename):
        bim = bpy.data.images.load(filename)
        btex = bpy.data.textures.new(name, 'IMAGE')
        btex.image = bim
        return btex

    def get_current_scene(self):
        return bpy.context.scene

class Importer24(object):
    def import_submesh(self, new_mesh, vertex, vbuffer, indices, materialName):
        """
        Import submesh info and fill blender face and vertex information.
        """
        vertex_legend = get_vertex_legend(vertex)
        pos_offset = vertex_legend[VES_POSITION][1]
        no_offset = vertex_legend[VES_NORMAL][1]
        bmat = None
        image = None
        if materialName in self._imported_materials:
            bmat = self._imported_materials[materialName]
        if materialName in self._imported_ogre_materials:
            ogremat = self._imported_ogre_materials[materialName]
            if ogremat.btex and ogremat.btex.image:
                image = ogremat.btex.image
        if VES_TEXTURE_COORDINATES in vertex_legend:
            uvco_offset = vertex_legend[VES_TEXTURE_COORDINATES][1]
        vertmaps = {}
        indices_map = []
        # vertices
        for idx in range(max(indices)+1):
            coords = get_vcoords(vbuffer, idx, pos_offset)
            if coords:
                if not coords in vertmaps:
                    new_mesh.verts.extend(*coords)
                    vertmaps[coords] = len(new_mesh.verts)-1
                indices_map.append(vertmaps[coords])
            else:
                new_mesh.verts.extend(0.0,0.0,0.0)
                indices_map.append(len(new_mesh.verts)-1)
        if not len(new_mesh.verts):
            logger.debug("mesh with no vertex!!")
        # faces
        for idx in range(len(indices)/3):
            idx = idx*3
            new_mesh.vertexUV = False
            face = [indices_map[indices[idx]],
                                indices_map[indices[idx+1]],
                                indices_map[indices[idx+2]]]
            new_mesh.faces.extend(face, ignoreDups=True)
            if len(new_mesh.faces) == 0:
                logger.debug("Degenerate face!")
                continue
            face = new_mesh.faces[len(new_mesh.faces)-1]
            if image:
                face.image = image
            try:
                no1 = get_nor(indices[idx], vbuffer, no_offset)
            except:
                no1 = [0.0,0.0,0.0]
            try:
                no2 = get_nor(indices[idx+1], vbuffer, no_offset)
            except:
                no2 = [0.0,0.0,0.0]
            try:
                no3 = get_nor(indices[idx+2], vbuffer, no_offset)
            except:
                no3 = [0.0,0.0,0.0]
            if VES_TEXTURE_COORDINATES in vertex_legend:
                uv1 = get_uv(indices[idx], vbuffer, uvco_offset)
                uv2 = get_uv(indices[idx+1], vbuffer, uvco_offset)
                uv3 = get_uv(indices[idx+2], vbuffer, uvco_offset)
                face.uv = (mathutils.Vector(uv1),
                           mathutils.Vector(uv2),
                           mathutils.Vector(uv3))
        if not len(new_mesh.faces):
            logger.debug("mesh with no faces!!")
        sys.stderr.write("*")
        sys.stderr.flush()
        return new_mesh

    def create_texture(self, name, filename):
        bim = Blender.Image.Load(filename)
        btex = Blender.Texture.New(name)
        btex.setType('Image')
        btex.image = bim
        return btex

    def apply_position(self, obj, pos, offset_x=128.0, offset_y=128.0,
                       offset_z=20.0):
        obj.setLocation(pos[0]-offset_x, pos[1]-offset_y, pos[2]-offset_z)

    def apply_scale(self, obj, scale):
        obj.setSize(scale[0], scale[1], scale[2])
    def unapply_position(self, pos, offset_x=128.0, offset_y=128.0,
                       offset_z=20.0):
        return [pos[0]+offset_x, pos[1]+offset_y, pos[2]+offset_z]


    def unapply_rotation(self, euler):
        r = 180.0/math.pi
        euler = mathutils.Euler([-euler[0]*r, -euler[1]*r,
                                        (euler[2]*r)+180.0])
        q = euler.toQuat()
        return [q.x, q.y, q.z, q.w]
        
    def apply_rotation(self, obj, rot):
        b_q = mathutils.Quaternion(rot[3], rot[0], rot[1],
                                           rot[2])
        #b_q1 = b_q.cross(Blender.Mathutils.Quaternion([0,-1,0]))
        #b_q2 = b_q1.cross(Blender.Mathutils.Quaternion([-1,0,0]))
        #b_q3 = b_q2.cross(Blender.Mathutils.Quaternion([0,0,-1]))
        r = math.pi/180.0;
        if b_q:
            b_q = mathutils.Quaternion(b_q.w, b_q.x, b_q.y, b_q.z)
            euler = b_q.toEuler()
            obj.setEuler(-euler[0]*r, -euler[1]*r, (euler[2]-180.0)*r)

    def getcreate_object(self, obj_uuid, name, mesh_data):
        obj = self.find_with_uuid(obj_uuid, bpy.data.objects,
                             "objects")
        if not obj:
            obj = Blender.Object.New("Mesh", name)
        obj.link(mesh_data)
        return obj

    def get_current_scene(self):
        scene = Blender.Scene.GetCurrent ()
        return scene


# Common
if bversion == 3:
    ImporterBase = Importer25
else:
    ImporterBase = Importer24

class Importer(ImporterBase):
    def __init__(self, gridinfo):
        self.gridinfo = gridinfo
        self.init_structures()

    def init_structures(self):
        """
        Initialize importer caches.

        Can be called to avoid caching of results.
        """
        self._imported_assets = {}
        self._imported_materials = {}
        self._imported_ogre_materials = {}

        self._objects = {}
        self._found = {"objects":0,"meshes":0,"materials":0,"textures":0}
        self._total_server = {"objects":0,"meshes":0,"materials":0,"textures":0}
        self._total = {"objects":{},"meshes":{},"materials":{},"textures":{}}

    def import_texture(self, texture):
        """
        Import the given texture from opensim.
        """
        logger.debug(("texture", texture))
        if texture in self._imported_assets:
            return self._imported_assets[texture]
        else:
            texture = texture.decode()
            tex = self.gridinfo.getAsset(texture)
            if "name" in tex:
                tex_name = tex["name"]
                try:
                    btex = bpy.data.textures[tex_name]
                    # XXX should update
                    return btex
                except:
                    f = open("/tmp/"+texture+".1.jpg", "wb")
                    f.write(tex["data"])
                    f.close()
                    split_name = tex_name.split("/")
                    if len(split_name) > 2:
                        tex_name = split_name[2]
                    dest = "/tmp/"+tex_name
                    if not dest[-3:] in ["png"]:
                        dest = dest + ".png"
                    try:
                        subprocess.call(["convert",
                                          "/tmp/"+texture+".1.jpg",
                                          dest])
                        btex = self.create_texture(tex_name, dest)
                        self._imported_assets[texture] = btex
                        return btex
                    except:
                        logger.error(("error opening:", dest))

    def create_blender_material(self, ogremat, mat):
        """
        Create a blender material from ogre format.
        """
        logger.debug("create_blender_material")
        textures = ogremat.textures
        bmat = None
        idx = 0
        mat_name = mat["name"].split("/")[0]
        try:
            bmat = bpy.data.materials[mat_name]
            if bversion == 3:
                bmat.name = "tobedeleted"
                bmat = bpy.data.materials.new(mat_name)
        except:
            bmat = bpy.data.materials.new(mat_name)
        # material base properties
        if ogremat.doambient:
            if bversion == 2:
                bmat.setAmb(ogremat.ambient)
            else:
                bmat.ambient = ogremat.ambient
        if ogremat.specular:
            if bversion == 2:
                bmat.setSpec(1.0)
                bmat.setSpecCol(ogremat.specular[:3])
                bmat.setHardness(int(ogremat.specular[3]*4.0))
            else:
                bmat.specular_intensity = 1.0
                ogremat.specular[:3]
                bmat.specular_color = ogremat.specular[:3]
                bmat.specular_hardness = int(ogremat.specular[3]*4.0)
        if ogremat.alpha < 1.0:
            bmat.alpha = ogremat.alpha
        # specular
        if bversion == 2:
           layerMappings = {'normalMap':'NOR',
                         'heightMap':'DISP',
                         'reflectionMap':'REF',
                         'opacityMap':'ALPHA',
                         'lightMap':'AMB',
                         'specularMap':'SPEC' }
        elif bversion == 3:
           layerMappings = {'normalMap':'use_map_normal',
                         'heightMap':'use_map_displacement',
                         'reflectionMap':'use_map_reflect',
                         'opacityMap':'use_map_alpha',
                         'lightMap':'use_map_ambient',
                         'specularMap':'use_map_specular' }

        for layerName, textureName in ogremat.layers.items():
            if layerName == 'shadowMap':
                if bversion == 2:
                    bmat.setMode(Blender.Material.Modes['SHADOWBUF'] & bmat.getMode())
                else:
                    bmat.use_cast_buffer_shadows = True
            if textureName:
                btex = self.import_texture(textureName)
                if btex:
                    if bversion == 2:
                        mapto = 'COL'
                    else:
                        mapto = 'use_map_color_diffuse'
                    if layerName in layerMappings:
                        mapto = layerMappings[layerName]
                    if mapto in ['use_map_color_diffuse', 'COL']:
                        ogremat.btex = btex
                    if bversion == 2:
                        if mapto:
                            mapto = Blender.Texture.MapTo[mapto]
                        bmat.setTexture(idx, btex, Blender.Texture.TexCo.ORCO, mapto) 
                    if bversion == 3:
                        new_slot = bmat.texture_slots.add()
                        setattr(new_slot, mapto, True)
                        new_slot.texture = btex
                        new_slot.texture_coords = 'ORCO'


                    idx += 1
        self._imported_materials[mat["name"]] = bmat
        return bmat

    def import_material(self, material, retries):
        """
        Import a material from opensim.
        """
        logger.debug(("material", material))
        btex = None
        bmat = None
        gridinfo = self.gridinfo
        try:
            if material in self._imported_assets:
                bmat = self._imported_assets[material]
            else:
            # XXX should check on library and refresh if its there
                mat = gridinfo.getAsset(material)
                ogremat = OgreMaterial(mat)
                self._imported_ogre_materials[mat["name"]] = ogremat
                bmat = self.create_blender_material(ogremat, mat)
                self._imported_assets[material] = bmat
        except CONNECTION_ERRORS:
            if retries > 0:
                return self.import_material(material, retries-1)
        return bmat

    def import_mesh(self, scenegroup):
        """
        Import mesh object from opensim scene.
        """
        logger.debug(("mesh", scenegroup["asset"]))
        if scenegroup["asset"] in self._imported_assets:
            return self._imported_assets[scenegroup["asset"]]
        asset = self.gridinfo.getAsset(scenegroup["asset"])
        if not asset["type"] == "43":
            logger.debug("("+asset["type"]+")")
            return
        return self.create_mesh_frombinary(scenegroup["asset"], asset["name"], asset["data"])

    def create_mesh_frombinary(self, meshId, meshName, data):
        mesh = oimporter.parse(data)
        if not mesh:
            logger.debug("error loading",meshId)
            return
        is_new = False
        try:
            new_mesh = bpy.data.meshes[meshName+meshId]
        except:
            new_mesh = bpy.data.meshes.new(meshName+meshId)
            is_new = True
            print("new mesh - bak!")
        if not is_new:
            if bversion == 3:
                new_mesh.name = "tobedeleted"
                new_mesh = bpy.data.meshes.new(meshName+meshId)
            else:
                new_mesh.faces.delete(1, range(len(new_mesh.faces)))
                new_mesh.verts.delete(1, range(len(new_mesh.verts)))
                new_mesh.materials = []
            print("old mesh!")

        self._imported_assets[meshId] = new_mesh
        for vertex, vbuffer, indices, materialName in mesh:
            self.import_submesh(new_mesh, vertex, vbuffer, indices, materialName)
        return new_mesh

    def import_object(self, scenegroup, new_mesh, materials=None, offset_x=128.0, offset_y=128.0,
                      offset_z=20.0):
        """
        Import object properties and create the blender mesh object.
        """
        logger.debug("import_object")
        pos = parse_vector(scenegroup["position"])
        scale = parse_vector(scenegroup["scale"])

        obj = self.getcreate_object(scenegroup["id"], scenegroup["asset"], new_mesh)
        self.apply_position(obj, pos)
        self.apply_rotation(obj, parse_vector(scenegroup["rotation"]))
        self.apply_scale(obj, scale)
        self.set_uuid(obj, str(scenegroup["id"]))

        # new_mesh properties have to be set here otherwise blender
        # can crash!!
        self.set_uuid(new_mesh, str(scenegroup["asset"]))
        if materials:
            if bversion == 3:
                for mat in materials:
                    new_mesh.materials.append(mat)
            else:
                new_mesh.materials = materials
        scene = self.get_current_scene()
        try:
            scene.objects.link(obj)
        except RuntimeError:
            pass # object already in scene
        new_mesh.update()
        #obj.makeDisplayList()
        #new_mesh.hasVertexColours(True) # for now we create them as blender does

        return obj

    def import_group(self, groupid, scenegroup, retries,
                     offset_x=128.0, offset_y=128.0, offset_z=20.0,
                     load_materials=True):
        """
        Import the given group into blender.
        """
        materials = []
        if load_materials:
           for material in scenegroup["materials"].keys():
                if not material == "00000000-0000-0000-0000-000000000000":
                    bmat = self.import_material(material, 10)
                    materials.append(bmat)

        try:
            new_mesh = None
            scenegroup["id"] = groupid
            if scenegroup["asset"] and not scenegroup["asset"] == "00000000-0000-0000-0000-000000000000":
                new_mesh = self.import_mesh(scenegroup)

            if new_mesh:
                sys.stderr.write(".")
                sys.stderr.flush()
                obj = self.import_object(scenegroup, new_mesh, materials, offset_x, offset_y,
                                         offset_z)
                return obj
        except CONNECTION_ERRORS:
            if retries > 0:
                sys.stderr.write("_")
                sys.stderr.flush()
                return self.import_group(groupid, scenegroup, retries-1)
            else:
                traceback.print_exc()
                sys.stderr.write("!"+scenegroup["asset"])
                sys.stderr.flush()

    def check_uuid(self, obj, groupid):
        """
        Check if the given object has the given groupid.
        """
        if self.get_uuid(obj) == groupid:
            return True

    def get_uuid(self, obj):
        """
        Get the uuid from the given object.
        """
        if "opensim" in obj.properties:
            if "uuid" in obj.properties["opensim"]:
                return obj.properties['opensim']['uuid']

    def set_uuid(self, obj, obj_uuid):
        """
        Set the uuid for the given blender object.
        """
        if not "opensim" in obj.properties:
            obj.properties["opensim"] = {}
        obj.properties["opensim"]["uuid"] = obj_uuid

    def find_with_uuid(self, groupid, objects, section):
        """
        Find the object with the given uuid.
        """
        if groupid in self._total[section]:
            return objects[self._total[section][groupid]]
        else:
            for obj in objects:
                obj_uuid = self.get_uuid(obj)
                if obj_uuid:
                    self._total[section][obj_uuid] = obj.name

    def check_group(self, groupid, scenegroup):
        """
        Run a check on the group, to see if it exists in blender.
        """
        if self.find_with_uuid(groupid, bpy.data.objects, "objects"):
            self._found["objects"] += 1
        self._total_server["objects"] += 1
        if self.find_with_uuid(scenegroup["asset"], bpy.data.meshes, "meshes"):
            self._found["meshes"] += 1
        self._total_server["meshes"] += 1

    def check_region(self, region_id, action="check"):
        """
        Run a check on the region, Checks correspondence of objects between
        Blender and OpenSim and returns a formatted result as an array.
        """
        self.init_structures()
        con = SimConnection()
        con.connect(self.gridinfo._url)
        scenedata = con._con.ogrescene_list({"RegionID":region_id})
        total = 0
        total_yes = 0
        for groupid, scenegroup in scenedata['res'].items():
            if getattr(self, action+"_group")(groupid, scenegroup):
                total_yes += 1
            total += 1
        report = []
        report.append("--. \n")
        report.append("total objects %s. \n"%(total,))
        for key in self._found.keys():
            report.append("total "+key+" %s. \n"%(self._total_server[key],))
            report.append(key+" in blend %s\n"%(self._found[key],))
        return report

    def sync_region(self, region_id):
        """
        Sync the given region. Downloads information for the given objects from
        opensim.
        """
        self.init_structures()
        con = SimConnection()
        con.connect(self.gridinfo._url)
        scenedata = con._con.ogrescene_list({"RegionID":region_id})["res"]
        objects = self.getSelected()
        if not objects:
            objects = bpy.data.objects
        for obj in objects:
            obj_uuid = str(self.get_uuid(obj))
            if obj_uuid:
                if obj_uuid in scenedata:
                    self.import_group(obj_uuid, scenedata[obj_uuid], 10)

    def import_region(self, region_id, action="import"):
        """
        Import the given region into blender.
        """
        self.init_structures()
        con = SimConnection()
        con.connect(self.gridinfo._url)
        scenedata = con._con.ogrescene_list({"RegionID":region_id})
        for groupid, scenegroup in scenedata['res'].items():
            getattr(self, action+"_group")(groupid, scenegroup, 10)
            self.queueRedraw('VIEW3D')


if __name__ == '__main__':
    base_url = "http://127.0.0.1:9000"
    gridinfo = GridInfo()
    gridinfo.connect(base_url, "caedes caedes", "XXXXXX")
    logger.debug(gridinfo.getGridInfo()["gridnick"])
    regions = gridinfo.getRegions()
    for id in regions:
        region = regions[id]
        logger.debug((" *", region["name"], region["x"], region["y"], id))
    importer = Importer(gridinfo)
    importer.import_region(id)


