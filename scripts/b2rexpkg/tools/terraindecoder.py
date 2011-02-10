import sys
import os
import math
import struct
import traceback

class BitReader(object):
    _num_bits_in_elem = 8
    def __init__(self, data):
        self._bit_ofs = 0
        self._elem_ofs = 0
        self._data = data
        self.len = len(data)*8
        self.pos = 0
    def ReadBits(self, count):
        data = [0,0,0,0]
        cur_byte = 0
        cur_bit = 0
        total_bits = min(self._num_bits_in_elem, count)
        while count > 0:
            count -= 1
            bit = self.ReadBit()
            if bit:
                newval = data[cur_byte] | (1 << (total_bits - 1 - cur_bit))
                data[cur_byte] = newval
            cur_bit += 1
            if cur_bit >= self._num_bits_in_elem:
                cur_byte += 1
                cur_bit = 0
                total_bits = min(self._num_bits_in_elem, count)
        return struct.pack("<BBBB", *data)
    def read(self, instructions):
        if instructions in ["bool"]:
            return self.ReadBit()
        datatype, nbits = instructions.split(":")
        if datatype in ["uintle", "uint"]:
            return struct.unpack("<I", self.ReadBits(int(nbits)))[0]
        if datatype in ["floatle", "float"]:
            return struct.unpack("<f", self.ReadBits(32))[0]
    def BitsLeft(self):
        return self.len - self.pos
    def ReadBit(self):
        if self.BitsLeft() == 0:
            raise Exception("Out of bits!")
        bit = struct.unpack("<B", self._data[self._elem_ofs:self._elem_ofs+1])[0] & (1 << (self._num_bits_in_elem - 1 - self._bit_ofs)) != 0
        self._bit_ofs += 1
        if self._bit_ofs >= self._num_bits_in_elem:
            self._bit_ofs = 0
            self._elem_ofs += 1
        self.pos = self._bit_ofs + (self._elem_ofs*8)
        return bit

cEndOfPatches = 97;
OO_SQRT2 = 0.7071067811865475244008443621049
class IDCTPrecomputationTables(object):
    def __init__(self, size):
        self.buildDequantizeTable(size)
        self.buildQuantizeTable(size)
        self.setupCosines(size)
        self.buildCopyMatrix(size)
    def buildDequantizeTable(self, size):
        self.dequantizeTable = []
        for j in range(size):
            for i in range(size):
                self.dequantizeTable.append(1.0 + (2.0 * float(i+j)))
    def buildQuantizeTable(self, size):
        self.quantizeTable = []
        for j in range(size):
            for i in range(size):
                self.quantizeTable.append(1.0 / (1.0 + (2.0 * float(i+j))))
    def setupCosines(self, size):
        hposz = (math.pi * 0.5) / float(size)
        self.cosineTable = []
        for u in range(size):
            for n in range(size):
                self.cosineTable.append(math.cos((2.0*float(n+1)) * (u*hposz)))
    def buildCopyMatrix(self, size):
        self.copyMatrix = list(range(size*size))
        diag = False
        right = True
        i = 0
        j = 0
        count = 0
        while i < size and j < size:
            self.copyMatrix[j * size + i] = count
            count += 1
            if not diag:
                if right:
                    if i < size-1:
                        i+=1
                    else:
                        j+=1
                    right = False
                    diag = True
                else:
                    if j < size-1:
                        j+=1
                    else:
                        i+=1
                    right = True
                    diag = True
            else:
                if right:
                    i+=1
                    j-=1
                    if i == size-1 or j == 0:
                        diag = False
                else:
                    i-=1
                    j+=1
                    if j == size-1 or i == 0:
                        diag = False

precompTables = IDCTPrecomputationTables(16)

class PatchHeader(object):
    def __init__(self, patchSize, data=None):
        self.patchSize = patchSize
        if data:
            self.decode(data)
    def decode(self, data):
        self.quantWBits = data.read("uintle:8")
        if self.quantWBits == cEndOfPatches:
            return
        self.dcOffset = data.read("floatle:32")
        self.range = data.read("uintle:16")

        patchIDs = data.read("uint:10")
        self.x = patchIDs >> 5
        self.y = patchIDs & 31
        self.wordBits = (self.quantWBits & 0x0f) + 2

class TerrainDecoder(object):
    def __init__(self, data, stride=None, patchSize=None):
        self.patches = []
        if not stride and not patchSize:
            stride = struct.unpack("<H", data[0:2])[0]
            patchSize = struct.unpack("<B", data[2:3])[0]
            layerType = struct.unpack("<B", data[3:4])[0]
            data = data[4:]
        self.decompressLand(data, stride, patchSize, layerType)

    @staticmethod
    def decode(data, stride=None, patchSize=None):
        decoder = TerrainDecoder(data, stride, patchSize)
        return decoder.getPatches()

    def getPatches(self):
        return self.patches

    def decodeTerrainPatch(self, header, data, size):
        patchdata = list(range(size*size))
        for i in range(size*size):
            if data.len - data.pos <= 0:
                while i < size*size:
                    patchdata[i] = 0
                    i+=1
                return patchdata

            if not data.ReadBit():
                patchdata[i] = 0
                continue

            if not data.ReadBit():
                while i < size*size:
                    patchdata[i] = 0
                    i+=1
                return patchdata
            signNegative = data.ReadBit()
            dataval = data.read("uint:"+str(header.wordBits))
            if signNegative:
                patchdata[i] = -dataval
            else:
                patchdata[i] = dataval
        return patchdata

    def decompressTerrainPatch(self, header, data):
        prequant = (header.quantWBits >> 4) +2
        quantize = 1 << prequant
        ooq = 1.0 / float(quantize)
        mult = ooq * float(header.range)
        addval = mult * float(1<<(prequant-1)) + header.dcOffset

        block = []
        if not header.patchSize == 16:
            print("TerrainDecoder:DecompressTerrainPatch: Unsupported patch size   present!")
        for n in range(16*16):
            idx = precompTables.copyMatrix[n]
            num = data[idx]
            val = num * precompTables.dequantizeTable[n]
            block.append(val)
        tempblock = list(range(16*16))
        for o in range(16):
            col = self.IDCTColumn16(block, tempblock, o)
        for o in range(16):
            line = self.IDCTLine16(tempblock, block, o)
        output = []
        for j in range(len(block)):
            output.append((block[j] * mult) + addval)
        return output

    def IDCTColumn16(self, linein, lineout, column):
        total = 0.0
        cStride = 16
        for n in range(16):
            total = OO_SQRT2 * linein[column]
            for u in range(1,16):
                total += linein[u*cStride + column] * precompTables.cosineTable[u*cStride + n]
            lineout[16 * n + column] = total

    def IDCTLine16(self, linein, lineout, line):
        oosob = 2.0 / 16.0
        lineSize = line * 16
        total = 0.0
        for n in range(16):
            total = OO_SQRT2 * linein[lineSize]
            for u in range(1, 16):
                total += linein[lineSize + u] * precompTables.cosineTable[u *16 +  n]
            lineout[lineSize+n] = total*oosob

    def decompressLand(self, rawdata, stride, patchSize, layerType):
        data = BitReader(rawdata)
        iter = 0
        while data.BitsLeft() > 0:
            try:
                header = PatchHeader(patchSize, data)
            except:
                traceback.print_exc()
                print("LAND:DecompressLand: Invalid header data!",
                        data.BitsLeft(), layerType, patchSize, stride, iter)
                return
            if header.quantWBits == cEndOfPatches:
                #print("LAND OK", len(self.patches))
                return
            cPatchesPerEdge = 16 # patchSize ?
            if header.x >= cPatchesPerEdge or header.y >= cPatchesPerEdge:
                print("LAND:DecompressLand: Invalid patch data!",
                      data.BitsLeft(), layerType, iter)
                return
            patch = self.decodeTerrainPatch(header, data, patchSize)
            patch = self.decompressTerrainPatch(header, patch)
            self.patches.append([header, patch])
            iter += 1


def checkbitreader():
    a = b''
    x1 = 10
    x2 = 245
    x3 = 666.0
    a = struct.pack("<f",x1)
    a += struct.pack("<f",x2)
    a += struct.pack("<f",x3)
    a += struct.pack("<I",20)
    a += struct.pack("<H",10)
    a += struct.pack("<B",255)
    a += struct.pack("<B",0)
    bits = BitReader(a)
    assert(bits.read("float:32") == x1)
    assert(bits.read("float:32") == x2)
    assert(bits.read("float:32") == x3)
    assert(bits.read("uint:32") == 20)
    assert(bits.read("uint:16") == 10)
    for i in range(8):
        assert(bits.read("bool") == True)
    for i in range(8):
        assert(bits.read("bool") == False)
    assert(bits.len == 32*4+16+16)
    assert(bits.pos == bits.len)

def drawlayer(layerdata, n, im):
    maxfound = 0
    header = layerdata[0]
    off_x = (header.y)*16
    off_y = (header.x)*16
    for j in range(16):
        for i in range(16):
            val = layerdata[1][(i*16)+j]
            if val > maxfound:
                maxfound = val
            val = ((val + 10.0)/40.0)*255
            val = int(min(max(0, val), 255))
            im.putpixel((i+(off_x), j+(off_y)), val)
    return maxfound
try:
    from PIL import Image
except:
    pass
if __name__ == "__main__":
    b = os.path.dirname
    scriptdir = os.path.realpath(__file__)
    checkbitreader()
    layerfolder = os.path.join(b(b(b(b(scriptdir)))), "test", "layers")
    totalblocks = 0
    im = Image.new("L", (16*16, 16*16))
    for layer_file in os.listdir(layerfolder):
        #if not layer_file == "0.layer":
            #        continue
        print("DECODING", layer_file)
        f = open(os.path.join(layerfolder, layer_file), "rb")
        data = f.read()
        f.close()
        res = TerrainDecoder.decode(data)
        print("RESULT", len(res))
        for layer in res:
            totalblocks += 1
            print("MAXFOUND",drawlayer(layer, totalblocks, im))
    im.save("/tmp/terrain/all.png")
    print("TOTAL", totalblocks)
