from distutils.core import setup

setup(name='TwitchNotifier',
      version='0.1',
      description='A tool that sits in the background and notifies you using libnotify if a channel you follow comes online or goes offline',
      author='Giedrius Statkevičius',
      author_email='giedrius.statkevicius@gmail.com',
      url='https://github.com/GiedriusS/TwitchNotifier',
      scripts=['twitchnotifier'],
      py_modules=['library.py'],
      )
