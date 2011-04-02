# Echo client program
import os
import socket
import struct
from .ksocket import KristalliSocket
from .template import MessageTemplateParser

class KristalliSession(object):
    def __init__(self, name):
        self.name = name.encode('utf-8')
        self._socket = KristalliSocket()
        self.templates = MessageTemplateParser()

    def connect(self, host, port):
        self._socket.connect((host, port))
        self.login()

    def login(self):
        self._socket.send(100, struct.pack('<H', len(self.name))+self.name)

    def loop(self):
        s = self._socket
        t = self.templates
        while True:
            data = s.recv()
            if data == '':
                break
            msgId, data = data
            if msgId == 1:
                val = data.get_u8()
                print " - Ping request", val
                s.send(2, data._data)
            elif msgId in t.templates:
                msg = t.parse(msgId, data)
                print(msg)
            else:
                if not os.path.exists("/tmp/"+str(msgId)+".txt"):
                    f = open("/tmp/"+str(msgId)+".txt", "w")
                    f.write(data._data)
                    f.close()
                print 'Received unknown', msgId, len(data._data)
        s.close()

if __name__ == "__main__":
    k = KristalliSession("caedes")
    k.templates.add_file('/home/caedes/SVN/REALXTEND/tundra/TundraLogicModule/TundraMessages.xml')
    k.connect('localhost', 2345)
    k.loop()

