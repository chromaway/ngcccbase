from PyQt4 import QtCore, QtGui, uic

from wallet import wallet
from tablemodel import TableModel

class HistoryTableModel(TableModel):
    _columns = ['Time', 'Operation', 'Amount', 'Asset', 'Address']
    _alignment = [
        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter,
        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
    ]

class HistoryPage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)
        uic.loadUi(uic.getUiPath('historypage.ui'), self)
        
        self.model = HistoryTableModel(self)
        self.tableView.setModel(self.model)

        self.tableView.horizontalHeader().setResizeMode(
            0, QtGui.QHeaderView.Stretch)
        for i in range(4):
            self.tableView.horizontalHeader().setResizeMode(
                i + 1, QtGui.QHeaderView.ResizeToContents)

    def update(self):
        self.model.removeRows(0, self.model.rowCount())
        tx_history = wallet.model.tx_history
        for ent in tx_history.get_all_entries():
            datetime = QtCore.QDateTime.fromTime_t(ent.txtime)
            datetime_str = datetime.toString(QtCore.Qt.DefaultLocaleShortDate)
            if (ent.txtype == 'send') or (ent.txtype == 'receive'):
                for tgt in ent.get_targets():
                    asset = tgt.get_asset()
                    moniker = asset.get_monikers()[0]
                    value_prefix = "-" if ent.txtype == 'send' else '+'
                    self.model.addRow([datetime_str, ent.txtype, 
                                       value_prefix + tgt.get_formatted_value(),
                                       moniker, tgt.get_address()])
            elif ent.txtype == 'trade':
                print ent.get_in_values()
                print ent.get_out_values()
                for val in ent.get_in_values():
                    asset = val.get_asset()
                    moniker = asset.get_monikers()[0]
                    print [datetime_str, ent.txtype, 
                                       "+" + val.get_formatted_value(),
                                       moniker, '']
                    self.model.addRow([datetime_str, ent.txtype, 
                                       "+" + val.get_formatted_value(),
                                       moniker, ''])
                for val in ent.get_out_values():
                    asset = val.get_asset()
                    moniker = asset.get_monikers()[0]
                    print [datetime_str, ent.txtype, 
                                       "-" + val.get_formatted_value(),
                                       moniker, '']
                    self.model.addRow([datetime_str, ent.txtype, 
                                       "-" + val.get_formatted_value(),
                                       moniker, ''])
            else:
                self.model.addRow([datetime_str, ent.txtype, 
                                   '', '', ''])
