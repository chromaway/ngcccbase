from PyQt4 import QtGui, uic

from wallet import wallet


class OverviewPage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('overviewpage.ui'), self)

        self.cbMoniker.currentIndexChanged.connect(self.updateWallet)

    def update(self):
        monikers = wallet.get_all_monikers()
        comboList = self.cbMoniker
        currentMoniker = str(comboList.currentText())
        comboList.clear()
        comboList.addItems(monikers)
        if currentMoniker and currentMoniker in monikers:
            comboList.setCurrentIndex(monikers.index(currentMoniker))

    def updateWallet(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return
        asset = wallet.get_asset_definition(moniker)
        balance = wallet.get_balance(asset)
        currency = 'BTC' if moniker == 'bitcoin' else moniker
        self.lblBalance.setText(
            '%s %s' % (asset.format_value(balance), currency))
