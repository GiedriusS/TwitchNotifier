'''
TwitchTV, Notify and config reading abstractions for TwitchNotifier
'''
import configparser
import time
import re
import sys
import os
import requests
import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify

BASE_URL = 'https://api.twitch.tv/kraken'
CLIENT_ID = 'pvv7ytxj4v7i10h0p3s7ewf4vpoz5fc'
HEAD = {'Accept': 'application/vnd.twitch.v3+json',
        'Client-ID': CLIENT_ID}
LIMIT = 100
SECTION = 'messages'


class Settings(object):
    '''
    Saves the user configuration and can parse it from files or environment
    variables.
    '''
    cfg = ''

    user_message = {'on': '$1 is $2', 'off': '$1 is $2'}
    notification_title = {'on': '$1', 'off': '$1'}
    notification_cont = {'on': 'is $2', 'off': 'is $2'}
    list_entry = {'on': '$1', 'off': '$1'}
    log_fmt = {'on': '(${%d %H:%M:%S}) $1 is $2', 'off': '(${%d %H:%M:%S}) $1 is $2'}

    def __init__(self, cfg):
        '''
        Initialize the object and parse cfg and environment variables to get the
        configuration

        Positional arguments:
        cfg - full path to the configuration file

        Raises:
        TypeError - cfg is not a string
        ValueError - cfg is empty
        '''
        if not isinstance(cfg, str):
            raise TypeError('Wrong type passed to Settings')
        if not cfg.strip():
            raise ValueError('Empty string passed to Settings')

        self.cfg = cfg
        self.conf = configparser.ConfigParser()
        self.read_file()
        self.environment()

    def environment(self):
        '''
        Parse user settings from the environment variables
        '''
        self.user_message['on'] = os.getenv('user_message', self.user_message['on'])
        self.user_message['off'] = os.getenv('user_message_off',
                                             self.user_message['off'])
        self.notification_title['on'] = os.getenv('notification_title',
                                                  self.notification_title['on'])
        self.notification_title['off'] = os.getenv('notification_title_off',
                                                   self.notification_title['off'])
        self.notification_cont['on'] = os.getenv('notification_content',
                                                 self.notification_cont['on'])
        self.notification_cont['off'] = os.getenv('notification_content_off',
                                                  self.notification_cont['off'])
        self.list_entry['on'] = os.getenv('list_entry', self.list_entry['on'])
        self.list_entry['off'] = os.getenv('list_entry_off', self.list_entry['off'])
        self.log_fmt['on'] = os.getenv('log_fmt', self.log_fmt['on'])
        self.log_fmt['off'] = os.getenv('log_fmt_off', self.log_fmt['off'])

    def read_file(self):
        '''
        Read self.cfg and parse user configuration from that file
        '''
        try:
            self.conf.read(self.cfg)
        except configparser.MissingSectionHeaderError:
            return

        if SECTION not in self.conf:
            print('Missing section "' + SECTION + '" in ' + self.cfg,
                  file=sys.stderr)
            return

        opt = self.conf[SECTION]
        self.user_message['on'] = opt.get('user_message', self.user_message['on'],
                                          raw=True)
        self.user_message['off'] = opt.get('user_message_off',
                                           self.user_message['off'],
                                           raw=True)
        self.notification_title['on'] = opt.get('notification_title',
                                                self.notification_title['on'],
                                                raw=True)
        self.notification_title['off'] = opt.get('notification_title_off',
                                                 self.notification_title['off'],
                                                 raw=True)
        self.notification_cont['on'] = opt.get('notification_content',
                                               self.notification_cont['on'],
                                               raw=True)
        self.notification_cont['off'] = opt.get('notification_content_off',
                                                self.notification_cont['off'],
                                                raw=True)
        self.list_entry['on'] = opt.get('list_entry', self.list_entry['on'], raw=True)
        self.list_entry['off'] = opt.get('list_entry_off',
                                         self.list_entry['off'],
                                         raw=True)
        self.log_fmt['on'] = opt.get('log_fmt', self.log_fmt['on'], raw=True)
        self.log_fmt['off'] = opt.get('log_fmt_off', self.log_fmt['off'],
                                      raw=True)


class NotifyApi(object):
    '''
    A wrapper around calls to the TTV API
    '''
    nick = ''
    verbose = False
    fhand = None
    statuses = {}

    def __init__(self, nick, fmt, logfile, verbose=False):
        '''
        Initialize the API with various options

        Positional arguments:
        nick - nickname of the user
        fmt - a Settings object
        logfile - location of the log file
        verbose - if we should be verbose in output

        Raises:
        TypeError - arguments with wrong types were passed to NotifyApi
        '''
        if not isinstance(nick, str) or not isinstance(verbose, bool):
            raise TypeError('Invalid variable type passed to NotifyApi')

        self.nick = nick
        self.verbose = verbose
        self.fmt = fmt
        if logfile is not None:
            self.fhand = open(logfile, 'a')

    def get_followed_channels(self, payload=None):
        '''
        Get a list of channels the user is following

        Positional arguments:
        payload - a dict that will be converted to args which will be passed in
        a GET request

        Raises:
        NameError - when the current nickname is invalid

        Returns a list of channels that user follows
        '''
        ret = []
        cmd = '/users/' + self.nick + '/follows/channels'

        if payload is None:
            payload = {}

        json = self.access_kraken(cmd, payload)
        if json is None:
            return ret

        if 'status' in json and json['status'] == 404:
            raise NameError(self.nick + ' is a invalid nickname!')

        if 'follows' in json:
            for chan in json['follows']:
                ret.append(chan['channel']['name'])

        return ret

    def __del__(self):
        '''Clean up everything'''
        Notify.uninit()
        if self.fhand is not None:
            self.fhand.close()

    def access_kraken(self, cmd, payload=None):
        '''
        Generic wrapper around kraken calls

        Positional arguments:
        cmd - command such as '/streams'
        payload - dict of arguments to send with the request

        Returns:
        None - error occured
        Otherwise, json response
        '''
        url = BASE_URL + cmd

        if payload is None:
            payload = {}

        try:
            req = requests.get(url, headers=HEAD, params=payload)
        except requests.exceptions.RequestException as ex:
            print('Exception in access_kraken::requests.get()',
                  '__doc__ = ' + str(ex.__doc__), file=sys.stderr, sep='\n')
            return None

        if self.verbose:
            print('-'*20, file=sys.stderr)
            print('cmd: ' + cmd, 'payload: ' + str(payload), file=sys.stderr, sep='\n')
            print('req.text: ' + req.text, 'req.status_code: ' +
                  str(req.status_code), 'req.headers: ' + str(req.headers),
                  file=sys.stderr, sep='\n')
            print('-'*20, file=sys.stderr)

        if req.status_code == requests.codes.bad:
            print('Kraken request returned bad code, bailing', file=sys.stderr)
            return None

        try:
            json = req.json()
        except ValueError:
            print('Failed to parse json in access_kraken',
                  file=sys.stderr)
            return None
        return json

    def check_if_online(self, chan):
        '''
        Check the online status of channels in a list and get formatted messages

        Positional arguments:
        chan - list of channel names

        Returns a dictionary of tuples of format (status, formatted_msg)
        '''
        ret = {}
        i = 0

        if len(chan) == 0:
            if self.verbose:
                print('channel passed to check_if_online is empty',
                      file=sys.stderr)
            return ret

        cont = True
        while cont:
            payload = {'channel': ','.join(chan[i*LIMIT:(i+1)*LIMIT]), 'limit': LIMIT,
                       'offset': 0}
            resp = self.access_kraken('/streams', payload)
            if resp is None or 'streams' not in resp:
                break

            for stream in resp['streams']:
                name = stream['channel']['name']
                ret[name] = (True, repl(stream, name, self.fmt.user_message['on']))

            i += 1
            cont = i*LIMIT < len(chan)

        for name in chan:
            if name not in ret:
                ret[name] = (False, repl(None, name, self.fmt.user_message['off']))

        return ret

    def get_status(self):
        '''
        Get a list of dictionaries in format of {'name': (True/False/None,
        stream_obj)} of self.nick followed channels

        True = channel is online, False = channel is offline, None = error
        '''
        followed_chans = []
        ret = {}
        offset = 0
        i = 0

        while True:
            fol = self.get_followed_channels({'offset': offset,
                                              'limit': LIMIT})
            for chan in fol:
                followed_chans.append(chan)

            if len(fol) == 0:
                break

            offset = offset + LIMIT

        if len(followed_chans) == 0:
            return ret

        cmd = '/streams'
        while True:
            payload = {'channel': ','.join(followed_chans[i*LIMIT:(i+1)*LIMIT]),
                       'offset': 0, 'limit': LIMIT}
            json = self.access_kraken(cmd, payload)
            if json and 'streams' in json:
                for stream in json['streams']:
                    ret[stream['channel']['name']] = (True, stream)

            i += 1
            if i*LIMIT > len(followed_chans):
                break

        for name in followed_chans:
            if name not in ret:
                ret[name] = (False, None)

        return ret

    def inform_user(self, online, data, name):
        '''
        Actually inform the user about the change in status.

        Positional arguments:
        online - is the user `name' online now or not
        data - information about the user from self.get_status()
        name - actual name of the user we are talking about
        '''
        if online is True:
            title = repl(data[1], name, self.fmt.notification_title['on'])
            message = repl(data[1], name, self.fmt.notification_cont['on'])
            self.log(data[1], name, self.fmt.log_fmt['on'])
        else:
            title = repl(data[1], name, self.fmt.notification_title['off'])
            message = repl(data[1], name, self.fmt.notification_cont['off'])
            self.log(data[1], name, self.fmt.log_fmt['off'])

        try:
            show_notification(title, message)
        except RuntimeError:
            print('Failed to show a notification:',
                  file=sys.stderr)
            print('Title: ' + title, file=sys.stderr)
            print('Message: ' + message, file=sys.stderr)

    def diff(self, new):
        '''
        Check if there is a difference between statuses in `new' and the
        dictionary inside the class and if there is then notify the user about
        the change

        Positional arguments:
        new - dictionary returned from get_status()
        '''
        for name, data in new.items():
            ison = data[0]
            if ison is None:
                continue
            if name not in self.statuses:
                self.statuses[name] = ison
                continue
            if ison == self.statuses[name]:
                continue

            if ison is True and not self.statuses[name] is True:
                self.inform_user(True, data, name)
            elif self.statuses[name] is True and not ison is True:
                self.inform_user(False, data, name)

            self.statuses[name] = ison

        Notify.uninit()

    def log(self, stream, chan, msg):
        '''
        Write formatted msg to self.fl if it's open

        Positional arguments:
        stream - stream object
        chan - channel name
        msg - a format string
        '''
        if self.fhand is None:
            return
        self.fhand.write(repl(stream, chan, msg) + '\n')
        self.fhand.flush()


def repl(stream, chan, msg):
    '''
    Format msg according to the stream object
    Note that only $1 and $2 will be replaced if stream is offline

    Keys:
    $1 - streamer username
    $2 - offline/online
    $3 - game
    $4 - viewers
    $5 - status
    $6 - language
    $7 - average FPS
    $8 - followers
    $9 - views
    ${} - everything between {} will be replaced as if strftime is applied

    Positional arguments:
    stream - stream object (a dictionary with certain values)
    chan - channel name
    msg - a format string

    Returns msg formatted
    '''
    ret = msg
    ret = ret.replace('$2', 'online' if stream else 'offline')
    ret = ret.replace('$1', chan)
    ret = re.sub(r'\$\{(.*)\}', lambda x: time.strftime(x.group(1)), ret)

    if stream and isinstance(stream, dict):
        ret = ret.replace('$3', str(stream.get('game', '')))
        ret = ret.replace('$4', str(stream.get('viewers', '')))
        ret = ret.replace('$5', stream.get('channel', {}).get('status',
                                                              ''))
        ret = ret.replace('$6', stream.get('channel', {}).get('language',
                                                              ''))
        ret = ret.replace('$7', str(stream.get('average_fps', '')))
        ret = ret.replace('$8', str(stream.get('channel',
                                               {}).get('followers', '')))
        ret = ret.replace('$9', str(stream.get('channel', {}).get('views',
                                                                  '')))

    return ret


def show_notification(title, message):
    '''
    Show a notification using libnotify/gobject

    Positional arguments:
    title - notification title
    message - notification message

    Raises:
    RuntimeError - failed to show the notification

    Note:
    This function is designed to be called a few times in a row so
    make sure to call Notify.uninit() afterwards
    '''
    if Notify.is_initted() is False:
        Notify.init('TwitchNotifier')

    if Notify.is_initted() is False:
        raise RuntimeError('Failed to init notify')

    notif = Notify.Notification.new(title, message)

    if not notif.show():
        raise RuntimeError('Failed to show a notification')
