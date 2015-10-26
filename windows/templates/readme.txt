Test environment for Mozmill test execution via the command line on Windows.

Installation
============

This environment includes easy_install and pip to support additional package
installations.

However once other tools are installed, for example mozmill version updates,
it binds the environment to the current directory.

To use the environment in an alternate location, simply unpack a fresh instance
of the archive.


Usage
=====

The run script can be used in interactive or scripted mode. For the latter,
parameters have to be passed in.

The maximum number of allowed parameters in scripted mode is 9.

Interactive:   run.cmd
Scripted:      run.cmd mozmill -b c:\(path to)\firefox.exe -t c:\mozmill-tests\firefox
