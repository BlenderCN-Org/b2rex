import struct

class KristalliData(object):
    def __init__(self, data):
        self._data = data
        self._idx = 0
        self._dyn_matrix = {}
        self._dyn_matrix[8] = self.get_u8
        self._dyn_matrix[16] = self.get_u16
        self._dyn_matrix[32] = self.get_u32

    def get_u8(self):
        val = struct.unpack('<B', self._data[self._idx:self._idx+1])[0]
        self._idx += 1
        return val

    def get_u16(self):
        val = struct.unpack('<H', self._data[self._idx:self._idx+2])[0]
        self._idx += 2
        return val

    def get_u32(self):
        val = struct.unpack('<I', self._data[self._idx:self._idx+4])[0]
        self._idx += 4
        return val

    def get_s8(self):
        val = self._data[self._idx]
        self._idx += 1
        return val

    def get_dyn_s8(self, dynamic_count):
        count = self.get_dynamic_count(dynamic_count)
        val = self._data[self._idx:self._idx+count]
        self._idx += count
        return val

    def get_dyn_u8(self, dynamic_count):
        count = self.get_dynamic_count(dynamic_count)
        val = struct.unpack('<'+'B'*count, self._data[self._idx:self._idx+count])
        self._idx += count
        return val

    def get_dynamic_count(self, dynamic_count):
        return self._dyn_matrix[dynamic_count]()
