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

import argparse
import logging
import socket
import subprocess
import sys

##################### CONFIGURATION ##########################
DEFAULT_CONF='~/.weenotifrc'
##################### END CONFIGURATION ######################

def gotHighlight(message, nick, conf):
    if not 'action' in conf:
        highlightProcessCmd = 'echo'
    else:
        highlightProcessCmd = conf['action']
    subprocess.call([highlightProcessCmd, message, nick])

def getResponse(sock, conf):
    READ_AT_ONCE=4096
    sockBytes = sock.recv(READ_AT_ONCE)
    if not sockBytes:
        return False # Connection closed
    
    if(len(sockBytes) < 5):
        logger.warning("Packet shorter than 5 bytes received. Ignoring.")
        return True

    if sockBytes[4] != 0:
        logger.warning("Received compressed message. Ignoring.")
        return True
    
    mLen,_ = read_int(sockBytes)
    lastPacket = sockBytes
    while(len(sockBytes) < mLen):
        if(len(lastPacket) < READ_AT_ONCE):
            logger.warning("Incomplete packet received. Ignoring.")
            return True
        lastPacket = sock.recv(READ_AT_ONCE)
        sockBytes += lastPacket

    body = sockBytes[5:]
    ident,body = read_str(body)
    if ident != "_buffer_line_added":
        return True
    logger.debug("Received buffer line.")

    dataTyp,body = read_typ(body)
    if(dataTyp != "hda"):
        logger.warning("Unknown buffer_line_added format. Ignoring.")
        return True
    hdaData,body = read_hda(body)

    for hda in hdaData:
        print(hda)
        if hda['highlight'] > 0:
            msg=hda['message']
            nick=""
            for tag in hda['tags_array']:
                if tag.startswith('nick_'):
                    nick = tag[5:]
            gotHighlight(msg, nick, conf)
    return True

def readConfig(path):
    return dict() # TODO implement

def readCommandLine():
    parser = argparse.ArgumentParser(description="WeeChat client to get "+\
        "highlight notifications from a distant bouncer.")
    parser.add_argument('-c','--config')
    parser.add_argument('-s','--server')
    parser.add_argument('-p','--port')
    parser.add_argument('-a','--action')
    parser.add_argument('-v', action='store_true')
    parser.add_argument('--log-file')
    parsed = parser.parse_args()
    
    parsedTable = vars(parsed)
    if(parsed.config != None):
        parsedTable.update(readConfig(parsed.config))

    return parsedTable


def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',\
        datefmt='%I:%M:%S')

    conf = readCommandLine()
    if not('config' in conf):
        conf.update(readConfig(DEFAULT_CONF))
    
    if('v' in conf and conf['v']): # Verbose
        logging.basicConfig(level = logging.DEBUG)
    if('log-file' in conf):
        logging.basicConfig(filename=conf['log-file'])


    sock = socket.socket()
    sock.connect(("localhost", 6667))
    sock.sendall(b'init compression=off\n')
    sock.sendall(b'sync *\n')
    while getResponse(sock,conf):
        pass

if __name__=='__main__':
    main()
