#!/usr/bin/env python

import fileinput
import fnmatch
import glob
import logging
import optparse
import os
import subprocess
import shutil
import sys
import urllib2
import zipfile

parser = optparse.OptionParser()
(options, args) = parser.parse_args()

con = True
while con:
	if not args:
		parser.error("Version of Mozmill to be installed is required as first parameter.")
	else:
		con = False
mozmill_version = args[0] #VERSION_MOZMILL <-> mozmill_version

VERSION_MERCURIAL = str(2.1)
VERSION_PYTHON = $(python -c "import sys;print sys.version[:3]")
VERSION_VIRTUALENV = str(1.7)

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, "templates")
download_dir = os.path.join(base_dir, "downloads")

env_dir = os.path.join(base_dir, "mozmill-env")
target_archive = os.path.join(os.path.dirname(base_dir), "%s-%s.zip" % (mozmill_version, os.path.basename(base_dir)))
URL_VIRTUALENV = "https://raw.github.com/pypa/virtualenv/%s/virtualenv.py" % VERSION_VIRTUALENV

logging.basicConfig(level=logging.INFO)

logging.info("Delete all possible existent folders")
for directory in (download_dir, env_dir, msys_dir):
    shutil.rmtree(directory, True)

def copytree(src, dst, symlinks=False, ignore=None):
    """
    Copy of shutil.copytree with proper exception handling when the target
    directory exists. (a simple try-except block addition)
    """
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    try:
        os.makedirs(dst)
    except:
        pass

    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree(srcname, dstname, symlinks, ignore)
            else:
                shutil.copy2(srcname, dstname)
                # XXX What about devices, sockets etc.?
        except (IOError, os.error), why:
            errors.append((srcname, dstname, str(why)))
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except EnvironmentError, err:
            errors.extend(err.args[0])
    try:
        shutil.copystat(src, dst)
    except WindowsError:
        # can't copy file access times on Windows
        pass
    except OSError, why:
        errors.extend((src, dst, str(why)))
    if errors:
        raise EnvironmentError(errors)

def remove_files(base_dir, pattern):
    '''Removes all the files matching the given pattern recursively.'''
    files = [os.path.join(root, filename)
             for root, dirnames, filenames in os.walk(base_dir)
                for filename in fnmatch.filter(filenames, pattern)]

    for a_file in files:
        os.remove(a_file)

def download(url, filename):
    '''Download a remote file from an URL to the specified local folder.'''

    try:
        req = urllib2.urlopen(url)
        with open(filename, 'wb') as fp:
            shutil.copyfileobj(req, fp)
    except urllib2.URLError, e:
        logging.critical("Failure downloading '%s': %s", url, str(e))
        raise e
		
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
		
logging.info("Fetching version %s of virtualenv and creating new environment", VERSION_VIRTUALENV)
virtualenv_path = os.path.join(download_dir, os.path.basename(URL_VIRTUALENV))
download(URL_VIRTUALENV, virtualenv_path)
subprocess.check_call(["python", virtualenv_path, env_dir])

#
#LINUX SCRIPT
#echo "Activating the new environment"
#source $ENV_DIR/bin/activate
#if [ ! -n "${VIRTUAL_ENV:+1}" ]; then
#    echo "### Failure in activating the new virtual environment: '$ENV_DIR'"
#    cleanup
#    exit 1
#fi
#

logging.info("Installing required Python modules")
run_cmd_path = os.path.join(env_dir, "run.cmd")
subprocess.check_call([run_cmd_path, "pip", "install",
                       "--upgrade", "--global-option='--pure'",
                       "mercurial==%s" % VERSION_MERCURIAL])
subprocess.check_call([run_cmd_path, "pip", "install",
                       "--upgrade", "mozmill==%s" % (mozmill_version)])
make_relocatable(os.path.join(python_scripts_dir, "*.py"))
make_relocatable(os.path.join(python_scripts_dir, "hg"))

#
#echo "Deactivating the environment"
#deactivate
#

logging.info("Copy template files into environment")
copytree(template_dir, env_dir, True)

logging.info("Reorganizing folder structure")
shutil.rmtree(os.path.join(python_dir, "Lib", "site-packages"), True)
shutil.move(os.path.join(env_dir, "Lib", "site-packages"),
            os.path.join(python_dir, "Lib"))
shutil.rmtree(os.path.join(env_dir, "Lib"), True)
python_scripts_dir = os.path.join(python_dir, "Scripts")
copytree(os.path.join(env_dir, "Scripts"), python_scripts_dir)
shutil.rmtree(os.path.join(env_dir, "Scripts"))
make_relocatable(os.path.join(python_scripts_dir, "*.py"))

logging.info("Deleting easy_install and pip scripts")
for pattern in ('easy_install*', 'pip*'):
    remove_files(python_scripts_dir, pattern)

#
#Remove the local symlink which gets created and doesn't seem to be necessary.
#See: https://github.com/pypa/virtualenv/issues/118
#rm -r $ENV_DIR/local
#
#cp -r templates/* $ENV_DIR
#
#echo "Updating scripts for relocation of the environment"
#sed -i 's/#!.*/#!\/usr\/bin\/env python/g' $ENV_DIR/bin/*
#

logging.info("Deleting pre-compiled Python modules and build folder")
remove_files(python_dir, "*.pyc")
shutil.rmtree(os.path.join(env_dir, "build"), True)

logging.info("Building zip archive of environment")
shutil.make_archive(target_archive, "zip", base_dir, os.path.basename(env_dir))

shutil.rmtree(env_dir, True)

logging.info("Successfully created the environment: '%s.zip'", target_archive)