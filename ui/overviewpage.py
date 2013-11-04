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

    def update_monikers(self, monikers):
        currentMoniker = self.get_moniker()
        self.cb_monikers.clear()
        monikers.remove('bitcoin')
        monikers = ['bitcoin'] + monikers
        self.cb_monikers.addItems(monikers)
        self.set_moniker(currentMoniker)

    def get_moniker(self):
        return str(self.cb_monikers.currentText())

    def set_moniker(self, moniker):
        monikers = [str(self.cb_monikers.itemText(i)) for i in range(self.cb_monikers.count())]
        if moniker and moniker in monikers:
            self.cb_monikers.setCurrentIndex(monikers.index(moniker))

    def update_wallet(self, address, balance):
        self.lbl_address.setText(address)
        self.lbl_balance.setText(balance)
