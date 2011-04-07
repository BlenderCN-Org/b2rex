#Blender Game Engine 2.55 Simple Camera Look
#Created by Mike Pan: mikepan.com

# Use mouse to look around
# W,A,S,D key to walk around
# E and C key to ascenpd and decend

import bpy
import mathutils
import os
from bge import logic as G
from bge import render as R
from bge import events

speed = 0.2    # walk speed
sensitivity = 1.0    # mouse sensitivity

owner = G.getCurrentController().owner

simrt = bpy.b2rex_session.simrt
session = bpy.b2rex_session

def import_object(obname):
    opath = "//cube.blend\\Object\\" + obname
    s = os.sep
    dpath = bpy.utils.script_paths()[0] + \
        '%saddons%sb2rexpkg%sdata%sblend%scube.blend\\Object\\' % (s, s, s, s, s)

    # DEBUG
    #print('import_object: ' + opath)

    bpy.ops.wm.link_append(
            filepath=opath,
            filename=obname,
            directory=dpath,
            filemode=1,
            link=False,
            autoselect=True,
            active_layer=True,
            instance_groups=True,
            relative_path=True)
            
   # for ob in bpy.context.selected_objects:
   #     ob.location = bpy.context.scene.cursor_location

if not "avatar" in bpy.data.objects:
    import_object("avatar")
    

avatar = bpy.data.objects["avatar"]


    


commands = simrt.getQueue()

for command in commands:
    if command[0] == "pos":
        print("command0")
        objid = command[1]
        pos = command[2]
        if objid == session.agent_id:
            print(pos, owner.get("uuid"))
            avatar.location = session._apply_position(pos)
#            owner.position = session._apply_position(pos)    
#            owner.applyMovement([0.1,0,0],True)



# center mouse on first frame, create temp variables

if "oldX" not in owner:
    G.mouse.position = (0.5,0.5)
    owner["oldX"] = 0.0
    owner["oldY"] = 0.0
    owner["minX"] = 10.0
    owner["minY"] = 10.0

else:
    
    # clamp camera to above surface
    #if owner.position[2] < 0:
    #    owner.position[2] = 0
        
    x = 0.5 - G.mouse.position[0]
    y = 0.5 - G.mouse.position[1]
    
    if abs(x) > abs(owner["minX"]) and abs(y) > abs(owner["minY"]):
    
        x *= sensitivity
        y *= sensitivity
        
        # Smooth movement
        #owner['oldX'] = (owner['oldX']*0.5 + x*0.5)
        #owner['oldY'] = (owner['oldY']*0.5 + y*0.5)
        #x = owner['oldX']
        #y = owner['oldY']
         
        # set the values
        owner.applyRotation([0, 0, x], False)
        owner.applyRotation([y, 0, 0], True)
        
        _rotmat = owner.worldOrientation
        print(_rotmat)
        _roteul = _rotmat.to_euler()
        _roteul[0] = 0
        _roteul[1] = 0
        rot = session.unapply_rotation(_roteul)
    #    print(rot)
        simrt.BodyRotation(rot)
    
    else:
        owner["minX"] = x
        owner["minY"] = y
        
    # Center mouse in game window
   

    G.mouse.position = (0.5,0.5)
    
    # keyboard control
    keyboard = G.keyboard.events
    if keyboard[events.WKEY]:
        simrt.Walk(True)
    elif keyboard[events.SKEY]:
        simrt.WalkBackwards(True)
    elif keyboard[events.AKEY]:
        simrt.BodyRotation([1, 0, 0, 1])
    elif keyboard[events.DKEY]:
        simrt.BodyRotation([1, 1, 0, 1])
    else:
        simrt.Stop()


"""






        owner.applyMovement([-speed,0,0], True)

        owner.applyMovement([speed,0,0], True)
    if keyboard[events.EKEY]:
        owner.applyMovement([0,speed,0], True)
    if keyboard[events.CKEY]:
        owner.applyMovement([0,-speed,0], True)
"""