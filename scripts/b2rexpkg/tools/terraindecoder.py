import os
import math
import struct
import traceback

from bitstring import ConstBitStream

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
    def __init__(self, data, patchSize, rawdata):
        self.patchSize = patchSize
        self.decode(data, rawdata)
    def decode(self, data, rawdata):
        self.quantWBits = data.read("uintle:8")
        if self.quantWBits == cEndOfPatches:
            return
        self.dcOffset = data.read("floatle:32")
        self.range = data.read("uint:16")
        patchIDs = data.read("uint:10")
        #patchIDs = struct.unpack("<H", struct.pack(">H", patchIDs))[0]
        x = patchIDs >> 5
        y = patchIDs & 31
        self.wordBits = (self.quantWBits & 0x0f) + 2
        print("Block", self.dcOffset, self.range, "x", x,
              "y", y, self.wordBits, data.pos)
        assert(x < self.patchSize)
        assert(y < self.patchSize)
        self.x = x
        self.y = y

class TerrainDecoder(object):
    def __init__(self, data, stride=None, patchSize=None):
        self.patches = []
        if not stride and not patchSize:
            stride = struct.unpack("<H", data[0:2])[0]
            patchSize = struct.unpack("<B", data[2])[0]
            layerType = struct.unpack("<B", data[3])[0]
            data = data[4:]
            print("stride",stride,"patchSize" ,patchSize,"layerType", layerType,
                 len(data), len(data)*8)
        self.decompressLand(data, stride, patchSize)
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
                print("out of bits when decoding terrain vertex", i, bitsleft)
                while i < size*size:
                    patchdata[i] = 0
                    i+=1
                return patchdata
            v = data.read("bool")
            if not v:
                patchdata[i] = 0
                continue
            v = data.read("bool")
            if not v:
                while i < size*size:
                    patchdata[i] = 0
                    i+=1
                return patchdata
            signNegative = data.read("bool")
            dataval = data.read("uint:"+str(header.wordBits))
            if signNegative:
                patchdata[i] = -dataval
            else:
                patchdata[i] = dataval
            i += 1
        return patchdata
    def decompressTerrainPatch(self, header, data):
        prequant = (header.quantWBits >> 4) +2
        quantize = 1 << prequant
        ooq = 1.0 / float(quantize)
        mult = ooq * float(header.range)
        addval = mult * float(1<<(prequant-1)) + header.dcOffset
        print("mult",mult,"addval",addval,"prequant",prequant,ooq,quantize)
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
            for u in range(0, 16):
                total += linein[lineSize + u] * precompTables.cosineTable[u *16 +  n]
            lineout[lineSize+n] = total*oosob

    def decompressLand(self, rawdata, stride, patchSize):
        #data = dec2bin(rawdata)
        data = ConstBitStream(bytes=rawdata, length=len(rawdata)*8)
        while data.pos < len(data):
            try:
                header = self.decodePatchHeader(data, patchSize, rawdata)
            except:
                print("TerrainDecoder:DecompressLand: Invalid header data!",
                        data.pos)
                traceback.print_exc()
                return
            if header.quantWBits == cEndOfPatches:
                print("LAND OK", len(self.patches), patchSize, stride)
                return
            cPatchesPerEdge = 16 # patchSize ?
            if header.x >= cPatchesPerEdge or header.y >= cPatchesPerEdge:
                print("TerrainDecoder:DecompressLand: Invalid patch data!",
                      data.pos)
                return
            patch = self.decodeTerrainPatch(header, data, patchSize)
            patch = self.decompressTerrainPatch(header, patch)
            self.patches.append([header, patch])
            print("next iter",data.pos)
    def decodePatchHeader(self, data, patchSize, rawdata):
        header = PatchHeader(data, patchSize, rawdata)
        return header


if __name__ == "__main__":
    b = os.path.dirname
    scriptdir = os.path.realpath(__file__)
    layerfolder = os.path.join(b(b(b(b(scriptdir)))), "test", "layers")
    for layer_file in os.listdir(layerfolder):
        #if not layer_file == "1.layer":
            #    continue
        print("DECODING", layer_file)
        f = open(os.path.join(layerfolder, layer_file), "rb")
        data = f.read()
        f.close()
        res = TerrainDecoder.decode(data)
        #print("RESULT",len(res))
