# standard
import re
import getpass, sys, logging
from threading import Thread
import threading

from optparse import OptionParser
import time

# related
from eventlet import api

# pyogp
from pyogp.lib.client.agent import Agent
from pyogp.lib.base.helpers import Helpers
from pyogp.lib.client.settings import Settings

from pyogp.lib.base.datatypes import UUID, Vector3, Quaternion

import popen2

class BlenderAgent(object):
    def login(self, in_queue, in_lock, out_queue, out_lock, firstline=""):
        """ login an to a login endpoint """ 

        parser = OptionParser(usage="usage: %prog [options] firstname lastname")

        logger = logging.getLogger("client.example")

        parser.add_option("-l", "--loginuri", dest="loginuri", default="https://login.aditi.lindenlab.com/cgi-bin/login.cgi",
                          help="specified the target loginuri")
        parser.add_option("-r", "--region", dest="region", default=None,
                          help="specifies the region (regionname/x/y/z) to connect to")
        parser.add_option("-q", "--quiet", dest="verbose", default=True, action="store_false",
                        help="enable verbose mode")
        parser.add_option("-p", "--password", dest="password", default=None,
                          help="specifies password instead of being prompted for one")


        (options, args) = parser.parse_args(['-l','http://localhost:9000/go.cgi',
                                             '-r','Taiga',
                                             '-q',
                                             '-p','nemesis',
                                            'caedes','caedes'])

        if len(args) != 2:
            parser.error("Expected arguments: firstname lastname")

        if options.verbose:
            console = logging.StreamHandler()
            console.setLevel(logging.DEBUG) # seems to be a no op, set it for the logger
            formatter = logging.Formatter('%(asctime)-30s%(name)-30s: %(levelname)-8s %(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)

            # setting the level for the handler above seems to be a no-op
            # it needs to be set for the logger, here the root logger
            # otherwise it is NOTSET(=0) which means to log nothing.
            logging.getLogger('').setLevel(logging.DEBUG)
        else:
            print "Attention: This script will print nothing if you use -q. So it might be boring to use it like that ;-)"

        # example from a pure agent perspective

        #grab a password!
        if options.password:
            password = options.password
        else:
            password = getpass.getpass()

        # let's disable inventory handling for this example
        settings = Settings()
        settings.ENABLE_INVENTORY_MANAGEMENT = False
        settings.ENABLE_EQ_LOGGING = False
        settings.ENABLE_CAPS_LOGGING = False

        #First, initialize the agent
        client = Agent(settings = settings, handle_signals=False)
        do_megahal = False
        if do_megahal:
            megahal_r, megahal_w = popen2.popen2("/usr/bin/megahal-personal -p -b -w -d /home/caedes/bots/lorea/.megahal")
            firstline = megahal_r.readline()

        # Now let's log it in
        api.spawn(client.login, options.loginuri, args[0], args[1], password, start_location = options.region, connect_region = True)
        client.sit_on_ground()

        # wait for the agent to connect to it's region
        while client.connected == False:
            api.sleep(0)

        while client.region.connected == False:
            api.sleep(0)

        client.say(str(firstline))
        # do sample script specific stuff here
        res = client.region.message_handler.register("ChatFromSimulator")
        queue = []
        def onChatFromViewer(packet):
            print packet
            fromname = packet["ChatData"][0]["FromName"].split(" ")[0]
            message = packet["ChatData"][0]["Message"]
            if message.startswith("#"):
                return
            if fromname.strip() == client.firstname:
                return
            elif message == "quit":
                if do_megahal:
                    megahal_w.write("#QUIT\n\n")
                    megahal_w.flush()
                client.say("byez!")
                api.sleep(10)
                if do_megahal:
                    megahal_r.close()
                    megahal_w.close()
                client.logout()
                api.sleep(50)
                #while client.connected:
                    #    api.sleep(0)
            elif message == "sit":
                client.fly(False)
                client.sit_on_ground()
            elif message == "stand":
                client.fly(False)
                client.stand()
            elif message == "fly":
                client.fly()
            elif message == "+q":
                if fromname not in queue:
                    queue.append(fromname)
                    client.say(str(queue))
            elif message == "-q":
                if fromname in queue:
                    queue.remove(fromname)
                    client.say(str(queue))
            else:
                if do_megahal:
                    megahal_w.write(message+"\n\n")
                    megahal_w.flush()
                    client.say(str(megahal_r.readline()))
            print "chat",packet["ChatData"][0]["Message"]
            print "chat",packet["ChatData"][0]["FromName"]

        res.subscribe(onChatFromViewer)
        res = client.region.objects.message_handler.register("ObjectUpdate")
        def onObjectUpdate(packet):
           #print "onObjectUpdate"
           for ObjectData_block in packet['ObjectData']:
               #print           ObjectData_block.name,          ObjectData_block.get_variable("ID"), ObjectData_block.var_list,           ObjectData_block.get_variable("State")
               objdata = ObjectData_block["ObjectData"]
               REGION_SIZE = 256.0
               MIN_HEIGHT = -REGION_SIZE
               MAX_HEIGHT = 4096.0
               if len(objdata) == 48:
                   pos = 0
                   pos = Vector3(X=Helpers.packed_u32_to_float(objdata, pos+
                                                             0,
                                                             -0.5*REGION_SIZE,
                                                             1.5*REGION_SIZE),
                                 Y=Helpers.packed_u32_to_float(objdata, pos+
                                                             4,
                                                             -0.5*REGION_SIZE,
                                                             1.5*REGION_SIZE),
                                 Z=Helpers.packed_u32_to_float(objdata, pos+
                                                             8, MIN_HEIGHT,
                                                             MAX_HEIGHT))
                   print pos
                   with out_lock:
                       print ObjectData_block["FullID"], ObjectData_block["ParentID"]
                       out_queue.append([ObjectData_block["FullID"],pos])
                       out_queue.append([ObjectData_block["ParentID"],pos])
               elif len(objdata) == 12:
                    # 8 bit precision update.

                    # Position. U8Vec3.
                    # Velocity. U8Vec3.
                    # Acceleration. U8Vec3.
                    # Rotation. U8Rot(4xU8).
                    # Angular velocity. U8Vec3

                    pos = Vector3(
                        X=Helpers.packed_u32_to_float(objdata,  0, -0.5*REGION_SIZE, 1.5*REGION_SIZE),
                        Y=Helpers.packed_u32_to_float(objdata,  4, -0.5*REGION_SIZE, 1.5*REGION_SIZE),
                        Z=Helpers.packed_u32_to_float(objdata,  8, MIN_HEIGHT, MAX_HEIGHT))
                    """
                    object_properties['Velocity'] = Vector3(
                        X=Helpers.packed_u8_to_float(objdata,  3, -REGION_SIZE, REGION_SIZE),
                        Y=Helpers.packed_u8_to_float(objdata,  4, -REGION_SIZE, REGION_SIZE),
                        Z=Helpers.packed_u8_to_float(objdata,  5, -REGION_SIZE, REGION_SIZE))
                    object_properties['Acceleration'] = Vector3(
                        X=Helpers.packed_u8_to_float(objdata,  6, -REGION_SIZE, REGION_SIZE),
                        Y=Helpers.packed_u8_to_float(objdata,  7, -REGION_SIZE, REGION_SIZE),
                        Z=Helpers.packed_u8_to_float(objdata,  8, -REGION_SIZE, REGION_SIZE))
                    object_properties['Rotation'] = Quaternion(
                        X=Helpers.packed_u8_to_float(objdata,  9, -1.0, 1.0),
                        Y=Helpers.packed_u8_to_float(objdata, 10, -1.0, 1.0),
                        Z=Helpers.packed_u8_to_float(objdata, 11, -1.0, 1.0),
                        W=Helpers.packed_u8_to_float(objdata, 12, -1.0, 1.0)) 
                    object_properties['AngularVelocity'] = Vector3(
                        X=Helpers.packed_u8_to_float(objdata, 13, -REGION_SIZE, REGION_SIZE),
                        Y=Helpers.packed_u8_to_float(objdata, 14, -REGION_SIZE, REGION_SIZE),
                        Z=Helpers.packed_u8_to_float(objdata, 15, -REGION_SIZE, REGION_SIZE))
                        """
                    print pos,"SMALL"
                    with out_lock:
                        out_queue.append([ObjectData_block["FullID"],pos])
              
               else:
                    print "Unparsed update of size ",len(objdata)
        res.subscribe(onObjectUpdate)

        # wait 30 seconds from some object data to come in
        now = time.time()
        start = now
        while now - start < 15 and client.running:
            api.sleep()
            now = time.time()
        client.say("going on")
        client.stand()

        while client.running == True:
            api.sleep(0)
            with in_lock:
                cmds = list(in_queue)
                while len(in_queue):
                    in_queue.pop()
            if cmds:
                for cmd in cmds:
                    if cmd[0] == "quit":
                        client.logout()
                    elif cmd[0] == "pos":
                        obj = client.region.objects.get_object_from_store(FullID=cmd[1])
                        if obj:
                            client.region.objects.send_ObjectPositionUpdate(client, client.agent_id,
                                                      client.session_id,
                                                      obj.LocalID, cmd[2])
                            print obj

        return
        # let's see what's nearby
        objects_nearby = client.region.objects.find_objects_within_radius(20)
        for item in objects_nearby:
            item.select(client)

        # print matches

        #while client.running:
            #        api.sleep(0)

        print ''
        print ''
        print 'At this point, we have an Agent object, Inventory dirs, and with a Region attribute'
        print 'Agent attributes:'
        for attr in client.__dict__:
            print attr, ':\t\t\t',  client.__dict__[attr]
        print ''
        print ''
        print 'Objects being tracked: %s' % len(client.region.objects.object_store)
        print ''
        print ''
        states = {}
        for _object in client.region.objects.object_store:
            if _object.State == 0:
                #items = _object.__dict__.items()
                #items.sort()
                print 'Object attributes'
                for attr in _object.__dict__:
                    print '\t\t%s:\t\t%s' % (attr, _object.__dict__[attr])
                print ''
            else:
                if states.has_key(_object.State):
                    states[_object.State]+=1
                else:
                    states[_object.State] = 1
        print ''
        print 'Object states I don\'t care about atm'
        for state in states:
            print '\t State: ', state, '\tFrequency: ', states[state]
        print ''
        print ''
        print 'Avatars being tracked: %s' % len(client.region.objects.avatar_store)
        print ''
        print ''
        for _avatar in client.region.objects.avatar_store:
            print 'ID:', _avatar.LocalID, '\tUUID: ', _avatar.FullID , '\tNameValue: ', _avatar.NameValue, '\tPosition: ', _avatar.Position
        print ''
        print ''
        print 'Region attributes:'
        for attr in client.region.__dict__:
            print attr, ':\t\t\t',  client.region.__dict__[attr]

class testit(Thread):
    def __init__ (self):
        import Blender
        self.firstline = 'Blender '+ str(Blender.Get('version'))
        self.running = True
        self.cmd_out_queue = []
        self.cmd_in_queue = []
        self.cmd_out_lock = threading.RLock()
        self.cmd_in_lock = threading.RLock()
        Thread.__init__(self)

    def apply_position(self, obj_uuid, pos):
        cmd = ['pos', obj_uuid, pos]
        self.addCmd(['pos', obj_uuid, pos])

    def run(self):
        agent = BlenderAgent()
        agent.login(self.cmd_in_queue,
                   self.cmd_in_lock,
                   self.cmd_out_queue,
                   self.cmd_out_lock,
                   self.firstline)
        print "quitting"
        self.running = False

    def addCmd(self, cmd):
        if isinstance(cmd, str):
            cmd = [cmd]
        with self.cmd_in_lock:
            if not cmd in self.cmd_in_queue:
                self.cmd_in_queue.append(cmd)

    def getQueue(self):
        with self.cmd_out_lock:
            cmd_out = list(self.cmd_out_queue)
            while len(self.cmd_out_queue):
                self.cmd_out_queue.pop()
        return cmd_out



running = False

def run_thread():
    global running
    running = testit()
    running.start()
    return running

def stop_thread():
    global running
    running.stop()
    running = None

def main():
    current = testit(cmd_queue)
    current.start()
    while current.isAlive():
        time.sleep(1)

if __name__=="__main__":
    main()

"""
Contributors can be viewed at:
http://svn.secondlife.com/svn/linden/projects/2008/pyogp/CONTRIBUTORS.txt 

$LicenseInfo:firstyear=2008&license=apachev2$

Copyright 2009, Linden Research, Inc.

Licensed under the Apache License, Version 2.0 (the "License").
You may obtain a copy of the License at:
    http://www.apache.org/licenses/LICENSE-2.0
or in 
    http://svn.secondlife.com/svn/linden/projects/2008/pyogp/LICENSE.txt

$/LicenseInfo$
"""

