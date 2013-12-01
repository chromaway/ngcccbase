from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import TableModel, ProxyModel


class AddressTableModel(TableModel):
    _columns = ['Moniker', 'Address', 'Balance']
    _alignment = [
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
    ]


class AddressProxyModel(ProxyModel):
    pass


class NewAddressDialog(QtGui.QDialog):
    def __init__(self, moniker, parent):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(uic.getUiPath('newaddressdialog.ui'), self)

        monikers = wallet.get_all_monikers()
        self.cbMoniker.addItems(monikers)
        if moniker in monikers:
            self.cbMoniker.setCurrentIndex(monikers.index(moniker))

    def get_data(self):
        return {
            'moniker': str(self.cbMoniker.currentText()),
        }


class ReceivePage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('receivepage.ui'), self)

        self.model = AddressTableModel(self)
        self.proxyModel = AddressProxyModel(self)
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

        self.cbMoniker.activated.connect(
            lambda *args: self.setMonikerFilter(self.cbMoniker.currentText()))
        self.btnNew.clicked.connect(self.btnNewClicked)
        self.btnCopy.clicked.connect(self.btnCopyClicked)
        self.tableView.selectionModel().selectionChanged.connect(
            self.tableViewSelectionChanged)

    def update(self):
        self.model.removeRows(0, self.model.rowCount())
        for moniker in wallet.get_all_monikers():
            for row in wallet.get_address_balance(moniker):
                self.model.addRow([moniker, row['address'], row['value']])

        moniker = self.cbMoniker.currentText()
        monikers = [''] + wallet.get_all_monikers()
        self.cbMoniker.clear()
        self.cbMoniker.addItems(monikers)
        if moniker in monikers:
            self.cbMoniker.setCurrentIndex(monikers.index(moniker))
        self.setMonikerFilter(self.cbMoniker.currentText())

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

    def setMonikerFilter(self, moniker):
        index = self.cbMoniker.findText(moniker)
        if index == -1:
            return
        if moniker != self.cbMoniker.currentText():
            self.cbMoniker.setCurrentIndex(index)
        self.proxyModel.setFilterKeyColumn(0)
        self.proxyModel.setFilterFixedString(moniker)

    def btnNewClicked(self):
        moniker = None
        selected = self.tableView.selectedIndexes()
        if selected:
            moniker = str(self.proxyModel.data(selected[0]).toString())
        dialog = NewAddressDialog(moniker, self)
        if dialog.exec_():
            moniker = dialog.get_data()['moniker']
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
