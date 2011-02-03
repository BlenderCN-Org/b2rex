import bpy

from bpy.props import StringProperty, PointerProperty, IntProperty
from bpy.props import BoolProperty, FloatProperty, CollectionProperty
from bpy.props import FloatVectorProperty

class B2RexRegions(bpy.types.IDPropertyGroup):
    pass

class B2RexBaseProps(bpy.types.IDPropertyGroup):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexObjectProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexMeshProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexTextureProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexImageProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexMaterialProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexProps(bpy.types.IDPropertyGroup):
    #B2RexProps.credentials = PasswordManager("b2rex")
    path = StringProperty(name='path', default='', description='')
    pack = StringProperty(name='pack', default='pack')
    username = StringProperty(name='username',
                              default='caedes caedes',
                              description='')
    password = StringProperty(name='password',
                              default='nemesis',
                              description='')
    server_url = StringProperty(name='server url',
                                default='http://delirium:9000',
                                description='')
    export_dir = StringProperty(name='export dir',
                                default='',
                                description='') 
    loc = FloatVectorProperty(name="location", 
                              description="offset to apply when exporting",
                              default=(128.0, 128.0, 20.0),
                              min=0.0,
                              max=512.0)
    regenMaterials = BoolProperty(name="Regen Material", default=True)
    rt_on = BoolProperty(name="RT", default=False)
    regenObjects = BoolProperty(name="Regen Objects", default=False)
    regenTextures = BoolProperty(name="Regen Textures", default=False)
    regenMeshes = BoolProperty(name="Regen Meshes", default=False)
    expand = BoolProperty(default=True,
                          description="Expand, to display settings")
    status = StringProperty(default="b2rex started", description="Expand, to diesply")
    selected_region = IntProperty(default=-1, description="Expand, to display")
    regions = CollectionProperty(type=B2RexRegions,
                                 name='Regions',
                                 description='Sessions on the server')
#    B2RexProps.regions.name = StringProperty(name='Name', description='Name of the session', maxlen=128, default='[session]')


