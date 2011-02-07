from threading import Thread
from .tools.jsonsocket import JsonSocket

import socket
import traceback
import time

class ClientThread(Thread):
    def __init__ (self, parent):
        Thread.__init__(self)
        self.parent = parent
    def run(self):
        while self.parent.alive:
            try:
                data = self.parent.socket.recv()
                self.parent.dataArrived(data)
                if not data:
                    self.parent.disconnected()
                    self.cleanup()
                    return
            except socket.timeout:
                pass
            except socket.error as e:
                if e.errno == 9:
                    self.cleanup()
                    return
        self.cleanup()
    def cleanup(self):
        print("exit client thread")
        self.parent = None

class ProxyAgent(Thread):
    def __init__ (self, context):
        Thread.__init__(self)
        self.ctx = context.region
        self.screen = context.screen
        self.connected = False
        self.socket = False
        self.queue = []
        self.cmds = []
        self.alive = False
    def dataArrived(self, data):
        self.queue.append(data)
        self.redraw()
    def addCmd(self, cmd):
        if cmd[0] == 'quit':
            self.alive = False
        else:
            self.cmds.append(cmd)
    def getQueue(self):
        queue = list(self.queue)
        self.queue = []
        return queue

    def apply_position(self, obj_uuid, pos, rot=0):
        if rot:
            cmd = ['pos', obj_uuid, [pos[0], pos[1], pos[2]], [rot[0], rot[1],
                                                           rot[2], rot[3]]]
        else:
            cmd = ['pos', obj_uuid, [pos[0], pos[1], pos[2]], 0]
        self.addCmd(cmd)

    def apply_scale(self, obj_uuid, scale):
        cmd = ['scale', obj_uuid, [scale[0], scale[1], scale[2]]]
        self.addCmd(cmd)

    def redraw(self):
        for area in self.screen.areas:
            if not area.type == 'VIEW_3D':
                area.tag_redraw()
    def disconnected(self):
        self.running = False
        self.connected = False
        self.receiver = None
        self.socket.close()
        self.socket = JsonSocket()
    def run(self):
        self.running = False
        self.alive = True
        self.socket = JsonSocket()
        self.receiver = None
        started = False
        starttime = time.time()-2
        blinkstart = time.time()
        while self.alive:
            time.sleep(0.04)
            found = False
            # msg queue
            if self.cmds and self.running:
                cmds = list(self.cmds)
                self.cmds = []
                for cmd in cmds:
                    self.socket.send(cmd)
            # try connecting every 2 seconds
            if time.time() - starttime > 2 and not self.running:
                try:
                    self.socket.connect(("localhost", 11112))
                    self.receiver = ClientThread(self)
                    self.running = True
                    self.connected = True
                    self.receiver.start()
                    self.socket.send(["ping"])
                except socket.error as e:
                    if e.errno == 111:
                        pass
                    if not e.errno in [111, 103]:
                        traceback.print_exc()
                    starttime = time.time()
                    self.running = False
                    self.connected = False
                self.redraw()
            # otherwise blink every 0.5 seconds
            if self.running == False and time.time() - blinkstart > 0.5:
                if self.connected:
                    self.connected = False
                else:
                    self.connected = True
                blinkstart = time.time()
                self.redraw()
        # clean up the thread
        if self.running:
            self.running = False
            self.receiver.join(0.4)
            self.socket.close()
            self.connected = False
            self.redraw()
        print("exit thread")


def run_thread(context, server_url, username, password, firstline):
    running = ProxyAgent(context)
    running.addCmd(["connect", server_url, username, password, firstline])
    running.start()
    return running


