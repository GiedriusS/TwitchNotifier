# TwitchNotifier
A simple python application that sits in the background and notifies you when some channel you follow comes up online or goes offline.

Optionally it can only check for offline/online channels once and exit using options -n/--online or -f/--offline. Also, if you pass -u/--user USER then TwitchNotifier will only check the status of USER and exit. Atleast -c/--nick or -u/--user has to be passed. If both are then -u/--user takes precendence. 

Uses twitch v3 api.

# Message configuration
Now you can configure the message format TwitchNotifier uses! Create a file called "twitchnotifier.cfg" in $XDG\_CONFIG\_HOME (or $HOME/.config, or /.config). You can look at twitchnotifier.cfg for a example. There has to be a section called "messages" with "user\_message", "notification\_title" and "notification\_content" (and with \_off suffix). Explanations of each key:

| Key                              | Explanation                                                     | 
| -------------------------------- | --------------------------------------------------------------- |
| $1                               | Channel name                                                    |
| $2                               | 'online' if channel is online, 'offline' if channel is offline  |
| $3                               | (Only if online) Game name                                      |
| $4                               | (Only if online) Number of viewers                              |
| $5                               | (Only if online) Status or IOW text above the player            |
| $6                               | (Only if online) Language                                       |
| $7                               | (Only if online) Average FPS                                    |

You don't have to reload twitchnotifier to use new configuration! Send SIGHUP to the TwitchNotifier process to make it reload the configuration. For example: `killall -s HUP twitchnotifier`.

# Usage
| Command                          | Explanation                                       |
| -------------------------------- | ------------------------------------------------- |
| twitchnotifier -u nadeshot       | Check if nadeshot is online                       |
| twitchnotifier -c Xangold        | Watch followed channels of Xangold                |
| twitchnotifier -c Xangold -n     | Check for online channels followed by Xangold     |
| twitchnotifier -h                | Show help message                                 |

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
| -i/--interval  | Interval between checks         |
| -n/--online    | Only check for online channels  |
| -f/--offline   | Only check for offline channels |
| -v/--verbose   | Enable verbose output           |
| -u/--user      | Check status of user            |
| -c/--nick      | Watch NICK followed channels    |
