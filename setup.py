#!/usr/bin/env python

from distutils.core import setup

try :
    from asterisk.Version  import VERSION
except :
    VERSION = None

description = []
f = open ('README')
logo_stripped = False
for line in f :
    if not logo_stripped and line.strip () :
        continue
    logo_stripped = True
    description.append (line)

licenses = ( 'Python Software Foundation License (agitb)'
           , 'GNU Library or Lesser General Public License (LGPL)'
           )

setup \
    ( name = 'pyst'
    , version = VERSION
    , description = 'A Python Interface to Asterisk'
    , long_description = ''.join (description)
    , author = 'Karl Putland'
    , author_email = 'kputland@users.sourceforge.net'
    , url = 'http://www.sourceforge.net/projects/pyst/'
    , packages = ['asterisk']
    , license = ', '.join (licenses)
    , platforms = 'UNIX'
    )
