#!/usr/bin/env python

import ConfigParser
import ctypes
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

# Link to the folder which contains the zip archives of virtualenv
URL_VIRTUALENV = 'https://codeload.github.com/pypa/virtualenv/zip/'

# Link to 7z unpacker
URL_7Z = 'http://downloads.sourceforge.net/project/sevenzip/7-Zip/'

# Link to ConEmu installer
URL_CONEMU_VERSIONS_MANIFEST = 'http://conemu-maximus5.googlecode.com/svn/trunk/ConEmu/version.ini'

VERSION_MERCURIAL = '2.6.2'
VERSION_MOZDOWNLOAD = '1.9'
VERSION_VIRTUALENV = '1.9.1'
VERSION_7Z = '9.20'
VERSION_7Z_SHORT = VERSION_7Z.replace('.', '')

dir_base = os.path.abspath(os.path.dirname(__file__))
dir_assets = os.path.join(dir_base, os.path.pardir, 'assets')
dir_env = os.path.join(dir_base, 'mozmill-env')
dir_msys = os.path.join(dir_env, 'msys')
dir_python = os.path.join(dir_env, 'python')
dir_tmp=os.path.join(dir_base, 'tmp')
dir_template = os.path.join(dir_base, 'templates')


def prepare_build():
    """
    Prepares necessary tools for building environment.

    """
    logging.info("Delete all possible existent folders")
    shutil.rmtree(dir_env, True)

    # Ensure we have a clean and existent temporary directory
    shutil.rmtree(dir_tmp, True)
    os.makedirs(dir_tmp)

    logging.info('Downloading virtualenv %s' % VERSION_VIRTUALENV)
    virtualenv_file = download(URL_VIRTUALENV + VERSION_VIRTUALENV,
                               os.path.join(dir_tmp, 'virtualenv.zip'))
    virtualenv_zip = zipfile.ZipFile(virtualenv_file)
    virtualenv_zip.extractall(dir_tmp)
    virtualenv_zip.close()

    logging.info("Downloading 7zip")
    sevenzip_path = '/'.join([VERSION_7Z, '7za%s.zip' % VERSION_7Z_SHORT])
    sevenzip_file = download(URL_7Z + sevenzip_path,
                            os.path.join(dir_tmp, '7z.zip'))
    sevenzip_dir = os.path.join(dir_tmp, '7z')
    os.makedirs(sevenzip_dir)
    sevenzip_zipfile = zipfile.ZipFile(sevenzip_file)
    sevenzip_zipfile.extractall(sevenzip_dir)
    sevenzip_zipfile.close()
    sevenzip_file  = os.path.join(sevenzip_dir, '7za.exe')

    logging.info('Downloading latest preview version of ConEmu')
    conemu_file, conemu_version = download_conemu()
    logging.info('Downloaded version of ConEmu: %s' % conemu_version)
    logging.info('Unpackaging ConEmu inside environment')
    conemu_tmp = os.path.join(dir_tmp, 'conemu')
    os.makedirs(conemu_tmp)
    subprocess.check_call([sevenzip_file, 'x', '-o%s' % dir_env, conemu_file])


def download_conemu(build_type='Preview'):
    """
    Downloads latest available version of ConEmu for defined build type.
    Available types:
    Preview, Devel
    We don't support Stable version because it does not support loading xml config from commandline.
    Returns downloaded version and path to downloaded file.
    """
    versions_manifest = download(URL_CONEMU_VERSIONS_MANIFEST, os.path.join(dir_tmp, 'conemu_versions.ini'))
    versions_config = ConfigParser.SafeConfigParser()
    versions_config.read(versions_manifest)
    section = "ConEmu_%s" % build_type
    version = versions_config.get(section, 'version')
    location_url = versions_config.get(section, 'location_arc').split(',')[-1]
    filename = download(location_url, os.path.join(dir_tmp, 'conemu.7z'))
    return filename, version


def copytree(src, dst, symlinks=False, ignore=None):
    """
    A copy of shutil.copytree.

    Includes proper exception handling when the target
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


def download(url, target):
    """Downloads the specified url to the given target."""
    response = urllib2.urlopen(url)
    with open(target, 'wb') as f:
        f.write(response.read())

    return target


def remove_files(dir_base, pattern):
    """Removes all the files matching the given pattern recursively."""
    files = [os.path.join(root, filename)
             for root, dirnames, filenames in os.walk(dir_base)
                for filename in fnmatch.filter(filenames, pattern)]

    for a_file in files:
        os.remove(a_file)


def make_relocatable(filepath):
    """Remove python path from the Scripts."""
    files = glob.glob(filepath)
    for a_file in files:
        for line in fileinput.input(a_file, inplace=1):
            if fileinput.isfirstline() and line.startswith('#!'):
                # Only on Windows we have to set Python into unbuffered mode
                print '#!python -u'
            else:
                print line,

        fileinput.close()


def main():
    logging.basicConfig(level=logging.INFO)

    parser = optparse.OptionParser()
    (options, args) = parser.parse_args()

    if not ctypes.windll.shell32.IsUserAnAdmin():
        logging.error('Sorry, this script requires administrative privileges.')
        sys.exit(126)

    if not args:
        parser.error('Version of Mozmill-Automation to be installed is required as first parameter.')
    mozmill_automation_version = args[0]

    prepare_build()

    logging.info("Copy template files into environment")
    copytree(dir_template, dir_env, True)

    logging.info('Copying Python installation (including pythonXX.dll into environment)')
    copytree(sys.prefix, os.path.join(dir_env, 'python'), True)
    dlls = glob.glob(os.path.join(os.environ['WINDIR'], 'system32', 'python*.dll'))
    for dll_file in dlls:
        shutil.copy(dll_file, dir_python)

    logging.info('Reorganizing folder structure')
    shutil.rmtree(os.path.join(dir_python, 'Lib', 'site-packages'), True)
    shutil.move(os.path.join(dir_env, 'Lib', 'site-packages'),
                os.path.join(dir_python, 'Lib'))
    shutil.rmtree(os.path.join(dir_env, 'Include'), True)
    shutil.rmtree(os.path.join(dir_env, 'Lib'), True)
    python_scripts_dir = os.path.join(dir_python, 'Scripts')
    copytree(os.path.join(dir_env, 'Scripts'), python_scripts_dir)
    shutil.rmtree(os.path.join(dir_env, 'Scripts'))
    make_relocatable(os.path.join(python_scripts_dir, '*.py'))

    run_cmd_path = os.path.join(dir_env, 'run.cmd')

    logging.info('Pre-installing mercurial %s in pure mode' % VERSION_MERCURIAL)
    subprocess.check_call([run_cmd_path, 'pip', 'install',
                           '--upgrade', "--global-option='--pure'",
                           'mercurial==%s' % VERSION_MERCURIAL])

    logging.info('Installing mozmill-automation %s and related packages' % mozmill_automation_version)
    subprocess.check_call([run_cmd_path, 'pip', 'install',
                           '--upgrade', 'mozmill-automation==%s' %
                               mozmill_automation_version])

    make_relocatable(os.path.join(python_scripts_dir, '*.py'))
    make_relocatable(os.path.join(python_scripts_dir, 'hg'))

    logging.info('Deleting easy_install and pip scripts')
    for pattern in ('easy_install*', 'pip*'):
        remove_files(python_scripts_dir, pattern)

    logging.info('Deleting pre-compiled Python modules and build folder')
    remove_files(dir_python, '*.pyc')
    shutil.rmtree(os.path.join(dir_env, 'build'), True)

    logging.info('Deleting MSYS home directory')
    shutil.rmtree(os.path.join(dir_msys, 'home'))

    logging.info('Building zip archive of environment')
    target_archive = os.path.join(os.path.dirname(dir_base), '%s-windows' % mozmill_automation_version)
    shutil.make_archive(target_archive, 'zip', dir_base, os.path.basename(dir_env))

    shutil.rmtree(dir_env, True)
    shutil.rmtree(dir_tmp, True)

    logging.info("Successfully created the environment: '%s.zip'", target_archive)

if __name__ == '__main__':
    main()
