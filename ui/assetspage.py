import json
from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import TableModel, ProxyModel


class AddAssetDialog(QtGui.QDialog):
    def __init__(self, parent, data=None):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(uic.getUiPath('addassetdialog.ui'), self)

        for wname in ['edtMoniker', 'edtColorDesc', 'edtUnit']:
            def clearBackground(event, wname=wname):
                getattr(self, wname).setStyleSheet('')
                QtGui.QLineEdit.focusInEvent(getattr(self, wname), event)
            getattr(self, wname).focusInEvent = clearBackground

        data = data or {}
        self.edtMoniker.setText(data.get('moniker', ''))
        self.edtColorDesc.setText(data.get('color_desc', ''))
        self.edtUnit.setText(data.get('unit', ''))
        self.btnBox.setFocus()

    def isValid(self):
        moniker = self.edtMoniker.text()
        a = bool(moniker)
        if a and moniker in wallet.get_all_monikers():
            QtGui.QMessageBox.warning(
                self, 'Already exists!',
                "Moniker <b>%s</b> already exists!" % moniker,
                QtGui.QMessageBox.Ok)
            a = False
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


class IssueCoinsDialog(QtGui.QDialog):
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        uic.loadUi(uic.getUiPath('issuedialog.ui'), self)

        self.cbScheme.addItem('obc')

        for wname in ['edtMoniker', 'edtUnits', 'edtAtoms']:
            def clearBackground(event, wname=wname):
                getattr(self, wname).setStyleSheet('')
                QtGui.QLineEdit.focusInEvent(getattr(self, wname), event)
            getattr(self, wname).focusInEvent = clearBackground

        self.edtUnits.textChanged.connect(self.changeTotalBTC)
        self.edtAtoms.textChanged.connect(self.changeTotalBTC)

        self.availableBTC = wallet.get_balance('bitcoin')
        self.lblTotalBTC.setToolTip('Available: %s bitcoin' % \
            wallet.get_asset_definition('bitcoin').format_value(self.availableBTC))

    def changeTotalBTC(self):
        amount = self.edtUnits.text().toInt()
        units = self.edtAtoms.text().toInt()
        if amount[1] and units[1]:
            need = amount[0] * units[0]
            text = '%s bitcoin' % \
                wallet.get_asset_definition('bitcoin').format_value(need)
            if need > self.availableBTC:
                text = '<font color="#FF3838">%s</font>' % text
            self.lblTotalBTC.setText(text)

    def isValid(self):
        moniker = self.edtMoniker.text()
        a = bool(moniker)
        if a and moniker in wallet.get_all_monikers():
            QtGui.QMessageBox.warning(
                self, 'Already exists!',
                "Moniker <b>%s</b> already exists!" % moniker,
                QtGui.QMessageBox.Ok)
            a = False
        if not a:
            self.edtMoniker.setStyleSheet('background:#FF8080')

        b = self.edtUnits.text().toInt()
        if not b[1]:
            self.edtUnits.setStyleSheet('background:#FF8080')

        c = self.edtAtoms.text().toInt()
        if not c[1]:
            self.edtAtoms.setStyleSheet('background:#FF8080')

        d = False
        if b[1] and c[1] and b[0]*c[0] <= self.availableBTC:
            d = True

        return all([a, b, c, d])

    def accept(self):
        if self.isValid():
            QtGui.QDialog.accept(self)

    def get_data(self):
        return {
            'moniker': str(self.edtMoniker.text()),
            'coloring_scheme': str(self.cbScheme.currentText()),
            'units': self.edtUnits.text().toInt()[0],
            'atoms': self.edtAtoms.text().toInt()[0],
        }


class AssetTableModel(TableModel):
    _columns = ['Moniker', 'Color set', 'Unit']
    _alignment = [
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
    ]


class AssetProxyModel(ProxyModel):
    pass


class AssetsPage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('assetspage.ui'), self)

        self.model = AssetTableModel(self)
        self.proxyModel = AssetProxyModel(self)
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

        self.btnAddNewAsset.clicked.connect(self.btnAddNewAssetClicked)
        self.btnAddExistingAsset.clicked.connect(self.btnAddExistingAssetClicked)
        self.btnImportAssetFromJSON.clicked.connect(self.btnImportAssetFromJSONClicked)

    def update(self):
        self.model.removeRows(0, self.model.rowCount())
        for asset in wallet.get_all_asset():
            self.model.addRow(
                [asset['monikers'][0], asset['color_set'][0], asset['unit']])

    def contextMenuEvent(self, event):
        selected = self.tableView.selectedIndexes()
        if not selected:
            return
        actions = [
            self.actionCopyMoniker,
            self.actionCopyColorSet,
            self.actionCopyUnit,
            self.actionCopyAsJSON,
            self.actionShowAddresses,
        ]
        menu = QtGui.QMenu()
        for action in actions:
            menu.addAction(action)
        result = menu.exec_(event.globalPos())
        if result is None or result not in actions:
            return
        if actions.index(result) in [0, 1, 2]:
            index = selected[actions.index(result)]
            QtGui.QApplication.clipboard().setText(
                self.proxyModel.data(index).toString())
        elif actions.index(result) == 3:
            moniker = str(self.proxyModel.data(selected[0]).toString())
            asset = wallet.get_asset_definition(moniker)
            QtGui.QApplication.clipboard().setText(
                json.dumps(asset.get_data()))
        elif actions.index(result) == 4:
            window = self.parentWidget().parentWidget().parentWidget()
            window.gotoReceivePage()
            window.receivepage.setMonikerFilter(
                self.proxyModel.data(selected[0]).toString())

    def selectRowByMoniker(self, moniker):
        moniker = QtCore.QString(moniker)
        for row in xrange(self.proxyModel.rowCount()):
            index = self.proxyModel.index(row, 0)
            if self.proxyModel.data(index).toString() == moniker:
                self.tableView.selectRow(row)
                break

    def btnAddNewAssetClicked(self):
        dialog = IssueCoinsDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            wallet.issue(data)
            self.update()
            self.selectRowByMoniker(data['moniker'])
            self.parent().parent().parent().update()

    def btnAddExistingAssetClicked(self, data=None):
        dialog = AddAssetDialog(self, data)
        if dialog.exec_():
            data = dialog.get_data()
            wallet.add_asset(data)
            self.update()
            self.selectRowByMoniker(data['moniker'])
            self.parent().parent().parent().update()

    def btnImportAssetFromJSONClicked(self):
        text, ok = QtGui.QInputDialog.getText(self, "Import asset from JSON", "JSON: ")
        if ok:
            try:
                data = json.loads(str(text))
                self.btnAddExistingAssetClicked({
                    'moniker': str(data['monikers'][0]),
                    'color_desc': str(data['color_set'][0]),
                    'unit': str(data['unit']),
                })
            except Exception, e:
                QtGui.QMessageBox.critical(self,
                    '', str(e), QtGui.QMessageBox.Ok)
