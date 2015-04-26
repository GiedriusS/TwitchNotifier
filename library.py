import configparser
import requests
import sys
from gi.repository import Notify

base_url = 'https://api.twitch.tv/kraken/'
client_id = 'pvv7ytxj4v7i10h0p3s7ewf4vpoz5fc'
head = {'Accept': 'application/vnd.twitch.v3+json',
        'Client-ID': client_id}


class Settings(object):
    '''
    A simple wrapper around configparser to read configuration
    '''
    directory = ''
    cfg = 'twitchnotifier.cfg'
    section = 'messages'
    user_message = '$1 is $2'
    notification_title = '$1'
    notification_content = '$1 is $2'

    def __init__(self, directory):
        '''
        Initialize the object and read the file to get the info

        Positional arguments:
        directory - where the configuration file is stored
        '''
        if not isinstance(directory, str):
            raise TypeError('Wrong type passed to Settings')
        if not directory.strip():
            raise ValueError('Empty directory passed to Settings')

        self.directory = directory
        self.conf = configparser.ConfigParser()
        self.read_file()

    def read_file(self):
        '''
        Read the file and get needed sections/info
        '''
        self.conf.read(self.directory + '/' + self.cfg)
        try:
            opt = self.conf[self.section]
            self.user_message = opt.get('user_message', self.user_message)
            self.notification_title = opt.get('notification_title',
                                              self.notification_title)
            self.notification_content = opt.get('notification_content',
                                                self.notification_content)
        except:
            print('No messages key exists in ' + self.cfg, file=sys.stderr)


class NotifyApi(object):
    '''
    Represents all twitch and libnotify/gobject calls the program needs
    '''
    nick = ''
    verbose = False

    def __init__(self, nick, fmt, verbose=False):
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

        if not Notify.init('TwitchNotifier'):
            raise RuntimeError('Failed to init libnotify')

    def get_followed_channels(self, payload={}):
        '''
        Get a list of channels the user is following

        Positional arguments:
        payload - dictionary converted to args passed in a GET request

        Raises:
        NameError - when the current nickname is invalid

        Returns a list of channels that user follows
        '''
        ret = []
        url = base_url + '/users/' + self.nick + '/follows/channels'

        try:
            r = requests.get(url, headers=head, params=payload)
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

    def check_if_online(self, chan, verb=False):
        '''
        Gets a stream object and returns a tuple in format of
        (formatted_msg, status)

        Positional arguments:
        chan - channel name

        Returns a tuple of format (formatted_msg, status)
        '''
        url = base_url + '/streams/' + chan

        try:
            r = requests.get(url, headers=head)
        except Exception as e:
            print('Exception in check_if_online::requests.get()',
                  '__doc__ = ' + str(e.__doc__), file=sys.stderr, sep='\n')
            return ('', None)

        try:
            json = r.json()
        except ValueError:
            print('Failed to parse json in check_if_online',
                  file=sys.stderr)
            if verb:
                print('r.text: ' + r.text, 'r.status_code: ' +
                      str(r.status_code), 'r.headers: ' + str(r.headers),
                      file=sys.stderr, sep='\n')
            return ('', None)

        if 'error' in json:
            print('Error in returned json object in check_if_online',
                  file=sys.stderr)
            if verb:
                print('r.text: ' + r.text, 'r.status_code: ' +
                      str(r.status_code), 'r.headers: ' + str(r.headers),
                      file=sys.stderr, sep='\n')
            return ('', None)

        return (self.repl(json['stream'], chan, self.fmt.user_message),
                False if 'stream' in json and json['stream'] is None else True)

    def show_notification(self, title, message):
        '''
        Show a notification using libnotify/gobject

        Positional arguments:
        title - notification title
        message - notification message

        Raises:
        RuntimeError - failed to show the notification
        '''
        n = Notify.Notification.new(title, message, 'dialog-information')

        if not n.show():
            raise RuntimeError('Failed to show a notification')

    def get_status(self):
        '''
        Get a list of lists in format of [name, True/False/None]
        True = channel is online, False = channel is offline, None = error
        '''
        ret = []
        offset = 0
        limit = 100

        while True:
            fol = self.get_followed_channels({'offset': offset,
                                              'limit': limit})
            for chan in fol:
                ret.append([chan, None])

            if len(fol) == 0:
                break

            offset = offset + limit

        url = base_url + 'streams?channel=' + ','.join(elem[0] for elem in ret)

        try:
            r = requests.get(url, headers=head)
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

        for el in ret:
            if 'streams' in json:
                for stream in json['streams']:
                    if stream['channel']['name'] == el[0]:
                        el[1] = True

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
        while (i < len(new) - 1) and (i < len(old) - 1):
            if (not new[i][1] is None and not old[i][1] is None and
                    new[i][0] == old[i][0]):
                if new[i][1] and not old[i][1]:
                    try:
                        self.show_notification(new[i][0], 'came online')
                    except RuntimeError:
                        print('Failed to show notification!',
                              file=sys.stderr)
                        print(new[i][0] + ' came online')

                if not new[i][1] and old[i][1]:
                    try:
                        self.show_notification(new[i][0], 'went offline')
                    except RuntimeError:
                        print('Failed to show notification!',
                              file=sys.stderr)
                        print(new[i][0] + ' went offline')
            i = i + 1

    def repl(self, stream, chan, msg):
        '''
        Returns msg with replaced stuff from stream
        Note that only $1 and $2 will be replaced if stream is offline

        Keys:
        $1 - streamer username
        $2 - offline/online
        $3 - game
        $4 - viewers
        $5 - average FPS
        $6 - views
        $7 - followers
        $8 - language
        $9 - status

        Positional arguments:
        stream - stream object (a dictionary with certain values)
        chan - channel name
        msg - a format string

        Returns msg formatted
        '''
        ret = msg
        ret = ret.replace('$2', 'online' if stream else 'offline')
        ret = ret.replace('$1', chan)

        if stream:
            ret = ret.replace('$3', stream['channel']['game'])
            ret = ret.replace('$4', str(stream['viewers']))
            ret = ret.replace('$5', str(stream['average_fps']))
            ret = ret.replace('$6', str(stream['channel']['views']))
            ret = ret.replace('$7', str(stream['channel']['followers']))
            ret = ret.replace('$8', stream['channel']['language'])
            ret = ret.replace('$9', stream['channel']['status'])
        return ret

if __name__ == '__main__':
    st = Settings('/home/giedrius/.config')

    core = NotifyApi('Xangold', st, True)
    list_of_chans = core.get_followed_channels()
    print(list_of_chans, len(list_of_chans))
    stat = core.get_status()
    print(core.check_if_online('nadeshot'))
    print(stat)
