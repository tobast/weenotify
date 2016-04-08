# weenotify
A minimalist Weechat client using the Weechat relay protocol to retrieve notifications from a bouncer and display them locally.

## Disclaimer
This program does not intend to be robust. That is, it will most certainly crash if you do not configure it properly, or feed it weird data. It does only intend to be a simply-written, working notification gatherer for Weechat.

This program does only support *unencrypted* Weechat Relay protocol. That is, your password and IRC data *will be transmitted without encryption*. Thus, it is *most advised* to connect it to your Weechat Relay *through a SSH/SSL/anything-that-encrypts tunnel*. The `ensure-background` option (see below) makes it really easy, use it!

## Running

### By hand
You can run this client simply by running ``./weenotify.py`` with the right options (see below).

### As a systemd user daemon
You can also use a systemd user daemon to automatically run weenotify in the background: see for instance https://wiki.archlinux.org/index.php/Systemd/User.

A basic systemd service file can be found in `systemd/`: you have to edit it to choose your install path in it. Then, place the weenotify.service file in ~/.local/share/systemd/user/. You can control weenotify with `systemctl --user X weenotify`, where `X` is either `start`, `stop`, `restart`, `enable`, `status`, ...

## Configuration
Each of these options can be passed, prefixed with `--`, directly through the command line, or be saved in a configuration file. The default configuration file (loaded if no configuration file is specified) is `~/.weenotifyrc`.

* `server`: address of the Weechat relay.
* `port`: port of the Weechat relay.
* `ensure-background`: runs the following command in the background. Periodically checks whether it is still open, reruns it if necessary, and resets the connection to the server if it was lost in the process. Mostly useful to establish a SSH tunnel: eg., to ensure that a SSH tunnel will be opened and closed with the application, set `ensure-background` to `ssh irc@example.com -o ServerAliveInterval=10 -L [LOCALPORT]:localhost:[RELAYPORT] -N` (note: the `-o` is essential to let you automatically reconnect when you loose the connection).
* `reconnect-delay`: delay between two attempts to reconnect after being disconnected from the server.
* `highlight-action`: program to invoke when highlighted. It will be called with the IRC line that triggered the highlight as its first argument, the message sender as its second argument, and the buffer name as its third.
* `privmsg-action`:  program to invoke when receiving a private message. Has the same behavior as `highlight-action`.
* `log-file`: log file path. If omitted, the logs will be directly printed.

The configuration file itself has a very simple syntax: to set the property [property] to the value [value], add the line `[property]=[value]`. A comment starts with a `#` and spans to the end of the line.

You can also pass to the program a few parameters that have no equivalent config file property:
* `-h`: display a short help message and exits,
* `-v`: verbose mode, turns on debug log messages,
* `-c` or `--config`: specifies a configuration file that will be read instead of the default configuration file.

Note that a command line option will always prevail on a configuration file option, shall there be a conflict.
