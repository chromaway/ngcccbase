from PyQt4 import QtCore, QtGui, uic

import os
import sys
import signal

from overviewpage import OverviewPage
from sendcoinspage import SendcoinsPage
from receivepage import ReceivePage
from tradepage import TradePage

from wallet import wallet


def getUiPath(ui_name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'forms', ui_name)
uic.getUiPath = getUiPath


class Application(QtGui.QApplication):
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        QtGui.QApplication.__init__(self, [])


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(uic.getUiPath('ngccc.ui'), self)

        self.overviewpage = OverviewPage()
        self.stackedWidget.addWidget(self.overviewpage)
        self.sendcoinspage = SendcoinsPage()
        self.stackedWidget.addWidget(self.sendcoinspage)
        self.receivepage = ReceivePage()
        self.stackedWidget.addWidget(self.receivepage)
        self.tradepage = TradePage()
        self.stackedWidget.addWidget(self.tradepage)

        self.bindActions()

        self.gotoOverviewPage()

    def bindActions(self):
        self.actionRescan.triggered.connect(wallet.scan)
        self.actionExit.triggered.connect(
            lambda: QtCore.QCoreApplication.instance().exit(0))

        self.toolbarActionGroup = QtGui.QActionGroup(self)

        self.toolbarActionGroup.addAction(self.actionGotoOverview)
        self.actionGotoOverview.triggered.connect(self.gotoOverviewPage)

        self.toolbarActionGroup.addAction(self.actionGotoSendcoins)
        self.actionGotoSendcoins.triggered.connect(self.gotoSendcoinsPage)

        self.toolbarActionGroup.addAction(self.actionGotoReceive)
        self.actionGotoReceive.triggered.connect(self.gotoReceivePage)

        self.toolbarActionGroup.addAction(self.actionP2PTrade)
        self.actionP2PTrade.triggered.connect(self.gotoP2PTradePage)

    def gotoOverviewPage(self):
        self.actionGotoOverview.setChecked(True)
        self.overviewpage.update()
        self.stackedWidget.setCurrentWidget(self.overviewpage)

    def gotoSendcoinsPage(self):
        self.actionGotoSendcoins.setChecked(True)
        self.sendcoinspage.update()
        self.stackedWidget.setCurrentWidget(self.sendcoinspage)

    def gotoReceivePage(self):
        self.actionGotoReceive.setChecked(True)
        self.receivepage.update()
        self.stackedWidget.setCurrentWidget(self.receivepage)

    def gotoP2PTradePage(self):
        self.actionP2PTrade.setChecked(True)
        self.tradepage.update()
        self.stackedWidget.setCurrentWidget(self.tradepage)


class QtUI(object):
    def __init__(self):
        if len(wallet.get_all_addresses('bitcoin')) == 0:
            wallet.get_new_address('bitcoin')
        app = Application()
        window = MainWindow()
        window.move(QtGui.QApplication.desktop().screen().rect().center()
                    - window.rect().center())
        window.show()
        sys.exit(app.exec_())
