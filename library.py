import requests
from gi.repository import Notify


class notify_api(object):
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

    def getFollowedChannels(self, payload={}):
        '''
        Get a list of channels the user is following

        Positional arguments:
        payload - dictionary converted to args passed in a GET request

        Raises:
        NameError - when the current nickname is invalid

        Returns a response object that contains all information
        '''
        url = self.base_url + '/users/' + self.nick + '/follows/channels'
        r = requests.get(url, headers=self.headers, params=payload)

        try:
            json = r.json()
        except ValueError:
            print('[ERROR] Failed to parse json in getFollowedChannels. '
                  'A empty json object was created')
            json = {}
            if self.verbose:
                print('r.text: ' + r.text, '\nr. status_code: ' + str(r.status_code),
                      '\nr.headers: ' + str(r.headers))

        if ('status' in json and json['status'] == 404):
            raise NameError(self.nick + ' is a invalid nickname!')

        ret = []
        for chan in json['follows']:
            ret.append(chan['channel']['name'])

        return ret

    def __del__(self):
        '''Uninit libnotify object'''
        Notify.uninit()

    def checkIfOnline(self, chan):
        '''
        Gets a stream object and sees if it's online

        Positional arguments:
        chan - channel name
        '''
        url = self.base_url + '/streams/' + chan
        r = requests.get(url, headers=self.headers)
        try:
            json = r.json()
        except ValueError:
            print('[ERROR] Failed to parse json in checkIfOnline. '
                  'A empty json object was created')
            json = {}
            if self.verbose:
                print('r.text: ' + r.text, '\nr. status_code: ' + str(r.status_code),
                      '\nr.headers: ' + str(r.headers))

        if 'stream' in json and json['stream'] is None:
            return False
        else:
            return True

    def showNotification(self, title, message):
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

    def getStatus(self):
        '''
        Get a list of tuples in format of (name, true/false)
        1 = channel is online, 0 = channel is offline
        '''
        ret = []
        offset = 0
        while True:
            chans = self.getFollowedChannels({'offset': offset})
            for chan in chans:
                pair = (chan, self.checkIfOnline(chan))
                ret.append(pair)

            if len(chans) == 0:
                break

            offset = offset + 25
        return ret

    def diff(self, a, b):
        '''
        Computes diff between two lists returned from getStatus() and notifies

        Positional arguments:
        a - newer list returned from getStatus()
        b - older list returned from getStatus()
        '''
        i = 0
        while i < len(a) - 1:
            if a[i][1] and not b[i][1]:
                try:
                    self.showNotification(a[i][0], "came online")
                except RuntimeError:
                    print('[ERROR] Failed to show notification!\n'
                          '' + a[i][0] + ' came online')

            elif not a[i][1] and b[i][1]:
                try:
                    self.showNotification(a[i][0], "went offline")
                except RuntimeError:
                    print('[ERROR] Failed to show notification!\n'
                          '' + a[i][0] + ' went offline')

            i = i + 1

if __name__ == '__main__':
    core = notify_api('Xangold')
    list_of_chans = core.getFollowedChannels()
    print(list_of_chans, len(list_of_chans))
    stat = core.getStatus()
    print(core.checkIfOnline('nadeshot'))
    print(stat)
