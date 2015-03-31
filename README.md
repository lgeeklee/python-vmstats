python-vmstats
==============

Python script using pyVmomi to get VM statistics

<b>Command line version:</b>

http://www.geeklee.co.uk/python-pyvmomi-get-vm-statistics-from-hypervisor/

<img src="http://www.geeklee.co.uk/wp-content/uploads/2014/04/vm-win-stats-py3.png" alt="Example output">

The script requires the following parameters:

-s HOST, --host HOST : Remote host to connect to.

-u USER, --user USER  : User name to use when connecting to host.

-p PASSWORD, --password PASSWORD : Password to use when connecting to host.

-m VM, --vm VM : Virtual Machine to report.

-i INT, --interval INT : Interval to average the vSphere stats over in minutes

The -p/--password is now optional and if not provided on the command line will prompt instead.


<b>The web version:</b>

http://www.geeklee.co.uk/web-python-pyvmomi-vm-statistics-hypervisor/

<img src="http://www.geeklee.co.uk/wp-content/uploads/2015/03/python-vmstats-web2.png" alt="Example output">


http://www.geeklee.co.uk/object-properties-containerview-pyvmomi/
