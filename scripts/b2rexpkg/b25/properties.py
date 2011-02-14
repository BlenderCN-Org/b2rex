import bpy

from bpy.props import StringProperty, PointerProperty, IntProperty
from bpy.props import BoolProperty, FloatProperty, CollectionProperty
from bpy.props import FloatVectorProperty

import logging

class B2RexRegions(bpy.types.IDPropertyGroup):
    pass

class B2RexChatLine(bpy.types.IDPropertyGroup):
    pass

class B2RexBaseProps(bpy.types.IDPropertyGroup):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexObjectProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')
    everyonemask_expand = BoolProperty(name='everyonemask_expand', default=False)


class B2RexMeshProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexTextureProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexImageProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')

class B2RexMaterialProps(B2RexBaseProps):
    uuid = StringProperty(name='uuid', default='', description='')
    autodetect = BoolProperty(name="autodetect", default=True)
    shader = StringProperty(name='shader',
                              default='',
                              description='')

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
    loglevel = IntProperty(name='loglevel',
                           default=logging.ERROR,
                          description='log level')
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
    rt_on = BoolProperty(name="RT", default=False, description="Enable real time connection")
    rt_budget = IntProperty(name="Rt Budget", default=20, min=5,
                              max=500, step=1, description="Number of milliseconds allocated for command execution every frame")
    rt_sec_budget = IntProperty(name="Rt Budget per second", default=250, min=50,
                              max=1000, step=1, description="Number of  milliseconds allocated for command execution every second")
    pool_workers = IntProperty(name="Download Threads", default=5, min=1,
                               max=100, step=1, description="Number of threads dedicated to downloading and transcoding")
    regenObjects = BoolProperty(name="Regen Objects", default=False)
    regenTextures = BoolProperty(name="Regen Textures", default=False)
    kbytesPerSecond = IntProperty(name="Kbyte/s", default=100,
                                  description="kbytes per second to throttle the connection to")
    terrainLOD = IntProperty(name="Terrain LOD", default=1, min=0, max=4,
                                  description="terrain lod level, needs restart to take effect")
    regenMeshes = BoolProperty(name="Regen Meshes", default=False)
    expand = BoolProperty(default=True,
                          description="Expand, to display settings")
    show_stats = BoolProperty(default=False,
                          description="Expand, to display stats")
    selected_region = IntProperty(default=-1, description="Expand, to display")
    regions = CollectionProperty(type=B2RexRegions,
                                 name='Regions',
                                 description='Sessions on the server')
    chat = CollectionProperty(type=B2RexChatLine,
                                 name='Chat',
                                 description='Chat with the server')
    selected_chat = IntProperty(default=-1, description="Expand, to display")
    next_chat = StringProperty(name='next_chat',
                              default='',
                              description='')
    inventory_expand = BoolProperty(default=False, description="Expand inventory")
    regions_expand = BoolProperty(default=False, description="Expand region controls")
    chat_expand = BoolProperty(default=False, description="Expand chat")
#    B2RexProps.regions.name = StringProperty(name='Name', description='Name of the session', maxlen=128, default='[session]')


