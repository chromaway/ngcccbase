#!/usr/bin/env python

import sys

import os
import os.path

from cx_Freeze import setup, Executable

base = None
if sys.platform == "win32":
    base = "Win32GUI"

def ls(path):
    for name in os.listdir(path):
        yield os.path.join(path, name)

import itertools

build_exe_options = {
    "include_files": list(itertools.chain(ls('ui/forms'), ls('ui/icons')))
}

setup(
    name='ngcccbase',
    version='0.0.2',
    description='A flexible and modular base for colored coin software.',
    classifiers=[
        "Programming Language :: Python",
    ],
    url='https://github.com/bitcoinx/ngcccbase',
    keywords='bitcoinx bitcoin coloredcoins',
    packages=["ngcccbase", "ngcccbase.services", "ngcccbase.p2ptrade", "ecdsa", "coloredcoinlib", "ui"],
    options = {"build_exe": build_exe_options},
    executables = [Executable("ngccc-server.py", base=base),
        Executable("ngccc-gui.py", base=base),
        Executable("ngccc-cli.py", base=base),
        Executable("ngccc.py", base=base),
    ]
)
