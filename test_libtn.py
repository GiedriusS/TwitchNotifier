import unittest
import libtn

class LibTest(unittest.TestCase):
    def test_get_followed_channels(self):
        api = libtn.NotifyApi('test_account123321', None, None, False)
        list_of_chans = api.get_followed_channels({'offset': 0, 'limit': 1})
        self.assertEqual(list_of_chans[0], 'xangold')
        self.assertEqual(len(list_of_chans), 1)
        list_of_chans = api.get_followed_channels({'offset': 1, 'limit': 1})
        self.assertEqual(len(list_of_chans), 0)
        list_of_chans = api.get_followed_channels({'offset': 0, 'limit': 100})
        self.assertEqual(list_of_chans[0], 'xangold')
        self.assertEqual(len(list_of_chans), 1)
        list_of_chans = api.get_followed_channels({'offset': 1, 'limit': 100})
        self.assertEqual(len(list_of_chans), 0)
        api = libtn.NotifyApi('test_account5555666', None, None, False)
        list_of_chans = api.get_followed_channels({'offset': 0, 'limit': 1})
        self.assertEqual(len(list_of_chans), 0)
        list_of_chans = api.get_followed_channels({'offset': 1, 'limit': 1})
        self.assertEqual(len(list_of_chans), 0)
        api = libtn.NotifyApi('metasigma', None, None, False)
        list_of_chans = api.get_followed_channels({'offset': 0, 'limit': 100})
        list_of_chans2 = api.get_followed_channels({'offset': 100, 'limit': 100})
        self.assertEqual(len(list_of_chans)+len(list_of_chans2) > 100, True)

    def test_check_if_online(self):
        settings = libtn.Settings('/tmp/doesn\'t_exist')
        acc = 'test_account123321'
        api = libtn.NotifyApi(acc, settings, None, False)
        self.assertEqual(api.check_if_online([acc])[acc][0], False)

    def test_diff(self):
        api = libtn.NotifyApi('test_account123321', None, None, False)
        output = {}
        def assign_output(online, _, name):
            output[name] = online
        api.inform_user = assign_output

        # off -> on
        example = {'abc': (False, {})}
        api.diff(example)
        example = {'abc': (True, {})}
        api.diff(example)
        self.assertEqual(output['abc'], True)

        # on -> off
        example = {'abc': (False, {})}
        api.diff(example)
        self.assertEqual(output['abc'], False)

        # off -> error
        example = {'abc': (None, {})}
        api.diff(example)
        self.assertEqual(output['abc'], False)

        # error -> on
        example = {'abc': (True, {})}
        api.diff(example)
        self.assertEqual(output['abc'], True)

        # on -> error
        example = {'abc': (None, {})}
        api.diff(example)
        self.assertEqual(output['abc'], True)

        # error -> off
        example = {'abc': (False, {})}
        api.diff(example)
        self.assertEqual(output['abc'], False)

        # off -> error
        example = {'abc': (None, {})}
        api.diff(example)
        self.assertEqual(output['abc'], False)

        # error -> error
        example = {'abc': (None, {})}
        api.diff(example)
        self.assertEqual(output['abc'], False)

if __name__ == '__main__':
    unittest.main()
