#!/usr/bin/env python2
# vim: set et sw=4:
"""agi

This module contains functions and classes to implment AGI scripts in python.
pyvr

{'agi_callerid' : 'mars.putland.int',
 'agi_channel'  : 'IAX[kputland@kputland]/119',
 'agi_context'  : 'default',
 'agi_dnid'     : '666',
 'agi_enhanced' : '0.0',
 'agi_extension': '666',
 'agi_language' : 'en',
 'agi_priority' : '1',
 'agi_rdnis'    : '',
 'agi_request'  : 'pyst',
 'agi_type'     : 'IAX'}

"""

import sys, pprint, re
from types import ListType
import signal

DEFAULT_TIMEOUT = 2000 # 2sec timeout used as default for functions that take timeouts
DEFAULT_RECORD  = 20000 # 20sec record time

re_code = re.compile(r'(^\d*)\s*(.*)')
re_kv = re.compile(r'(?P<key>\w+)=(?P<value>[^\s]+)\s*(?:\((?P<data>.*)\))*')

class AGIException(Exception): pass
class AGIError(AGIException): pass

class AGIUnknownError(AGIError): pass

class AGIAppError(AGIError): pass

# there are several different types of hangups we can detect
# they all are derrived from AGIHangup
class AGIHangup(AGIAppError): pass
class AGISIGHUPHangup(AGIHangup): pass
class AGISIGPIPEHangup(AGIHangup): pass
class AGIResultHangup(AGIHangup): pass

class AGIDBError(AGIAppError): pass

class AGIUsageError(AGIError): pass
class AGIInvalidCommand(AGIError): pass

class AGI:
    """
    This class encapsulates communication between Asterisk an a python script.
    It handles encoding commands to Asterisk and parsing responses from
    Asterisk. 
    """
    
    def __init__(self):
        self._got_sighup = False
        signal.signal(signal.SIGHUP, self._handle_sighup)  # handle SIGHUP
        sys.stderr.write('ARGS: ')
        sys.stderr.write(str(sys.argv))
        sys.stderr.write('\n')
        self.env = {}
        self._get_agi_env()

    def _get_agi_env(self):
        while 1:
            line = sys.stdin.readline().strip()
            sys.stderr.write('ENV LINE: ')
            sys.stderr.write(line)
            sys.stderr.write('\n')
            if line == '':
                #blank line signals end
                break
            key,data = line.split(':')[0], ':'.join(line.split(':')[1:])
            key = key.strip()
            data = data.strip()
            if key <> '':
                self.env[key] = data
        sys.stderr.write('class AGI: self.env = ')
        sys.stderr.write(pprint.pformat(self.env))
        sys.stderr.write('\n')

    def _quote(self, string):
        return ''.join(['"', str(string), '"'])

    def _handle_sighup(self, signum, frame):
        """Handle the SIGHUP signal"""
        self._got_sighup = True

    def test_hangup(self):
        """This function throws AGIHangup if we have recieved a SIGHUP"""
        if self._got_sighup:
           raise AGISIGHUPHangup("Received SIGHUP from Asterisk")
        
    def execute(self, command, *args):
        self.test_hangup()

        try:
            self.send_command(command, *args)
            return self.get_result()
        except IOError,e:
            if e.errno == 32:
                # Broken Pipe * let us go
                raise AGISIGPIPEHangup("Received SIGPIPE")
            else:
                raise

    def send_command(self, command, *args):
        """Send a command to Asterisk"""
        command = command.strip()
        command = '%s %s' % (command, ' '.join(map(str,args)))
        command = command.strip()
        if command[-1] != '\n':
            command += '\n'
        sys.stderr.write('    COMMAND: %s' % command)
        sys.stdout.write(command)
        sys.stdout.flush()

    def get_result(self, stdin=sys.stdin):
        """Read the result of a command from Asterisk"""
        code = 0
        result = {'result':('','')}
        line = stdin.readline().strip()
        sys.stderr.write('    RESULT_LINE: %s\n' % line)
        m = re_code.search(line)
        if m:
            code, response = m.groups()
            code = int(code)

        if code == 200:
            for key,value,data in re_kv.findall(response):
                result[key] = (value, data)

                # If user hangs up... we get 'hangup' in the data
                if data == 'hangup':
                    raise AGIResultHangup("User hungup during execution")

                if key == 'result' and value == '-1':
                    raise AGIAppError("Error executing application, or hangup")

            sys.stderr.write('    RESULT_DICT: %s\n' % pprint.pformat(result))
            return result
        elif code == 510:
            raise AGIInvalidCommand(response)
        elif code == 520:
            usage = [line]
            line = stdin.readline().strip()
            while line[:3] != '520':
                usage.append(line)
                line = stdin.readline().strip()
            usage.append(line)
            usage = '%s\n' % '\n'.join(usage)
            raise AGIUsageError(usage)
        else:
            raise AGIUnknownError(code, 'Unhandled code or undefined response')

    def _process_digit_list(self, digits):
        if type(digits) == ListType:
            digits = ''.join(map(str, digits))
        return self._quote(digits)

    def answer(self):
        """agi.answer() --> None
        Answer channel if not already in answer state.
        """
        self.execute('ANSWER')['result'][0]

    def wait_for_digit(self, timeout=DEFAULT_TIMEOUT):
        """agi.wait_for_digit(timeout=DEFAULT_TIMEOUT) --> digit
        Waits for up to 'timeout' milliseconds for a channel to receive a DTMF
        digit.  Returns digit dialed
        Throws AGIError on channel falure
        """
        res = self.execute('WAIT FOR DIGIT', timeout)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except ValueError:
                raise AGIError('Unable to convert result to digit: %s' % res)

    def send_text(self, text=''):
        """agi.send_text(text='') --> None
        Sends the given text on a channel.  Most channels do not support the
        transmission of text.
        Throws AGIError on error/hangup
        """
        self.execute('SEND TEXT', self._quote(text))['result'][0]

    def receive_char(self, timeout=DEFAULT_TIMEOUT):
        """agi.receive_char(timeout=DEFAULT_TIMEOUT) --> chr
        Receives a character of text on a channel.  Specify timeout to be the
        maximum time to wait for input in milliseconds, or 0 for infinite. Most channels
        do not support the reception of text.
        """
        res = self.execute('RECEIVE CHAR', timeout)['result'][0]

        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def tdd_mode(self, mode='off'):
        """agi.tdd_mode(mode='on'|'off') --> None
        Enable/Disable TDD transmission/reception on a channel. 
        Throws AGIAppError if channel is not TDD-capable.
        """
        res = self.execute('TDD MODE', mode)['result'][0]
        if res == '0':
            raise AGIAppError('Channel %s is not TDD-capable')
            
    def stream_file(self, filename, escape_digits='', sample_offset=0):
        """agi.stream_file(filename, escape_digits='', sample_offset=0) --> digit
        Send the given file, allowing playback to be interrupted by the given
        digits, if any.  escape_digits is a string '12345' or a list  of 
        ints [1,2,3,4,5] or strings ['1','2','3'] or mixed [1,'2',3,'4']
        If sample offset is provided then the audio will seek to sample
        offset before play starts.  Returns  digit if one was pressed.
        Throws AGIError if the channel was disconnected.  Remember, the file
        extension must not be included in the filename.
        """
        escape_digits = self._process_digit_list(escape_digits)
        response = self.execute('STREAM FILE', filename, escape_digits, sample_offset)
        res = response['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)
    
    def control_stream_file(self, filename, escape_digits='', skipms=3000, fwd='', rew='', pause=''):
        """
        Send the given file, allowing playback to be interrupted by the given
        digits, if any.  escape_digits is a string '12345' or a list  of 
        ints [1,2,3,4,5] or strings ['1','2','3'] or mixed [1,'2',3,'4']
        If sample offset is provided then the audio will seek to sample
        offset before play starts.  Returns  digit if one was pressed.
        Throws AGIError if the channel was disconnected.  Remember, the file
        extension must not be included in the filename.
        """
        escape_digits = self._process_digit_list(escape_digits)
        response = self.execute('CONTROL STREAM FILE', self._quote(filename), escape_digits, self._quote(skipms), self._quote(fwd), self._quote(rew), self._quote(pause))
        res = response['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def send_image(self, filename):
        """agi.send_image(filename) --> None
        Sends the given image on a channel.  Most channels do not support the
        transmission of images.   Image names should not include extensions.
        Throws AGIError on channel failure
        """
        res = self.execute('SEND IMAGE', filename)['result'][0]
        if res != '0':
            raise AGIAppError('Channel falure on channel %s' % self.env.get('agi_channel','UNKNOWN'))

    def say_digits(self, digits, escape_digits=''):
        """agi.say_digits(digits, escape_digits='') --> digit
        Say a given digit string, returning early if any of the given DTMF digits
        are received on the channel.  
        Throws AGIError on channel failure
        """
        digits = self._process_digit_list(digits)
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY DIGITS', digits, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_number(self, number, escape_digits=''):
        """agi.say_number(number, escape_digits='') --> digit
        Say a given digit string, returning early if any of the given DTMF digits
        are received on the channel.  
        Throws AGIError on channel failure
        """
        number = self._process_digit_list(number)
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY NUMBER', number, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_alpha(self, characters, escape_digits=''):
        """agi.say_alpha(string, escape_digits='') --> digit
        Say a given character string, returning early if any of the given DTMF
        digits are received on the channel.  
        Throws AGIError on channel failure
        """
        characters = self._process_digit_list(characters)
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY ALPHA', characters, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_phonetic(self, characters, escape_digits=''):
        """agi.say_phonetic(string, escape_digits='') --> digit
        Phonetically say a given character string, returning early if any of
        the given DTMF digits are received on the channel.  
        Throws AGIError on channel failure
        """
        characters = self._process_digit_list(characters)
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY PHONETIC', characters, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_date(self, seconds, escape_digits=''):
        """agi.say_date(seconds, escape_digits='') --> digit
        Say a given date, returning early if any of the given DTMF digits are
        pressed.  The date should be in seconds since the UNIX Epoch (Jan 1, 1970 00:00:00)
        """
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY DATE', seconds, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def say_time(self, seconds, escape_digits=''):
        """agi.say_time(seconds, escape_digits='') --> digit
        Say a given time, returning early if any of the given DTMF digits are
        pressed.  The time should be in seconds since the UNIX Epoch (Jan 1, 1970 00:00:00)
        """
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('SAY TIME', seconds, escape_digits)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)
    
    def say_datetime(self, seconds, escape_digits='', format='', zone=''):
        """agi.say_datetime(seconds, escape_digits='', format='', zone='') --> digit
        Say a given date in the format specfied (see voicemail.conf), returning
        early if any of the given DTMF digits are pressed.  The date should be
        in seconds since the UNIX Epoch (Jan 1, 1970 00:00:00).
        """
        escape_digits = self._process_digit_list(escape_digits)
        if format: format = self._quote(format)
        res = self.execute('SAY DATETIME', seconds, escape_digits, format, zone)['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def get_data(self, filename, timeout=DEFAULT_TIMEOUT, max_digits=255):
        """agi.get_data(filename, timeout=DEFAULT_TIMEOUT, max_digits=255) --> digits
        Stream the given file and receive dialed digits
        """
        result = self.execute('GET DATA', filename, timeout, max_digits)
        res, value = result['result']
        return res
    
    def get_option(self, filename, escape_digits='', timeout=0):
        """agi.get_option(filename, escape_digits='', timeout=0) --> digit
        Send the given file, allowing playback to be interrupted by the given
        digits, if any.  escape_digits is a string '12345' or a list  of 
        ints [1,2,3,4,5] or strings ['1','2','3'] or mixed [1,'2',3,'4']
        Returns  digit if one was pressed.
        Throws AGIError if the channel was disconnected.  Remember, the file
        extension must not be included in the filename.
        """
        escape_digits = self._process_digit_list(escape_digits)
        if timeout:
            response = self.execute('GET OPTION', filename, escape_digits, timeout)
        else:
            response = self.execute('GET OPTION', filename, escape_digits)

        res = response['result'][0]
        if res == '0':
            return ''
        else:
            try:
                return chr(int(res))
            except:
                raise AGIError('Unable to convert result to char: %s' % res)

    def set_context(self, context):
        """agi.set_context(context)
        Sets the context for continuation upon exiting the application.
        No error appears to be produced.  Does not set exten or priority
        Use at your own risk.  Ensure that you specify a valid context.
        """
        self.execute('SET CONTEXT', context)

    def set_extension(self, extension):
        """agi.set_extension(extension)
        Sets the extension for continuation upon exiting the application.
        No error appears to be produced.  Does not set context or priority
        Use at your own risk.  Ensure that you specify a valid extension.
        """
        self.execute('SET EXTENSION', extension)

    def set_priority(self, priority):
        """agi.set_priority(priority)
        Sets the priority for continuation upon exiting the application.
        No error appears to be produced.  Does not set exten or context
        Use at your own risk.  Ensure that you specify a valid priority.
        """
        self.execute('set priority', priority)

    def goto_on_exit(self, context='', extension='', priority=''):
        context = context or self.env['agi_context']
        extension = extension or self.env['agi_extension']
        priority = priority or self.env['agi_priority']
        self.set_context(context)
        self.set_extension(extension)
        self.set_priority(priority)

    def record_file(self, filename, format='gsm', escape_digits='#', timeout=DEFAULT_RECORD, offset=0, beep='beep'):
        """agi.record_file(filename, format, escape_digits, timeout=DEFAULT_TIMEOUT, offset=0, beep='beep') --> None
        Record to a file until a given dtmf digit in the sequence is received
        The format will specify what kind of file will be recorded.  The timeout 
        is the maximum record time in milliseconds, or -1 for no timeout. Offset 
        samples is optional, and if provided will seek to the offset without 
        exceeding the end of the file
        """
        escape_digits = self._process_digit_list(escape_digits)
        res = self.execute('RECORD FILE', self._quote(filename), format, escape_digits, timeout, offset, beep)['result'][0]
        try:
            return chr(int(res))
        except:
            raise AGIError('Unable to convert result to digit: %s' % res)

    def set_autohangup(self, secs):
        """agi.set_autohangup(secs) --> None
        Cause the channel to automatically hangup at <secs> seconds in the
        future.  Of course it can be hungup before then as well.   Setting to
        0 will cause the autohangup feature to be disabled on this channel.
        """
        self.execute('SET AUTOHANGUP', secs)

    def hangup(self, channel=''):
        """agi.hangup(channel='')
        Hangs up the specified channel.
        If no channel name is given, hangs up the current channel
        """
        self.execute('HANGUP', channel)

    def appexec(self, application, options=''):
        """agi.appexec(application, options='')
        Executes <application> with given <options>.
        Returns whatever the application returns, or -2 on failure to find
        application
        """
        result = self.execute('EXEC', application, self._quote(options))
        res = result['result'][0]
        if res == '-2':
            raise AGIAppError('Unable to find application: %s' % application)
        return res

    def set_callerid(self, number):
        """agi.set_callerid(number) --> None
        Changes the callerid of the current channel.
        """
        self.execute('SET CALLERID', number)

    def channel_status(self, channel=''):
        """agi.channel_status(channel='') --> int
        Returns the status of the specified channel.  If no channel name is
        given the returns the status of the current channel.

        Return values:
        0 Channel is down and available
        1 Channel is down, but reserved
        2 Channel is off hook
        3 Digits (or equivalent) have been dialed
        4 Line is ringing
        5 Remote end is ringing
        6 Line is up
        7 Line is busy
        """
        try:
           result = self.execute('CHANNEL STATUS', channel)
        except AGIHangup:
           raise
        except AGIAppError:
           result = {'result': ('-1','')}

        return int(result['result'][0])

    def set_variable(self, name, value):
        """Set a channel variable.
        """
        self.execute('SET VARIABLE', self._quote(name), self._quote(value))

    def get_variable(self, name):
        """Get a channel variable.

        This function returns the value of the indicated channel variable.  If
        the variable is not set, an empty string is returned.
        """
        try:
           result = self.execute('GET VARIABLE', self._quote(name))
        except AGIResultHangup:
           result = {'result': ('1', 'hangup')}

        res, value = result['result']
        return value

    def get_full_variable(self, name, channel = None):
        """Get a channel variable.

        This function returns the value of the indicated channel variable.  If
        the variable is not set, an empty string is returned.
        """
        try:
           if channel:
              result = self.execute('GET FULL VARIABLE', self._quote(name), self._quote(channel))
           else:
              result = self.execute('GET FULL VARIABLE', self._quote(name))

        except AGIResultHangup:
           result = {'result': ('1', 'hangup')}

        res, value = result['result']
        return value

    def verbose(self, message, level=1):
        """agi.verbose(message='', level=1) --> None
        Sends <message> to the console via verbose message system.
        <level> is the the verbose level (1-4)
        """
        self.execute('VERBOSE', self._quote(message), level)

    def database_get(self, family, key):
        """agi.database_get(family, key) --> str
        Retrieves an entry in the Asterisk database for a given family and key.
        Returns 0 if <key> is not set.  Returns 1 if <key>
        is set and returns the variable in parenthesis
        example return code: 200 result=1 (testvariable)
        """
        family = '"%s"' % family
        key = '"%s"' % key
        result = self.execute('DATABASE GET', self._quote(family), self._quote(key))
        res, value = result['result']
        if res == '0':
            raise AGIDBError('Key not found in database: family=%s, key=%s' % (family, key))
        elif res == '1':
            return value
        else:
            raise AGIError('Unknown exception for : family=%s, key=%s, result=%s' % (family, key, pprint.pformat(result)))

    def database_put(self, family, key, value):
        """agi.database_put(family, key, value) --> None
        Adds or updates an entry in the Asterisk database for a
        given family, key, and value.
        """
        result = self.execute('DATABASE PUT', self._quote(family), self._quote(key), self._quote(value))
        res, value = result['result']
        if res == '0':
            raise AGIDBError('Unable to put vaule in databale: family=%s, key=%s, value=%s' % (family, key, value))
            
    def database_del(self, family, key):
        """agi.database_del(family, key) --> None
        Deletes an entry in the Asterisk database for a
        given family and key.
        """
        result = self.execute('DATABASE DEL', self._quote(family), self._quote(key))
        res, value = result['result']
        if res == '0':
            raise AGIDBError('Unable to delete from database: family=%s, key=%s' % (family, key))

    def database_deltree(self, family, key=''):
        """agi.database_deltree(family, key='') --> None
        Deletes a family or specific keytree with in a family
        in the Asterisk database.
        """
        result = self.execute('DATABASE DELTREE', self._quote(family), self._quote(key))
        res, value = result['result']
        if res == '0':
            raise AGIDBError('Unable to delete tree from database: family=%s, key=%s' % (family, key))

    def noop(self):
        """agi.noop() --> None
        Does nothing
        """
        self.execute('NOOP')

if __name__=='__main__':
    agi = AGI()
    #agi.appexec('festival','Welcome to Klass Technologies.  Thank you for calling.')
    #agi.appexec('festival','This is a test of the text to speech engine.')
    #agi.appexec('festival','Press 1 for sales ')
    #agi.appexec('festival','Press 2 for customer support ')
    #agi.hangup()
    #agi.goto_on_exit(extension='1234', priority='1')
    #sys.exit(0)
    #agi.say_digits('123', [4,'5',6])
    #agi.say_digits([4,5,6])
    #agi.say_number('1234')
    #agi.say_number('01234')  # 668
    #agi.say_number('0xf5')   # 245
    agi.get_data('demo-congrats')
    agi.hangup()
    sys.exit(0)
    #agi.record_file('pyst-test') #FAILS
    #agi.stream_file('demo-congrats', [1,2,3,4,5,6,7,8,9,0,'#','*'])
    #agi.appexec('background','demo-congrats')

    try:
        agi.appexec('backgrounder','demo-congrats')
    except AGIAppError:
        sys.stderr.write("Handled exception for missing application backgrounder\n")

    agi.set_variable('foo','bar')
    agi.get_variable('foo')

    try:
        agi.get_variable('foobar')
    except AGIAppError:
        sys.stderr.write("Handled exception for missing variable foobar\n")

    try:
        agi.database_put('foo', 'bar', 'foobar')
        agi.database_put('foo', 'baz', 'foobaz')
        agi.database_put('foo', 'bat', 'foobat')
        v = agi.database_get('foo', 'bar')
        sys.stderr.write('DBVALUE foo:bar = %s\n' % v)
        v = agi.database_get('bar', 'foo')
        sys.stderr.write('DBVALUE foo:bar = %s\n' % v)
        agi.database_del('foo', 'bar')
        agi.database_deltree('foo')
    except AGIDBError:
        sys.stderr.write("Handled exception for missing database entry bar:foo\n")

    agi.hangup()
