import os
from PyQt4 import QtGui, QtCore

from pwallet import PersistentWallet
from wallet_controller import WalletController
from mainwindow import MainWindow


class QtUI(object):
    def __init__(self):
        self.wallet = PersistentWallet()
        self.walletController = WalletController(self.wallet.get_model())

        app = QtGui.QApplication([])
        self.mainWindow = MainWindow(self)
        self.mainWindow.show()
        app.exec_()

    def get_path_to_ui(self, ui_name):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forms', ui_name)

    def get_asset_definition(self, moniker):
        adm = self.wallet.get_model().get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("asset not found")

    def exit(self):
        QtCore.QCoreApplication.instance().exit(0)
