from PyQt4 import QtCore, QtGui, uic

from wallet import wallet


class AddAssetDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(uic.getUiPath('addassetdialog.ui'), self)

        for wname in ['edtMoniker', 'edtColorDesc', 'edtUnit']:
            getattr(self, wname).focusInEvent = \
                lambda e, name=wname: getattr(self, name).setStyleSheet('')

    def isValid(self):
        a = bool(self.edtMoniker.text())
        if not a:
            self.edtMoniker.setStyleSheet('background:#FF8080')

        b = bool(self.edtColorDesc.text())
        if not b:
            self.edtColorDesc.setStyleSheet('background:#FF8080')

        c = str(self.edtUnit.text()).isdigit()
        if not c:
            self.edtUnit.setStyleSheet('background:#FF8080')

        return all([a, b, c])

    def accept(self):
        if self.isValid():
            QtGui.QDialog.accept(self)

    def get_data(self):
        return {
            'moniker': str(self.edtMoniker.text()),
            'color_desc': str(self.edtColorDesc.text()),
            'unit': int(self.edtUnit.text()),
        }


class AssetTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._columns = ['Moniker', 'Color set', 'Unit']
        self._alignment = [
            QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
            QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
        ]
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

    def updateData(self):
        self.removeRows(0, len(self._data))
        for asset in wallet.get_all_asset():
            self.addRow(
                [asset['monikers'][0], asset['color_set'][0], asset['unit']])


class AssetPage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('assetpage.ui'), self)

        self.model = AssetTableModel(self)
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
        self.tableView.horizontalHeader().setResizeMode(
            2, QtGui.QHeaderView.ResizeToContents)

        self.btnAddAsset.clicked.connect(self.btnAddAssetClicked)

    def update(self):
        self.model.updateData()

    def contextMenuEvent(self, event):
        selected = self.tableView.selectedIndexes()
        if not selected:
            return
        actions = [
            self.actionCopyMoniker,
            self.actionCopyColorSet,
            self.actionCopyUnit,
        ]
        menu = QtGui.QMenu()
        for action in actions:
            menu.addAction(action)
        result = menu.exec_(event.globalPos())
        if result is None or result not in actions:
            return
        index = selected[actions.index(result)]
        QtGui.QApplication.clipboard().setText(
            self.proxyModel.data(index).toString())

    def btnAddAssetClicked(self):
        dialog = AddAssetDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            wallet.add_asset(data)
            self.update()
            data = [data['moniker'], data['color_desc'], str(data['unit'])]
            for row in xrange(self.proxyModel.rowCount()):
                valid = True
                for column in xrange(3):
                    index = self.proxyModel.index(row, column)
                    if str(self.proxyModel.data(index).toString()) != data[column]:
                        valid = False
                if valid:
                    self.tableView.selectRow(row)
                    break
