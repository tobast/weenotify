# -*- coding: utf-8 -*-
"""
Generic notifcation class.
Every notification should inherit from this class.
"""

from subprocess import call
from shlex import split
import logging

class Notification():
    """ Generic notification class. All kind of notification should inherit
    from this clas.
    """

    def __init__(self, command):
        self.command = split(command)

    def notify(self, callarray):
        """ Calls the __safeCall method to execute the notification"""
        if len(callarray) == 2:
            callarray.reverse()
            self.__safecall(callarray)
        if len(callarray) == 3:
            callarray = [callarray[2], callarray[1]+ "| " + callarray[0]]
            self.__safecall(callarray)

    def __safecall(self, callarray):
        """ Runs an external program, catching exceptions """
        if len(callarray) == 0:
            logging.error("Trying to call an unspecified external program.")
            return
        try:
            call(self.command + callarray)
        except:
            logging.error("[HL] Could not execute "+ " ".join(self.command))
