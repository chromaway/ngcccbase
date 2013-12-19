from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import TableModel, ProxyModel


class OffersTableModel(TableModel):
    _columns = ['Price', 'Quantity', 'Total', 'MyOffer']
    _alignment = [
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        0,
    ]


class OffersProxyModel(ProxyModel):
    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.BackgroundRole and index.isValid():
            oid = str(self.data(self.index(index.row(), 3)).toString())
            if oid in wallet.p2p_agent.my_offers:
                return QtCore.QVariant(QtGui.QColor(200, 200, 200))
        return ProxyModel.data(self, index, role)


class TradePage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('tradepage.ui'), self)

        wallet.p2ptrade_init()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_agent)
        self.timer.start(2500)

        self.modelBuy = OffersTableModel(self)
        self.proxyModelBuy = OffersProxyModel(self)
        self.proxyModelBuy.setSourceModel(self.modelBuy)
        self.proxyModelBuy.setDynamicSortFilter(True)
        self.proxyModelBuy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModelBuy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tvBuy.setModel(self.proxyModelBuy)
        self.tvBuy.hideColumn(3)
        self.tvBuy.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tvBuy.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        self.tvBuy.horizontalHeader().setResizeMode(
            1, QtGui.QHeaderView.ResizeToContents)

        self.modelSell = OffersTableModel(self)
        self.proxyModelSell = OffersProxyModel(self)
        self.proxyModelSell.setSourceModel(self.modelSell)
        self.proxyModelSell.setDynamicSortFilter(True)
        self.proxyModelSell.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxyModelSell.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.tvSell.setModel(self.proxyModelSell)
        self.tvSell.hideColumn(3)
        self.tvSell.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.tvSell.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        self.tvSell.horizontalHeader().setResizeMode(
            1, QtGui.QHeaderView.ResizeToContents)

        self.cbMoniker.currentIndexChanged.connect(self.cbMonikerIndexChanged)

        for wname in ['edtBuyQuantity', 'edtBuyPrice', 'edtSellQuantity', 'edtSellPrice']:
            def clearBackground(event, wname=wname):
                getattr(self, wname).setStyleSheet('')
                QtGui.QLineEdit.focusInEvent(getattr(self, wname), event)
            getattr(self, wname).focusInEvent = clearBackground

        self.edtBuyQuantity.textChanged.connect(self.lblBuyTotalChange)
        self.edtBuyPrice.textChanged.connect(self.lblBuyTotalChange)
        self.btnBuy.clicked.connect(self.btnBuyClicked)
        self.tvBuy.doubleClicked.connect(self.tvBuyDoubleClicked)

        self.edtSellQuantity.textChanged.connect(self.lblSellTotalChange)
        self.edtSellPrice.textChanged.connect(self.lblSellTotalChange)
        self.btnSell.clicked.connect(self.btnSellClicked)
        self.tvSell.doubleClicked.connect(self.tvSellDoubleClicked)

        self.need_update_offers = False
        def set_need_update_offers(data):
            self.need_update_offers = True
        wallet.p2p_agent.set_event_handler('offers_updated', 
                                           set_need_update_offers)

        def information_about_offer(offer, action='Create'):
            A, B = offer.get_data()['A'], offer.get_data()['B']
            bitcoin = wallet.get_asset_definition('bitcoin')
            sell_offer = B['color_spec'] == ''
            asset = wallet.get_asset_definition_by_color_set(
                (A if sell_offer else B)['color_spec'])
            value = (A if sell_offer else B)['value']
            total = (B if sell_offer else A)['value']
            text = '{action} {type} offer {value} {moniker} for {price} btc. (Total: {total} btc)'.format(**{
                'action': action,
                'type': 'sell' if sell_offer else 'buy',
                'value': asset.format_value(value),
                'moniker': asset.get_monikers()[0],
                'price': bitcoin.format_value(total*asset.unit/value),
                'total': bitcoin.format_value(total),
            })
            QtGui.QMessageBox.information(self,
                '{action} offer'.format(action=action), text, QtGui.QMessageBox.Yes)

        wallet.p2p_agent.set_event_handler('register_my_offer',
            lambda offer: information_about_offer(offer, 'Create'))
        wallet.p2p_agent.set_event_handler('cancel_my_offer',
            lambda offer: information_about_offer(offer, 'Cancel'))

    def update(self):
        monikers = wallet.get_all_monikers()
        monikers.remove('bitcoin')
        comboList = self.cbMoniker
        currentMoniker = str(comboList.currentText())
        comboList.clear()
        comboList.addItems(monikers)
        if currentMoniker and currentMoniker in monikers:
            comboList.setCurrentIndex(monikers.index(currentMoniker))

    def update_agent(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return
        wallet.p2p_agent.update()
        if self.need_update_offers:
            self.update_offers()

    def update_offers(self):
        self.need_update_offers = False
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return
        bitcoin = wallet.get_asset_definition('bitcoin')
        asset = wallet.get_asset_definition(moniker)
        color_desc = asset.get_color_set().color_desc_list[0]

        selected_oids = [None, None]
        viewsList = [
            [0, self.tvBuy,  self.proxyModelBuy],
            [1, self.tvSell, self.proxyModelSell],
        ]
        for i, view, proxy in viewsList:
            selected = view.selectedIndexes()
            if selected:
                index = proxy.index(selected[0].row(), 3)
                selected_oids[i] = str(proxy.data(index).toString())

        self.modelBuy.removeRows(0, self.modelBuy.rowCount())
        self.modelSell.removeRows(0, self.modelSell.rowCount())
        offers = wallet.p2p_agent.their_offers.items() + wallet.p2p_agent.my_offers.items()
        for i, item in enumerate(offers):
            oid, offer = item
            data = offer.get_data()
            if data['A'].get('color_spec') == color_desc:
                value = data['A']['value']
                total = data['B']['value']
                price = int(total*asset.unit/float(value))
                self.modelSell.addRow([
                    bitcoin.format_value(price),
                    asset.format_value(value),
                    bitcoin.format_value(total),
                    oid,
                ])
            if data['B'].get('color_spec') == color_desc:
                value = data['B']['value']
                total = data['A']['value']
                price = int(total*asset.unit/float(value))
                self.modelBuy.addRow([
                    bitcoin.format_value(price),
                    asset.format_value(value),
                    bitcoin.format_value(total),
                    oid,
                ])

        for i, view, proxy in viewsList:
            for row in xrange(proxy.rowCount()):
                oid = str(proxy.data(proxy.index(row, 3)).toString())
                if oid == selected_oids[i]:
                    view.selectRow(row)

    def cbMonikerIndexChanged(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return

        asset = wallet.get_asset_definition('bitcoin')
        value = asset.format_value(wallet.get_balance(asset))
        text = '<b>Buy</b> {0} (Available: {1} bitcoin)'.format(moniker, value)
        self.lblBuy.setText(text)

        asset = wallet.get_asset_definition(moniker)
        value = asset.format_value(wallet.get_balance(asset))
        text = '<b>Sell</b> {0} (Available: {1} {0})'.format(moniker, value)
        self.lblSell.setText(text)

        self.update_offers()

    def lblBuyTotalChange(self):
        self.lblBuyTotal.setText('')
        if self.edtBuyQuantity.text().toDouble()[1] \
                and self.edtBuyPrice.text().toDouble()[1]:
            value = self.edtBuyQuantity.text().toDouble()[0]
            bitcoin = wallet.get_asset_definition('bitcoin')
            price = bitcoin.parse_value(
                self.edtBuyPrice.text().toDouble()[0])
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
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            return
        offer = wallet.p2ptrade_make_offer(False, {
            'moniker': moniker,
            'value': value,
            'price': price,
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update_offers()
        self.edtBuyQuantity.setText('')
        self.edtBuyPrice.setText('')

    def tvBuyDoubleClicked(self):
        selected = self.tvBuy.selectedIndexes()
        if not selected:
            return
        index = self.proxyModelBuy.index(selected[0].row(), 3)
        oid = str(self.proxyModelBuy.data(index).toString())
        if oid in wallet.p2p_agent.their_offers:
            offer = wallet.p2p_agent.their_offers[oid]
            bitcoin = wallet.get_asset_definition('bitcoin')
            if wallet.get_balance(bitcoin) < offer.get_data()['B']['value']:
                QtGui.QMessageBox.warning(self, '', "Not enough money...",
                    QtGui.QMessageBox.Cancel)
                return
            message = "Sell <b>{value}</b> {moniker} for <b>{course}</b> \
bitcoin (Total: <b>{total}</b> bitcoin)".format(**{
                'value': self.proxyModelBuy.data(selected[1]).toString(),
                'moniker': str(self.cbMoniker.currentText()),
                'course': self.proxyModelBuy.data(selected[0]).toString(),
                'total': self.proxyModelBuy.data(selected[2]).toString(),
            })
            retval = QtGui.QMessageBox.question(
                self, "Confirm buy coins", message,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel,
                QtGui.QMessageBox.Cancel)
            if retval != QtGui.QMessageBox.Yes:
                return
            new_offer = wallet.p2ptrade_make_mirror_offer(offer)
            wallet.p2p_agent.register_my_offer(new_offer)
        else:
            offer = wallet.p2p_agent.my_offers[oid]
            wallet.p2p_agent.cancel_my_offer(offer)
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
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            return
        offer = wallet.p2ptrade_make_offer(True, {
            'moniker': moniker,
            'value': value,
            'price': price,
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update_offers()
        self.edtSellQuantity.setText('')
        self.edtSellPrice.setText('')

    def tvSellDoubleClicked(self):
        selected = self.tvSell.selectedIndexes()
        if not selected:
            return
        index = self.proxyModelSell.index(selected[0].row(), 3)
        oid = str(self.proxyModelSell.data(index).toString())
        if oid in wallet.p2p_agent.their_offers:
            offer = wallet.p2p_agent.their_offers[oid]
            moniker = str(self.cbMoniker.currentText())
            asset = wallet.get_asset_definition(moniker)
            if wallet.get_balance(asset) < offer.get_data()['A']['value']:
                QtGui.QMessageBox.warning(self, '', "Not enough money...",
                    QtGui.QMessageBox.Cancel)
                return
            message = "Buy <b>{value}</b> {moniker} for <b>{course}</b> \
bitcoin (Total: <b>{total}</b> bitcoin)".format(**{
                'value': self.proxyModelSell.data(selected[1]).toString(),
                'moniker': moniker,
                'course': self.proxyModelSell.data(selected[0]).toString(),
                'total': self.proxyModelSell.data(selected[2]).toString(),
            })
            retval = QtGui.QMessageBox.question(
                self, "Confirm buy coins", message,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel,
                QtGui.QMessageBox.Cancel)
            if retval != QtGui.QMessageBox.Yes:
                return
            new_offer = wallet.p2ptrade_make_mirror_offer(offer)
            wallet.p2p_agent.register_my_offer(new_offer)
        else:
            offer = wallet.p2p_agent.my_offers[oid]
            wallet.p2p_agent.cancel_my_offer(offer)
        self.update_offers()
