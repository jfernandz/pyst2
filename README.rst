pyst2: A Python Interface to Asterisk
=====================================

.. image:: https://img.shields.io/pypi/v/pyst2.svg
    :alt: pyst2 Release
    :target: https://pypi.python.org/pypi/pyst2

.. image:: https://img.shields.io/pypi/dm/pyst2.svg
    :alt: pyst2 Downloads
    :target: https://pypi.python.org/pypi/pyst2

.. image:: https://img.shields.io/travis/rdegges/pyst2.svg
    :alt: pyst2 Build
    :target: https://travis-ci.org/rdegges/pyst2

.. image:: https://github.com/rdegges/pyst2/raw/master/assets/snake-sketch.jpg
   :alt: Snake Sketch

Project Documentation
---------------------

http://pyst2.readthedocs.io


Meta
----

- Author: Randall Degges
- Email: r@rdegges.com
- Site: http://www.rdegges.com
- Status: *looking for maintainer*, active

**NOTE**: This project is now mantained by Francesco Rana. 
Please be patient because I'm not used to the job yet, but I'll do my best.
Many and infinite thanks to Randall Degges for his wonderful work. I'm actually using the
library in some project of mine, so I'm more than happy to help and push it further if I can.
I'm happy to accept pull requests and cut releases as needed.
If you want to contribute to the project, please do!


Purpose
-------

pyst2 consists of a set of interfaces and libraries to allow programming of
Asterisk from python. The library currently supports AGI, AMI, and the parsing
of Asterisk configuration files. The library also includes debugging facilities
for AGI.

This project has been forked from pyst (http://sf.net/projects/pyst/) because
it was impossible for me to contact the project maintainer (after several
attempts), and I'd like to bring the project up-to-date, fix bugs, and make
it more usable overall.

My immediate plans include adding full documentation, re-writing some
of the core routines, adding a test suite, and accepting pull requests.

If you are one of the current maintainers, and would like to take over the
fork, please contact me: r@rdegges.com, so we can get that setup!


Installation
------------

To install ``pyst2``, simply run:

.. code-block:: console

    $ pip install pyst2

This will install the latest version of the library automatically.


Documentation
-------------

Documentation is currently only in python docstrings, you can use
pythons built-in help facility::

 import asterisk
 help (asterisk)
 import asterisk.agi
 help (asterisk.agi)
 import asterisk.manager
 help (asterisk.manager)
 import asterisk.config
 help (asterisk.config)

Some notes on platforms: We now specify "platforms = 'Any'" in
``setup.py``. This means, the manager part of the package will probably
run on any platform. The agi scripts on the other hand are called
directly on the host where Asterisk is running. Since Asterisk doesn't
run on windows platforms (and probably never will) the agi part of the
package can only be run on Asterisk platforms.

FastAGI
-------

FastAGI support is a python based raw SocketServer, To start the server
python fastagi.py should start it listening on localhost and the default
asterisk FastAGI port. This does require the newest version of pyst2.
The FastAGI server runs in as a Forked operation for each request, in
an attempt to prevent blocking by a single bad service. As a result the
FastAGI server may consume more memory then a single process. If you need
to use a single process simply uncomment the appropriate line. Future versions
of this will use a config file to set options.

Credits
-------

Thanks to Karl Putland for writing the original package.

Thanks to Matthew Nicholson for maintaining the package for some years
and for handing over maintenance when he was no longer interested.

Thanks to Randall Degges for maintaining this for and accepting
pull requests.


Things to do for pyst
---------------------

This is the original changelog merged into the readme file. I'm not so
sure I really want to change all these things (in particular the
threaded implementation looks good to me). I will maintain a section
summarizing the changes in this README. Detailed changes will be
available in the version control tool (currently git).

* ChangeLog:
  The ChangeLog needs to be updated from the monotone logs.

* Documentation:
  All of pyst's inline documentation needs to be updated.

* manager.py:
  This should be converted to be single threaded.  Also there is a race
  condition when a user calls manager.logoff() followed by
  manager.close().  The close() function may still call logoff again if
  the socket thread has not yet cleared the _connected flag.

  A class should be made for each manager action rather than having a
  function in a manager class.  The manager class should be adapted to
  have a send method that know the general format of the classes.

Matthew Nicholson writes on the mailinglist (note that I'm not sure I'll do
this, I'm currently satisfied with the threaded implementation):

  For pyst 0.3 I am planning to clean up the manager.py.  There are
  several know issues with the code.  No one has actually reported these
  as problems, but I have personally had trouble with these.  Currently
  manager.py runs in several threads, the main program thread, a thread to
  read from the network, and an event distribution thread.  This causes
  problems with non thread safe code such as the MySQLdb libraries.  This
  design also causes problems when an event handler throws an exception
  that causes the event processing thread to terminate.

  The second problem is with the way actions are sent.  Each action has a
  specific function associated with it in the manager object that takes
  all possible arguments that may ever be passed to that action.  This
  makes the api somewhat rigid and the Manager object cluttered.

  To solve these problems I am basically going to copy the design of my
  Astxx manager library (written in c++) and make it more python like.
  Each action will be a different object with certain methods to handle
  various tasks, with one function in the actual Manager class to send the
  action.  This will make the Manager class much smaller and much more
  flexible.  The current code will be consolidated into a single threaded
  design with hooks to have the library process events and such.  These
  hooks will be called from the host application's main loop.
