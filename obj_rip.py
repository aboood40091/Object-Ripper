#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Object Ripper
# Version v1.0
# Copyright © 2017 AboodXD

# Code shamelessly stolen from Puzzle
# Thanks, RoadrunnerWMC and Tempus!

"""obj_rip.py: Rip objects from a Tileset."""

import json, os, platform, struct, sys

from PyQt5 import QtCore, QtGui, QtWidgets
Qt = QtCore.Qt

import SARC
if platform.system() == 'Windows':
    import gtx_extract as gtx

tile_name = ''

Tileset = None

curr_path = os.path.dirname(os.path.realpath(sys.argv[0])).replace("\\", "/")

class TilesetClass():
    '''Contains Tileset data. Inits itself to a blank tileset.
    Methods: addTile, removeTile, addObject, removeObject, clear'''

    class Tile():
        def __init__(self, image, nml, bytelist):
            '''Tile Constructor'''

            self.image = image
            self.normalmap = nml
            self.byte0 = bytelist[0]
            self.byte1 = bytelist[1]
            self.byte2 = bytelist[2]
            self.byte3 = bytelist[3]
            self.byte4 = bytelist[4]
            self.byte5 = bytelist[5]
            self.byte6 = bytelist[6]
            self.byte7 = bytelist[7]


    class Object():

        def __init__(self, height, width, randByte, uslope, lslope, tilelist):
            '''Tile Constructor'''

            self.height = height
            self.width = width

            self.randX = (randByte >> 4) & 1
            self.randY = (randByte >> 5) & 1
            self.randLen = randByte & 0xF

            self.upperslope = uslope
            self.lowerslope = lslope

            self.tiles = tilelist


        def getRandByte(self):
            """
            Builds the Randomization byte.
            """
            if (self.width, self.height) != (1, 1): return 0
            if self.randX + self.randY == 0: return 0
            byte = 0
            if self.randX: byte |= 16
            if self.randY: byte |= 32
            return byte | (self.randLen & 0xF)


    def __init__(self):
        '''Constructor'''

        self.tiles = []
        self.objects = []

        self.slot = 0


    def addTile(self, image, nml, bytelist = (0, 0, 0, 0, 0, 0, 0, 0)):
        '''Adds an tile class to the tile list with the passed image or parameters'''

        self.tiles.append(self.Tile(image, nml, bytelist))


    def addObject(self, height = 1, width = 1, randByte = 0, uslope = [0, 0], lslope = [0, 0], tilelist = [[(0, 0, 0)]]):
        '''Adds a new object'''

        global Tileset

        if tilelist == [[(0, 0, 0)]]:
            tilelist = [[(0, 0, Tileset.slot)]]

        self.objects.append(self.Object(height, width, randByte, uslope, lslope, tilelist))


    def removeObject(self, index):
        '''Removes an Object by Index number. Don't use this much, because we want objects to preserve their ID.'''

        self.objects.pop(index)


    def clear(self):
        '''Clears the tileset for a new file'''

        self.tiles = []
        self.objects = []


    def clearCollisions(self):
        '''Clears the collisions data'''

        for tile in self.tiles:
            tile.byte0 = 0
            tile.byte1 = 0
            tile.byte2 = 0
            tile.byte3 = 0
            tile.byte4 = 0
            tile.byte5 = 0
            tile.byte6 = 0
            tile.byte7 = 0

def ripObj(data):
    arc = SARC.SARC_Archive(data)

    Image = None
    NmlMap = None
    behaviourdata = None
    objstrings = None
    metadata = None

    for folder in arc.contents:
        if folder.name == 'BG_tex':
            for file in folder.contents:
                if file.name.endswith('_nml.gtx') and len(file.data) in (1421344, 4196384):
                    NmlMap = file.data
                elif file.name.endswith('.gtx') and len(file.data) in (1421344, 4196384):
                    Image = file.data
                        
        elif folder.name == 'BG_chk':
            for file in folder.contents:
                if file.name.startswith('d_bgchk_') and file.name.endswith('.bin'):
                    behaviourdata = file.data
        elif folder.name == 'BG_unt':
            for file in folder.contents:
                if file.name.endswith('_hd.bin'):
                    metadata = file.data
                elif file.name.endswith('.bin'):
                    objstrings = file.data


    if (Image == None) or (NmlMap == None) or (behaviourdata == None) or (objstrings == None) or (metadata == None):
        print('Not a valid tileset, sadly.')
        sys.exit(1)

    dest = LoadTexture_NSMBU(Image)
    destnml = LoadTexture_NSMBU(NmlMap)

    tileImage = QtGui.QPixmap.fromImage(dest)
    nmlImage = QtGui.QPixmap.fromImage(destnml)

    behaviours = []
    for entry in range(256):
        thisline = list(struct.unpack('>8B', behaviourdata[entry*8:entry*8+8]))
        behaviours.append(tuple(thisline))


    Xoffset = 2
    Yoffset = 2
    for i in range(256):
        Tileset.addTile(
            tileImage.copy(Xoffset,Yoffset,60,60),
            nmlImage.copy(Xoffset,Yoffset,60,60),
            behaviours[i])
        Xoffset += 64
        if Xoffset >= 2048:
            Xoffset = 2
            Yoffset += 64


    meta = []
    for i in range(len(metadata) // 6):
        meta.append(struct.unpack_from('>HBBxB', metadata, i * 6))

    tilelist = [[]]
    upperslope = [0, 0]
    lowerslope = [0, 0]
    byte = 0

    for entry in meta:
        offset = entry[0]
        byte = struct.unpack_from('>B', objstrings, offset)[0]
        row = 0

        while byte != 0xFF:

            if byte == 0xFE:
                tilelist.append([])

                if (upperslope[0] != 0) and (lowerslope[0] == 0):
                    upperslope[1] = upperslope[1] + 1

                if lowerslope[0] != 0:
                    lowerslope[1] = lowerslope[1] + 1

                offset += 1
                byte = struct.unpack_from('>B', objstrings, offset)[0]

            elif (byte & 0x80):

                if upperslope[0] == 0:
                    upperslope[0] = byte
                else:
                    lowerslope[0] = byte

                offset += 1
                byte = struct.unpack_from('>B', objstrings, offset)[0]

            else:
                tilelist[-1].append(struct.unpack_from('>3B', objstrings, offset))

                offset += 3
                byte = struct.unpack_from('>B', objstrings, offset)[0]

        tilelist.pop()

        if (upperslope[0] & 0x80) and (upperslope[0] & 0x2):
            for i in range(lowerslope[1]):
                pop = tilelist.pop()
                tilelist.insert(0, pop)

        Tileset.addObject(entry[2], entry[1], entry[3], upperslope, lowerslope, tilelist)

        tilelist = [[]]
        upperslope = [0, 0]
        lowerslope = [0, 0]

    Tileset.slot = Tileset.objects[0].tiles[0][0][2] & 3

    for object in Tileset.objects:
        object.jsonData = {}

    count = 0
    for object in Tileset.objects:
        tex = QtGui.QPixmap(object.width * 60, object.height * 60)
        tex.fill(Qt.transparent)
        painter = QtGui.QPainter(tex)

        Xoffset = 0
        Yoffset = 0

        Tilebuffer = b''

        for i in range(len(object.tiles)):
            for tile in object.tiles[i]:
                if (Tileset.slot == 0) or ((tile[2] & 3) != 0):
                    painter.drawPixmap(Xoffset, Yoffset, Tileset.tiles[tile[1]].image)
                Tilebuffer += (Tileset.tiles[tile[1]].byte0).to_bytes(1, 'big')
                Tilebuffer += (Tileset.tiles[tile[1]].byte1).to_bytes(1, 'big')
                Tilebuffer += (Tileset.tiles[tile[1]].byte2).to_bytes(1, 'big')
                Tilebuffer += (Tileset.tiles[tile[1]].byte3).to_bytes(1, 'big')
                Tilebuffer += (Tileset.tiles[tile[1]].byte4).to_bytes(1, 'big')
                Tilebuffer += (Tileset.tiles[tile[1]].byte5).to_bytes(1, 'big')
                Tilebuffer += (Tileset.tiles[tile[1]].byte6).to_bytes(1, 'big')
                Tilebuffer += (Tileset.tiles[tile[1]].byte7).to_bytes(1, 'big')
                Xoffset += 60
            Xoffset = 0
            Yoffset += 60

        painter.end()

        # Slopes
        if object.upperslope[0] != 0:

            # Reverse Slopes
            if object.upperslope[0] & 0x2:
                a = struct.pack('>B', object.upperslope[0])

                if object.height == 1:
                    iterationsA = 0
                    iterationsB = 1
                else:
                    iterationsA = object.upperslope[1]
                    iterationsB = object.lowerslope[1] + object.upperslope[1]

                for row in range(iterationsA, iterationsB):
                    for tile in object.tiles[row]:
                        a += struct.pack('>BBB', tile[0], tile[1], tile[2])
                    a += b'\xfe'

                if object.height > 1:
                    a += struct.pack('>B', object.lowerslope[0])

                    for row in range(0, object.upperslope[1]):
                        for tile in object.tiles[row]:
                            a += struct.pack('>BBB', tile[0], tile[1], tile[2])
                        a += b'\xfe'

                a += b'\xff'


            # Regular Slopes
            else:
                a = struct.pack('>B', object.upperslope[0])

                for row in range(0, object.upperslope[1]):
                    for tile in object.tiles[row]:
                        a += struct.pack('>BBB', tile[0], tile[1], tile[2])
                    a += b'\xfe'

                if object.height > 1:
                    a += struct.pack('>B', object.lowerslope[0])

                    for row in range(object.upperslope[1], object.height):
                        for tile in object.tiles[row]:
                            a += struct.pack('>BBB', tile[0], tile[1], tile[2])
                        a += b'\xfe'

                a += b'\xff'


        # Not slopes!
        else:
            a = b''

            for tilerow in object.tiles:
                for tile in tilerow:
                    a += struct.pack('>BBB', tile[0], tile[1], tile[2])

                a += b'\xfe'

            a += b'\xff'

        Objbuffer = a
        Metabuffer = struct.pack('>HBBxB', (0 if count == 0 else len(Objbuffer)), object.width, object.height, object.getRandByte())

        if not os.path.isdir(curr_path + "/" + tile_name):
            os.mkdir(curr_path + "/" + tile_name)

        tex.save(curr_path + "/" + tile_name + "/" + tile_name + "_object_" + str(count) + ".png", "PNG")

        object.jsonData['img'] = tile_name + "_object_" + str(count) + ".png"

        with open(curr_path + "/" + tile_name + "/" + tile_name + "_object_" + str(count) + ".colls", "wb+") as colls:
            colls.write(Tilebuffer)

        object.jsonData['colls'] = tile_name + "_object_" + str(count) + ".colls"

        with open(curr_path + "/" + tile_name + "/" + tile_name + "_object_" + str(count) + ".objlyt", "wb+") as objlyt:
            objlyt.write(Objbuffer)

        object.jsonData['objlyt'] = tile_name + "_object_" + str(count) + ".objlyt"

        with open(curr_path + "/" + tile_name + "/" + tile_name + "_object_" + str(count) + ".meta", "wb+") as meta:
            meta.write(Metabuffer)

        object.jsonData['meta'] = tile_name + "_object_" + str(count) + ".meta"

        count += 1

    count = 0
    for object in Tileset.objects:
        tex = QtGui.QPixmap(object.width * 60, object.height * 60)
        tex.fill(Qt.transparent)
        painter = QtGui.QPainter(tex)

        Xoffset = 0
        Yoffset = 0

        for i in range(len(object.tiles)):
            for tile in object.tiles[i]:
                if (Tileset.slot == 0) or ((tile[2] & 3) != 0):
                    painter.drawPixmap(Xoffset, Yoffset, Tileset.tiles[tile[1]].normalmap)
                Xoffset += 60
            Xoffset = 0
            Yoffset += 60

        painter.end()

        if not os.path.isdir(curr_path + "/" + tile_name):
            os.mkdir(curr_path + "/" + tile_name)

        tex.save(curr_path + "/" + tile_name + "/" + tile_name + "_object_" + str(count) + "_nml.png", "PNG")

        object.jsonData['nml'] = tile_name + "_object_" + str(count) + "_nml.png"

        count += 1

    count = 0
    for object in Tileset.objects:
        with open(curr_path + "/" + tile_name + "/" + tile_name + "_object_" + str(count) + ".json", 'w+') as outfile:
            json.dump(object.jsonData, outfile)

        count += 1

    if tile_name not in [None, '']:
        sys.exit(0)

def LoadTexture_NSMBU(tiledata):
    if platform.system() == 'Windows':
        tile_path = curr_path + '/Tools'
    elif platform.system() == 'Linux':
        tile_path = curr_path + '/linuxTools'
    elif platform.system() == 'Darwin':
        tile_path = curr_path + '/macTools'

    with open(tile_path + '/texture.gtx', 'wb') as binfile:
        binfile.write(tiledata)

    if platform.system() == 'Windows': # Dirty, but works :P
        data = gtx.readGFD(tiledata) # Read GTX

        if data.format == 0x1A: # for RGBA8, use gtx_extract
            os.chdir(curr_path + '/Tools')
            os.system('gtx_extract.exe texture.gtx texture.bmp')
            os.chdir(curr_path)

            # Return as a QImage
            img = QtGui.QImage(tile_path + '/texture.bmp')
            os.remove(tile_path + '/texture.bmp')

        elif data.format == 0x33: # for DXT5, use Abood's GTX Extractor
            # Convert to DDS
            hdr, data2 = gtx.get_deswizzled_data(data)
            with open(tile_path + '/texture2.dds', 'wb+') as output:
                output.write(hdr)
                output.write(data2)

            # Decompress DXT5
            os.chdir(curr_path + '/Tools')
            os.system('nvcompress.exe -rgb -nomips -alpha  texture2.dds texture.dds')
            os.chdir(curr_path)
            os.remove(tile_path + '/texture2.dds')

            # Read DDS, return as a QImage
            with open(tile_path + '/texture.dds', 'rb') as img:
                imgdata = img.read()[0x80:0x80+(data.dataSize*4)]
            img = QtGui.QImage(imgdata, data.width, data.height, QtGui.QImage.Format_ARGB32)
            os.remove(tile_path + '/texture.dds')

    elif platform.system() == 'Linux':
        os.chdir(curr_path + '/linuxTools')
        os.system('chmod +x ./gtx_extract.elf')
        os.system('./gtx_extract.elf texture.gtx texture.bmp')
        os.chdir(curr_path)

        # Return as a QImage
        img = QtGui.QImage(tile_path + '/texture.bmp')
        os.remove(tile_path + '/texture.bmp')

    elif platform.system() == 'Darwin':
        os.system('open -a "' + curr_path + '/macTools/gtx_extract" --args "' + curr_path + '/macTools/texture.gtx" "' + curr_path + '/macTools/texture.bmp"')

        # Return as a QImage
        img = QtGui.QImage(tile_path + '/texture.bmp')
        os.remove(tile_path + '/texture.bmp')

    else:
        print('Not a supported platform, sadly...')
        sys.exit(1)

    os.remove(tile_path + '/texture.gtx')

    return img

class main(QtWidgets.QMainWindow):
    def __init__(self, name, parent=None):
        super(main, self).__init__(parent)

        global Tileset, tile_name

        Tileset = TilesetClass()
        tile_name = os.path.basename(os.path.splitext(sys.argv[1])[0])

        if len(sys.argv) != 2:
            print("Usage: obj_rip tileset")
            sys.exit(1)

        with open(sys.argv[1], "rb") as inf:
            data = inf.read()

        if not data.startswith(b'SARC'):
            print('Not a valid tileset, sadly.')
            sys.exit(1)

        ripObj(data)

if __name__ == '__main__':

    app = QtWidgets.QApplication([sys.argv[0]])
    window = main(sys.argv[1])
    window.show()
    sys.exit(app.exec_())
    app.deleteLater()
