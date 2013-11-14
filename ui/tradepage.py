from PyQt4 import QtGui, uic

from wallet import wallet


class TradePage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        uic.loadUi(uic.getUiPath('tradepage.ui'), self)

        self.widgetsEnabled(False)
        self.cbMoniker.currentIndexChanged.connect(self.updateMoniker)

    def update(self):
        monikers = wallet.get_all_monikers()
        monikers.remove('bitcoin')
        comboList = self.cbMoniker
        currentMoniker = str(comboList.currentText())
        comboList.clear()
        comboList.addItems(monikers)
        if currentMoniker and currentMoniker in monikers:
            comboList.setCurrentIndex(monikers.index(currentMoniker))

    def widgetsEnabled(self, enable):
        widgetNames = [
            'edtBuyQuantity', 'edtBuyPrice', 'btnBuy', 'tableBuyBids',
            'edtSellQuantity', 'edtSellPrice', 'btnSell', 'tableSellBids',
            'tableTradesBids'
        ]
        for name in widgetNames:
            getattr(self, name).setEnabled(enable)

    def updateMoniker(self):
        self.widgetsEnabled(True)

        asset = wallet.get_asset_definition('bitcoin')
        self.lblBitcoinBalance.setText('%s BTC' % \
            asset.format_value(wallet.get_balance(asset)))

        moniker = str(self.cbMoniker.currentText())
        asset = wallet.get_asset_definition(moniker)
        self.lblMonikerBalance.setText('%s %s' % \
            (asset.format_value(wallet.get_balance(asset)), moniker))

        self.grpBinds.setTitle('Buy %s' % moniker)
        self.grpSell.setTitle('Sell %s' % moniker)
