#    Tichy
#    copyright 2008 Guillaume Chereau (charlie@openmoko.org)
#
#    This file is part of Tichy.
#
#    Tichy is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Tichy is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Tichy.  If not, see <http://www.gnu.org/licenses/>.

__docformat__ = 'reStructuredText'

"""Config module

This module gives access to a global config instance that can be used
to store configuration values that can be accessed at any point in the
code.
"""

import ConfigParser
import logging
import os

logger = logging.getLogger('config')

# The global config instance
config = None

def parse(cfg_file=None):
    """parse the config files

    We look into 3 locations : first the local dir, then /etc/paroli/,
    then the home directory

    :Parameters:

        cfg_file : str | None
            the configuartion file to use, or None for default config
            files

    :Returns: the ConfigParser object
    """
    global config
    if config:
        logger.warning("parsing config twice")

    config = ConfigParser.SafeConfigParser()
    if not cfg_file:
        local_path = "./paroli.cfg"
        system_path = "/etc/paroli/paroli.cfg"
        home_path = os.path.expanduser("~/.paroli/paroli.cfg")
        files = [local_path, system_path, home_path]
    else:
        files = cfg_file.split(':')
    for path in files:
        logger.info("read config file %s", path)
        config.read(path)
    return config
