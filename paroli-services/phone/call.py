#
#    Tichy
#
#    copyright 2008 Guillaume Chereau (charlie@openmoko.org)
#
#    This file is part of Tichy.
#
#    Tichy is free software: you can redistribute it and/or modify it
#    under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Tichy is distributed in the hope that it will be useful, but
#    WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Tichy.  If not, see <http://www.gnu.org/licenses/>.

__docformat__ = 'reStructuredText'

import logging
logger = logging.getLogger('Call')

import tichy
from tel_number import TelNumber

class Call(tichy.Item):
    """Class that represents a voice call"""

    def __init__(self, number, direction='out', timestamp=None,
                 status='inactive'):
        """Create a new call object

        :Parameters:

            number : `tichy.TelNumber` | str
                The number of the peer

            direction : str
               'out' for outgoing call, 'in' for incoming call

            timestamp
                the time at which we created the call. If set to None
                we use the current time

            status : str | None
                Can be any of :
                    - 'inactive'
                    - 'incoming'
                    - 'outoing'
                    - 'activating'
                    - 'active'
                    - 'releasing'
                    - 'released'
                (default to 'inactive')

            checked : boolean
                Actaully it's used only for "missed" calls

        Signals

            initiating
                The call is being initiated

            outgoing
                The call is outgoing

            activated
                The call has been activated

            releasing
                The call is being released

            released
                The call has been released
        """
        self.number = TelNumber.as_type(number)
        self.direction = direction
        self.timestamp = tichy.Time.as_type(timestamp)
        self.status = status
        self.missed = False
        self.checked = True

    def get_text(self):
        return self.number.get_text()

    @property
    def description(self):
        if (self.missed):
            return "Missed" + " at " + unicode(self.timestamp.simple_repr())
        else:
            if (self.direction == "out"):  
                return "Outgoing" + " at " + unicode(self.timestamp.simple_repr())
            elif (self.direction == "in"):
                return "Incoming" + " at " + unicode(self.timestamp.simple_repr())

    @tichy.tasklet.tasklet
    def initiate(self):
        """Initiate the call

        This will try to get the 'GSM' service and call its 'initiate'
        method.
        """
        logger.info("initiate call")
        gsm_service = tichy.Service.get('GSM')
        yield gsm_service._initiate(self)
        self.status = 'initiating'
        self.emit(self.status)

    @tichy.tasklet.tasklet
    def release(self):
        logger.info("release call")
        if self.status in ['releasing', 'released']:
            return
        gsm_service = tichy.Service.get('GSM')
        try:
            yield gsm_service._release(self)
        except Exception, e:
            #XXX should the call get a 
            #logger.debug('call error')
            self.emit("error", e)
            self.status = 'released'
        else:
            self.status = 'releasing'
        self.emit(self.status)

    @tichy.tasklet.tasklet
    def activate(self):
        """Activate the call"""
        logger.info("activate call")
        gsm_service = tichy.Service.get('GSM')
        yield gsm_service._activate(self)
        self.status = 'activating'
        self.emit(self.status)

    # XXX: those methods should be tasklets

    def mute_ringtone(self):
        """mute the call ringtone if it is ringing"""
        logger.info("mute ring tone")
        tichy.Service.get('Audio').stop_all_sounds()
        tichy.Service.get('Vibrator').stop()

    def mute(self):
        """Mute an active call"""
        logger.info("mute call")
        tichy.Service.get('Audio').set_mic_status(False)

    def unmute(self):
        """Un Mute an active call"""
        logger.info("mute call")
        tichy.Service.get('Audio').set_mic_status(True)

    def mute_toggle(self):
        logger.info("mute call toggle")
        if tichy.Service.get('Audio').get_mic_status() == 1:
            tichy.Service.get('Audio').set_mic_status(0)
        else:
            tichy.Service.get('Audio').set_mic_status(1)

    @tichy.tasklet.tasklet
    def send_dtmf(self, code):
        """Send one or more Dual Tone Multiple Frequency (DTMF)
        signals during an active call"""
        gsm_service = tichy.Service.get('GSM')
        if self.status != 'active':
            raise Exception("Can't send DMTF to a call that is not active")
        yield gsm_service._send_dtmf(self, code)

    # Those methods are only supposed to be called by the gsm service

    def _outgoing(self):
        self.status = 'outgoing'
        self.emit('outgoing')

    def _active(self):
        self.status = 'active'
        self.emit('activated')

    def _released(self):
        if self.status == 'incoming':
            self.missed = True
            self.checked = False
        self.status = 'released'
        self.emit('released')

    def _incoming(self):
        self.status = 'incoming'
        self.emit('incoming')

    def check(self):
        self.checked = True

    # TODO: In the long run we should really use a system similar to
    #       PEAK, where we can define all the Items attributes and
    #       every atomic value has a save and load method.  So that we
    #       don't have to create all those `to_dict` and `from_dict`
    #       methods. We could use a Struct Item for this kind of
    #       things.

    def to_dict(self):
        """return all the attributes in a python dict"""
        return {'number': str(self.number),
                'status': str(self.status),
                'direction': self.direction,
                'timestamp': str(self.timestamp)}

    @classmethod
    def from_dict(self, kargs):
        """return a new Call object from a dictionary

        This should be compatible with the `to_dict` method
        """
        number = kargs['number']
        status = kargs['status']
        direction = kargs['direction']
        timestamp = kargs['timestamp']
        return Call(number, direction=direction, timestamp=timestamp,
                    status=status)
