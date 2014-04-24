#!/usr/bin/env python

"""
ngccc-gui.py

QT interface to the Next-Generation Colored Coin Client
This command will start a GUI interface.

Note that this requires the install of PyQt4 and PIP.
Neither of those are accessible by pip.
Use this command in ubuntu to install:
   apt-get install python-qtp python-sip
"""

from ngcccbase.logger import setup_logging
import install_https
from ui.qtui import QtUI

def start_ui():
    QtUI()

setup_logging()
start_ui()
