from PyQt4 import QtCore, QtGui, uic


class AddressTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent):
        QtCore.QAbstractTableModel.__init__(self)
        self.columns = ['Color', 'Address']
        self.addresses = [
            ['bitcoin', '1PhPzHMUwbHi3HHjTGGMRgsrWsHq1QXG1f'],
            ['bitcoin', '17LwKaDbzhysqahriTDMAEfEjbbWRMnKCJ'],
            ['bitcoin', '1DKnFhS8bmiGNahefnCQNoDAbCwfT6JP4z'],
            ['bitcoin', '16dcN6vNv3gvTuNuwPfNp6V9sG5iRQ3Pzd'],
            ['bitcoin', '12jszpvWzDkhMB161YyXUqAhhzWaoEzvFq']
        ]

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
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.columns[section];
        return QtCore.QVariant();

class ReceivePage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        uic.loadUi(uic.getUiPath('receivepage.ui'), self)
        self.model = AddressTableModel(self)
        self.setModel(self.model)

    def setModel(self, model):
        self.model = model
        if not model:
            return

        proxyModel = QtGui.QSortFilterProxyModel(self)
        proxyModel.setSourceModel(model)
        proxyModel.setDynamicSortFilter(True)
        proxyModel.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        proxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tableView.setModel(proxyModel)
        self.tableView.sortByColumn(0, QtCore.Qt.AscendingOrder)

        self.tableView.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)
        self.tableView.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.ResizeToContents)

    def update_addresses(self, addresses):
        pass
