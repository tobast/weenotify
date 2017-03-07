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


def read_int(data):
    """ Reads an integer at the beginning of [data], returns a pair of
    this integer and the remaining data. """
    return (int.from_bytes(data[:4], byteorder='big'), data[4:])


def read_str(data):
    """ Reads a string at the beginning of [data], returns a pair of
    this string and the remaining data. """
    strLen, data = read_int(data)
    return (data[:strLen].decode('utf-8'), data[strLen:])


def read_ptr(data):
    ptrLen = data[0]
    ptrData = data[1:ptrLen+1]
    return int(ptrData.decode('utf-8'), 16), data[ptrLen+1:]


def read_tim(data):
    timLen = data[0]
    data = data[1:]
    strTim = data[:timLen].decode('utf-8')
    return (int(strTim), data[timLen:])


def read_chr(data):
    return (data[0], data[1:])


def read_typ(data):
    return (data[:3].decode('utf-8'), data[3:])


def read_arr(data):
    elemType, data = read_typ(data)
    readFct = READ_FUNCTIONS[elemType]
    nbElem, data = read_int(data)
    out = []
    for i in range(nbElem):
        elt, data = readFct(data)
        out.append(elt)
    return out, data


def read_hda(data):
    def buildKeysArray(keys):
        out = []
        for pair in keys.split(','):
            pSplit = pair.split(':')
            out.append((pSplit[0], READ_FUNCTIONS[pSplit[1]]))
        return out
    hpath, data = read_str(data)
    hpathSplit = hpath.split('/')
    keys, data = read_str(data)
    keysArray = buildKeysArray(keys)
    count, data = read_int(data)
    out = []
    for dataSet in range(count):
        curSet = dict()
        path = []
        for k in range(len(hpathSplit)):
            ptr, data = read_ptr(data)
            path.append(ptr)
        curSet['__path'] = path
        for pair in keysArray:
            curSet[pair[0]], data = pair[1](data)
        out.append(curSet)
    return out, data


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
