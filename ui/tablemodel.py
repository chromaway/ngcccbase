from PyQt4 import QtCore, QtGui


class TableModel(QtCore.QAbstractTableModel):
    _columns = None
    _alignment = None

    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._data = []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._columns)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid():
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.QVariant(self._alignment[index.column()])
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(self._data[index.row()][index.column()])

        return QtCore.QVariant()

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation == QtCore.Qt.Horizontal \
                and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self._columns[section])

        return QtCore.QVariant()

    def addRow(self, row):
        index = len(self._data)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        self._data.append(row)
        self.endInsertRows()

    def removeRows(self, row, count, parent=None):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row+count-1)
        for _ in range(row, row+count):
            self._data.pop(row)
        self.endRemoveRows()


class ProxyModel(QtGui.QSortFilterProxyModel):
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.isValid() and role == QtCore.Qt.BackgroundRole:
            if index.row() % 2 == 1:
                color = QtGui.QColor(243, 243, 243)
            else:
                color = QtGui.QColor(255, 255, 255)
            return QtCore.QVariant(color)
        return QtGui.QSortFilterProxyModel.data(self, index, role)
