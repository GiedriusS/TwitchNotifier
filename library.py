import requests
from gi.repository import Notify


class NotifyApi(object):
    '''
    Represents all twitch and libnotify/gobject calls the program needs
    '''
    nick = ''
    token = ''
    base_url = 'https://api.twitch.tv/kraken/'
    headers = {}
    verbose = False

    def __init__(self, nick, token='', verbose=False):
        '''
        Initialize the object with a nick and a optional token

        Positional arguments:
        nick - nickname of the user
        token - a special OAUTH token generated from Twitch
        verbose - if we should be verbose in output
        '''
        if not nick.strip():
            raise ValueError('Nick passed to notify_api '
                             'is not a string!')
        if not isinstance(nick, str) or not isinstance(token, str):
            raise TypeError('Invalid variable passed to notify_api')

        self.nick = nick
        self.token = token
        self.headers = {'Accept': 'application/vnd.twitch.v2+json',
                        'Client-ID': self.token}
        self.verbose = verbose

        if not Notify.init('TwitchNotifier'):
            raise RuntimeError('Failed to init libnotify')

    def get_followed_channels(self, payload={}):
        '''
        Get a list of channels the user is following

        Positional arguments:
        payload - dictionary converted to args passed in a GET request

        Raises:
        NameError - when the current nickname is invalid

        Returns a response object that contains all information
        '''
        url = self.base_url + '/users/' + self.nick + '/follows/channels'

        try:
            r = requests.get(url, headers=self.headers, params=payload)
        except Exception as e:
            print('[ERROR] Exception in get_followed_channels::requests.get().',
                  '\n[ERROR] __doc__ = ' + e.__doc__,
                  '\n[ERROR] __str__ = ' + e.__str__,
                  '\n[ERROR] __traceback__ ' + e.__traceback__)
            return []

        try:
            json = r.json()
        except ValueError:
            print('[ERROR] Failed to parse json in get_followed_channels. '
                  'A empty json object was created')
            json = {}
            if self.verbose:
                print('r.text: ' + r.text, '\nr. status_code: ' +
                      str(r.status_code), '\nr.headers: ' + str(r.headers))

        if ('status' in json and json['status'] == 404):
            raise NameError(self.nick + ' is a invalid nickname!')

        ret = []
        if 'follows' in json:
            for chan in json['follows']:
                ret.append(chan['channel']['name'])

        return ret

    def __del__(self):
        '''Uninit libnotify object'''
        Notify.uninit()

    def check_if_online(self, chan):
        '''
        Gets a stream object and sees if it's online

        Positional arguments:
        chan - channel name
        '''
        url = self.base_url + '/streams/' + chan

        try:
            r = requests.get(url, headers=self.headers)
        except Exception as e:
            print('[ERROR] Exception in check_if_online::requests.get().',
                  '\n[ERROR] __doc__ = ' + e.__doc__,
                  '\n[ERROR] __str__ = ' + e.__str__,
                  '\n[ERROR] __traceback__ ' + e.__traceback__)
            return False

        try:
            json = r.json()
        except ValueError:
            print('[ERROR] Failed to parse json in check_if_online. '
                  'A empty json object was created')
            json = {}
            if self.verbose:
                print('r.text: ' + r.text, '\nr. status_code: ' +
                      str(r.status_code), '\nr.headers: ' + str(r.headers))

        if 'stream' in json and json['stream'] is None:
            return False
        else:
            return True

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
        Get a list of tuples in format of (name, true/false)
        1 = channel is online, 0 = channel is offline
        '''
        ret = []
        offset = 0
        while True:
            chans = self.get_followed_channels({'offset': offset})
            for chan in chans:
                pair = (chan, self.check_if_online(chan))
                ret.append(pair)

            if len(chans) == 0:
                break

            offset = offset + 25
        return ret

    def diff(self, new, old):
        '''
        Computes diff between two lists returned from get_status() and notifies

        Positional arguments:
        new - newer list returned from get_status()
        old - older list returned from get_status()
        '''
        i = 0
        while i < len(new) - 1:
            if new[i][1] and not old[i][1]:
                try:
                    self.show_notification(new[i][0], "came online")
                except RuntimeError:
                    print('[ERROR] Failed to show notification!\n'
                          '' + new[i][0] + ' came online')

            elif not new[i][1] and old[i][1]:
                try:
                    self.show_notification(new[i][0], "went offline")
                except RuntimeError:
                    print('[ERROR] Failed to show notification!\n'
                          '' + new[i][0] + ' went offline')

            i = i + 1

if __name__ == '__main__':
    core = notify_api('Xangold')
    list_of_chans = core.get_followed_channels()
    print(list_of_chans, len(list_of_chans))
    stat = core.get_status()
    print(core.check_if_online('nadeshot'))
    print(stat)
