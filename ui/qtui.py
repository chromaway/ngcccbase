import os, sys, signal
from PyQt4 import QtGui, uic

from pwallet import PersistentWallet
from wallet_controller import WalletController

from overviewpage import OverviewPage
from sendcoins import SendcoinsPage


def getUiPath(ui_name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forms', ui_name)
uic.getUiPath = getUiPath

class QtUI(QtGui.QMainWindow):
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        self.app = QtGui.QApplication([])

        QtGui.QMainWindow.__init__(self)
        uic.loadUi(uic.getUiPath('ngcccbase.ui'), self)

        self.overviewpage = OverviewPage()
        self.stackedWidget.addWidget(self.overviewpage)
        self.bindOverviewPage()
        self.sendcoinspage = SendcoinsPage()
        self.stackedWidget.addWidget(self.sendcoinspage)
        self.bindSendcoinsPage()

        self.bindActions()
        self.move(QtGui.QApplication.desktop().screen().rect().center() - self.rect().center())
        self.show()

        self.wallet = PersistentWallet()
        self.walletController = WalletController(self.wallet.get_model())
        #self.gotoOverviewPage()
        self.gotoSendcoinsPage()

        sys.exit(self.app.exec_())

    def bindActions(self):
        # menu actions
        self.actionExit.triggered.connect(lambda: self.app.exit(0))
        # toolbar actions
        self.toolbarActions = [
            self.actionGotoOverview,
            self.actionGotoSendcoins,
        ]
        self.actionGotoOverview.triggered.connect(self.gotoOverviewPage)
        self.actionGotoSendcoins.triggered.connect(self.gotoSendcoinsPage)

    def bindOverviewPage(self):
        def btn_newAddressClicked(*args, **kwargs):
            asset = self.get_asset_definition('bitcoin')
            address = self.walletController.get_new_address(asset)
            addresses = [addr.get_address()
                            for addr in self.walletController.get_all_addresses(asset)]
            self.overviewpage.update_btc_addresses(addresses)
            self.overviewpage.set_btc_address(addr.get_address())
        self.overviewpage.btn_newAddress.clicked.connect(btn_newAddressClicked)

        def btn_newAsset(*args, **kwargs):
            # need change page to issue coins
            pass
        self.overviewpage.btn_newAsset.clicked.connect(btn_newAsset)

        def updateWallet(*args, **kwargs):
            address = self.overviewpage.get_btc_address()
            moniker = self.overviewpage.get_asset()
            if address and moniker:
                asset = self.get_asset_definition(moniker)
                balance = self.walletController.get_balance(asset)
                if moniker == 'bitcoin':
                    balance = '%.8f BTC' % (balance,)
                else:
                    address = '%s@%s' % (moniker, address)
                    balance = '%.8f %s' % (balance, moniker)
                self.overviewpage.update_wallet(address, balance)
        self.overviewpage.cb_addresses.currentIndexChanged.connect(updateWallet)
        self.overviewpage.cb_assets.currentIndexChanged.connect(updateWallet)

    def gotoOverviewPage(self):
        # set bitcoin addresses
        bitcoin_asset = self.get_asset_definition('bitcoin')
        bitcoin_addresses = [addr.get_address()
                                for addr in self.walletController.get_all_addresses(bitcoin_asset)]
        self.overviewpage.update_btc_addresses(bitcoin_addresses)
        # set available assets
        assets = self.wallet.get_model().get_asset_definition_manager().assdef_by_moniker.keys()
        self.overviewpage.update_assets(assets)
        # goto
        self.stackedWidget.setCurrentWidget(self.overviewpage)
        # change toolbar buttons
        for action in self.toolbarActions:
            action.setChecked(False)
        self.actionGotoOverview.setChecked(True)

    def bindSendcoinsPage(self):
        pass

    def gotoSendcoinsPage(self):
        # goto
        self.stackedWidget.setCurrentWidget(self.sendcoinspage)
        # change toolbar buttons
        for action in self.toolbarActions:
            action.setChecked(False)
        self.actionGotoSendcoins.setChecked(True)

    def get_asset_definition(self, moniker):
        adm = self.wallet.get_model().get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("asset not found")
