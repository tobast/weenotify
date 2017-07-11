''' Reads a configuration file '''

import os
import argparse
import yaml


class MissingMandatoryOption(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Missing mandatory option '{}'".format(self.name)


class Configuration:
    ''' Reads command line arguments and a configuration file, and sticks the
    results together. '''

    __COMMAND_LINE_OPTS__ = [
        ('-c', 'config', 'Use the given configuration file.'),
        ('-s', 'server', 'Address of the Weechat relay.'),
        ('-p', 'port', 'Port of the Weechat relay.'),
        ('--compression', 'compression', 'Enable Weechat relay protocol data'
            'compression.'),
        ('', 'reconnect-delay', 'Delay between two attempts to reconnect '
                                'after being disconnected from the server.'),
        ('', 'log-file', 'Log file. If omitted, the logs will be directly '
                         'printed.'),
        ]

    __DEFAULT_VALUES__ = {
        'compression': True,
        'reconnect-delay': 10,
    }

    __DEFAULT_CONF__ = os.path.expanduser("~") + '/.weenotifyrc'

    __MANDATORY__ = ['server', 'port']

    def __init__(self):
        clArgs = self.__readCommandLine__()
        confPath = clArgs['config']
        if confPath is None:
            confPath = self.__DEFAULT_CONF__
        fileConf = self.__readFile__(confPath)

        # Command line prevails over conf file
        wholeConf = self.__cleanDict__(clArgs)
        for key in fileConf.keys():
            if fileConf[key] is not None and key not in wholeConf:
                wholeConf[key] = fileConf[key]
        self.conf = self.__cleanDict__(wholeConf)

        for mandatory in self.__MANDATORY__:
            if mandatory not in self.conf or not self.conf[mandatory]:
                raise MissingMandatoryOption(mandatory)

    def __cleanDict__(self, dic):
        out = {}
        for entry in dic:
            if dic[entry] is not None:
                out[entry] = dic[entry]
        return out

    def __readCommandLine__(self):
        parser = argparse.ArgumentParser(
            description="WeeChat client to get highlight notifications from a "
            "distant bouncer.")
        parser.add_argument('-v', action='store_true')
        for cfgItem in self.__COMMAND_LINE_OPTS__:
            shortOpt, longOpt, helpMsg = \
                cfgItem[0], cfgItem[1], cfgItem[2]

            if shortOpt == '':
                parser.add_argument('--'+longOpt, dest=longOpt, help=helpMsg)
            else:
                parser.add_argument(shortOpt, '--'+longOpt, dest=longOpt,
                                    help=helpMsg)
        parsed = parser.parse_args()
        parsedTable = vars(parsed)

        return parsedTable

    def __readFile__(self, path):
        conf = {}
        with open(path, 'r') as handle:
            content = handle.read()
            conf = yaml.load(content)
        return conf

    def isSet(self, prop):
        return prop in self.conf and self.conf[prop]

    @property
    def logfile(self):
        if 'log-file' not in self.conf or not self.conf['log-file']:
            return None
        return os.path.expanduser(self.conf['log-file'])

    def __getitem__(self, key):
        return self.conf.get(key, self.__DEFAULT_VALUES__.get(key))
