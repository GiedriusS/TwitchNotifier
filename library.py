'''
TwitchTV and config reading abstractions for TN
'''
import configparser
import time
import re
import requests
import sys
import os
from gi.repository import Notify

BASE_URL = 'https://api.twitch.tv/kraken/'
CLIENT_ID = 'pvv7ytxj4v7i10h0p3s7ewf4vpoz5fc'
HEAD = {'Accept': 'application/vnd.twitch.v3+json',
        'Client-ID': CLIENT_ID}
LIMIT = 100


class Settings(object):
    '''
    A simple wrapper around configparser to read configuration
    '''
    cfg = ''
    section = 'messages'

    user_message = '$1 is $2'
    user_message_off = '$1 is $2'

    notification_title = '$1'
    notification_cont = 'is $2'
    notification_title_off = '$1'
    notification_cont_off = 'is $2'

    list_entry = '$1'
    list_entry_off = '$1'

    log_fmt = '(${%d %H:%M:%S}) $1 is $2'
    log_fmt_off = '(${%d %H:%M:%S}) $1 is $2'

    def __init__(self, cfg):
        '''
        Initialize the object and read the file to get the info

        Positional arguments:
        cfg - full path to the configuration file
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
        Read environment variables into the settings
        '''
        self.user_message = os.getenv('user_message', self.user_message)
        self.user_message_off = os.getenv('user_message_off',
                                          self.user_message_off)
        self.notification_title = os.getenv('notification_title',
                                            self.notification_title)
        self.notification_cont = os.getenv('notification_content',
                                           self.notification_cont)
        self.list_entry = os.getenv('list_entry', self.list_entry)
        self.log_fmt = os.getenv('log_fmt', self.log_fmt)
        self.notification_title_off = os.getenv('notification_title_off',
                                                self.notification_title_off)
        self.notification_cont_off = os.getenv('notification_content_off',
                                               self.notification_cont_off)
        self.list_entry_off = os.getenv('list_entry_off', self.list_entry_off)
        self.log_fmt_off = os.getenv('log_fmt_off', self.log_fmt_off)

    def read_file(self):
        '''
        Read the file and get needed sections/info
        '''
        try:
            self.conf.read(self.cfg)
        except configparser.MissingSectionHeaderError:
            print(self.cfg + ' contains no section headers!', file=sys.stderr)
            return

        if self.section not in self.conf:
            print('Missing section in ' + self.cfg, file=sys.stderr)
            return

        opt = self.conf[self.section]
        self.user_message = opt.get('user_message', self.user_message,
                                    raw=True)
        self.user_message_off = opt.get('user_message_off',
                                        self.user_message_off,
                                        raw=True)
        self.notification_title = opt.get('notification_title',
                                          self.notification_title,
                                          raw=True)
        self.notification_title_off = opt.get('notification_title_off',
                                              self.notification_title_off,
                                              raw=True)
        self.notification_cont = opt.get('notification_content',
                                         self.notification_cont,
                                         raw=True)
        self.notification_cont_off = opt.get('notification_content_off',
                                             self.notification_cont_off,
                                             raw=True)
        self.list_entry = opt.get('list_entry', self.list_entry, raw=True)
        self.list_entry_off = opt.get('list_entry_off',
                                      self.list_entry_off,
                                      raw=True)
        self.log_fmt = opt.get('log_fmt', self.log_fmt, raw=True)
        self.log_fmt_off = opt.get('log_fmt_off', self.log_fmt_off,
                                   raw=True)


class NotifyApi(object):
    '''
    Represents all twitch and libnotify/gobject calls the program needs
    '''
    nick = ''
    verbose = False
    fhand = None

    def __init__(self, nick, fmt, logfile, verbose=False):
        '''
        Initialize the object with a nick and verbose option

        Positional arguments:
        nick - nickname of the user
        fmt - a Settings object
        verbose - if we should be verbose in output
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
        payload - dictionary converted to args passed in a GET request

        Raises:
        NameError - when the current nickname is invalid

        Returns a list of channels that user follows
        '''
        ret = []
        cmd = 'users/' + self.nick + '/follows/channels'

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
        payload - arguments to send over the request

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

        if req.status_code == requests.codes.bad:
            print('Kraken request returned bad code, bailing', file=sys.stderr)
            return None

        try:
            json = req.json()
        except ValueError:
            print('Failed to parse json in access_kraken',
                  file=sys.stderr)
            if self.verbose:
                print('req.text: ' + req.text, 'req.status_code: ' +
                      str(req.status_code), 'req.headers: ' + str(req.headers),
                      file=sys.stderr, sep='\n')
            return None
        return json

    def check_if_online(self, chan):
        '''
        Gets a list of tuples in format of (channel, status, formatted_msg)

        Positional arguments:
        chan - list of channel names

        Returns a list of tuples of format (channel, status, formatted_msg)
        '''
        ret = []

        if len(chan) == 0:
            if self.verbose:
                print('channel passed to check_if_online is empty',
                      file=sys.stderr)
            return ret

        offset = 0
        cont = True
        while cont:
            payload = {'channel': ','.join(chan), 'limit': LIMIT,
                       'offset': offset}
            resp = self.access_kraken('/streams', payload)
            if resp is None:
                break

            for stream in resp['streams']:
                ret.append((stream['channel']['name'], True,
                            repl(stream, stream['channel']['name'],
                                 self.fmt.user_message)))
            offset = offset + LIMIT
            cont = len(resp['streams']) > 0

        names = [a[0] for a in ret]
        for elem in chan:
            if elem not in names and len(str.strip(elem)) > 0:
                ret.append((elem, False, repl(None, elem,
                                              self.fmt.user_message_off)))
        return ret

    def get_status(self):
        '''
        Get a list of lists in format of [name, True/False/None, stream_obj]
        True = channel is online, False = channel is offline, None = error
        '''
        ret = []
        offset = 0

        while True:
            fol = self.get_followed_channels({'offset': offset,
                                              'limit': LIMIT})
            for chan in fol:
                ret.append([chan, None, None])

            if len(fol) == 0:
                break

            offset = offset + LIMIT

        cmd = 'streams'
        payload = {'channel': ','.join(elem[0] for elem in ret)}
        json = self.access_kraken(cmd, payload)

        if json and 'streams' in json:
            for elem in ret:
                for stream in json['streams']:
                    if stream['channel']['name'] == elem[0]:
                        elem[1] = True
                        elem[2] = stream

        # Turn all None channels into False
        # Because we have already passed the part with exceptions
        for elem in ret:
            if elem[1] is None:
                elem[1] = False

        return ret

    def diff(self, new, old):
        '''
        Computes diff between two lists returned from get_status() and notifies

        Positional arguments:
        new - newer list returned from get_status()
        old - older list returned from get_status()
        '''
        i = 0
        Notify.init('TwitchNotifier')
        while i < len(new) and i < len(old):
            if (not new[i][1] is None and not old[i][1] is None and
                    new[i][0] == old[i][0]):

                if new[i][1] and not old[i][1]:
                    title = repl(new[i][2], new[i][0],
                                 self.fmt.notification_title)
                    message = repl(new[i][2], new[i][0],
                                   self.fmt.notification_cont)
                    self.log(new[i][2], new[i][0], self.fmt.log_fmt)
                    if Notify.is_initted() is False:
                        print(new[i][0] + ' is online')
                        continue

                    try:
                        show_notification(title, message)
                    except RuntimeError:
                        print('Failed to show notification!',
                              file=sys.stderr)
                        print(new[i][0] + ' is online')

                elif not new[i][1] and old[i][1]:
                    title = repl(new[i][2], new[i][0],
                                 self.fmt.notification_title_off)
                    message = repl(new[i][2], new[i][0],
                                   self.fmt.notification_cont_off)
                    self.log(new[i][2], new[i][0], self.fmt.log_fmt_off)
                    if Notify.is_initted() is False:
                        print(new[i][0] + ' is offline')
                        continue

                    try:
                        show_notification(title, message)
                    except RuntimeError:
                        print('Failed to show notification!',
                              file=sys.stderr)
                        print(new[i][0] + ' is offline')
            i = i + 1
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
    Returns msg with replaced stuff from stream
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
        ret = ret.replace('$7', str(stream.get('average_fps')))
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

if __name__ == '__main__':
    ST = Settings('/home/giedrius/.config/twitchnotifier.cfg')

    CORE = NotifyApi('Xangold', ST, '/home/giedrius/log', True)
    LIST_OF_CHANS = CORE.get_followed_channels()
    print(LIST_OF_CHANS, len(LIST_OF_CHANS))
    STAT = CORE.get_status()
    print(CORE.check_if_online('nadeshot'))
    print(STAT)
    show_notification('Hello', 'From TwitchNotifier')
    Notify.uninit()
