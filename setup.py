#!/usr/bin/env python

# Mostly stolen from paster generated setup.py files for pyramid projects

from setuptools import setup, find_packages
import os

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

requires = [
        'pycoin',
        'bunch',
        'python-jsonrpc',
        'python-bitcoinrpc',
        'python-bitcoinlib',
    ]

dependency_links=[
    "https://github.com/jgarzik/python-bitcoinrpc/archive/master.zip#egg=python-bitcoinrpc",
    "https://github.com/Ademan/python-bitcoinlib/archive/pythonize.zip#egg=python-bitcoinlib", # Temporary measure until upstream adds setup.py
    ]
setup(name='ngcccbase',
    version='0.0.1',
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
    #entry_points="""\
    #[console_scripts]
    #ngcccbase-server = 
    #""",
    )
