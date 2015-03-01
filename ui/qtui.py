import httplib
import urllib2
import socket
from PyQt4 import QtCore, QtGui, uic

import os
import sys
import signal

from overviewpage import OverviewPage
from sendcoinspage import SendcoinsPage
from assetspage import AssetsPage
from receivepage import ReceivePage
from tradepage import TradePage
from historypage import HistoryPage

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


class ConnectionStatus(QtGui.QLabel):

    def updateStatus(self):
        self.setStatus(wallet.connected())

    def setStatus(self, connected):
        if connected:
            self.setText("Status: Connected")
        else:
            self.setText("Status: Disconnected")


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(uic.getUiPath('ngccc.ui'), self)

        self.overviewpage = OverviewPage(self)
        self.stackedWidget.addWidget(self.overviewpage)
        self.sendcoinspage = SendcoinsPage(self)
        self.stackedWidget.addWidget(self.sendcoinspage)
        self.assetspage = AssetsPage(self)
        self.stackedWidget.addWidget(self.assetspage)
        self.receivepage = ReceivePage(self)
        self.stackedWidget.addWidget(self.receivepage)
        self.historypage = HistoryPage(self)
        self.stackedWidget.addWidget(self.historypage)
        self.tradepage = TradePage(self)
        self.stackedWidget.addWidget(self.tradepage)

        self.bindActions()

        self.gotoOverviewPage()

        self.utxo_timer = QtCore.QTimer()
        self.utxo_timer.timeout.connect(self.update_utxo_fetcher)
        self.utxo_timer.start(2500)
        wallet.async_utxo_fetcher.start_thread()

        self._sys_excepthook = sys.excepthook
        sys.excepthook = self.excepthook

        self.connectionStatus = ConnectionStatus("Status: Unknown")
        self.statusBar().addWidget(self.connectionStatus)

    def excepthook(self, exctype, value, traceback):
        QtGui.QMessageBox.critical(self, '', str(value), QtGui.QMessageBox.Ok)
        self._sys_excepthook(exctype, value, traceback)

    def update_utxo_fetcher(self):
        try:
            got_updates = wallet.async_utxo_fetcher.update()
            if got_updates:
                self.currentPage.update()
            self.connectionStatus.updateStatus()
        except httplib.CannotSendRequest: # bitcoind disconnected
            self.connectionStatus.setStatus(False)
        except httplib.BadStatusLine: # bitcoind disconnected
            self.connectionStatus.setStatus(False)
        except socket.error: # bitcoind not started
            self.connectionStatus.setStatus(False)
        except urllib2.HTTPError: # chromanode disconnected
            self.connectionStatus.setStatus(False)


    def bindActions(self):
        self.actionExit.triggered.connect(
            lambda: QtCore.QCoreApplication.instance().exit(0))

        self.toolbarActionGroup = QtGui.QActionGroup(self)

        self.toolbarActionGroup.addAction(self.actionGotoOverview)
        self.actionGotoOverview.triggered.connect(self.gotoOverviewPage)

        self.toolbarActionGroup.addAction(self.actionGotoSendcoins)
        self.actionGotoSendcoins.triggered.connect(self.gotoSendcoinsPage)

        self.toolbarActionGroup.addAction(self.actionGotoAssets)
        self.actionGotoAssets.triggered.connect(self.gotoAssetsPage)

        self.toolbarActionGroup.addAction(self.actionGotoReceive)
        self.actionGotoReceive.triggered.connect(self.gotoReceivePage)

        self.toolbarActionGroup.addAction(self.actionGotoHistory)
        self.actionGotoHistory.triggered.connect(self.gotoHistoryPage)

        self.toolbarActionGroup.addAction(self.actionP2PTrade)
        self.actionP2PTrade.triggered.connect(self.gotoP2PTradePage)

    def update(self):
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

    def gotoAssetsPage(self):
        self.actionGotoAssets.setChecked(True)
        self.setPage(self.assetspage)

    def gotoReceivePage(self):
        self.actionGotoReceive.setChecked(True)
        self.setPage(self.receivepage)

    def gotoHistoryPage(self):
        self.actionGotoHistory.setChecked(True)
        self.setPage(self.historypage)

    def gotoP2PTradePage(self):
        self.actionP2PTrade.setChecked(True)
        self.setPage(self.tradepage)

class QtUI(object):
    def __init__(self):
        global wallet
        app = Application()
        if wallet.connected():
            window = MainWindow()
            center = QtGui.QApplication.desktop().screen().rect().center()
            window.move(center - window.rect().center())
            window.show()
        else: # not connected
            msg = "Couldn't connect to server!"
            QtGui.QMessageBox.critical(None, '', msg, QtGui.QMessageBox.Ok)
            return

        retcode = app.exec_()
        wallet.stop_all()
        sys.exit(retcode)

