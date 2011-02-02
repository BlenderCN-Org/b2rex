import bpy

from bpy.props import StringProperty, PointerProperty, IntProperty
from bpy.props import BoolProperty, FloatProperty, CollectionProperty
from bpy.props import FloatVectorProperty

class B2RexRegions(bpy.types.IDPropertyGroup):
    pass

class B2RexProps(bpy.types.IDPropertyGroup):
    #B2RexProps.credentials = PasswordManager("b2rex")
    path = StringProperty(name='path', default='')
    pack = StringProperty(name='pack', default='pack')
    username = StringProperty(name='username', default='caedes caedes')
    password = StringProperty(name='password', default='nemesis')
    server_url = StringProperty(name='server url', default='http://delirium:9000')
    export_dir = StringProperty(name='login password', default='') 
    loc = FloatVectorProperty(name="location", 
                              description="offset to apply when exporting",
                              default=(128.0, 128.0, 20.0),
                              min=0.0,
                              max=512.0)
    regenMaterials = BoolProperty(name="Regen Material", default=False)
    regenObjects = BoolProperty(name="Regen Objects", default=False)
    regenTextures = BoolProperty(name="Regen Textures", default=False)
    regenMeshes = BoolProperty(name="Regen Meshes", default=False)
    expand = BoolProperty(default=False, description="Expand, to diesply")
    status = StringProperty(default="b2rex started", description="Expand, to diesply")
    selected_region = IntProperty(default=-1, description="Expand, to diesply")
    regions = CollectionProperty(type=B2RexRegions,
                                 name='Regions',
                                 description='Sessions on the server')
#    B2RexProps.regions.name = StringProperty(name='Name', description='Name of the session', maxlen=128, default='[session]')


