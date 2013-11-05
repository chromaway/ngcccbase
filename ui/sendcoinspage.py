from PyQt4 import QtGui, uic


class SendcoinsPage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        uic.loadUi(uic.getUiPath('sendcoins.ui'), self)

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

    def set_max_amount(self, amount):
        self.edt_amount.setMaximum(amount)
        moniker = self.get_moniker()
        if moniker == 'bitcoin':
            moniker = 'BTC'
        self.lbl_availaleBalance.setText(str(amount) + ' ' + moniker)

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

    def get_data(self):
        data = []
        if all([self.edt_address_validate(), self.edt_amount_validate()]):
            return data
        address = str(self.edt_address.text())
        amount  = self.edt_amount.value()
        moniker = self.get_moniker()
        if address and amount > 0 and moniker:
            data.append({
                'address': address,
                'amount': amount,
                'moniker': moniker,
            })
        return data
