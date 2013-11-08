from PyQt4 import QtGui, uic

from wallet import wallet


class OverviewPage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        uic.loadUi(uic.getUiPath('overviewpage.ui'), self)

        self.cb_monikers.currentIndexChanged.connect(self.updateWallet)

    def update(self):
        monikers = wallet.get_all_monikers()
        monikers.remove('bitcoin')
        monikers = ['bitcoin'] + monikers
        comboList = self.cb_monikers
        currentMoniker = str(comboList.currentText())
        comboList.clear()
        comboList.addItems(monikers)
        if currentMoniker and currentMoniker in monikers:
            comboList.setCurrentIndex(monikers.index(currentMoniker))

    def updateWallet(self):
        moniker = str(self.cb_monikers.currentText())
        balance = wallet.get_balance(moniker)
        self.lbl_balance.setText('%.8f %s' % (balance, moniker))
        '''
        address = self.overviewpage.get_btc_address()
        moniker = self.overviewpage.get_moniker()
        if address and moniker:
            asset = self.get_asset_definition(moniker)
            balance = self.walletController.get_balance(asset)
            if moniker == 'bitcoin':
                balance = '%.8f BTC' % (balance,)
            else:
                address = '%s@%s' % (moniker, address)
                balance = '%.8f %s' % (balance, moniker)
            self.overviewpage.update_wallet(address, balance)
        self.lbl_address.setText(address)
        self.lbl_balance.setText(balance)
        '''
