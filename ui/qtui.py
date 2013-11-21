from PyQt4 import QtCore, QtGui, uic

import os
import sys
import signal

from overviewpage import OverviewPage
from sendcoinspage import SendcoinsPage
from assetpage import AssetPage
from addressespage import AddressesPage
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

        if len(wallet.get_all_addresses('bitcoin')) == 0:
            wallet.get_new_address('bitcoin')
        #wallet.p2p_agent_refresh.start()


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
        self.addressespage = AddressesPage(self)
        self.stackedWidget.addWidget(self.addressespage)
        self.tradepage = TradePage(self)
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

        self.toolbarActionGroup.addAction(self.actionGotoAsset)
        self.actionGotoAsset.triggered.connect(self.gotoAssetPage)

        self.toolbarActionGroup.addAction(self.actionGotoAddresses)
        self.actionGotoAddresses.triggered.connect(self.gotoAddressesPage)

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

    def gotoAssetPage(self):
        self.actionGotoAsset.setChecked(True)
        self.assetpage.update()
        self.stackedWidget.setCurrentWidget(self.assetpage)

    def gotoAddressesPage(self):
        self.actionGotoAddresses.setChecked(True)
        self.addressespage.update()
        self.stackedWidget.setCurrentWidget(self.addressespage)

    def gotoP2PTradePage(self):
        self.actionP2PTrade.setChecked(True)
        self.tradepage.update()
        self.stackedWidget.setCurrentWidget(self.tradepage)


class QtUI(object):
    def __init__(self):
        app = Application()
        window = MainWindow()
        window.move(QtGui.QApplication.desktop().screen().rect().center()
                    - window.rect().center())
        window.show()
        sys.exit(app.exec_())
