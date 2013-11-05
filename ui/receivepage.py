from PyQt4 import QtCore, QtGui, uic


class ReceivePage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        uic.loadUi(uic.getUiPath('receivepage.ui'), self)
        self.model = QtGui.QStandardItemModel(0, 3, self)
        self.model.setHorizontalHeaderItem(0, QtGui.QStandardItem(QtCore.QString('Color')))
        self.model.setHorizontalHeaderItem(1, QtGui.QStandardItem(QtCore.QString('Balance')))
        self.model.setHorizontalHeaderItem(2, QtGui.QStandardItem(QtCore.QString('Address')))
        self.tbl_addresses.setModel(self.model)

    def update_addresses(self, addresses):
        self.model.clear()
        for address in addresses:
            self.model.appendRow([
                QtGui.QStandardItem(QtCore.QString(address['moniker'])),
                QtGui.QStandardItem(QtCore.QString(address['balance'])),
                QtGui.QStandardItem(QtCore.QString(address['address']))])
