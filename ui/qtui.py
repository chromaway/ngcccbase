from PyQt4 import QtCore, QtGui, uic

import os
import sys
import signal

from overviewpage import OverviewPage
from sendcoinspage import SendcoinsPage
from assetpage import AssetPage
from receivepage import ReceivePage
from tradepage import TradePage

from wallet import wallet

try:
    main_file = os.path.abspath(sys.modules['__main__'].__file__)
except AttributeError:
    main_file = sys.executable
ui_path = os.path.join(os.path.dirname(main_file), 'ui', 'forms')

def getUiPath(ui_name):
    return os.path.join(ui_path, ui_name)

uic.getUiPath = getUiPath


class Application(QtGui.QApplication):
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        QtGui.QApplication.__init__(self, [])

        # this is slow
        wallet.controller.scan_utxos()

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(uic.getUiPath('ngccc.ui'), self)

        self.overviewpage = OverviewPage(self)
        self.stackedWidget.addWidget(self.overviewpage)
        self.sendcoinspage = SendcoinsPage(self)
        self.stackedWidget.addWidget(self.sendcoinspage)
        self.assetpage = AssetPage(self)
        self.stackedWidget.addWidget(self.assetpage)
        self.receivepage = ReceivePage(self)
        self.stackedWidget.addWidget(self.receivepage)
        self.tradepage = TradePage(self)
        self.stackedWidget.addWidget(self.tradepage)

        self.bindActions()

        self.gotoOverviewPage()

    def bindActions(self):
        self.actionRescan.triggered.connect(self.rescanAction)
        self.actionExit.triggered.connect(
            lambda: QtCore.QCoreApplication.instance().exit(0))

        self.toolbarActionGroup = QtGui.QActionGroup(self)

        self.toolbarActionGroup.addAction(self.actionGotoOverview)
        self.actionGotoOverview.triggered.connect(self.gotoOverviewPage)

        self.toolbarActionGroup.addAction(self.actionGotoSendcoins)
        self.actionGotoSendcoins.triggered.connect(self.gotoSendcoinsPage)

        self.toolbarActionGroup.addAction(self.actionGotoAsset)
        self.actionGotoAsset.triggered.connect(self.gotoAssetPage)

        self.toolbarActionGroup.addAction(self.actionGotoReceive)
        self.actionGotoReceive.triggered.connect(self.gotoReceivePage)

        self.toolbarActionGroup.addAction(self.actionP2PTrade)
        self.actionP2PTrade.triggered.connect(self.gotoP2PTradePage)

    def rescanAction(self):
        wallet.scan()
        self.currentPage.update()

    def setPage(self, page):
        page.update()
        self.stackedWidget.setCurrentWidget(page)
        self.currentPage = page

    def gotoOverviewPage(self):
        self.actionGotoOverview.setChecked(True)
        self.setPage(self.overviewpage)

    def gotoSendcoinsPage(self):
        self.actionGotoSendcoins.setChecked(True)
        self.setPage(self.sendcoinspage)

    def gotoAssetPage(self):
        self.actionGotoAsset.setChecked(True)
        self.setPage(self.assetpage)

    def gotoReceivePage(self):
        self.actionGotoReceive.setChecked(True)
        self.setPage(self.receivepage)

    def gotoP2PTradePage(self):
        self.actionP2PTrade.setChecked(True)
        self.setPage(self.tradepage)


class QtUI(object):
    def __init__(self):
        app = Application()
        window = MainWindow()
        window.move(QtGui.QApplication.desktop().screen().rect().center()
                    - window.rect().center())
        window.show()
        sys.exit(app.exec_())
