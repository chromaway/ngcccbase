#!/usr/bin/env python

# Mostly stolen from paster generated setup.py files for pyramid projects

from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

requires = [
    'pycoin == 0.51',
    'bunch == 1.0.1',
    'python-jsonrpc == 0.7.3',
    'python-bitcoinlib == 0.1.1',
    'apigen == 1.1.6',
    'web.py == 0.37',
    'six == 1.9.0',
    'requests == 2.7.0',
    'argparse == 1.2.1',
    'websocket-client == 0.30.0',
]

dependency_links = [
    "https://github.com/petertodd/python-bitcoinlib/archive/v0.1.1.zip" +
    "#egg=python-bitcoinlib",
]

setup(
    name='ngcccbase',
    version='0.0.10',
    description='A flexible and modular base for colored coin software.',
    long_description=README,
    classifiers=[
        "Programming Language :: Python",
    ],
    url='https://github.com/bitcoinx/ngcccbase',
    keywords='bitcoinx bitcoin coloredcoins',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    dependency_links=dependency_links,
    test_suite="ngcccbase.tests",
)
