from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from createofferdialog import CreateOfferDialog


class OffersTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent):
        QtCore.QAbstractTableModel.__init__(self)
        self.columns = ['oid', 'A.value', 'A.colorid', 'B.value', 'B.colorid']
        self.offers = []

    def rowCount(self, parent=None):
        return len(self.offers)

    def columnCount(self, parent=None):
        return len(self.columns)

    def data(self, index, role):
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.offers[index.row()][index.column()])
        return QtCore.QVariant()

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal \
                and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.columns[section])
        return QtCore.QVariant()

    def addRow(self, row):
        index = len(self.offers)
        self.beginInsertRows(QtCore.QModelIndex(), index, index)
        self.offers.append(row)
        self.endInsertRows()

    def removeRows(self, row, count, parent=None):
        self.beginRemoveRows(QtCore.QModelIndex(), row, row+count-1)
        for _ in range(row, row+count):
            self.offers.pop(row)
        self.endRemoveRows()

    def updateData(self):
        wallet.p2p_agent.update()
        self.removeRows(0, len(self.offers))
        for offer in wallet.p2p_agent.their_offers.values():
            d = offer.get_data()
            self.addRow([d['oid'], d['A']['value'], d['A'].get('colorid', None), d['B']['value'], d['B'].get('colorid')])


class TradePage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('tradepage.ui'), self)

        self.model = OffersTableModel(self)
        self.proxyModel = QtGui.QSortFilterProxyModel(self)
        self.proxyModel.setSourceModel(self.model)
        self.proxyModel.setDynamicSortFilter(True)
        self.proxyModel.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tableView.setModel(self.proxyModel)
        self.tableView.sortByColumn(0, QtCore.Qt.AscendingOrder)
        for i in xrange(self.model.columnCount()):
            self.tableView.horizontalHeader().setResizeMode(
                i, QtGui.QHeaderView.ResizeToContents)

        self.btnCreateSell.clicked.connect(self.get_create_offer_func(True))
        self.btnCreateBuy.clicked.connect(self.get_create_offer_func(False))

    def update(self):
        self.model.updateData()

    def get_create_offer_func(self, sell):
        def func():
            dialog = CreateOfferDialog(self, sell)
            if dialog.exec_():
                offer = wallet.p2ptrade_make_offer(sell, dialog.get_data())
                wallet.p2p_agent.register_my_offer(offer)
            self.update()
        return func
