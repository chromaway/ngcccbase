from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import AbstractTableModel


class AddressTableModel(AbstractTableModel):
    _columns = ['Moniker', 'Address']
    _alignment = [
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
    ]


class NewAddressDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(uic.getUiPath('newaddressdialog.ui'), self)

        self.cbMoniker.addItems(wallet.get_all_monikers())

    def getSelectedMoniker(self):
        return str(self.cbMoniker.currentText())


class ReceivePage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('receivepage.ui'), self)

        self.model = AddressTableModel(self)
        self.proxyModel = QtGui.QSortFilterProxyModel(self)
        self.proxyModel.setSourceModel(self.model)
        self.proxyModel.setDynamicSortFilter(True)
        self.proxyModel.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tableView.setModel(self.proxyModel)
        self.tableView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tableView.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        self.tableView.horizontalHeader().setResizeMode(
            1, QtGui.QHeaderView.ResizeToContents)

        self.chkOnlyBitcoin.stateChanged.connect(self.chkOnlyBitcoinStateChanged)
        self.btnNew.clicked.connect(self.btnNewClicked)
        self.btnCopy.clicked.connect(self.btnCopyClicked)
        self.tableView.selectionModel().selectionChanged.connect(
            self.tableViewSelectionChanged)

    def update(self):
        self.model.removeRows(0, self.model.rowCount())
        for moniker in wallet.get_all_monikers():
            for address in wallet.get_all_addresses(moniker):
                self.model.addRow([moniker, address])

    def contextMenuEvent(self, event):
        selected = self.tableView.selectedIndexes()
        if not selected:
            return
        actions = [
            self.actionCopyAddress,
            self.actionCopyColor,
        ]
        menu = QtGui.QMenu()
        for action in actions:
            menu.addAction(action)
        result = menu.exec_(event.globalPos())
        if result is None or result not in actions:
            return
        index = selected[actions.index(result)]
        QtGui.QApplication.clipboard().setText(
            self.proxyModel.data(index))

    def chkOnlyBitcoinStateChanged(self, checked):
        if checked == QtCore.Qt.Checked:
            self.proxyModel.setFilterFixedString(QtCore.QString('bitcoin'))
            self.proxyModel.setFilterKeyColumn(0)
        else:
            self.proxyModel.setFilterFixedString(QtCore.QString(''))

    def btnNewClicked(self):
        dialog = NewAddressDialog(self)
        if dialog.exec_():
            moniker = dialog.getSelectedMoniker()
            addr = wallet.get_new_address(moniker)
            self.update()
            for row in xrange(self.proxyModel.rowCount()):
                index = self.proxyModel.index(row, 1)
                if str(self.proxyModel.data(index).toString()) == addr:
                    self.tableView.selectRow(row)
                    break

    def btnCopyClicked(self):
        selected = self.tableView.selectedIndexes()
        if selected:
            address = str(self.proxyModel.data(selected[1]).toString())
            QtGui.QApplication.clipboard().setText(address)

    def tableViewSelectionChanged(self, selected, deselected):
        if len(selected):
            self.tableView.selectRow(selected.indexes()[0].row())
            self.btnCopy.setEnabled(True)
        else:
            self.btnCopy.setEnabled(False)
