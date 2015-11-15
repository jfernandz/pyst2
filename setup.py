"""Packaging files and information."""


from setuptools import setup

from asterisk import __version__ as version


setup(

    # Basic package information:
    name = 'pyst2',
    version = version,
    packages = ['asterisk'],

    # Packaging options:
    zip_safe = False,
    include_package_data = True,

    # Package dependencies:
    install_requires = ['six>=1.9.0'],

    # Metadata for PyPI:
    author = 'Randall Degges',
    author_email = 'r@rdegges.com',
    license = 'Python Software Foundation License / GNU Library or Lesser General Public License (LGPL) / UNLICENSE',
    url = 'https://github.com/rdegges/pyst2',
    keywords = 'python asterisk agi ami telephony telephony sip voip',
    description = 'A Python Interface to Asterisk',
    long_description = open('README.rst').read(),

    # Classifiers:
    platforms = 'Any',
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Other Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Telecommunications Industry',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Communications :: Internet Phone',
        'Topic :: Communications :: Telephony',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],

)
