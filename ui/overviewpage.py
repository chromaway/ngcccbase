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
        if moniker == '':
            return
        asset = wallet.get_asset_definition(moniker)
        balance = wallet.get_balance(asset)
        self.lbl_balance.setText(
            '%s %s' % (asset.format_value(balance), moniker))
        wam = wallet.model.get_address_manager()
        addr = wam.get_some_address(asset.get_color_set()).get_address()
        self.lbl_address.setText(addr)
