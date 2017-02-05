#! /usr/bin/env python
# coding=utf-8

"""
checkmyreqs

Parses a requirements file to check what libraries are listed as supported with a given Python version

Uses xmlrpc pypi methods as defined here: http://wiki.python.org/moin/PyPIXmlRpc
"""

from __future__ import print_function

import argparse
import os
import re
import sys
import errno

from blessings import Terminal

TERMINAL = Terminal()

try:
    # Different location in Python 3
    from xmlrpc.client import ServerProxy
except ImportError:
    from xmlrpclib import ServerProxy


BASE_PATH = os.path.dirname(os.path.abspath(__file__))
CLIENT = ServerProxy('https://pypi.python.org/pypi')

IGNORED_PREFIXES = ['#', 'git+', 'hg+', 'svn+', 'bzr+', '\n', '\r\n']


def parse_requirements_file(req_file, stop_at_error):
    """
    Parse a requirements file, returning packages with versions in a dictionary
    :param req_file: requirements file to parse

    :return dict of package names and versions
    """
    packages = {}

    for line in req_file:
        line = line.strip()
        for prefix in IGNORED_PREFIXES:
            if not line or line.startswith(prefix):
                line = None
                break
        if line:
            line = line.strip()

            if '==' in line:
                package_name, version = line.split('==')
                packages[package_name] = version
            else:
                if stop_at_error:
                    sys.exit('{} does not have a valid version number'.format(line))
                else:
                    print(TERMINAL.yellow('{} does not have a valid version number'.format(line)))

    return packages


def check_packages(packages, python_version, stop_at_error):
    """
    Checks a list of packages for compatibility with the given Python version
    Prints warning line if the package is not supported for the given Python version
    If upgrading the package will allow compatibility, the version to upgrade is printed
    If the package is not listed on pypi.python.org, error line is printed

    :param packages: dict of packages names and versions
    :param python_version: python version to be checked for support
    """

    for package_name, package_version in packages.items():
        # print(TERMINAL.bold(package_name))

        package_info = CLIENT.release_data(package_name, package_version)
        package_releases = CLIENT.package_releases(package_name)

        if package_releases:
            supported_pythons = get_supported_pythons(package_info)


            # Some entries list support of Programming Language :: Python :: 3
            # So we also want to check the major revision number of the version
            # against the list of supported versions
            major_python_version = python_version.split('.')[0]

            if python_version in supported_pythons:
                pass
                # print(TERMINAL.green('compatible'))
            elif major_python_version in supported_pythons:
                pass
                # print(TERMINAL.green('compatible'))
            else:
                latest_version = package_releases[0]
                latest_package_info = CLIENT.release_data(package_name, latest_version)
                latest_supported_pythons = get_supported_pythons(latest_package_info)

                upgrade_available = ''


                if supported_pythons:

                    if python_version in latest_supported_pythons:
                        upgrade_available = ' - update to v{} for support'.format(latest_version)
                    if stop_at_error:
                        sys.exit('{}={} not compatible with Python {}{}'.format(package_name, package_version, python_version, upgrade_available))
                    else:
                        print(TERMINAL.red('{}={} not compatible with Python {}{}'.format(package_name, package_version, python_version, upgrade_available)))
                else:
                    # We get here if there was not compatability information for
                    # the package version we requested

                    if python_version in latest_supported_pythons:
                        upgrade_available = ' - update to v{} for explicit support'.format(latest_version)
                    if stop_at_error:
                        sys.exit('{}={} version not specified{}'.format(package_name, package_version, upgrade_available))
                    else:
                        print(TERMINAL.yellow('{}={} version not specified{}'.format(package_name, package_version, upgrade_available)))

        else:
            if stop_at_error:
                sys.exit('{}={} not available on pip'.format(package_name, package_version))
            else:
                print(TERMINAL.red('{}={} not available on pip'.format(package_name, package_version)))

        # print('-----')


def get_supported_pythons(package_info):
    """
    Returns a list of supported python versions for a specific package version
    :param package_info: package info dictionary, retrieved from pypi.python.org
    :return: Versions of Python supported, may be empty
    """
    versions = []
    classifiers = package_info.get('classifiers', [])

    for c in classifiers:
        if c.startswith('Programming Language :: Python ::'):
            version = c.split(' ')[-1].strip()
            versions.append(version)

    return versions


def main():
    """
    Parses user input for requirements files and python version to check compatibility for
    :return:
    """
    parser = argparse.ArgumentParser('Checks a requirements file for Python version compatibility')

    parser.add_argument(
        '-f', '--files', required=False,
        help='requirements file(s) to check',
        type=argparse.FileType(), nargs="+"
    )
    parser.add_argument(
        '-p', '--python', required=False,
        help='Version of Python to check against. E.g. 2.5',
        default='.'.join(map(str, [sys.version_info.major, sys.version_info.minor]))
    )
    parser.add_argument(
        '-e', '--error', required=False,
        help='Terminate the check and throw error msg when encounter warnings or errors',
        action='store_true'
    )

    args = parser.parse_args()

    # If a file wasn't passed in, check if pip freeze has been piped, then try to read requirements.txt
    if args.files is None:
        if not sys.stdin.isatty():
            args_files = [sys.stdin]
        else:
            try:
                args_files = [open('requirements.txt')]

            except IOError:
                sys.exit('Default file requirements.txt not found')
    else:
        args_files = args.files

    stop_at_error = args.error

    # Make sure Python version is in X.Y format
    if re.match('^[2-3].[0-9]$', args.python) is None:
        sys.exit('Python argument invalid: Must be in X.Y format, where X is 2 or 3 and Y is 0-9')

    print('Checking dependencies for compatibility with Python {}'.format(args.python))

    for filepath in args_files:
        print('{0}\r\n*****'.format(filepath.name))

        packages = parse_requirements_file(filepath, stop_at_error)
        check_packages(packages, args.python, stop_at_error)
        print('\n')


if __name__ == '__main__':
    main()
