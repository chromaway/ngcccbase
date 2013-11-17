from PyQt4 import QtGui, uic

from wallet import wallet


class CreateOfferDialog(QtGui.QDialog):
    def __init__(self, parent, sell):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(uic.getUiPath('createofferdialog.ui'), self)

        self.cbMoniker.currentIndexChanged.connect(self.cbMonikerIndexChanged)
        self.cbMoniker.addItems(wallet.get_all_monikers())

        self.lblTotal.clear()

        self.edtUnits.textChanged.connect(self.lblTotalBTCRefresh)
        self.edtPrice.textChanged.connect(self.lblTotalBTCRefresh)

        self.btnCreate.setText('Sell' if sell else 'Buy')
        self.btnCreate.clicked.connect(self.btnCreateClicked)
        self.btnCancel.clicked.connect(self.reject)

    def cbMonikerIndexChanged(self):
        asset = wallet.get_asset_definition('bitcoin')
        self.lblAvailableBTC.setText('%s BTC' % \
            asset.format_value(wallet.get_balance(asset)))

        moniker = str(self.cbMoniker.currentText())
        if moniker == 'bitcoin':
            self.lblAvailableMoniker.setVisible(False)
        else:
            self.lblAvailableMoniker.setVisible(True)
            asset = wallet.get_asset_definition(moniker)
            self.lblAvailableMoniker.setText('%s %s' % \
                (asset.format_value(wallet.get_balance(asset)), moniker))

    def lblTotalBTCRefresh(self):
        if not (self.edtUnits.text() and self.edtPrice.text()):
            self.lblTotal.clear()
            return
        value = float(self.edtUnits.text())
        price = float(self.edtPrice.text())
        self.lblTotal.setText('%s BTC' % str(value*price))

    def btnCreateClicked(self):
        # TODO: validate edtUnits, edtPrice, check available balance ...
        if self.edtUnits.text() and self.edtPrice.text():
            self.accept()

    def get_data(self):
        return {
            'moniker': str(self.cbMoniker.currentText()),
            'value': float(self.edtUnits.text()),
            'price': float(self.edtPrice.text()),
        }
