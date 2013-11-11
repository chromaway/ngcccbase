from PyQt4 import QtGui, uic

from wallet import wallet


class SendcoinsPage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        uic.loadUi(uic.getUiPath('sendcoinspage.ui'), self)

        self.btn_send.clicked.connect(self.on_btnSend)
        self.edt_address.returnPressed.connect(self.on_btnSend)
        self.edt_amount.editingFinished.connect(lambda: self.on_btnSend() if self.edt_amount.hasFocus() else 0)
        self.cb_monikers.currentIndexChanged.connect(self.updateAvailableBalance)

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

    def edt_address_validate(self):
        valid = True
        if len(str(self.edt_address.text())) != 34:
            valid = False
            self.edt_address.setStyleSheet('background:#FF8080')
        else:
            self.edt_address.setStyleSheet('')
        return valid

    def edt_amount_validate(self):
        valid = True
        if self.edt_amount.value() == 0:
            valid = False
            self.edt_amount.setStyleSheet('background:#FF8080')
        else:
            self.edt_amount.setStyleSheet('')
        return valid

    def on_btnSend(self):
        data = []
        if all([self.edt_address_validate(), self.edt_amount_validate()]):
            return data
        address = str(self.edt_address.text())
        amount  = self.edt_amount.value()
        moniker = str(self.cb_monikers.currentText())
        if address and amount > 0 and moniker:
            data.append({
                'address': address,
                'value': amount,
                'moniker': moniker,
            })
        if not data:
            return
        message = 'Are you sure you want to send'
        for recipient in data:
            message += '<br><b>{amount} {moniker}</b> to {address}'.format(**recipient)
        message += '?'
        retval = QtGui.QMessageBox.question(self, 'Confirm send coins',
            message,
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel,
            QtGui.QMessageBox.Cancel)
        if retval == QtGui.QMessageBox.Yes:
            wallet.send_coins(data)

    def updateAvailableBalance(self):
        moniker = str(self.cb_monikers.currentText())
        if moniker:
            balance = wallet.get_balance(moniker)
            asset = wallet.get_asset_definition(moniker)
            self.edt_amount.setMaximum(balance)
            self.lbl_availaleBalance.setText('%s %s' % (asset.format_value(balance), moniker))
