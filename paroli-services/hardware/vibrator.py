#    Paroli
#
#    copyright 2008 Mirko Lindner (mirko@openmoko.org)
#
#    This file is part of Paroli.
#
#    Paroli is free software: you can redistribute it and/or modify it
#    under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Paroli is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Paroli.  If not, see <http://www.gnu.org/licenses/>.

__docformat__ = 'reStructuredText'

import dbus

import tichy
from tichy.tasklet import WaitDBus

import logging
logger = logging.getLogger('vibrator')


class VibratorService(tichy.Service):
    """The 'Vibrator' service

    This service can be used to start or stop the device vibrator if
    it has one.
    """

    service = 'Vibrator'

    def __init__(self):
        """Connect to the freesmartphone DBus object"""
        super(VibratorService, self).__init__()
        try:
            bus = dbus.SystemBus(mainloop=tichy.mainloop.dbus_loop)
            vibrator = bus.get_object('org.freesmartphone.odeviced', '/org/freesmartphone/Device/LED/neo1973_vibrator')
            self.vibrator = dbus.Interface(vibrator, 'org.freesmartphone.Device.LED')

        except Exception, e:
            logger.warning("can't use freesmartphone vibrator : %s", e)
            self.vibrator = None

    def start(self):
        """Start the vibrator"""
        logger.info("start vibrator")
        if not self.vibrator:
            return
        self.vibrator.SetBlinking(300, 700)

    def stop(self):
        """Stop the vibrator"""
        logger.info("stop vibrator")
        if not self.vibrator:
            return
        self.vibrator.SetBrightness(0)
