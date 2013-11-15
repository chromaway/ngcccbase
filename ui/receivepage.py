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
        if not index.isValid():
            return QtCore.QVariant()
        elif role != QtCore.Qt.DisplayRole and role != QtCore.Qt.EditRole:
            return QtCore.QVariant()
        value = ''
        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            col = index.column()
            value = self.addresses[row][col]
        return QtCore.QVariant(value)

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal \
                and role == QtCore.Qt.DisplayRole:
            return self.columns[section]
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
        monikers = wallet.get_all_monikers()
        for moniker in monikers:
            for address in wallet.get_all_addresses(moniker):
                self.addRow([moniker, address])


class ReceivePage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
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

        self.chk_onlyBitcoin.stateChanged.connect(self.on_chkOnlyBitcoin)
        self.btn_copy.clicked.connect(self.on_btnCopy)
        self.tableView.selectionModel().selectionChanged.connect(
            self.on_tableViewSelect)

    def update(self):
        self.model.updateData()

    def on_chkOnlyBitcoin(self, checked):
        if checked == QtCore.Qt.Checked:
            self.proxyModel.setFilterFixedString(QtCore.QString('bitcoin'))
            self.proxyModel.setFilterKeyColumn(0)
        else:
            self.proxyModel.setFilterFixedString(QtCore.QString(''))

    def on_btnCopy(self):
        selected = self.tableView.selectedIndexes()
        if selected:
            address = str(self.proxyModel.data(selected[1]).toString())
            clipboard = QtGui.QApplication.clipboard()
            clipboard.setText(address)

    def on_tableViewSelect(self, selected, deselected):
        if len(selected):
            self.tableView.selectRow(selected.indexes()[0].row())
            self.btn_copy.setEnabled(True)
        else:
            self.btn_copy.setEnabled(False)
