from PyQt4 import QtCore, QtGui, uic

from wallet import wallet


class AddressTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent):
        QtCore.QAbstractTableModel.__init__(self)
        self.columns = ['Color', 'Address']
        self.addresses = []

    def rowCount(self, parent):
        return len(self.addresses)

    def columnCount(self, parent):
        return len(self.columns)

    def data(self, index, role):
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.addresses[index.row()][index.column()])
        return QtCore.QVariant()

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal \
                and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.columns[section])
        return QtCore.QVariant()

    def addRow(self, row):
        index = len(self.addresses)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        self.addresses.append(row)
        self.endInsertRows()

    def removeRows(self, row, count, parent=None):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row+count-1)
        for _ in range(row, row+count):
            self.addresses.pop(row)
        self.endRemoveRows()

    def updateData(self):
        self.removeRows(0, len(self.addresses))
        for moniker in wallet.get_all_monikers():
            for address in wallet.get_all_addresses(moniker):
                self.addRow([moniker, address])


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
        self.model.updateData()

    def contextMenuEvent(self, event):
        selected = self.tableView.selectedIndexes()
        if not selected:
            return
        menu = QtGui.QMenu()
        menu.addAction(self.actionCopyAddress)
        menu.addAction(self.actionCopyColor)
        result = menu.exec_(event.globalPos())
        if result is None:
            return
        if result in [self.actionCopyColor, self.actionCopyAddress]:
            text = str(self.proxyModel.data(selected[
                0 if result == self.actionCopyColor else 1]).toString())
            QtGui.QApplication.clipboard().setText(text)

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
