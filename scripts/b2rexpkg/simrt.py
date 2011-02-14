# standard
import os
import sys
import uuid
import logging
import time
import math
import popen2
import base64
import socket
import struct
from collections import defaultdict
from threading import Thread

# related
import eventlet
from eventlet import api
from eventlet import Queue

if __name__ == '__main__':
    simrt_path = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(os.path.join(simrt_path))
    sys.path.append(os.path.join(simrt_path, 'tools'))
try:
    from jsonsocket import JsonSocket
    from simtypes import LayerTypes, AssetType
except:
    from b2rexpkg.tools.jsonsocket import JsonSocket
    from b2rexpkg.tools.simtypes import LayerTypes, AssetType

# pyogp
from pyogp.lib.base.exc import LoginError
from pyogp.lib.base.helpers import Helpers
from pyogp.lib.base.message.message import Message, Block
from pyogp.lib.base.datatypes import UUID, Vector3, Quaternion

from pyogp.lib.client.agent import Agent
from pyogp.lib.client.enums import PCodeEnum
from pyogp.lib.client.settings import Settings
from pyogp.lib.client.namevalue import NameValueList

# internal rt module
from rt.handlers.chat import ChatHandler
from rt.handlers.layerdata import LayerDataHandler
from rt.handlers.parcel import ParcelHandler
from rt.handlers.object import ObjectHandler
from rt.handlers.select import SelectHandler
from rt.handlers.inventory import InventoryHandler
from rt.handlers.rexdata import RexDataHandler
from rt.handlers.throttle import ThrottleHandler
from rt.handlers.online import OnlineHandler
from rt.handlers.bootstrap import BootstrapHandler
from rt.handlers.simstats import SimStatsHandler
from rt.handlers.xferupload import XferUploadManager
from rt.handlers.agentmovement import AgentMovementHandler
from rt.handlers.regionhandshake import RegionHandshakeHandler

from rt.tools import v3_to_list, q_to_list, uuid_combine, uuid_to_s
from rt.tools import unpack_v3, unpack_q, b_to_s, prepare_server_name


class AgentManager(object):
    do_megahal = False
    verbose = False
    def __init__(self, in_queue, out_queue):
        self.nlayers = 0
        self._handlers = {}
        self._generichandlers = {}
        self._cmdhandlers = defaultdict(list)
        self.client = None
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.initialize_logger()

    def registerGenericHandler(self, message, handler):
        self._generichandlers[message] = handler

    def onGenericMessage(self, packet):
        methodname = packet["MethodData"][0]["Method"]
        if methodname in self._generichandlers:
            self._generichandlers[methodname](packet["ParamList"])
        else:
            self.logger.debug("unrecognized generic message"+packet["MethodData"][0]["Method"])
            print(packet)


    def sendLocalTeleport(self, agent, pos):
        client = self.client
        if not agent.FullID == self.client.agent_id:
            print("Trying to move an agent for other user")
        t_id = uuid.uuid4()
        invoice_id = UUID()
        self.client.teleport(region_handle=client.region.RegionHandle, 
                             position=Vector3(X=pos[0], Y=pos[1], Z=pos[2]))

    def sendAutopilot(self, agent, pos):
        packet = Message('GenericMessage',
                        Block('AgentData',
                                AgentID = client.agent_id,
                                SessionID = client.session_id,
                             TransactionID = t_id),
                        Block('MethodData',
                                Method = 'autopilot',
                                Invoice = invoice_id),
                        Block('ParamList', Parameter=data_x),
                        Block('ParamList', Parameter=data_y),
                        Block('ParamList', Parameter=data_z))
        self.client.region.enqueue_message(packet)

    def onCoarseLocationUpdate(self, packet):
        #print("COARSE LOCATION UPDATE")
        #print(packet)
        for i, block in enumerate(packet["Location"]):
            X = block['X']
            Y = block['Y']
            Z = block['Z']
            agent = packet["AgentData"][i]["AgentID"]

            self.out_queue.put(["CoarseLocationUpdate", str(agent), (X, Y, Z)])

    def subscribe_region_callbacks(self, region):
        for handler in self._handlers.values():
            handler.onRegionConnected(region)

    def subscribe_region_pre_callbacks(self, region):
        for handler in self._handlers.values():
            handler.onRegionConnect(region)

        res = region.message_handler.register("CoarseLocationUpdate")
        res.subscribe(self.onCoarseLocationUpdate)
        res = region.message_handler.register("GenericMessage")
        res.subscribe(self.onGenericMessage)

    def addHandler(self, handler):
        self._handlers[handler.getName()] = handler
        for a in dir(handler):
            if a.startswith("process"):
                self._cmdhandlers[a[7:]].append(getattr(handler, a))
        service = handler.getName().lower()
        setattr(self, service, handler)

    def login(self, server_url, username, password, regionname, firstline=""):
        """ login an to a login endpoint """ 
        in_queue = self.in_queue
        out_queue = self.out_queue

        client = self.initialize_agent()

        self.uploader = XferUploadManager(self)
        self.addHandler(self.uploader)
        self.addHandler(OnlineHandler(self))
        self.addHandler(RegionHandshakeHandler(self))
        self.addHandler(SimStatsHandler(self))
        self.addHandler(AgentMovementHandler(self))
        self.addHandler(LayerDataHandler(self))
        self.addHandler(ParcelHandler(self))
        self.addHandler(ThrottleHandler(self))
        self.addHandler(RexDataHandler(self))
        self.addHandler(InventoryHandler(self))
        self.addHandler(ChatHandler(self))
        self.addHandler(SelectHandler(self))
        self.addHandler(ObjectHandler(self))

        # Now let's log it in
        firstname, lastname = username.split(" ", 1)
        loginuri = prepare_server_name(server_url)

        api.spawn(client.login, loginuri, firstname, lastname, password,
                  start_location = regionname, connect_region = True)

        client.sit_on_ground()

        # wait for the agent to connect to it's region
        while client.connected == False:
            api.sleep(0)

        for handler in self._handlers.values():
            handler.onAgentConnected(client)

        self.subscribe_region_pre_callbacks(client.region)

        # inform our client of connection success
        out_queue.put(["connected", str(client.agent_id),
                             str(client.agent_access)])
 
        caps_sent = False
        caps = {}

        # wait until the client is connected
        while client.region.connected == False:
            # look for GetTexture and send to client as soon as possible
            if not caps_sent and "GetTexture" in client.region.capabilities:
                for cap in client.region.capabilities:
                    caps[cap] = client.region.capabilities[cap].public_url
                self.out_queue.put(["capabilities", caps])
                caps_sent = True
            api.sleep(0)

        self.subscribe_region_callbacks(client.region)

        self.throttle.sendThrottle()

        # speak up the first line
        client.say(str(firstline))

        # main loop for the agent
        while client.running == True:
            api.sleep(0)
            cmd = in_queue.get()
            #   # 10-rot
            command = cmd[0]
            command = command[0].upper()+command[1:]
            if command in self._cmdhandlers:
                # we have a registered handler
                for handler in self._cmdhandlers[command]:
                    handler(*cmd[1:])
            else:
                # try a function in this class
                handler = 'process'+command
                try:
                    # look for a function called processCommandName with first
                    # letter of command capitalized, so quit, becomes processQuit
                    func = getattr(self, handler)
                except:
                    print("Cant find handler for ", handler)
                else:
                    func(*cmd[1:])

    def processQuit(self):
        return # ignore
        out_queue.put(["quit"])
        client.logout()
        return

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


class ProxyFunction(object):
    def __init__(self, name, parent):
        self._name = name
        self._parent = parent
    def __call__(self, *args):
        self._parent.addCmd([self._name]+list(args))

class GreenletsThread(Thread):
    def __init__ (self, server_url, username, password, region, firstline="Hello"):
        self.running = True
        self.agent = True
        self.cmd_out_queue = []
        self.cmd_in_queue = []
        self.out_queue = Queue()
        self.in_queue = Queue()
        self.server_url = server_url
        self.regionname = region
        self.username = username
        self.password = password
        self.firstline = firstline
        Thread.__init__(self)

    def apply_position(self, obj_uuid, pos, rot=None):
        cmd = ['pos', obj_uuid, pos, rot]
        self.addCmd(cmd)

    def __getattr__(self, name):
        return ProxyFunction(name, self)

    def apply_scale(self, obj_uuid, scale):
        cmd = ['scale', obj_uuid, scale]
        self.addCmd(cmd)

    def run(self):
        agent = AgentManager(self.in_queue,
                   self.out_queue)
        agent.login(self.server_url,
                    self.username,
                    self.password,
                    self.regionname,
                    self.firstline)
        agent.logger.debug("Quitting")
        self.agent = agent
        self.running = False

    def addCmd(self, cmd):
        self.in_queue.put(cmd)

    def getQueue(self):
        out_queue = []
        while self.out_queue.qsize():
            out_queue.append(self.out_queue.get())
        return out_queue


running = False

def run_thread(context, server_url, username, password, region, firstline):
    global running
    running = GreenletsThread(server_url, username, password, region, firstline)
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
        self.deferred_cmds = []
    def read_client(self, json_socket, pool):
        global running
        while True:
            data = json_socket.recv()
            if not data:
                # client disconnected, bail out
                self.current.out_queue.put(["quit"])
                break
            if data[0] == 'connect':
                if not running:
                    # initial connect command
                    running = GreenletsThread(*data[1:])
                    self.current = running
                    pool.spawn_n(running.run)
                    for cmd in self.deferred_cmds:
                        running.addCmd(cmd)
                    self.deferred_cmds = []
                    json_socket.send(["hihi"])
                else:
                    running.addCmd(["bootstrap"])
            elif self.current:
                # forward command
                self.current.addCmd(data)
            else:
                if data[0] in ["throttle"]:
                    self.deferred_cmds.append(data)
        print("exit read client")
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
        starttime = time.time()
        while self.connected:
            if self.current:
                cmd = self.current.out_queue.get()
                if cmd[0] == "quit":
                    print("quit on handle client")
                    break;
                else:
                    json_socket.send(cmd)
                #for cmd in self.current.queue.get():
                    #    json_socket.send(cmd)
                    #api.sleep(0)
            else:
                api.sleep(0)
        json_socket.close()
        if running:
            running.addCmd(["quit"])
            running = None
            # run_main = False
        # live..
        #raise eventlet.StopServe

run_main = True
def main():
    server = eventlet.listen(('0.0.0.0', 11112))
    pool = eventlet.GreenPool(1000)
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


