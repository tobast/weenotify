#!/usr/bin/python3
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
import os
import shlex
import signal
import socket
import subprocess
import sys
import time

import packetRead

##################### CONFIGURATION ##########################
DEFAULT_CONF=(os.path.expanduser("~"))+'/.weenotifrc'
##################### END CONFIGURATION ######################

def expandPaths(path):
    return os.path.expanduser(path)

def safeCall(callArray):
    if(len(callArray) == 0):
        logging.error("Trying to call an unspecified external program.")
        return
    try:
        subprocess.call(shlex.split(callArray[0])+callArray[1:])
    except:
        logging.error("Could not execute "+callArray[0])

def gotHighlight(message, nick, conf):
    if not 'highlight-action' in conf or not conf['highlight-action']:
        return # No action defined: do nothing.

    highlightProcessCmd = expandPaths(conf['highlight-action'])
    safeCall([highlightProcessCmd, message, nick])

def gotPrivMsg(message, nick, conf):
    if not 'privmsg-action' in conf or not conf['privmsg-action']:
        return # No action defined: do nothing.

    privmsgProcessCmd = expandPaths(conf['privmsg-action'])
    safeCall([privmsgProcessCmd, message, nick])

def getResponse(sock, conf):
    READ_AT_ONCE=4096
    sockBytes = sock.recv(READ_AT_ONCE)
    if not sockBytes:
        return False # Connection closed
    
    if(len(sockBytes) < 5):
        logging.warning("Packet shorter than 5 bytes received. Ignoring.")
        return True

    if sockBytes[4] != 0:
        logging.warning("Received compressed message. Ignoring.")
        return True
    
    mLen,_ = packetRead.read_int(sockBytes)
    lastPacket = sockBytes
    while(len(sockBytes) < mLen):
        if(len(lastPacket) < READ_AT_ONCE):
            logging.warning("Incomplete packet received. Ignoring.")
            return True
        lastPacket = sock.recv(READ_AT_ONCE)
        sockBytes += lastPacket

    body = sockBytes[5:]
    ident,body = packetRead.read_str(body)
    if ident != "_buffer_line_added":
        return True
    logging.debug("Received buffer line.")

    dataTyp,body = packetRead.read_typ(body)
    if(dataTyp != "hda"):
        logging.warning("Unknown buffer_line_added format. Ignoring.")
        return True
    hdaData,body = packetRead.read_hda(body)

    for hda in hdaData:
        msg=hda['message']
        nick=""
        for tag in hda['tags_array']:
            if tag.startswith('nick_'):
                nick = tag[5:]

        if hda['highlight'] > 0:
            gotHighlight(msg, nick, conf)
            continue
        for tag in hda['tags_array']:
            if tag.startswith('notify_'):
                notifLevel = tag[7:]
                if notifLevel == 'private':
                    gotPrivMsg(msg, nick, conf)
                    break

    return True

CONFIG_ITEMS = [
    ('-c','config', 'Use the given configuration file.', DEFAULT_CONF),
    ('-s','server', 'Address of the Weechat relay.'),
    ('-p','port', 'Port of the Weechat relay.'),
    ('','ensure-background', 'Runs the following command in the background.'+\
        ' Periodically checks whether it is still open, reruns it if '+\
        'necessary, and resets the connection to the server if it was lost '+\
        'in the process. Mostly useful to establish a SSH tunnel.'),
    ('','reconnect-delay','Delay between two attempts to reconnect after '+\
        'being disconnected from the server.', '10'),
    ('-a','highlight-action', 'Program to invoke when highlighted.'),
    ('','privmsg-action', 'Program to invoke when receiving a private message.'),
    ('','log-file', 'Log file. If omitted, the logs will be directly printed.')
    ]
    
def readConfig(path, createIfAbsent=False):
    outDict = dict()
    try:
        with open(path,'r') as handle:
            confOpts = [ x[1] for x in CONFIG_ITEMS ]
            for line in handle:
                if '#' in line:
                    line = line[:line.index('#')].strip()
                if(line == ''):
                    continue

                if '=' in line:
                    eqPos = line.index('=')
                    attr = line[:eqPos].strip()
                    arg = line[eqPos+1:].strip()
                    if(attr in confOpts): # Valid option
                        outDict[attr] = arg
                    else:
                        logging.warning('Unknown option: '+attr+'.')
            handle.close()
    except FileNotFoundError:
        if(createIfAbsent):
            with open(path, 'x') as touchHandle:
                pass
        else:
            logging.error("The configuration file '"+path+"' does not exists.")
    except IOError:
        logging.error("Could not read the configuration file at '"+path+"'.")
    return outDict

def readCommandLine():
    parser = argparse.ArgumentParser(description="WeeChat client to get "+\
        "highlight notifications from a distant bouncer.")
    parser.add_argument('-v', action='store_true')
    for cfgItem in CONFIG_ITEMS:
        shortOpt,longOpt,helpMsg,dft = cfgItem[0],cfgItem[1],cfgItem[2],None
        if len(cfgItem) >= 4:
            dft = cfgItem[3]
        if shortOpt == '':
            parser.add_argument('--'+longOpt, dest=longOpt, help=helpMsg,\
                default=dft)
        else:
            parser.add_argument(shortOpt, '--'+longOpt, dest=longOpt,\
                help=helpMsg, default=dft)
    parsed = parser.parse_args()
    
    parsedTable = vars(parsed)
    if(parsed.config != None):
        parsedTable.update(readConfig(parsed.config))

    return parsedTable

def sigint(sig, frame):
    logging.info("Stopped.")
    exit(0)

def ensureBackgroundCheckRun(proc,conf):
    """ Runs (or re-runs if it has terminated) the 'ensure-background'
        option command-line if it was specified. """
    if not 'ensure-background' in conf or not conf['ensure-background']:
        return

    if proc == None or proc.poll() != None: # Not started or terminated
        if proc != None: # Proc has died.
            logging.warning("Background process has died.")
        logging.info("Starting background process...")
        proc = subprocess.Popen(shlex.split(conf['ensure-background']))
        time.sleep(0.5) # Wait a little to let it settle.
    return proc

def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',\
        datefmt='%H:%M:%S')

    conf = readCommandLine()
    conf.update(readConfig(conf['config'],True))
    #TODO command line prevails
    
    logging.getLogger().setLevel(logging.INFO)
    if('log-file' in conf):
        logging.basicConfig(filename=conf['log-file'])
    if('v' in conf and conf['v']): # Verbose
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("Verbose mode.")

    if not 'server' in conf or not conf['server'] or\
            not 'port' in conf or not conf['port']:
        print("Missing argument(s): server address and/or port.")
        exit(1)

    signal.signal(signal.SIGINT, sigint)

    bgProcess = None

    logging.info("Entering main loop.")
    while True:
        try:
            bgProcess = ensureBackgroundCheckRun(bgProcess, conf)
            sock = socket.socket()
            logging.info("Connecting to "+conf['server']+":"+conf['port']+"...")
            sock.connect((conf['server'], int(conf['port'])))
            logging.info("Connected")
            sock.sendall(b'init compression=off\n')
            sock.sendall(b'sync *\n')

            while getResponse(sock,conf):
                bgProcess = ensureBackgroundCheckRun(bgProcess, conf)
            logging.warning("Connection lost. Retrying...")
        except ConnectionRefusedError:
            logging.error("Connection refused. Retrying...")
        except socket.error as exn:
            logging.error("Connection error: %s. Retrying..." % exn)
        time.sleep(conf['reconnect-delay'])

if __name__=='__main__':
    main()
