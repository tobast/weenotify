"""
    WeeNotify

    A minimalist Weechat client using the Weechat relay protocol to
    retrieve notifications from a bouncer and display them locally.

    ---
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import zlib


class PacketData:
    '''  Handles the data from a relay packet and allows easy reading '''
    def __init__(self, data):
        self.data = data


    def __len__(self):
        return len(self.data)


    def append(self, data):
        ''' Appends `data` to the data already contained in the packet '''
        self.data += more


    def decompress(self):
        self.data = zlib.decompress(self.data)


    def __extract__(self, size):
        ''' Extracts the first `size` bytes of `self.data` and trucates
        `self.data` accordingly. '''
        out = self.data[:size]
        self.data = self.data[size:]
        return out


    def read_int(self):
        ''' Extracts an integer '''
        return int.from_bytes(self.__extract__(4), byteorder='big')


    def read_str(self):
        ''' Extracts a string '''
        strLen = self.read_int()
        return self.__extract__(strLen).decode('utf-8')
        # FIXME ^ what about errors?


    def read_ptr(self):
        ''' Extracts a pointer '''
        ptrLen = self.__extract__(1)
        ptrData = self.__extract__(ptrLen)
        return int(ptrData.decode('utf-8'), 16)


    def read_tim(self):
        ''' Extracts a timestamp '''
        timLen = self.__extract__(0)
        strTim = self.__extract__(timLen).decode('utf-8')
        return int(strTim)


    def read_chr(self):
        ''' Extracts a char '''
        return self.__extract__(1)


    def read_typ(self):
        ''' Extracts a type '''
        return self.__extract__(3).decode('utf-8')


    def read_arr(self):
        ''' Extracts an array '''
        elemType = self.read_typ()
        readFct = self.READ_FUNCTIONS[elemType]
        nbElem = self.read_int()
        out = []
        for i in range(nbElem):
            elt = readFct()
            out.append(elt)
        return out


    def read_hda(self):
        ''' Extracts some hda data '''
        def buildKeysArray(keys):
            out = []
            for pair in keys.split(','):
                pSplit = pair.split(':')
                out.append((pSplit[0], READ_FUNCTIONS[pSplit[1]]))
            return out
        hpath = self.read_str()
        hpathSplit = hpath.split('/')
        keys = self.read_str()
        keysArray = buildKeysArray(keys)
        count = self.read_int()
        out = []
        for dataSet in range(count):
            curSet = dict()
            path = []
            for k in range(len(hpathSplit)):
                ptr = self.read_ptr()
                path.append(ptr)
            curSet['__path'] = path
            for pair in keysArray:
                curSet[pair[0]], data = pair[1](data)
            out.append(curSet)
        return out

    READ_FUNCTIONS = {
        'int': read_int,
        'str': read_str,
        'ptr': read_ptr,
        'tim': read_tim,
        'chr': read_chr,
        'typ': read_typ,
        'arr': read_arr,
        'hda': read_hda,
    }
