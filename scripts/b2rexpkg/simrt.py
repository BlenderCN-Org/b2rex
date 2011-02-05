# standard
import re
import getpass, sys, logging
import time
import math
import popen2
import struct
import urlparse
from threading import Thread, RLock

# related
import eventlet
from eventlet import api
try:
    from jsonsocket import JsonSocket
except:
    from b2rexpkg.tools.jsonsocket import JsonSocket
import socket

# pyogp
from pyogp.lib.base.exc import LoginError
from pyogp.lib.base.helpers import Helpers
from pyogp.lib.base.datatypes import UUID, Vector3, Quaternion

from pyogp.lib.client.agent import Agent
from pyogp.lib.client.settings import Settings
from pyogp.lib.client.enums import PCodeEnum

# Extra asset and inventory types for rex
import pyogp.lib.client.enums
pyogp.lib.client.enums.AssetType.OgreMesh = 43
pyogp.lib.client.enums.AssetType.OgreSkeleton = 44
pyogp.lib.client.enums.AssetType.OgreMaterial = 45
pyogp.lib.client.enums.AssetType.OgreParticles = 47
pyogp.lib.client.enums.AssetType.FlashAnimation = 49
pyogp.lib.client.enums.AssetType.GAvatar = 46

pyogp.lib.client.enums.InventoryType.OgreParticles = 41
pyogp.lib.client.enums.InventoryType.FlashAnimation = 42
pyogp.lib.client.enums.InventoryType.OgreMaterial = 41

def v3_to_list(v3):
    return [v3.X, v3.Y, v3.Z]
def q_to_list(q):
    return [q.X, q.Y, q.Z, q.W]
def b_to_s(b):
    return b.decode('utf-8')
def uuid_to_s(b):
    return str(b)

class BlenderAgent(object):
    do_megahal = False
    verbose = True
    def __init__(self, in_queue, in_lock, out_queue, out_lock):
        self.in_queue = in_queue
        self.in_lock = in_lock
        self.out_queue = out_queue
        self.out_lock = out_lock
        self.initialize_logger()

    def onRexPrimData(self, packet):
        rexdata = packet[1]["Parameter"]
        self.logger.debug("REXPRIMDATA "+str(len(rexdata)))
        if len(rexdata) < 102:
            rexdata = rexdata + ('\0'*(102-len(rexdata)))
        obj_uuid = str(UUID(packet[0]["Parameter"]))
        pars = {}
        pars["drawType"] = struct.unpack("<b", rexdata[0])[0]
        pars["RexIsVisible "]= struct.unpack("<?", rexdata[1])[0]
        pars["RexCastShadows "]= struct.unpack("<?", rexdata[2])[0]
        pars["RexLightCreatesShadows "]= struct.unpack("<?", rexdata[3])[0]
        pars["RexDescriptionTexture"] = struct.unpack("<?", rexdata[4])[0]
        pars["RexScaleToPrim "]= struct.unpack("<?", rexdata[5])[0]
        pars["RexDrawDistance "]= struct.unpack("<f", rexdata[6:6+4])[0]
        pars["RexLOD "]= struct.unpack("<f", rexdata[10:10+4])[0]
        pars["RexMeshUUID "]= str(UUID(bytes=rexdata[14:14+16]))
        pars["RexCollisionMeshUUID "]= str(UUID(bytes=rexdata[30:30+16]))
        pars["RexParticleScriptUUID "]= str(UUID(bytes=rexdata[46:46+16]))
        pars["RexAnimationPackageUUID "]= str(UUID(bytes=rexdata[62:62+16]))
        with self.out_lock:
            self.out_queue.append(['RexPrimData', obj_uuid, pars])
        animname = ""
        idx = 78
        while rexdata[idx] != '\0':
            idx += 1
        animname = rexdata[78:idx+1]
        pos = idx+1
        RexAnimationRate = struct.unpack("<f", rexdata[pos:pos+4])[0]
        materialsCount = struct.unpack("<b", rexdata[pos+4])[0]
        pos = pos+5
        for i in range(materialsCount):
            assettype = struct.unpack("<b", rexdata[pos])[0]
            matuuid_b = rexdata[pos+1:pos+1+16]
            matuuid = UUID(bytes=matuuid_b)
            matindex = struct.unpack("<b", rexdata[pos+17])[0]
            pos = pos + 18
        if not len(rexdata) > pos:
            self.logger.debug("RexPrimData: no more data")
            return
        idx = pos
        while rexdata[idx] != '\0':
              idx += 1
        RexClassName = rexdata[pos:idx+1]
        self.logger.debug(" REXCLASSNAME: " + str(RexClassName))

    def onGenericMessage(self, packet):
        if packet["MethodData"][0]["Method"] == "RexPrimData":
            self.onRexPrimData(packet["ParamList"])
        else:
            self.logger.debug("unrecognized generic message"+packet["MethodData"][0]["Method"])

    def onObjectPermissions(self, packet):
        self.logger.debug("PERMISSIONS!!!")
    def onObjectProperties(self, packet):
        self.logger.debug("PERMISSIONS!!!")

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
        parsed_url = urlparse.urlparse(server_url)
        split_netloc = parsed_url.netloc.split(":")
        if len(split_netloc) == 2:
            server_name, port = split_netloc
        else:
            server_name = parsed_url.netloc
            port = None
        try:
            # reconstruct the url with the ip to avoid problems
            res_server_name = socket.gethostbyname(server_name)
            if res_server_name == '::1': # :-P
                res_server_name = '127.0.0.1'
            if res_server_name in ['127.0.01', '::1']:
                server_name = res_server_name
        except:
            pass
        if port:
            server_name = server_name + ":" + port
        else:
            server_name = server_name + '/xml-rpc.php'
        server_url = parsed_url.scheme + '://' + server_name
        #if not server_url.endswith("/"):
            #    server_url = server_url + "/"
        loginuri = server_url
        api.spawn(client.login, loginuri, firstname, lastname, password,
                  start_location = region, connect_region = True)

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
        res = client.region.message_handler.register("SimStats")
        res.subscribe(self.onSimStats)
        res = client.region.message_handler.register("RexPrimData")
        res.subscribe(self.onRexPrimData)
        res = client.region.message_handler.register("GenericMessage")
        res.subscribe(self.onGenericMessage)
        res = client.region.message_handler.register("ObjectPermissions")
        res.subscribe(self.onObjectPermissions)
        res = client.region.message_handler.register("ObjectProperties")
        res.subscribe(self.onObjectPermissions)
        res = client.region.objects.message_handler.register("RexPrimData")
        res.subscribe(self.onRexPrimData)

        # wait 30 seconds for some object data to come in
        now = time.time()
        start = now
        #while now - start < 30 and client.running:
            #    api.sleep(0)
            #now = time.time()

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
                cmd_type = 9 # 1-pos, 2-rot, 3-rotpos 4,20-scale, 5-pos,scale,
                # 10-rot
                for cmd in cmds:
                    api.sleep(0)
                    if cmd[0] == "quit":
                        client.logout()
                    elif cmd[0] == "msg":
                        client.say(cmd[1])
                    elif cmd[0] == "scale":
                        cmd_type = 12
                        obj = client.region.objects.get_object_from_store(FullID=cmd[1])
                        if obj:
                            data = cmd[2]
                            client.region.objects.send_ObjectPositionUpdate(client, client.agent_id,
                                                      client.session_id,
                                                      obj.LocalID, data, cmd_type)
                    elif cmd[0] == "pos":
                        obj = client.region.objects.get_object_from_store(FullID=cmd[1])
                        if obj:
                            pos = cmd[2]
                            rot = cmd[3]
                            if rot:
                                X = rot[0]
                                Y = rot[1]
                                Z = rot[2]
                                W = rot[3]
                                norm = math.sqrt((X*X)+(Y*Y)+(Z*Z)+(W*W))
                                if norm == 0:
                                    data = [pos[0], pos[1], pos[2]]
                                else:
                                    norm = 1.0 / norm
                                    if W < 0:
                                        X = -X
                                        Y = -Y
                                        Z = -Z
                                    data = [pos[0], pos[1], pos[2],
                                            #0.0,0.0,0.0,
                                            #0.0,0.0,0.0,
                                            X*norm, Y*norm, Z*norm]
                                    cmd_type = 11 # PrimGroupRotation
                            else:
                                data = [pos[0], pos[1], pos[2]]
                            client.region.objects.send_ObjectPositionUpdate(client, client.agent_id,
                                                      client.session_id,
                                                      obj.LocalID, data, cmd_type)
    def initialize_logger(self):
        self.logger = logging.getLogger("b2rex.simrt")

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

    def initialize_agent(self):
        # let's disable inventory handling for this example
        settings = Settings()
        settings.ENABLE_INVENTORY_MANAGEMENT = False
        settings.ENABLE_EQ_LOGGING = False
        settings.ENABLE_CAPS_LOGGING = False
        settings.ENABLE_REGION_EVENT_QUEUE = False
        settings.REGION_EVENT_QUEUE_POLL_INTERVAL = 1

        #First, initialize the agent
        client = Agent(settings = settings, handle_signals=False)
        self.client = client
        self.do_megahal = False
        if self.do_megahal:
            megahal_r, megahal_w = popen2.popen2("/usr/bin/megahal-personal -p -b -w -d /home/caedes/bots/lorea/.megahal")
            firstline = megahal_r.readline()
        return client

    def onSimStats(self, packet):
        return
        for stat in packet["Stat"]:
            self.logger.debug(str(stat["StatID"]) + " " + str(stat["StatValue"]))
        self.logger.debug("received sim stats!"+str(packet))

    def onObjectUpdate(self, packet):
        out_queue = self.out_queue
        out_lock = self.out_lock
        for ObjectData_block in packet['ObjectData']:
           #print ObjectData_block.name, ObjectData_block.get_variable("ID"), ObjectData_block.var_list, ObjectData_block.get_variable("State")
           objdata = ObjectData_block["ObjectData"]
           obj_uuid = uuid_to_s(ObjectData_block["FullID"])
           with out_lock:
                out_queue.append(['props', obj_uuid,
                                  {"OwnerID": str(ObjectData_block["OwnerID"])}])
           if "Scale" in ObjectData_block.var_list:
               scale = ObjectData_block["Scale"]
               with out_lock:
                   out_queue.append(['scale', obj_uuid,
                                     v3_to_list(scale)])
           if len(objdata) == 48:
               pos_vector = Vector3(objdata)
               vel = Vector3(objdata[12:])
               acc = Vector3(objdata[24:])
               rot = Quaternion(objdata[36:])
               with out_lock:
                   out_queue.append(['pos', obj_uuid, v3_to_list(pos_vector)])
                   out_queue.append(['rot', obj_uuid, q_to_list(rot)])
           elif len(objdata) == 12:
               if True:
                   # position only packed as 3 floats
                   pos = Vector3(objdata)
                   with out_lock:
                       out_queue.append(['pos', obj_uuid, v3_to_list(pos)])
               elif ObjectData_block.Type in [4, 20, 12, 28]:
                   # position only packed as 3 floats
                   scale = Vector3(objdata)
                   with out_lock:
                       out_queue.append(['scale', obj_uuid, v3_to_list(scale)])
               elif ObjectData_block.Type in [2, 10]:
                   # rotation only packed as 3 floats
                   rot = Quaternion(objdata)
                   with out_lock:
                       out_queue.append(['rot', obj_uuid, q_to_list(rot)])
         
           else:
                # missing sizes: 28, 40, 44, 64
                self.logger.debug("Unparsed update of size "+str(len(objdata)))

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
        self.logger.debug("chat:"+packet["ChatData"][0]["Message"])
        self.logger.debug("chat:"+packet["ChatData"][0]["FromName"])


class GreenletsThread(Thread):
    def __init__ (self, server_url, username, password, firstline="Hello"):
        self.running = True
        self.cmd_out_queue = []
        self.cmd_in_queue = []
        self.cmd_out_lock = RLock()
        self.cmd_in_lock = RLock()
        self.server_url = server_url
        self.username = username
        self.password = password
        self.firstline = firstline
        Thread.__init__(self)

    def apply_position(self, obj_uuid, pos, rot=None):
        cmd = ['pos', obj_uuid, pos, rot]
        self.addCmd(cmd)

    def apply_scale(self, obj_uuid, scale):
        cmd = ['scale', obj_uuid, scale]
        self.addCmd(cmd)

    def run(self):
        agent = BlenderAgent(self.cmd_in_queue,
                   self.cmd_in_lock,
                   self.cmd_out_queue,
                   self.cmd_out_lock)
        agent.login(self.server_url,
                    self.username,
                    self.password,
                    self.firstline)
        agent.logger.debug("Quitting")
        self.running = False

    def addCmd(self, cmd):
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

def run_thread(context, server_url, username, password, firstline):
    global running
    running = GreenletsThread(server_url, username, password, firstline)
    running.start()
    return running

def stop_thread():
    global running
    running.stop()
    running = None


# the following is to run in stand alone mode
class ClientHandler(object):
    def __init__(self):
        self.current = None
    def read_client(self, json_socket, pool):
        global running
        while True:
            data = json_socket.recv()
            if not data:
                # client disconnected, bail out
                break
            if data[0] == 'connect' and not running:
                # initial connect command
                running = GreenletsThread(*data[1:])
                self.current = running
                pool.spawn_n(running.run)
                json_socket.send(["hihi"])
            elif self.current:
                # forward command
                print("forward command", data)
                self.current.addCmd(data)
            api.sleep(0)
        # exit
        self.connected = False
    def handle_client(self, json_socket, pool):
        global running
        global run_main
        self.connected = True
        pool.spawn_n(self.read_client, json_socket, pool)
        if running:
            json_socket.send(["state", "connected"])
        else:
            json_socket.send(["state", "idle"])
        while self.connected:
            api.sleep(0)
            if self.current:
                queue = self.current.getQueue()
                for cmd in queue:
                    print(cmd)
                    json_socket.send(cmd)
                    api.sleep(0)
        if running:
            running.addCmd(["quit"])
            run_main = False
            sys.exit()

run_main = True
def main():
    server = eventlet.listen(('0.0.0.0', 11112))
    pool = eventlet.GreenPool(10000)
    while run_main:
         new_sock, address = server.accept()
         client_handler = ClientHandler()
         pool.spawn_n(client_handler.handle_client, JsonSocket(new_sock), pool)
         api.sleep(0)

    #current = GreenletsThread(cmd_queue)
    #current.start()
    #while current.isAlive():
        #    time.sleep(1)

if __name__=="__main__":
    main()


