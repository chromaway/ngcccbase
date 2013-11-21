from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import AbstractTableModel


class OffersTableModel(AbstractTableModel):
    _columns = ['Price', 'Quantity', 'Total']
    _alignment = [
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
    ]


class TradePage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('tradepage.ui'), self)

        wallet.p2ptrade_init()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_offers)
        self.timer.start(2500)

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

        for wname in ['edtBuyQuantity', 'edtBuyPrice', 'edtSellQuantity', 'edtSellPrice']:
            getattr(self, wname).focusInEvent = \
                lambda e, name=wname: getattr(self, name).setStyleSheet('')

        self.edtBuyQuantity.textChanged.connect(self.lblBuyTotalChange)
        self.edtBuyPrice.textChanged.connect(self.lblBuyTotalChange)
        self.btnBuy.clicked.connect(self.btnBuyClicked)

        self.edtSellQuantity.textChanged.connect(self.lblSellTotalChange)
        self.edtSellPrice.textChanged.connect(self.lblSellTotalChange)
        self.btnSell.clicked.connect(self.btnSellClicked)

    def update(self):
        monikers = wallet.get_all_monikers()
        monikers.remove('bitcoin')
        comboList = self.cbMoniker
        currentMoniker = str(comboList.currentText())
        comboList.clear()
        comboList.addItems(monikers)
        if currentMoniker and currentMoniker in monikers:
            comboList.setCurrentIndex(monikers.index(currentMoniker))

    def update_offers(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return
        bitcoin = wallet.get_asset_definition('bitcoin')
        asset = wallet.get_asset_definition(moniker)
        color_desc = asset.get_color_set().color_desc_list[0]

        wallet.p2p_agent.update()
        self.modelBuy.removeRows(0, self.modelBuy.rowCount())
        self.modelSell.removeRows(0, self.modelSell.rowCount())
        for offer in wallet.p2p_agent.their_offers.values():
            data = offer.get_data()
            if data['A'].get('color_spec') == color_desc:
                value = data['A']['value']
                total = data['B']['value']
                price = int(total*asset.unit/float(value))
                self.modelBuy.addRow([
                    bitcoin.format_value(price),
                    asset.format_value(value),
                    bitcoin.format_value(total),
                ])
            if data['B'].get('color_spec') == color_desc:
                value = data['B']['value']
                total = data['A']['value']
                price = int(total*asset.unit/float(value))
                self.modelSell.addRow([
                    bitcoin.format_value(price),
                    asset.format_value(value),
                    bitcoin.format_value(total),
                ])

    def cbMonikerIndexChanged(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return
        asset = wallet.get_asset_definition(moniker)
        balance = wallet.get_balance(asset)
        self.lblSell.setText('Sell %s' % moniker)
        self.lblSellAvailable.setText(
            '(Available: %s %s)' % (asset.format_value(balance), moniker))
        asset = wallet.get_asset_definition('bitcoin')
        balance = wallet.get_balance(asset)
        self.lblBuy.setText('Buy %s' % moniker)
        self.lblBuyAvailable.setText(
            '(Available: %s bitcoin)' % asset.format_value(balance))
        self.update_offers()

    def lblBuyTotalChange(self):
        self.lblBuyTotal.setText('')
        if self.edtBuyQuantity.text().toDouble()[1] \
                and self.edtBuyPrice.text().toDouble()[1]:
            value = self.edtBuyQuantity.text().toDouble()[0]
            bitcoin = wallet.get_asset_definition('bitcoin')
            price = bitcoin.parse_value(
                self.edtBuyPrice.text().toDouble()[0])
            print price
            total = value*price
            self.lblBuyTotal.setText('%s bitcoin' % bitcoin.format_value(total))

    def btnBuyClicked(self):
        valid = True
        if not self.edtBuyQuantity.text().toDouble()[1]:
            self.edtBuyQuantity.setStyleSheet('background:#FF8080')
            valid = False
        if not self.edtBuyPrice.text().toDouble()[1]:
            self.edtBuyPrice.setStyleSheet('background:#FF8080')
            valid = False
        if not valid:
            return
        moniker = str(self.cbMoniker.currentText())
        asset = wallet.get_asset_definition(moniker)
        value = self.edtBuyQuantity.text().toDouble()[0]
        bitcoin = wallet.get_asset_definition('bitcoin')
        price = self.edtBuyPrice.text().toDouble()[0]
        delta = wallet.get_balance(bitcoin) - value*bitcoin.parse_value(price)
        if delta < 0:
            message = 'The transaction amount exceeds the balance by %s bitcoin' % \
                bitcoin.format_value(-delta)
            QtGui.QMessageBox.critical(
                self, '', message,
                QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
            return
        offer = wallet.p2ptrade_make_offer(False, {
            'moniker': moniker,
            'value': value,
            'price': price,
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update_offers()

    def lblSellTotalChange(self):
        self.lblSellTotal.setText('')
        if self.edtSellQuantity.text().toDouble()[1] \
                and self.edtSellPrice.text().toDouble()[1]:
            value = self.edtSellQuantity.text().toDouble()[0]
            bitcoin = wallet.get_asset_definition('bitcoin')
            price = bitcoin.parse_value(
                self.edtSellPrice.text().toDouble()[0])
            total = value*price
            self.lblSellTotal.setText('%s bitcoin' % bitcoin.format_value(total))

    def btnSellClicked(self):
        valid = True
        if not self.edtSellQuantity.text().toDouble()[1]:
            self.edtSellQuantity.setStyleSheet('background:#FF8080')
            valid = False
        if not self.edtSellPrice.text().toDouble()[1]:
            self.edtSellPrice.setStyleSheet('background:#FF8080')
            valid = False
        if not valid:
            return
        moniker = str(self.cbMoniker.currentText())
        asset = wallet.get_asset_definition(moniker)
        value = self.edtSellQuantity.text().toDouble()[0]
        bitcoin = wallet.get_asset_definition('bitcoin')
        price = self.edtSellPrice.text().toDouble()[0]
        delta = wallet.get_balance(asset) - asset.parse_value(value)
        if delta < 0:
            message = 'The transaction amount exceeds the balance by %s %s' % \
                (asset.format_value(-delta), moniker)
            QtGui.QMessageBox.critical(
                self, '', message,
                QtGui.QMessageBox.Ok, QtGui.QMessageBox.Ok)
            return
        offer = wallet.p2ptrade_make_offer(True, {
            'moniker': moniker,
            'value': value,
            'price': price,
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update_offers()
