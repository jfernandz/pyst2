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

licenses = ( 'Python Software Foundation License'
           , 'GNU Library or Lesser General Public License (LGPL)'
           )


setup \
    ( name = 'pyst'
    , version = VERSION
    , description = 'A Python Interface to Asterisk'
    , long_description = ''.join (description)
    , author = 'Karl Putland'
    , author_email = 'kputland@users.sourceforge.net'
    , maintainer = 'Ralf Schlatterbeck'
    , maintainer_email = 'rsc@runtux.com'
    , url = 'http://www.sourceforge.net/projects/pyst/'
    , packages = ['asterisk']
    , license = ', '.join (licenses)
    , platforms = 'Any'
    , classifiers =
        [ 'Development Status :: 5 - Production/Stable'
        , 'Environment :: Other Environment'
        , 'Intended Audience :: Developers'
        , 'Intended Audience :: Telecommunications Industry'
        , 'Operating System :: OS Independent'
        , 'Programming Language :: Python'
        , 'Programming Language :: Python :: 2.4'
        , 'Programming Language :: Python :: 2.5'
        , 'Programming Language :: Python :: 2.6'
        , 'Programming Language :: Python :: 2.7'
        , 'Topic :: Communications :: Internet Phone'
        , 'Topic :: Communications :: Telephony'
        , 'Topic :: Software Development :: Libraries :: Python Modules'
        ] + ['License :: OSI Approved :: ' + l for l in licenses]
    )
