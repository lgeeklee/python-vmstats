python-vmstats
==============

Python script using pyVmomi to get VM statistics

<b>Command line version:</b>

<img src="https://github.com/lgeeklee/python-vmstats/blob/master/vm-win-stats-py3.png" alt="Example output">

The script requires the following parameters:

-s HOST, --host HOST : Remote host to connect to.

-u USER, --user USER  : User name to use when connecting to host.

-p PASSWORD, --password PASSWORD : Password to use when connecting to host.

-m VM, --vm VM : Virtual Machine to report.

-i INT, --interval INT : Interval to average the vSphere stats over in minutes

-c, --cert_check_skip : Skip ssl certificate check

The -p/--password is now optional and if not provided on the command line will prompt instead.


<b>The web version:</b>

<img src="https://github.com/lgeeklee/python-vmstats/blob/master/python-vmstats-web2.png" alt="Example output">


