#!/usr/bin/env python
# vim: set expandtab shiftwidth=4:

"""
.. module:: manager
   :synopsis: Python Interface for Asterisk Manager

This module provides a Python API for interfacing with the asterisk manager.

Example
-------

.. code-block:: python

   import asterisk.manager
   import sys

   def handle_shutdown(event, manager):
      print "Recieved shutdown event"
      manager.close()
      # we could analize the event and reconnect here

   def handle_event(event, manager):
      print "Recieved event: %s" % event.name

   manager = asterisk.manager.Manager()
   try:
       # connect to the manager
       try:
          manager.connect('host')
          manager.login('user', 'secret')

           # register some callbacks
           manager.register_event('Shutdown', handle_shutdown) # shutdown
           manager.register_event('*', handle_event)           # catch all

           # get a status report
           response = manager.status()

           manager.logoff()
       except asterisk.manager.ManagerSocketException as e:
          print "Error connecting to the manager: %s" % e.strerror
          sys.exit(1)
       except asterisk.manager.ManagerAuthException as e:
          print "Error logging in to the manager: %s" % e.strerror
          sys.exit(1)
       except asterisk.manager.ManagerException as e:
          print "Error: %s" % e.strerror
          sys.exit(1)

   finally:
      # remember to clean up
      manager.close()

Remember all header, response, and event names are case sensitive.

Not all manager actions are implmented as of yet, feel free to add them
and submit patches.

Specification
-------------
"""

import sys
import os
import socket
import threading
from six import PY3
from six.moves import queue
import re
from types import *
from time import sleep

EOL = '\r\n'


class ManagerMsg(object):
    """A manager interface message"""
    def __init__(self, response):
        # the raw response, straight from the horse's mouth:
        self.response = response
        self.data = ''
        self.headers = {}

        # parse the response
        self.parse(response)

        # This is an unknown message, may happen if a command (notably
        # 'dialplan show something') contains a \n\r\n sequence in the
        # middle of output. We hope this happens only *once* during a
        # misbehaved command *and* the command ends with --END COMMAND--
        # in that case we return an Event.  Otherwise we asume it is
        # from a misbehaving command not returning a proper header (e.g.
        # IAXnetstats in Asterisk 1.4.X)
        # A better solution is probably to retain some knowledge of
        # commands sent and their expected return syntax. In that case
        # we could wait for --END COMMAND-- for 'command'.
        # B0rken in asterisk. This should be parseable without context.
        if 'Event' not in self.headers and 'Response' not in self.headers:
            # there are commands that return the ActionID but not
            # 'Response', e.g., IAXpeers in Asterisk 1.4.X
            if self.has_header('ActionID'):
                self.headers['Response'] = 'Generated Header'
            elif '--END COMMAND--' in self.data:
                self.headers['Event'] = 'NoClue'
            else:
                self.headers['Response'] = 'Generated Header'

    def parse(self, response):
        """Parse a manager message"""

        data = []
        for n, line in enumerate(response):
            # all valid header lines end in \r\n
            if not line.endswith('\r\n'):
                data.extend(response[n:])
                break
            try:
                k, v = (x.strip() for x in line.split(':', 1))
                # if header is ChanVariable it can have more that one value
                # we store the variable in a dictionary parsed
                if 'ChanVariable' in k:
                    if not self.headers.has_key('ChanVariable'):
                        self.headers['ChanVariable']={}
                    name, value = (x.strip() for x in v.split('=',1))
                    self.headers['ChanVariable'][name]=value
                else:
                    self.headers[k] = v
            except ValueError:
                # invalid header, start of multi-line data response
                data.extend(response[n:])
                break
        self.data = ''.join(data)

    def has_header(self, hname):
        """Check for a header"""
        return hname in self.headers

    def get_header(self, hname, defval=None):
        """Return the specfied header"""
        return self.headers.get(hname, defval)

    def __getitem__(self, hname):
        """Return the specfied header"""
        return self.headers[hname]

    def __repr__(self):
        if 'Response' in self.headers:
            return self.headers['Response']
        else:
            return self.headers['Event']


class Event(object):
    """Manager interface Events, __init__ expects and 'Event' message"""
    def __init__(self, message):

        # store all of the event data
        self.message = message
        self.data = message.data
        self.headers = message.headers

        # if this is not an event message we have a problem
        if not message.has_header('Event'):
            raise ManagerException(
                'Trying to create event from non event message')

        # get the event name
        self.name = message.get_header('Event')

    def has_header(self, hname):
        """Check for a header"""
        return hname in self.headers

    def get_header(self, hname, defval=None):
        """Return the specfied header"""
        return self.headers.get(hname, defval)

    def __getitem__(self, hname):
        """Return the specfied header"""
        return self.headers[hname]

    def __repr__(self):
        return self.headers['Event']

    def get_action_id(self):
        return self.headers.get('ActionID', 0000)


class Manager(object):
    def __init__(self):
        self._sock = None     # our socket
        self.title = None     # set by received greeting
        self._connected = threading.Event()
        self._running = threading.Event()

        # our hostname
        self.hostname = socket.gethostname()

        # our queues
        self._message_queue = queue.Queue()
        self._response_queue = queue.Queue()
        self._event_queue = queue.Queue()

        # callbacks for events
        self._event_callbacks = {}

        self._reswaiting = []  # who is waiting for a response

        # sequence stuff
        self._seqlock = threading.Lock()
        self._seq = 0

        # some threads
        self.message_thread = threading.Thread(target=self.message_loop)
        self.event_dispatch_thread = threading.Thread(
            target=self.event_dispatch)

        self.message_thread.setDaemon(True)
        self.event_dispatch_thread.setDaemon(True)

    def __del__(self):
        self.close()

    def connected(self):
        """
        Check if we are connected or not.
        """
        return self._connected.isSet()

    def next_seq(self):
        """Return the next number in the sequence, this is used for ActionID"""
        self._seqlock.acquire()
        try:
            return self._seq
        finally:
            self._seq += 1
            self._seqlock.release()

    def send_action(self, cdict={}, **kwargs):
        """
        Send a command to the manager

        If a list is passed to the cdict argument, each item in the list will
        be sent to asterisk under the same header in the following manner:

        cdict = {"Action": "Originate",
                 "Variable": ["var1=value", "var2=value"]}
        send_action(cdict)

        ...

        Action: Originate
        Variable: var1=value
        Variable: var2=value
        """

        if not self._connected.isSet():
            raise ManagerException("Not connected")

        # fill in our args
        cdict.update(kwargs)

        # set the action id
        if 'ActionID' not in cdict:
            cdict['ActionID'] = '%s-%08x' % (self.hostname, self.next_seq())
        clist = []

        # generate the command
        for key, value in cdict.items():
            if isinstance(value, list):
                for item in value:
                    item = tuple([key, item])
                    clist.append('%s: %s' % item)
            else:
                item = tuple([key, value])
                clist.append('%s: %s' % item)
        clist.append(EOL)
        command = EOL.join(clist)

        # lock the socket and send our command
        try:
            self._sock.write(command.encode('utf8','ignore'))
            self._sock.flush()
        except socket.error as e:
            raise ManagerSocketException(e.errno, e.strerror)

        self._reswaiting.insert(0, 1)
        response = self._response_queue.get()
        self._reswaiting.pop(0)

        if not response:
            raise ManagerSocketException(0, 'Connection Terminated')

        return response

    def _receive_data(self):
        """
        Read the response from a command.
        """

        multiline = False
        status = False
        wait_for_marker = False
        eolcount = 0
        # loop while we are sill running and connected
        while self._running.isSet() and self._connected.isSet():
            try:
                lines = []
                for line in self._sock:
                    line = line.decode('utf8','ignore')
                    # check to see if this is the greeting line
                    if not self.title and '/' in line and not ':' in line:
                        # store the title of the manager we are connecting to:
                        self.title = line.split('/')[0].strip()
                        # store the version of the manager we are connecting to:
                        self.version = line.split('/')[1].strip()
                        # fake message header
                        lines.append('Response: Generated Header\r\n')
                        lines.append(line)
                        break
                    # If the line is EOL marker we have a complete message.
                    # Some commands are broken and contain a \n\r\n
                    # sequence, in the case wait_for_marker is set, we
                    # have such a command where the data ends with the
                    # marker --END COMMAND--, so we ignore embedded
                    # newlines until we see that marker
                    if line == EOL and not wait_for_marker:
                        multiline = False
                        if lines or not self._connected.isSet():
                            break
                        # ignore empty lines at start
                        continue
                    # If the user executed the status command, it's a special
                    # case, so we need to look for a marker.
                    if 'status will follow' in line:
                        status = True
                        wait_for_marker = True
                    lines.append(line)

                    # line not ending in \r\n or without ':' isn't a
                    # valid header and starts multiline response
                    if not line.endswith('\r\n') or ':' not in line:
                        multiline = True
                    # Response: Follows indicates we should wait for end
                    # marker --END COMMAND--
                    if not (multiline or status) and line.startswith('Response') and \
                            line.split(':', 1)[1].strip() == 'Follows':
                        wait_for_marker = True
                    # same when seeing end of multiline response
                    if multiline and (line.startswith('--END COMMAND--') or line.strip().endswith('--END COMMAND--')):
                        wait_for_marker = False
                        multiline = False
                    # same when seeing end of status response
                    if status and 'StatusComplete' in line:
                        wait_for_marker = False
                        status = False
                    if not self._connected.isSet():
                        break
                else:
                    # EOF during reading
                    self._sock.close()
                    self._connected.clear()
                # if we have a message append it to our queue
                if lines and self._connected.isSet():
                    self._message_queue.put(lines)
                else:
                    self._message_queue.put(None)
            except socket.error:
                self._sock.close()
                self._connected.clear()
                self._message_queue.put(None)

    def register_event(self, event, function):
        """
        Register a callback for the specfied event.
        If a callback function returns True, no more callbacks for that
        event will be executed.
        """

        # get the current value, or an empty list
        # then add our new callback
        current_callbacks = self._event_callbacks.get(event, [])
        current_callbacks.append(function)
        self._event_callbacks[event] = current_callbacks

    def unregister_event(self, event, function):
        """
        Unregister a callback for the specified event.
        """
        current_callbacks = self._event_callbacks.get(event, [])
        current_callbacks.remove(function)
        self._event_callbacks[event] = current_callbacks

    def message_loop(self):
        """
        The method for the event thread.
        This actually recieves all types of messages and places them
        in the proper queues.
        """

        # start a thread to recieve data
        t = threading.Thread(target=self._receive_data)
        t.setDaemon(True)
        t.start()

        try:
            # loop getting messages from the queue
            while self._running.isSet():
                # get/wait for messages
                data = self._message_queue.get()

                # if we got None as our message we are done
                if not data:
                    # notify the other queues
                    self._event_queue.put(None)
                    for waiter in self._reswaiting:
                        self._response_queue.put(None)
                    break

                # parse the data
                message = ManagerMsg(data)

                # check if this is an event message
                if message.has_header('Event'):
                    self._event_queue.put(Event(message))
                # check if this is a response
                elif message.has_header('Response'):
                    self._response_queue.put(message)
                else:
                    print('No clue what we got\n%s' % message.data)
        finally:
            # wait for our data receiving thread to exit
            t.join()

    def event_dispatch(self):
        """This thread is responsible for dispatching events"""

        # loop dispatching events
        while self._running.isSet():
            # get/wait for an event
            ev = self._event_queue.get()

            # if we got None as an event, we are finished
            if not ev:
                break

            # dispatch our events

            # first build a list of the functions to execute
            callbacks = (self._event_callbacks.get(ev.name, [])
                         + self._event_callbacks.get('*', []))

            # now execute the functions
            for callback in callbacks:
                if callback(ev, self):
                    break

    def connect(self, host, port=5038):
        """Connect to the manager interface"""

        if self._connected.isSet():
            raise ManagerException('Already connected to manager')

        # make sure host is a string
        assert type(host) is str

        port = int(port)  # make sure port is an int

        # create our socket and connect
        try:
            _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _sock.connect((host, port))
            if PY3:
                self._sock = _sock.makefile(mode='rwb', buffering=0)
            else:
                self._sock = _sock.makefile()
            _sock.close()
        except socket.error as e:
            raise ManagerSocketException(e.errno, e.strerror)

        # we are connected and running
        self._connected.set()
        self._running.set()

        # start the event thread
        self.message_thread.start()

        # start the event dispatching thread
        self.event_dispatch_thread.start()

        # get our initial connection response
        return self._response_queue.get()

    def close(self):
        """Shutdown the connection to the manager"""

        # if we are still running, logout
        if self._running.isSet() and self._connected.isSet():
            self.logoff()

        if self._running.isSet():
            # put None in the message_queue to kill our threads
            self._message_queue.put(None)

            # wait for the event thread to exit
            self.message_thread.join()

            # make sure we do not join our self (when close is called from event handlers)
            if threading.currentThread() != self.event_dispatch_thread:
                # wait for the dispatch thread to exit
                self.event_dispatch_thread.join()

        self._running.clear()

# Manager actions

    def login(self, username, secret):
        """Login to the manager, throws ManagerAuthException when login falis"""

        cdict = {'Action': 'Login'}
        cdict['Username'] = username
        cdict['Secret'] = secret
        response = self.send_action(cdict)

        if response.get_header('Response') == 'Error':
            raise ManagerAuthException(response.get_header('Message'))

        return response

    def ping(self):
        """Send a ping action to the manager"""
        cdict = {'Action': 'Ping'}
        response = self.send_action(cdict)
        return response

    def logoff(self):
        """Logoff from the manager"""

        cdict = {'Action': 'Logoff'}
        response = self.send_action(cdict)

        return response

    def hangup(self, channel):
        """Hangup the specified channel"""

        cdict = {'Action': 'Hangup'}
        cdict['Channel'] = channel
        response = self.send_action(cdict)

        return response

    def status(self, channel=''):
        """Get a status message from asterisk"""

        cdict = {'Action': 'Status'}
        cdict['Channel'] = channel
        response = self.send_action(cdict)

        return response

    def redirect(self, channel, exten, priority='1', extra_channel='', context=''):
        """Redirect a channel"""

        cdict = {'Action': 'Redirect'}
        cdict['Channel'] = channel
        cdict['Exten'] = exten
        cdict['Priority'] = priority
        if context:
            cdict['Context'] = context
        if extra_channel:
            cdict['ExtraChannel'] = extra_channel
        response = self.send_action(cdict)

        return response

    def originate(self, channel, exten, context='', priority='', timeout='', application='', data='', caller_id='', run_async=False, earlymedia='false', account='', variables={}):
        """Originate a call"""

        cdict = {'Action': 'Originate'}
        cdict['Channel'] = channel
        cdict['Exten'] = exten
        if context:
            cdict['Context'] = context
        if priority:
            cdict['Priority'] = priority
        if timeout:
            cdict['Timeout'] = timeout
        if application:
            cdict['Application'] = application
        if data:
            cdict['Data'] = data
        if caller_id:
            cdict['CallerID'] = caller_id
        if run_async:
            cdict['Async'] = 'yes'
        if earlymedia:
            cdict['EarlyMedia'] = earlymedia
        if account:
            cdict['Account'] = account
        # join dict of vairables together in a string in the form of 'key=val|key=val'
        # with the latest CVS HEAD this is no longer necessary
        # if variables: cdict['Variable'] = '|'.join(['='.join((str(key), str(value))) for key, value in variables.items()])
        if variables:
            cdict['Variable'] = ['='.join(
                (str(key), str(value))) for key, value in variables.items()]

        response = self.send_action(cdict)

        return response

    def mailbox_status(self, mailbox):
        """Get the status of the specfied mailbox"""

        cdict = {'Action': 'MailboxStatus'}
        cdict['Mailbox'] = mailbox
        response = self.send_action(cdict)

        return response

    def command(self, command):
        """Execute a command"""

        cdict = {'Action': 'Command'}
        cdict['Command'] = command
        response = self.send_action(cdict)

        return response

    def extension_state(self, exten, context):
        """Get the state of an extension"""

        cdict = {'Action': 'ExtensionState'}
        cdict['Exten'] = exten
        cdict['Context'] = context
        response = self.send_action(cdict)

        return response

    def playdtmf(self, channel, digit):
        """Plays a dtmf digit on the specified channel"""

        cdict = {'Action': 'PlayDTMF'}
        cdict['Channel'] = channel
        cdict['Digit'] = digit
        response = self.send_action(cdict)

        return response

    def absolute_timeout(self, channel, timeout):
        """Set an absolute timeout on a channel"""

        cdict = {'Action': 'AbsoluteTimeout'}
        cdict['Channel'] = channel
        cdict['Timeout'] = timeout
        response = self.send_action(cdict)
        return response

    def mailbox_count(self, mailbox):
        cdict = {'Action': 'MailboxCount'}
        cdict['Mailbox'] = mailbox
        response = self.send_action(cdict)
        return response

    def sippeers(self):
        cdict = {'Action': 'Sippeers'}
        response = self.send_action(cdict)
        return response

    def sipshowpeer(self, peer):
        cdict = {'Action': 'SIPshowpeer'}
        cdict['Peer'] = peer
        response = self.send_action(cdict)
        return response

    def sipshowregistry(self):
        cdict = {'Action': 'SIPShowregistry'}
        response = self.send_action(cdict)
        return response

    def iaxregistry(self):
        cdict = {'Action': 'IAXregistry'}
        response = self.send_action(cdict)
        return response

    def reload(self, module):
        """ Reloads config for a given module """

        cdict = {'Action': 'Reload'}
        cdict['Module'] = module
        response = self.send_action(cdict)
        return response

    def dbdel(self, family, key):
        cdict = {'Action': 'DBDel'}
        cdict['Family'] = family
        cdict['Key'] = key
        response = self.send_action(cdict)
        return response

    def dbdeltree(self, family, key):
        cdict = {'Action': 'DBDelTree'}
        cdict['Family'] = family
        cdict['Key'] = key
        response = self.send_action(cdict)
        return response

    def dbget(self, family, key):
        cdict = {'Action': 'DBGet'}
        cdict['Family'] = family
        cdict['Key'] = key
        response = self.send_action(cdict)
        return response

    def dbput(self, family, key, val):
        cdict = {'Action': 'DBPut'}
        cdict['Family'] = family
        cdict['Key'] = key
        cdict['Val'] = val
        response = self.send_action(cdict)
        return response

class ManagerException(Exception):
    pass


class ManagerSocketException(ManagerException):
    pass


class ManagerAuthException(ManagerException):
    pass
