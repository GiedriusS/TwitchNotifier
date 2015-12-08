'''
A python module that setups the program for distribution
'''
from distutils.core import setup

setup(name='TwitchNotifier',
      version='0.4.2',
      description='Daemon that notifies you using libnotify if followed chan '
                  'goes off/on. Optionally only does this once.',
      author='Giedrius Statkevičius',
      author_email='giedrius.statkevicius@gmail.com',
      url='https://github.com/GiedriusS/TwitchNotifier',
      scripts=['twitchnotifier'],
      py_modules=['library'],
     )
