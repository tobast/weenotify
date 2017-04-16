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
import time
import threading
import zlib

import packetRead

''' ================= CONFIGURATION ========================== '''
DEFAULT_CONF = (os.path.expanduser("~"))+'/.weenotifyrc'
''' ================= END CONFIGURATION ====================== '''


def expandPaths(path):
    """ Expands user directories in a path """
    return os.path.expanduser(path)


def safeCall(callArray):
    """ Runs an external program, catching exceptions """
    if(len(callArray) == 0):
        logging.error("Trying to call an unspecified external program.")
        return
    try:
        subprocess.call(shlex.split(callArray[0])+callArray[1:])
    except:
        logging.error("Could not execute "+callArray[0])


class RelayClient(threading.Thread):
    def __init__(self, conf):
        threading.Thread.__init__(self)
        self.daemon = True  # Stop when the program terminates
        self.conf = conf
        self.sock = None
        self.packet_actions = {
            'ask_buffers': self.asked_buffers,
            '_buffer_line_added': self.buffer_line_added
        }
        self.buffers = {}

    def run(self):
        self.connect()
        while True:
            READ_AT_ONCE = 4096
            data = self.recv(READ_AT_ONCE)
            if len(data) < 5:
                logging.warning("Packet shorter than 5 bytes received. "
                                "Ignoring.")
                continue

            dataLen, _ = packetRead.read_int(data)
            lastPacket = data
            while len(data) < dataLen:
                if len(lastPacket) < READ_AT_ONCE:
                    logging.warning("Incomplete packet received. Ignoring.")
                    break
                lastPacket = self.recv(READ_AT_ONCE)
                data += lastPacket
            if len(data) < dataLen:
                continue
            self.process_packet(data)

    def process_packet(self, packet):
        if packet[4] == 0x01:
            body = zlib.decompress(packet[5:])
        elif packet[4] == 0x00:
            body = packet[5:]
        else:
            logging.warning("Unknown compression flag. Ignoring.")
            return
        ident, body = packetRead.read_str(body)
        if ident in self.packet_actions:
            self.packet_actions[ident](body)

    def connect(self):
        while True:
            try:
                self.sock = socket.socket()
                logging.info("Connecting to {}:{}...".format(
                    self.conf['server'], self.conf['port']))
                self.sock.connect((self.conf['server'],
                                   int(self.conf['port'])))
                logging.info("Connected")
                self.init_connection()
                return
            except ConnectionRefusedError:
                self.sock = None
                logging.error("Connection refused. Retrying...")
            except socket.error as exn:
                self.sock = None
                logging.error("Connection error: %s. Retrying..." % exn)
            time.sleep(float(self.conf['reconnect-delay']))

    def init_connection(self):
        password = self.conf.get('password', None)
        compression = self.conf.get('compression', 'off')
        if password is not None:
            self.sock.sendall(
                'init compression={},password={}\n'.format(compression, password)
                .encode('utf-8'))
        else:
            self.sock.sendall(b'init compression={}\n'.format(compression))
        self.sock.sendall(b'sync *\n')
        # Ask for name of buffers
        self.sock.sendall(b'(ask_buffers) hdata buffer:gui_buffers(*) name\n')

    def recv(self, n):
        while True:
            try:
                data = self.sock.recv(n)
                if data:
                    return data
                logging.warning("Connection lost. Retrying...")
            except socket.error as exn:
                logging.error("Connection error: %s. Retrying..." % exn)
            self.connect()

    def asked_buffers(self, body):
        data_type, body = packetRead.read_typ(body)
        if(data_type != "hda"):
            logging.warning("Unknown asked_buffers format. Ignoring.")
            return
        hdaData, _ = packetRead.read_hda(body)
        for hda in hdaData:
            self.buffers[hda['__path'][-1]] = hda['name']

    def buffer_line_added(self, body):
        data_type, body = packetRead.read_typ(body)
        if(data_type != "hda"):
            logging.warning("Unknown buffer_line_added format. Ignoring.")
            return
        hdaData, _ = packetRead.read_hda(body)
        for hda in hdaData:
            msg = hda['message']
            buffer = hda.get('buffer', 0)
            if buffer not in self.buffers:
                self.sock.sendall(
                    b'(ask_buffers) hdata buffer:gui_buffers(*) name\n')
                buffer_name = '<unknown>'
            else:
                buffer_name = self.buffers[buffer]

            nick = ""

            for tag in hda['tags_array']:
                if tag.startswith('nick_'):
                    nick = tag[5:]

            if hda['highlight'] > 0:
                self.gotHighlight(msg, nick, buffer_name)
                continue

            for tag in hda['tags_array']:
                if tag.startswith('notify_'):
                    notifLevel = tag[7:]
                    if notifLevel == 'private':
                        self.gotPrivMsg(msg, nick, buffer_name)
                        break

    def gotHighlight(self, message, nick, buffer_name):
        if not self.conf.get('highlight-action', None):
            return  # No action defined: do nothing.

        logging.debug("Notifying highlight message.")
        highlightProcessCmd = expandPaths(self.conf['highlight-action'])
        safeCall([highlightProcessCmd, message, nick, buffer_name])

    def gotPrivMsg(self, message, nick, buffer_name):
        if not self.conf.get('privmsg-action', None):
            return  # No action defined: do nothing.

        logging.debug("Notifying private message.")
        privmsgProcessCmd = expandPaths(self.conf['privmsg-action'])
        safeCall([privmsgProcessCmd, message, nick, buffer_name])


CONFIG_ITEMS = [
    ('-c', 'config', 'Use the given configuration file.', DEFAULT_CONF),
    ('-s', 'server', 'Address of the Weechat relay.'),
    ('-p', 'port', 'Port of the Weechat relay.'),
    ('--compression', 'compression', 'Enable Weechat relay protocol data'
        'compression.'),
    ('', 'ensure-background', 'Runs the following command in the background. '
        'Periodically checks whether it is still open, reruns it if '
        'necessary, and resets the connection to the server if it was lost '
        'in the process. Mostly useful to establish a SSH tunnel.'),
    ('', 'reconnect-delay', 'Delay between two attempts to reconnect after '
        'being disconnected from the server.', '10'),
    ('-a', 'highlight-action', 'Program to invoke when highlighted.'),
    ('', 'privmsg-action', 'Program to invoke when receiving a private '
        'message.'),
    ('', 'log-file', 'Log file. If omitted, the logs will be directly '
        'printed.'),
    ('', 'password', 'Relay password')
    ]


def readConfig(path, createIfAbsent=False):
    """ Reads the configuration file at `path`, returning a dictionnary
    containing the options found """

    outDict = dict()
    try:
        with open(path, 'r') as handle:
            confOpts = [x[1] for x in CONFIG_ITEMS]
            for line in handle:
                if '#' in line:
                    line = line[:line.index('#')].strip()
                if(line == ''):
                    continue

                if '=' in line:
                    eqPos = line.index('=')
                    attr = line[:eqPos].strip()
                    arg = line[eqPos+1:].strip()
                    if(attr in confOpts):  # Valid option
                        outDict[attr] = arg
                    else:
                        logging.warning('Unknown option: '+attr+'.')
            handle.close()
    except FileNotFoundError:
        if(createIfAbsent):
            try:
                open(path, 'x')
            except FileExistsError:
                pass  # That should not happen, but whatever.
            except OSError as exn:
                logging.error("Could not create {}: {}.".format(
                    path, exn))
        else:
            logging.error("The configuration file '"+path+"' does not exists.")
    except IOError:
        logging.error("Could not read the configuration file at '"+path+"'.")
    return outDict


def readCommandLine():
    parser = argparse.ArgumentParser(
        description="WeeChat client to get highlight notifications from a "
        "distant bouncer.")
    parser.add_argument('-v', action='store_true')
    for cfgItem in CONFIG_ITEMS:
        shortOpt, longOpt, helpMsg, dft = \
            cfgItem[0], cfgItem[1], cfgItem[2], None

        if len(cfgItem) >= 4:
            dft = cfgItem[3]
        if shortOpt == '':
            parser.add_argument('--'+longOpt, dest=longOpt, help=helpMsg,
                                default=dft)
        else:
            parser.add_argument(shortOpt, '--'+longOpt, dest=longOpt,
                                help=helpMsg, default=dft)
    parsed = parser.parse_args()

    parsedTable = vars(parsed)

    return parsedTable


def dictUnion(d1, d2):
    out = d1
    for key in d2.keys():
        if d2[key] is not None or key not in d1:
            out[key] = d2[key]
    return out


def ensureBackgroundCheckRun(proc, conf):
    """ Runs (or re-runs if it has terminated) the 'ensure-background'
        option command-line if it was specified. """
    if 'ensure-background' not in conf or not conf['ensure-background']:
        return

    if proc is None or proc.poll() is not None:  # Not started or terminated
        if proc is not None:  # Proc has died.
            logging.warning("Background process has died.")
        logging.info("Starting background process...")
        proc = subprocess.Popen(shlex.split(conf['ensure-background']))
        time.sleep(0.5)  # Wait a little to let it settle.
    return proc


def main():
    def sigint(sig, frame):
        if bgProcess is not None:
            bgProcess.terminate()
            logging.info("Terminated background process.")
        logging.info("Stopped.")
        exit(0)

    # command line prevails
    conf = readCommandLine()
    conf = dictUnion(readConfig(conf['config'], True), conf)

    if 'log-file' not in conf:
        conf['log-file'] = None
    if conf['log-file'] is not None:
        conf['log-file'] = expandPaths(conf['log-file'])
    if conf['log-file'] is not None and not os.path.isfile(conf['log-file']):
        try:
            touchHandle = open(conf['log-file'], 'x')
            touchHandle.close()
        except:
            print("ERROR: failed to create log file. Exiting.")
            exit(1)

    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%H:%M:%S', filename=conf['log-file'])

    logging.getLogger().setLevel(logging.INFO)
    if('v' in conf and conf['v']):  # Verbose
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("Verbose mode.")

    if 'server' not in conf or not conf['server'] or\
            'port' not in conf or not conf['port']:
        print("Missing argument(s): server address and/or port.")
        exit(1)

    signal.signal(signal.SIGINT, sigint)
    signal.signal(signal.SIGTERM, sigint)

    client = RelayClient(conf)
    bgProcess = ensureBackgroundCheckRun(None, conf)

    logging.info("Entering main loop.")
    client.start()
    while True:
        bgProcess = ensureBackgroundCheckRun(bgProcess, conf)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
