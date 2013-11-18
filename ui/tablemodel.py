from PyQt4 import QtCore


class AbstractTableModel(QtCore.QAbstractTableModel):
    _columns = None
    _alignment = None

    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._data = []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._columns)

    def data(self, index, role):
        if role == QtCore.Qt.TextAlignmentRole:
            return self._alignment[index.column()]

        if index.isValid() and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self._data[index.row()][index.column()])

        return QtCore.QVariant()

    def headerData(self, section, orientation, role):
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
