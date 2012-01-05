#!/usr/bin/env python

import fileinput
import glob
import logging
import optparse
import os
import subprocess
import shutil
import sys
import urllib
import zipfile

from os.path import join as path_join


URL_MSYS = "http://sourceforge.net/projects/mingw/files/MSYS/BaseSystem/msys-core/msys-1.0.11/MSYS-1.0.11.exe/download"
URL_MINTTY = "http://mintty.googlecode.com/files/mintty-1.0.1-msys.zip"
URL_VIRTUALENV = "https://bitbucket.org/ianb/virtualenv/raw/1.5.2/virtualenv.py"

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = path_join(base_dir, "templates")
download_dir = path_join(base_dir, "downloads")

env_dir = path_join(base_dir, "mozmill-env")
msys_dir = path_join(env_dir, "msys")
python_dir = path_join(env_dir, "python")


def remove_files(pattern):
    '''Removes all the files matching the given pattern recursively.'''
    files = glob.glob(pattern)
    for a_file in files:
        os.remove(a_file)


def download(url, filename):
    '''Download a remote file from an URL to the specified local folder.'''

    try:
        urllib.urlretrieve(url, filename)
    except Exception, e:
        logging.exception("Failure downloading '%s': %s", url, str(e))
        raise


def make_relocatable(filepath):
    '''Remove python path from the Scripts'''
    files = glob.glob(filepath)
    for a_file in files:
        for line in fileinput.input(a_file, inplace=1):
            if fileinput.isfirstline() and line.startswith("#!"):
                # Only on Windows we have to set Python into unbuffered mode
                print "#!python -u"
            else:
                print line,

        fileinput.close()

logging.basicConfig(level=logging.INFO)
parser = optparse.OptionParser()
(options, args) = parser.parse_args()

if not args:
    parser.error("Version of Mozmill to be installed is"
                 " required as first parameter.")
mozmill_version = args[0]

logging.info("Delete all possible existent folders")
for directory in (download_dir, env_dir, msys_dir):
    shutil.rmtree(directory, True)

logging.info("Download and install 'MSYS' in unattended mode. "
             "Answer questions with 'y' and 'n'.")
# See: http://www.jrsoftware.org/ishelp/index.php?topic=setupcmdline
os.mkdir(download_dir)
setup_msys = path_join(download_dir, "setup_msys.exe")
download(URL_MSYS, setup_msys)
subprocess.check_call([setup_msys, '/VERYSILENT', '/SP-', '/DIR=%s' % (msys_dir),
                       '/NOICONS' ])

logging.info("Download and install 'mintty'")
mintty_path = path_join(download_dir, os.path.basename(URL_MINTTY))
download(URL_MINTTY, mintty_path)
mintty_zip = zipfile.ZipFile(mintty_path, "r")
mintty_zip.extract("mintty.exe", path_join(msys_dir, 'bin'))
mintty_zip.close()

logging.info("Copy template files into environment")
shutil.copytree(template_dir, env_dir, True)

logging.info("Copy Python installation (including pythonXX.dll into environment")
shutil.copytree(sys.prefix, path_join(env_dir, 'python'), True)
dlls = glob.glob(path_join(os.environ['WINDIR'], "system32", "python*.dll"))
for dll_file in dlls:
    shutil.copy(dll_file, python_dir)

logging.info("Download 'virtualenv' and create new virtual environment")
virtualenv_path = path_join(download_dir, os.path.basename(URL_VIRTUALENV))
filename = download(URL_VIRTUALENV, virtualenv_path)
subprocess.check_call(["python", filename, "--no-site-packages", "mozmill-env"])

logging.info("Reorganizing folder structure")
shutil.move(path_join(env_dir, "Scripts"), python_dir)
shutil.rmtree(path_join(python_dir, "Lib", "site-packages"), True)
shutil.move(path_join(env_dir, "Lib", "site-packages"),
            path_join(python_dir, "Lib"))
shutil.rmtree(path_join(env_dir, "Lib"), True)
python_scripts_dir = path_join(python_dir, "Scripts")
make_relocatable(path_join(python_scripts_dir, "*.py"))

logging.info("Installing required Python modules")
run_cmd_path = path_join(env_dir, "run.cmd")
subprocess.check_call([run_cmd_path, "pip", "install",
                       "--global-option='--pure'", "mercurial==1.9.3"])
subprocess.check_call([run_cmd_path, "pip", "install",
                       "mozmill==%s" % (mozmill_version)])
make_relocatable(path_join(python_scripts_dir, "*.py"))
make_relocatable(path_join(python_scripts_dir, "hg"))

logging.info("Deleting easy_install and pip scripts")
for pattern in ('easy_install*', 'pip*'):
    remove_files(path_join(python_scripts_dir, pattern))

logging.info("Deleting pre-compiled Python modules and build folder")
remove_files(path_join(python_dir, "*.pyc"))
shutil.rmtree(path_join(env_dir, "build"), True)

logging.info("Building zip archive of environment")
target_archive = path_join(os.path.dirname(base_dir), "win-%s" % mozmill_version)
shutil.make_archive(target_archive, "zip", env_dir)

shutil.rmtree(env_dir, True)

logging.info("Successfully created the environment: '%s.zip'", target_archive)
