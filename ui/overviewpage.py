from PyQt4 import QtGui, uic


class OverviewPage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        uic.loadUi(uic.getUiPath('overviewpage.ui'), self)

    def update_btc_addresses(self, addresses):
        currentAddress = self.get_btc_address()
        self.cb_addresses.clear()
        self.cb_addresses.addItems(addresses)
        self.set_btc_address(currentAddress)

    def get_btc_address(self):
        return str(self.cb_addresses.currentText())

    def set_btc_address(self, address):
        addresses = [str(self.cb_addresses.itemText(i)) for i in range(self.cb_addresses.count())]
        if address and address in addresses:
            self.cb_addresses.setCurrentIndex(addresses.index(address))

    def update_assets(self, assets):
        currentAsset = self.get_asset()
        self.cb_assets.clear()
        assets.remove('bitcoin')
        assets = ['bitcoin'] + assets
        self.cb_assets.addItems(assets)
        self.set_assets(currentAsset)

    def get_asset(self):
        return str(self.cb_assets.currentText())

    def set_assets(self, asset):
        assets = [str(self.cb_assets.itemText(i)) for i in range(self.cb_assets.count())]
        if asset and asset in assets:
            self.cb_addresses.setCurrentIndex(assets.index(asset))

    def update_wallet(self, address, balance):
        self.lbl_address.setText(address)
        self.lbl_balance.setText(balance)
