#!/usr/bin/env python

import sys
from cx_Freeze import setup, Executable
#from setuptools import find_packages

base = None
if sys.platform == "win32":
    base = "Win32GUI"

build_exe_options = {}

setup(
    name='ngcccbase',
    version='0.0.1',
    description='A flexible and modular base for colored coin software.',
    classifiers=[
        "Programming Language :: Python",
    ],
    url='https://github.com/bitcoinx/ngcccbase',
    keywords='bitcoinx bitcoin coloredcoins',
    packages=["ngcccbase", "ngcccbase.services", "ngcccbase.p2ptrade", "ecdsa", "coloredcoinlib", "ui"],
    #options = {"build_exe": build_exe_options},
    executables = [Executable("ngccc-server.py", base=base),
        Executable("ngccc-gui.py", base=base),
        Executable("ngccc-cli.py", base=base),
        Executable("ngccc.py", base=base),
    ]
)
