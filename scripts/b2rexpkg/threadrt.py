from threading import Thread, Timer
from .tools.jsonsocket import JsonSocket

try:
    from queue import Queue
except:
    from Queue import Queue

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
    def __init__ (self, context, server_url, username, password, firstline):
        Thread.__init__(self)
        self.server_url = server_url
        self.username = username
        self.password = password
        self.firstline = firstline
        self.ctx = context.region
        self.screen = context.screen
        self.in_queue = Queue()
        self.out_queue = Queue()
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
        self.out_queue.put(cmd)
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
        if self.running:
            self.running = False
            self.connected = False
            self.receiver = None
            self.socket.close()
            self.socket = JsonSocket()
            # start reconnecting
            self.check_timer = Timer(0.5, self.check_connection)
            self.check_timer.start()

    def check_connection(self):
        print("check connection")
        # try connecting every 2 seconds
        if time.time() - self.starttime > 2 and not self.running:
            try:
                self.socket.connect(("localhost", 11112))
                self.receiver = ClientThread(self)
                self.running = True
                self.connected = True
                self.receiver.start()
                self.redraw()
                print("connected!!", self.server_url, self.username)
                self.addCmd(["connect", self.server_url, self.username,
                                self.password, self.firstline])
                return
            except socket.error as e:
                if e.errno == 111:
                    pass
                if not e.errno in [111, 103]:
                    traceback.print_exc()
                self.starttime = self.starttime + 2
                self.running = False
                self.connected = False
        # otherwise blink every 0.5 seconds
        if self.running == False and time.time() - self.blinkstart > 1:
            self.connected = not self.connected
            self.blinkstart = time.time()
            self.redraw()
        print("check connection later..")
        self.check_timer = Timer(1, self.check_connection)
        self.check_timer.start()

    def run(self):
        self.running = False
        self.alive = True
        self.socket = JsonSocket()
        self.receiver = None
        started = False
        self.starttime = time.time()-2
        self.blinkstart = time.time()
        self.check_timer = Timer(0.5, self.check_connection)
        self.check_timer.start()
        while self.alive:
            found = False
            # msg queue
            if self.running:
                print("get cmd")
                cmd = self.out_queue.get()
                print("send",cmd)
                if cmd[0] == "quit":
                    self.socket.send(cmd)
                    self.socket.close()
                    break
                try:
                    self.socket.send(cmd)
                except socket.error as e:
                    if e.errno == 32: # broken pipe
                        self.disconnected()
            else:
                time.sleep(0.4)
        # clean up the thread
        if self.running:
            self.running = False
            self.receiver.join(0.4)
            self.socket.close()
            self.connected = False
            self.redraw()
        print("exit thread")


def run_thread(context, server_url, username, password, firstline):
    running = ProxyAgent(context, server_url, username, password, firstline)
    running.start()
    return running


