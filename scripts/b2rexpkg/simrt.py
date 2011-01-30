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
from pyogp.lib.client.enums import PCodeEnum

from pyogp.lib.base.datatypes import UUID, Vector3, Quaternion

import popen2

class BlenderAgent(object):
    do_megahal = False
    verbose = False
    def __init__(self, in_queue, in_lock, out_queue, out_lock):
        self.in_queue = in_queue
        self.in_lock = in_lock
        self.out_queue = out_queue
        self.out_lock = out_lock

    def login(self, server_url, username, password, firstline=""):
        """ login an to a login endpoint """ 
        in_queue = self.in_queue
        out_queue = self.out_queue
        in_lock = self.in_lock
        out_lock = self.out_lock

        client = self.initialize_agent()

        # Now let's log it in
        region = 'Taiga'
        firstname, lastname = username.split(" ", 1)
        if not server_url.endswith("/"):
            server_url = server_url + "/"
        loginuri = server_url + 'go.cgi'
        print loginuri, firstname, lastname, password
        api.spawn(client.login, loginuri, firstname, lastname, password, start_location = region, connect_region = True)

        client.sit_on_ground()

        # wait for the agent to connect to it's region
        while client.connected == False:
            api.sleep(0)

        while client.region.connected == False:
            api.sleep(0)

        # script specific stuff here
        client.say(str(firstline))

        res = client.region.message_handler.register("ChatFromSimulator")
        queue = []

        res.subscribe(self.onChatFromViewer)
        res = client.region.objects.message_handler.register("ObjectUpdate")
        res.subscribe(self.onObjectUpdate)

        # wait 30 seconds for some object data to come in
        now = time.time()
        start = now
        while now - start < 30 and client.running:
            api.sleep(0)
            now = time.time()

        client.say("going on")
        client.stand()

        # main loop for the agent
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
                            #for group in client.group_manager.group_store:
                                #    print ':\t\t\t',  group.GroupName
                                #print client.region.objects.avatar_store
                                #print obj
                                #if hasattr(obj, 'PCode') and obj.PCode ==  PCodeEnum.Avatar:
                                    #    print "AVATAR!"

    def initialize_agent(self):
        logger = logging.getLogger("client.example")

        if self.verbose:
            console = logging.StreamHandler()
            console.setLevel(logging.DEBUG) # seems to be a no op, set it for the logger
            formatter = logging.Formatter('%(asctime)-30s%(name)-30s: %(levelname)-8s %(message)s')
            console.setFormatter(formatter)
            logging.getLogger('').addHandler(console)

            # setting the level for the handler above seems to be a no-op
            # it needs to be set for the logger, here the root logger
            # otherwise it is NOTSET(=0) which means to log nothing.
            logging.getLogger('').setLevel(logging.DEBUG)

        # example from a pure agent perspective

        # let's disable inventory handling for this example
        settings = Settings()
        settings.ENABLE_INVENTORY_MANAGEMENT = False
        settings.ENABLE_EQ_LOGGING = False
        settings.ENABLE_CAPS_LOGGING = False

        #First, initialize the agent
        client = Agent(settings = settings, handle_signals=False)
        self.client = client
        self.do_megahal = False
        if self.do_megahal:
            megahal_r, megahal_w = popen2.popen2("/usr/bin/megahal-personal -p -b -w -d /home/caedes/bots/lorea/.megahal")
            firstline = megahal_r.readline()
        return client

    def onObjectUpdate(self, packet):
       REGION_SIZE = 256.0
       MIN_HEIGHT = -REGION_SIZE
       MAX_HEIGHT = 4096.0
       out_queue = self.out_queue
       out_lock = self.out_lock
       #print "onObjectUpdate"
       for ObjectData_block in packet['ObjectData']:
           #print           ObjectData_block.name,          ObjectData_block.get_variable("ID"), ObjectData_block.var_list,           ObjectData_block.get_variable("State")
           objdata = ObjectData_block["ObjectData"]
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
               with out_lock:
                   out_queue.append(['pos',ObjectData_block["FullID"],pos])
                   #out_queue.append([ObjectData_block["ParentID"],pos])
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
                    out_queue.append(['pos',ObjectData_block["FullID"],pos])
          
           else:
                print "Unparsed update of size ",len(objdata)

    def onChatFromViewer(self, packet):
        client = self.client
        out_lock = self.out_lock
        out_queue = self.out_queue
        fromname = packet["ChatData"][0]["FromName"].split(" ")[0]
        message = packet["ChatData"][0]["Message"]
        with out_lock:
            out_queue.append(['msg',fromname, message])
        if message.startswith("#"):
            return
        if fromname.strip() == client.firstname:
            return
        elif message == "quit":
            if self.do_megahal:
                megahal_w.write("#QUIT\n\n")
                megahal_w.flush()
            client.say("byez!")
            api.sleep(10)
            if self.do_megahal:
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
            if self.do_megahal:
                megahal_w.write(message+"\n\n")
                megahal_w.flush()
                client.say(str(megahal_r.readline()))
        print "chat",packet["ChatData"][0]["Message"]
        print "chat",packet["ChatData"][0]["FromName"]


class GreenletsThread(Thread):
    def __init__ (self, server_url, username, password, firstline="Hello"):
        self.running = True
        self.cmd_out_queue = []
        self.cmd_in_queue = []
        self.cmd_out_lock = threading.RLock()
        self.cmd_in_lock = threading.RLock()
        self.server_url = server_url
        self.username = username
        self.password = password
        self.firstline = firstline
        Thread.__init__(self)

    def apply_position(self, obj_uuid, pos):
        cmd = ['pos', obj_uuid, pos]
        self.addCmd(['pos', obj_uuid, pos])

    def run(self):
        agent = BlenderAgent(self.cmd_in_queue,
                   self.cmd_in_lock,
                   self.cmd_out_queue,
                   self.cmd_out_lock)
        agent.login(self.server_url,
                    self.username,
                    self.password,
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

def run_thread(server_url, username, password, firstline):
    global running
    running = GreenletsThread(server_url, username, password, firstline)
    running.start()
    return running

def stop_thread():
    global running
    running.stop()
    running = None

def main():
    current = GreenletsThread(cmd_queue)
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

