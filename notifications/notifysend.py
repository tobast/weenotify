# -*- coding: utf-8 -*-
"""
Sends a desktop notification using notify-send command.
"""
from . import notification
import logging

class NotifySend(notification.Notification):
    """ On screen notification of the message. """
    def __init__(self, image="", timer=2000, level="normal"):
        self._command = "/usr/bin/notify-send -t {} -u {}" + ("-i {}" if image else "")
        self.image = image
        self.timer = timer
        self.level = level
        super().__init__(self.__format())

    def __format(self):
        """ Formats the command. """
        return self._command.format(self.timer, self.level, self.image)
