Test environment for Mozmill test execution via the command line on Linux.

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

Interactive:   . ./run
Scripted:      ./run mozmill -b /usr/bin/firefox-bin -t ~/mozmill-tests/firefox
