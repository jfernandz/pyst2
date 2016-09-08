#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
Example to get and set variables via AGI.

You can call directly this script with AGI() in Asterisk dialplan.
"""

from asterisk.agi import *

agi = AGI()

string = 'カタカナ'

agi.verbose(string)

print('VERBOSE "カタカナ" 1')

# Get variable environment
extension = agi.env['agi_extension']

# Get variable in dialplan
phone_exten = agi.get_variable('PHONE_EXTEN')

# Set variable, it will be available in dialplan
agi.set_variable('EXT_CALLERID', string)