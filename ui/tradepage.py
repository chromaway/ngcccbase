from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import AbstractTableModel


class OffersTableModel(AbstractTableModel):
    _columns = ['Quantity', 'Price']
    _alignment = [
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
    ]


class TradePage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('tradepage.ui'), self)

        wallet.p2ptrade_init()

        self.modelBuy = OffersTableModel()
        self.proxyModelBuy = QtGui.QSortFilterProxyModel(self)
        self.proxyModelBuy.setSourceModel(self.modelBuy)
        self.proxyModelBuy.setDynamicSortFilter(True)
        self.proxyModelBuy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModelBuy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tvBuy.setModel(self.proxyModelBuy)
        self.tvBuy.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tvBuy.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        self.tvBuy.horizontalHeader().setResizeMode(
            1, QtGui.QHeaderView.ResizeToContents)

        self.modelSell = OffersTableModel()
        self.proxyModelSell = QtGui.QSortFilterProxyModel(self)
        self.proxyModelSell.setSourceModel(self.modelSell)
        self.proxyModelSell.setDynamicSortFilter(True)
        self.proxyModelSell.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModelSell.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tvSell.setModel(self.proxyModelSell)
        self.tvSell.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tvSell.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        self.tvSell.horizontalHeader().setResizeMode(
            1, QtGui.QHeaderView.ResizeToContents)

        self.cbMoniker.currentIndexChanged.connect(self.cbMonikerIndexChanged)

        for wname in ['edtBuyUnits', 'edtBuyPrice', 'edtSellUnits', 'edtSellPrice']:
            getattr(self, wname).focusInEvent = \
                lambda e, name=wname: getattr(self, name).setStyleSheet('')

        self.edtBuyUnits.textChanged.connect(self.lblBuyTotalChange)
        self.edtBuyPrice.textChanged.connect(self.lblBuyTotalChange)
        self.btnBuy.clicked.connect(self.btnBuyClicked)

        self.edtSellUnits.textChanged.connect(self.lblSellTotalChange)
        self.edtSellPrice.textChanged.connect(self.lblSellTotalChange)
        self.btnSell.clicked.connect(self.btnSellClicked)

    def update(self):
        monikers = wallet.get_all_monikers()
        comboList = self.cbMoniker
        currentMoniker = str(comboList.currentText())
        comboList.clear()
        comboList.addItems(monikers)
        if currentMoniker and currentMoniker in monikers:
            comboList.setCurrentIndex(monikers.index(currentMoniker))

        wallet.p2p_agent.update()
        self.modelBuy.removeRows(0, self.modelBuy.rowCount())
        self.modelSell.removeRows(0, self.modelSell.rowCount())
        for offer in wallet.p2p_agent.their_offers.values():
            data = offer.get_data()
            #from pprint import pprint
            #pprint(data)
            #print

    def cbMonikerIndexChanged(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return
        asset = wallet.get_asset_definition(moniker)
        balance = wallet.get_balance(asset)
        self.lblSell.setText('Sell %s' % moniker)
        self.lblSellAvailable.setText(
            '(Available: %s %s | Units: %s)' % (asset.format_value(balance), moniker, balance))
        asset = wallet.get_asset_definition('bitcoin')
        balance = wallet.get_balance(asset)
        self.lblBuy.setText('Buy %s' % moniker)
        self.lblBuyAvailable.setText(
            '(Available: %s BTC | Units: %s)' % (asset.format_value(balance), balance))

    def lblBuyTotalChange(self):
        self.lblBuyTotal.setText('')
        if self.edtBuyUnits.text().toInt()[1] \
                and self.edtBuyPrice.text().toFloat()[1]:
            total = self.edtBuyUnits.text().toInt()[0]*self.edtBuyPrice.text().toFloat()[0]
            if total > wallet.get_balance('bitcoin'):
                tpl = '<font color=\"#FF3838\">%s bitcoin</font>'
            else:
                tpl = '%s bitcoin'
            self.lblBuyTotal.setText(tpl % total)

    def btnBuyClicked(self):
        valid = True
        if not self.edtBuyUnits.text().toInt()[1]:
            self.edtBuyUnits.setStyleSheet('background:#FF8080')
            valid = False
        if not self.edtBuyPrice.text().toFloat()[1]:
            self.edtBuyPrice.setStyleSheet('background:#FF8080')
            valid = False
        if not valid:
            return
        total = self.edtBuyUnits.text().toInt()[0]*self.edtBuyPrice.text().toFloat()[0]
        if total > wallet.get_balance('bitcoin'):
            return
        offer = wallet.p2ptrade_make_offer(False, {
            'moniker': str(self.cbMoniker.currentText()),
            'value': self.edtBuyUnits.text().toInt()[0],
            'price': self.edtBuyPrice.text().toFloat()[0],
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update()

    def lblSellTotalChange(self):
        self.lblSellTotal.setText('')
        if self.edtSellUnits.text().toInt()[1] \
                and self.edtSellPrice.text().toFloat()[1]:
            total = self.edtSellUnits.text().toInt()[0]*self.edtSellPrice.text().toFloat()[0]
            moniker = str(self.cbMoniker.currentText())
            if total > wallet.get_balance(moniker):
                tpl = '<font color=\"#FF3838\">%s %s</font>'
            else:
                tpl = '%s %s'
            self.lblSellTotal.setText(tpl % (total, moniker))

    def btnSellClicked(self):
        valid = True
        if not self.edtSellUnits.text().toInt()[1]:
            self.edtSellUnits.setStyleSheet('background:#FF8080')
            valid = False
        if not self.edtSellPrice.text().toFloat()[1]:
            self.edtSellPrice.setStyleSheet('background:#FF8080')
            valid = False
        if not valid:
            return
        total = self.edtSellUnits.text().toInt()[0]*self.edtSellPrice.text().toFloat()[0]
        moniker = str(self.cbMoniker.currentText())
        if total > wallet.get_balance(moniker):
            return
        offer = wallet.p2ptrade_make_offer(True, {
            'moniker': moniker,
            'value': self.edtBuyUnits.text().toInt()[0],
            'price': self.edtBuyPrice.text().toFloat()[0],
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update()
