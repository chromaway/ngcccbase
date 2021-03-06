from PyQt4 import QtCore, QtGui, uic

from decimal import Decimal
from wallet import wallet
from tablemodel import TableModel, ProxyModel

import logging


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
        self.logger = logging.getLogger('ngcccbase.ui.trade')

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

        self.cbMoniker.currentIndexChanged.connect(self.update_balance)

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

        def information_about_offer(offer, action, buysell_text):
            A, B = offer.get_data()['A'], offer.get_data()['B']
            bitcoin = wallet.get_asset_definition('bitcoin')
            sell_offer = B['color_spec'] == ''
            asset = wallet.get_asset_definition_by_color_set(
                (A if sell_offer else B)['color_spec'])
            value = (A if sell_offer else B)['value']
            total = (B if sell_offer else A)['value']
            if not value:
                return # division by zero
            text = '{action} {type} {value} {moniker} @{price} btc ea. (Total: {total} btc)'.format(**{
                'action': action,
                'type': buysell_text[sell_offer],
                'value': asset.format_value(value),
                'moniker': asset.get_monikers()[0],
                'price': bitcoin.format_value(total*asset.unit/value),
                'total': bitcoin.format_value(total),
            })
            self.add_log_entry(text)

        wallet.p2p_agent.set_event_handler(
            'register_my_offer',
            lambda offer: information_about_offer(offer, 'Created', ("bid", "ask")))
        wallet.p2p_agent.set_event_handler(
            'cancel_my_offer',
            lambda offer: information_about_offer(offer, 'Canceled', ("bid", "ask")))
        wallet.p2p_agent.set_event_handler(
            'make_ep',
            lambda ep: information_about_offer(ep.my_offer, 'In progress',
                                               ('buying', 'selling')))
        wallet.p2p_agent.set_event_handler(
            'accept_ep',
            lambda eps: information_about_offer(eps[1].my_offer, 'In progress',
                                                ('buying', 'selling')))
        def on_trade_complete(ep):
            information_about_offer(ep.my_offer,
                                    'Trade complete:', ('bought', 'sold'))
            self.update_balance()
        wallet.p2p_agent.set_event_handler('trade_complete', on_trade_complete)

    def add_log_entry(self, text):
        self.listEventLog.addItem(text)

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
                price = int(Decimal(total)*Decimal(asset.unit)/Decimal(value))
                self.modelSell.addRow([
                    bitcoin.format_value(price),
                    asset.format_value(value),
                    bitcoin.format_value(total),
                    oid,
                ])
            if data['B'].get('color_spec') == color_desc:
                value = data['B']['value']
                total = data['A']['value']
                price = int(Decimal(total)*Decimal(asset.unit)/Decimal(value))
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

    def update_balance(self):
        moniker = str(self.cbMoniker.currentText())
        if moniker == '':
            return

        asset = wallet.get_asset_definition('bitcoin')
        value = asset.format_value(wallet.get_available_balance(asset))
        self.lblBuy.setText('<b>Buy</b> %s' % moniker)
        self.lblBuyAvail.setText('(Available: %s bitcoin)' % value)

        asset = wallet.get_asset_definition(moniker)
        value = asset.format_value(wallet.get_available_balance(asset))
        self.lblSell.setText('<b>Sell</b> %s' % moniker)
        self.lblSellAvail.setText('(Available: %s %s)' % (value, moniker))

        self.update_offers()

    def lblBuyTotalChange(self):
        bitcoin = wallet.get_asset_definition('bitcoin')
        quantity = self._to_decimal(self.edtBuyQuantity)
        price = bitcoin.parse_value(self._to_decimal(self.edtBuyPrice))
        total = quantity * price
        if total:
            self.lblBuyTotal.setText('%sBTC' % bitcoin.format_value(total))
        else:
            self.lblBuyTotal.setText('')

    def validate_buy_input(self, quantity, price):
        moniker = str(self.cbMoniker.currentText())
        asset = wallet.get_asset_definition(moniker)
        bitcoin = wallet.get_asset_definition('bitcoin')

        # check if quantity was given
        if quantity <= Decimal("0"): # no quantity
            self.edtBuyQuantity.setStyleSheet('background:#FF8080')
            return False

        # check if price was given
        if price <= Decimal("0"): # no price
            self.edtBuyPrice.setStyleSheet('background:#FF8080')
            return False

        # quantity must be multiple of atom
        if not asset.validate_value(quantity):
            message = "Quantity must be a multiple of %s!" % asset.get_atom()
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            self.edtBuyQuantity.setStyleSheet('background:#FF8080')
            return False

        # price must be multiple of atom
        if not bitcoin.validate_value(price):
            message = "Price must be a multiple of %s!" % asset.get_atom()
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            self.edtBuyPrice.setStyleSheet('background:#FF8080')
            return False

        # check if amount exceeds available balance
        needed = quantity * bitcoin.parse_value(price)
        available = wallet.get_available_balance(bitcoin)
        delta = available - needed
        if delta < 0:
            neg_delta = bitcoin.format_value(-delta)
            msg_str = 'The amount exceeds available balance by %s bitcoin!'
            message = msg_str % neg_delta
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            self.edtBuyQuantity.setStyleSheet('background:#FF8080')
            self.edtBuyPrice.setStyleSheet('background:#FF8080')
            return False

        return True

    def _to_decimal(self, edit_field):
        try:
            return Decimal(str(edit_field.text()))
        except:
            return Decimal("0")

    def btnBuyClicked(self):
        quantity = self._to_decimal(self.edtBuyQuantity)
        price = self._to_decimal(self.edtBuyPrice)
        if not self.validate_buy_input(quantity, price):
            return # invalid input
        moniker = str(self.cbMoniker.currentText())
        offer = wallet.p2ptrade_make_offer(False, {
            'moniker': moniker,
            'value': quantity,
            'price': price,
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update_offers()
        self.edtBuyQuantity.setText('')
        self.edtBuyPrice.setText('')

    def tvBuyDoubleClicked(self):
        """click on bids, colored coins will be sold"""
        selected = self.tvBuy.selectedIndexes()
        if not selected:
            return
        index = self.proxyModelBuy.index(selected[0].row(), 3)
        oid = str(self.proxyModelBuy.data(index).toString())
        if oid in wallet.p2p_agent.their_offers:
            offer = wallet.p2p_agent.their_offers[oid]
            moniker = str(self.cbMoniker.currentText())
            asset = wallet.get_asset_definition(moniker)
            if wallet.get_available_balance(asset) < offer.get_data()['B']['value']:
                self.logger.warn("%s avail <  %s required",
                                 wallet.get_available_balance(asset),
                                 offer.get_data()['A']['value'])
                msg = "Not enough coins: %s %s needed, %s available" % \
                    (str(self.proxyModelBuy.data(selected[2]).toString()),
                     moniker,
                     asset.format_value(wallet.get_available_balance(asset)))
                QtGui.QMessageBox.warning(self, '', msg,
                    QtGui.QMessageBox.Ok)
                return
            message = "About to <u>sell</u> <b>{value}</b> {moniker} @ <b>{course}</b> \
bitcoin each. <br> (Total: <b>{total}</b> bitcoin)".format(**{
                'value': self.proxyModelBuy.data(selected[1]).toString(),
                'moniker': str(self.cbMoniker.currentText()),
                'course': self.proxyModelBuy.data(selected[0]).toString(),
                'total': self.proxyModelBuy.data(selected[2]).toString(),
            })
            retval = QtGui.QMessageBox.question(
                self, "Confirm buying asset", message,
                QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
                QtGui.QMessageBox.Cancel)
            if retval != QtGui.QMessageBox.Ok:
                return
            new_offer = wallet.p2ptrade_make_mirror_offer(offer)
            wallet.p2p_agent.register_my_offer(new_offer)
        else:
            offer = wallet.p2p_agent.my_offers[oid]
            wallet.p2p_agent.cancel_my_offer(offer)
        self.update_offers()

    def lblSellTotalChange(self):
        bitcoin = wallet.get_asset_definition('bitcoin')
        quantity = self._to_decimal(self.edtSellQuantity)
        price = bitcoin.parse_value(self._to_decimal(self.edtSellPrice))
        total = quantity * price
        if total:
            self.lblSellTotal.setText('%sBTC' % bitcoin.format_value(total))
        else:
            self.lblSellTotal.setText('')

    def validate_sell_input(self, quantity, price):
        moniker = str(self.cbMoniker.currentText())
        asset = wallet.get_asset_definition(moniker)
        bitcoin = wallet.get_asset_definition('bitcoin')

        # check if quantity was given
        if quantity <= Decimal("0"): # no quantity
            self.edtSellQuantity.setStyleSheet('background:#FF8080')
            return False

        # check if price was given
        if price <= Decimal("0"): # no price
            self.edtSellPrice.setStyleSheet('background:#FF8080')
            return False

        # quantity must be multiple of atom
        if not asset.validate_value(quantity):
            atom = asset.format_value(1)
            message = "Quantity must be a multiple of %s!" % atom
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            self.edtSellQuantity.setStyleSheet('background:#FF8080')
            return False

        # price must be multiple of atom
        if not bitcoin.validate_value(price):
            atom = bitcoin.format_value(1)
            message = "Price must be a multiple of %s!" % atom
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            self.edtSellPrice.setStyleSheet('background:#FF8080')
            return False

        # check if amount exceeds available balance
        needed = asset.parse_value(quantity)
        delta = wallet.get_available_balance(asset) - needed
        if delta < 0:
            args = (asset.format_value(-delta), moniker)
            msg_str = 'The amount exceeds available balance by %s %s'
            message = msg_str % args
            QtGui.QMessageBox.critical(self, '', message, QtGui.QMessageBox.Ok)
            self.edtSellQuantity.setStyleSheet('background:#FF8080')
            self.edtSellPrice.setStyleSheet('background:#FF8080')
            return False

        return True


    def btnSellClicked(self):
        quantity = self._to_decimal(self.edtSellQuantity)
        price = self._to_decimal(self.edtSellPrice)
        if not self.validate_sell_input(quantity, price):
            return # invalid input
        moniker = str(self.cbMoniker.currentText())
        offer = wallet.p2ptrade_make_offer(True, {
            'moniker': moniker,
            'value': quantity,
            'price': price,
        })
        wallet.p2p_agent.register_my_offer(offer)
        self.update_offers()
        self.edtSellQuantity.setText('')
        self.edtSellPrice.setText('')

    def tvSellDoubleClicked(self):
        """"Click on asks, colored coins are going to be bought"""
        selected = self.tvSell.selectedIndexes()
        if not selected:
            return
        index = self.proxyModelSell.index(selected[0].row(), 3)
        oid = str(self.proxyModelSell.data(index).toString())
        if oid in wallet.p2p_agent.their_offers:
            offer = wallet.p2p_agent.their_offers[oid]
            moniker = str(self.cbMoniker.currentText())
            bitcoin = wallet.get_asset_definition('bitcoin')
            if wallet.get_available_balance(bitcoin) < offer.get_data()['B']['value']:
                self.logger.warn("Not enough money: %s <  %s",
                                 wallet.get_available_balance(bitcoin),
                                 offer.get_data()['B']['value'])
                msg = "Not enough money: %s bitcoins needed, %s available" % \
                    (self.proxyModelSell.data(selected[2]).toString(),
                     bitcoin.format_value(wallet.get_available_balance(bitcoin)))
                QtGui.QMessageBox.warning(self, '', msg,
                                          QtGui.QMessageBox.Ok)
                return
            message = "About to <u>buy</u> <b>{value}</b> {moniker} @ <b>{course}</b> \
bitcoin each. <br> (Total: <b>{total}</b> bitcoin)".format(**{
                'value': self.proxyModelSell.data(selected[1]).toString(),
                'moniker': moniker,
                'course': self.proxyModelSell.data(selected[0]).toString(),
                'total': self.proxyModelSell.data(selected[2]).toString(),
            })
            retval = QtGui.QMessageBox.question(
                self, "Confirm buy coins", message,
                QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel,
                QtGui.QMessageBox.Cancel)
            if retval != QtGui.QMessageBox.Ok:
                return
            new_offer = wallet.p2ptrade_make_mirror_offer(offer)
            wallet.p2p_agent.register_my_offer(new_offer)
        else:
            offer = wallet.p2p_agent.my_offers[oid]
            wallet.p2p_agent.cancel_my_offer(offer)
        self.update_offers()
