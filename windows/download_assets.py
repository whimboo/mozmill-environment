#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import ConfigParser
import hashlib
import logging
import os
import shutil
import urllib2
import zipfile

logging.basicConfig(level=logging.INFO)


URL_VIRTUALENV = 'https://codeload.github.com/pypa/virtualenv/zip/'
URL_7Z = 'http://downloads.sourceforge.net/project/sevenzip/7-Zip/'
URL_CONEMU_VERSIONS_MANIFEST = 'http://conemu-maximus5.googlecode.com/svn/trunk/ConEmu/version.ini'

VERSION_MERCURIAL = '2.6.2'
VERSION_MOZDOWNLOAD = '1.9'
VERSION_VIRTUALENV = '1.10.1'
VERSION_7Z = '9.20'
VERSION_7Z_SHORT = VERSION_7Z.replace('.', '')

dir_base = os.path.abspath(os.path.dirname(__file__))
dir_assets = os.path.join(dir_base, os.path.pardir, 'assets')
dir_tmp = os.path.join(dir_base, 'tmp')


def download(url, target):
    """Downloads the specified url to the given target."""
    response = urllib2.urlopen(url)
    with open(target, 'wb') as f:
        f.write(response.read())

    return target


def get_file_hash(filepath):
    """ Returns md5 hash for given filepath. """
    md5 = hashlib.md5()
    file_ = open(filepath, 'rb')
    md5.update(file_.read())
    return md5.hexdigest()


def save_assets_index(fileinfos):
    """ Saves assets informations about download urls and md5. """
    index_file = open(os.path.join(dir_assets, "index.txt"), "w+")

    for file_name, download_url, file_path in fileinfos:
        file_hash = get_file_hash(file_path)
        index_info = "Filename: {0}\n"\
                     "Download url: {1}\n"\
                     "MD5: {2}\n".format(file_name, download_url, file_hash)
        index_file.write(index_info)
        index_file.write('\n\n')

    index_file.close()


def download_assets():
    """ Prepares necessary tools for building environment.
    Return a list of assets with informations
    """
    assets = []

    if not os.path.exists(dir_assets):
        logging.info('Creating assets directory')
        os.makedirs(dir_assets)

    logging.info('Downloading virtualenv %s' % VERSION_VIRTUALENV)
    virtualenv_url = URL_VIRTUALENV + VERSION_VIRTUALENV
    virtualenv_file = download(virtualenv_url, os.path.join(dir_assets,
                              'virtualenv.zip'))
    assets.append(('virtualenv.zip', virtualenv_url, virtualenv_file))

    logging.info("Downloading 7zip %s" % VERSION_7Z_SHORT)
    sevenzip_url_fragment = '/'.join([VERSION_7Z, '7za%s.zip' % VERSION_7Z_SHORT])
    sevenzip_url = URL_7Z + sevenzip_url_fragment
    sevenzip_file = download(sevenzip_url, os.path.join(dir_assets, '7z.zip'))
    assets.append(['7z.zip', sevenzip_url, sevenzip_file])

    logging.info('Downloading latest preview version of ConEmu')
    conemu_url, conemu_file, conemu_version = download_conemu()
    logging.info('Downloaded version of ConEmu: %s' % conemu_version)
    assets.append(['conemu.7z', conemu_url, conemu_file])

    return assets


def download_conemu(build_type='Preview'):
    """
    Downloads latest available version of ConEmu for defined build type.
    We don't support Stable version (120727c) because it doesn't support
    loading xml config from commandline.

    :param build_type: {basestring} build type name e.g. Preview, Devel
    :return {tuple}: Returns url to file, filename, file's version.
    """
    versions_manifest = download(URL_CONEMU_VERSIONS_MANIFEST, os.path.join(dir_tmp, 'conemu_versions.ini'))
    versions_config = ConfigParser.SafeConfigParser()
    versions_config.read(versions_manifest)
    section = "ConEmu_%s" % build_type
    version = versions_config.get(section, 'version')
    location_url = versions_config.get(section, 'location_arc').split(',')[-1]
    filename = download(location_url, os.path.join(dir_assets, 'conemu.7z'))
    return location_url, filename, version


if __name__ == '__main__':
    shutil.rmtree(dir_tmp, True)
    os.makedirs(dir_tmp)

    assets = download_assets()
    save_assets_index(assets)

    shutil.rmtree(dir_tmp, True)