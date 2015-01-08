# TwitchNotifier
A simple python application that sits in the background and notifies you when some channel you follow comes up online or goes offline
Uses twitch v2 api.

# Requirements
| Name            | Version   |
| --------------- | --------- |
| python-requests | >=2.5.1   |
| libnotify       | >=0.7.6   |
| python-gobject  | >= 3.14.0 |
| python          | >= 3.4.2  |

# Options
| Option         | Explanation                     |
| -------------- | ------------------------------- |
| -h/--help      | Print help message              |
| -t/--token     | OAUTH token                     |
| -i/--interval  | Interval between checks         |
| -n/--online    | Only check for online channels  |
| -f/--offline   | Only check for offline channels |
