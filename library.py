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
        directory - where the configuration file is stored
        '''
        if not isinstance(cfg, str):
            raise TypeError('Wrong type passed to Settings')
        if not cfg.strip():
            raise ValueError('Empty string passed to Settings')

        self.cfg = cfg
        self.conf = configparser.ConfigParser()
        self.read_file()

        # Environment variables can override settings
        self.user_message = os.getenv('user_message', self.user_message)
        self.user_message_off = os.getenv('user_message_off',
                                          self.user_message_off)
        self.notification_title = os.getenv('notification_title',
                                            self.notification_title)
        self.notification_cont = os.getenv('notification_cont',
                                           self.notification_cont)
        self.list_entry = os.getenv('list_entry', self.list_entry)
        self.log_fmt = os.getenv('log_fmt', self.log_fmt)
        self.notification_title_off = os.getenv('notification_title_off',
                                                self.notification_title_off)
        self.notification_cont_off = os.getenv('notification_cont_off',
                                               self.notification_cont_off)
        self.list_entry_off = os.getenv('list_entry_off', self.list_entry_off)
        self.log_fmt_off = os.getenv('log_fmt_off', self.log_fmt_off)

    def read_file(self):
        '''
        Read the file and get needed sections/info
        '''
        self.conf.read(self.cfg)
        try:
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
        except:
            print('Wrong or missing options in ' + self.cfg, file=sys.stderr)


class NotifyApi(object):
    '''
    Represents all twitch and libnotify/gobject calls the program needs
    '''
    nick = ''
    verbose = False
    fl = None

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
            self.fl = open(logfile, 'a')

        if not Notify.init('TwitchNotifier'):
            raise RuntimeError('Failed to init libnotify')

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
        url = BASE_URL + '/users/' + self.nick + '/follows/channels'

        if payload is None:
            payload = {}

        try:
            r = requests.get(url, headers=HEAD, params=payload)
        except Exception as e:
            print('Exception in get_followed_channels::requests.get()',
                  '__doc__ = ' + str(e.__doc__), file=sys.stderr, sep='\n')
            return ret

        try:
            json = r.json()
        except ValueError:
            print('Failed to parse json in get_followed_channels()',
                  file=sys.stderr)
            if self.verbose:
                print('r.text: ' + r.text, 'r.status_code: ' +
                      str(r.status_code), 'r.headers: ' + str(r.headers),
                      file=sys.stderr, sep='\n')
            return ret

        if 'status' in json and json['status'] == 404:
            raise NameError(self.nick + ' is a invalid nickname!')

        if 'follows' in json:
            for chan in json['follows']:
                ret.append(chan['channel']['name'])

        return ret

    def __del__(self):
        '''Uninit libnotify object'''
        Notify.uninit()
        if self.fl is not None:
            self.fl.close()

    def check_if_online(self, chan):
        '''
        Gets a stream object and returns a tuple in format of
        (formatted_msg, status)

        Positional arguments:
        chan - channel name

        Returns a tuple of format (formatted_msg, status)
        '''

        if not chan.strip():
            if self.verbose:
                print('channel passed to check_if_online is empty',
                      file=sys.stderr)
            return ('', None)

        url = BASE_URL + '/streams/' + chan

        try:
            r = requests.get(url, headers=HEAD)
        except Exception as e:
            print('Exception in check_if_online::requests.get()',
                  '__doc__ = ' + str(e.__doc__), file=sys.stderr, sep='\n')
            return ('', None)

        try:
            json = r.json()
        except ValueError:
            print('Failed to parse json in check_if_online',
                  file=sys.stderr)
            if self.verbose:
                print('r.text: ' + r.text, 'r.status_code: ' +
                      str(r.status_code), 'r.headers: ' + str(r.headers),
                      file=sys.stderr, sep='\n')
            return ('', None)

        if 'error' in json:
            print('Error in returned json object in check_if_online',
                  file=sys.stderr)
            if self.verbose:
                print('r.text: ' + r.text, 'r.status_code: ' +
                      str(r.status_code), 'r.headers: ' + str(r.headers),
                      file=sys.stderr, sep='\n')
            return ('', None)

        online = False if 'stream' in json and json['stream'] is None else True

        if online:
            return (self.repl(json['stream'], chan, self.fmt.user_message),
                    online)
        else:
            return (self.repl(json['stream'], chan, self.fmt.user_message_off),
                    online)

    def show_notification(self, title, message):
        '''
        Show a notification using libnotify/gobject

        Positional arguments:
        title - notification title
        message - notification message

        Raises:
        RuntimeError - failed to show the notification
        '''
        n = Notify.Notification.new(title, message)

        if not n.show():
            raise RuntimeError('Failed to show a notification')

    def get_status(self):
        '''
        Get a list of lists in format of [name, True/False/None, stream_obj]
        True = channel is online, False = channel is offline, None = error
        '''
        ret = []
        offset = 0
        limit = 100

        while True:
            fol = self.get_followed_channels({'offset': offset,
                                              'limit': limit})
            for chan in fol:
                ret.append([chan, None, None])

            if len(fol) == 0:
                break

            offset = offset + limit

        url = BASE_URL + 'streams?channel=' + ','.join(elem[0] for elem in ret)

        try:
            r = requests.get(url, headers=HEAD)
        except Exception as e:
            print('Exception in get_status::requests.get()',
                  '__doc__ = ' + str(e.__doc__), file=sys.stderr, sep='\n')
            return ret

        try:
            json = r.json()
        except ValueError:
            print('Failed to parse json in get_status',
                  file=sys.stderr)
            return ret

        if 'streams' in json:
            for el in ret:
                for stream in json['streams']:
                    if stream['channel']['name'] == el[0]:
                        el[1] = True
                        el[2] = stream

        # Turn all None channels into False
        # Because we have already passed the part with exceptions
        for el in ret:
            if el[1] is None:
                el[1] = False

        return ret

    def diff(self, new, old):
        '''
        Computes diff between two lists returned from get_status() and notifies

        Positional arguments:
        new - newer list returned from get_status()
        old - older list returned from get_status()
        '''
        i = 0
        while i < len(new) and i < len(old):
            if (not new[i][1] is None and not old[i][1] is None and
                    new[i][0] == old[i][0]):

                if new[i][1] and not old[i][1]:
                    title = self.repl(new[i][2], new[i][0],
                                      self.fmt.notification_title)
                    message = self.repl(new[i][2], new[i][0],
                                        self.fmt.notification_cont)
                    self.log(new[i][2], new[i][0], self.fmt.log_fmt)
                    try:
                        self.show_notification(title, message)
                    except RuntimeError:
                        print('Failed to show notification!',
                              file=sys.stderr)
                        print(new[i][0] + ' is online')

                elif not new[i][1] and old[i][1]:
                    title = self.repl(new[i][2], new[i][0],
                                      self.fmt.notification_title_off)
                    message = self.repl(new[i][2], new[i][0],
                                        self.fmt.notification_cont_off)
                    self.log(new[i][2], new[i][0], self.fmt.log_fmt_off)
                    try:
                        self.show_notification(title, message)
                    except RuntimeError:
                        print('Failed to show notification!',
                              file=sys.stderr)
                        print(new[i][0] + ' is offline')
            i = i + 1

    def log(self, stream, chan, msg):
        '''
        Write formatted msg to self.fl if it's open

        Positional arguments:
        stream - stream object
        chan - channel name
        msg - a format string
        '''
        if self.fl is None:
            return
        self.fl.write(self.repl(stream, chan, msg) + '\n')
        self.fl.flush()

    def repl(self, stream, chan, msg):
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
            ret = ret.replace('$8', stream.get('channel', {}).get('followers',
                                                                  ''))
            ret = ret.replace('$9', stream.get('channel', {}).get('views',
                                                                  ''))

        return ret

if __name__ == '__main__':
    ST = Settings('/home/giedrius/.config/twitchnotifier.cfg')

    CORE = NotifyApi('Xangold', ST, '/home/giedrius/log', True)
    LIST_OF_CHANS = CORE.get_followed_channels()
    print(LIST_OF_CHANS, len(LIST_OF_CHANS))
    STAT = CORE.get_status()
    print(CORE.check_if_online('nadeshot'))
    print(STAT)
    CORE.show_notification('Hello', 'From TwitchNotifier')
