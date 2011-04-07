import struct

class KristalliData(object):
    def __init__(self, data):
        self._data = data
        self._idx = 0
        self._dyn_matrix = {}
        self._dyn_matrix[8] = self.get_u8
        self._dyn_matrix[16] = self.get_u16
        self._dyn_matrix[32] = self.get_u32

    def fill(self, size):
        remaining = size - (len(self._data) - self._idx)
        if remaining >= 0:
            self._data += b'\0'*remaining

    @staticmethod
    def encode_ve16(num):
        if num < 128:
            return struct.pack("<B", num)
        elif num < 16384:
            c = (num & 127) | 128
            b = num>>7
            encoded = struct.pack("<B", c) + struct.pack("<B", b)
            return encoded
        else:
            # XXX TODO
            print("KristalliData:encode_ve16:unimplemented_path")
            encoded = struct.pack("<I", num)
            return encoded

    def get_u8(self):
        val = struct.unpack('<B', self._data[self._idx:self._idx+1])[0]
        self._idx += 1
        return val

    def get_float(self):
        val = struct.unpack('<f', self._data[self._idx:self._idx+4])[0]
        self._idx += 4
        return val

    def get_u16(self):
        val = struct.unpack('<H', self._data[self._idx:self._idx+2])[0]
        self._idx += 2
        return val

    def get_u32(self):
        val = struct.unpack('<I', self._data[self._idx:self._idx+4])[0]
        self._idx += 4
        return val

    def get_s32(self):
        val = struct.unpack('<i', self._data[self._idx:self._idx+4])[0]
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
        return self.get_dyn_s8(dynamic_count)
        count = self.get_dynamic_count(dynamic_count)
        val = struct.unpack('<'+'B'*count, self._data[self._idx:self._idx+count])
        self._idx += count
        return val

    def get_dynamic_count(self, dynamic_count):
        return self._dyn_matrix[dynamic_count]()

    # tundra specific
    def get_transform(self):
        val = struct.unpack("<fffffffff", self._data[self._idx:self._idx+36])
        self._idx += 36
        return val

    def get_vector4(self):
        val = struct.unpack("<ffff", self._data[self._idx:self._idx+16])
        self._idx += 16
        return val

    def get_vector3(self):
        val = struct.unpack("<fff", self._data[self._idx:self._idx+12])
        self._idx += 12
        return val

    def get_string_list(self, list_count, dynamic_count):
        string_list = []
        nelements = self.get_dynamic_count(list_count)
        for idx in range(nelements):
            string_list.append(self.get_string(dynamic_count))
        return string_list

    def get_string(self, dynamic_count):
        count = self.get_dynamic_count(dynamic_count)
        end = self._data.find(b'\0', self._idx)
        if not end == -1:
           end = min(end+1, self._idx+count)
        val = self._data[self._idx:end]
        self._idx = end
        return val.strip(b'\0')

    def get_bool(self):
        return bool(self.get_u8())


