"""
A simple socket wrapper that sends and receives json.

 s = JsonSocket()
 s.connect(('localhost', 11112))
 s.send({'foo':'bar', 'val': 2.4})

"""

import socket
import struct

from .data import KristalliData

class KristalliSocket(object):
    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
    def __getattr__(self, name):
        return getattr(self.sock, name)
    def __hasattr__(self, name):
        return hasattr(self.sock, name)
    def accept(self):
        sock, addr = self.sock.accept()
        return KristalliSocket(sock), addr
    def send(self, msgId, data):
        msg = struct.pack("<B", msgId) + data
        msg_len = len(msg)
        strlen = KristalliData.encode_ve16(msg_len)
        totalsent = 0
        totalmsg = strlen+msg
        totallen = len(totalmsg)
        while totalsent < totallen:
            sent = self.sock.send(totalmsg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent += sent
    def recv_byte(self):
        data = self.sock.recv(1)
        if len(data) < 1:
            return None
        return struct.unpack("<B", data)[0]

    def recv_half(self):
        data = self.sock.recv(2)
        if len(data) < 2:
            raise Exception("Not enough data!")
        return struct.unpack("<H", data)[0]

    def get_vle16(self):
        c = self.recv_byte()
        if c > 127:
            b = self.recv_byte()
            c = c & 127
            if b > 127:
                b = b & 127
                a = self.recv_half()
                return (a << 14) | (b << 7) | c, 4
            else:
                return (b << 7) | c, 2
        else:
            return c, 1
            
    def recv(self):
        datalen, datalen_size = self.get_vle16()
        msgID, msgID_size = self.get_vle16()
        """
        data = self.sock.recv(2)
        if len(data) < 2:
            return None
        if len(data) > 2:
            print("TOO MUCH DATA")

        datalen, msgID = struct.unpack("<BB", data)
        if datalen > 127:
            c = datalen & 127
            b = msgID
            if b > 127:
                print("MESSAGE TOO BIG!!")
            datalen = (b << 7) | c
        #raise RuntimeError("socket connection broken")
        """
        datalen = datalen-msgID_size
        msg = b''
        currlen = 0
        while currlen < datalen:
            msg += self.sock.recv(datalen-currlen)
            if len(msg) == currlen:
                return None
            currlen = len(msg)
        return msgID, KristalliData(msg)


