from PyQt4 import QtGui, uic


class MainWindow(QtGui.QMainWindow):
    def __init__(self, ui):
        QtGui.QMainWindow.__init__(self)
        self.ui = ui
        uic.loadUi(ui.get_path_to_ui('mainwindow.ui'), self)
        self.pushButton_2.clicked.connect(self.action_Refresh_onClicked)
        self.pushButton.clicked.connect(self.action_Send_onClicked)
        self.action_Exit.triggered.connect(ui.exit)
        self.move(QtGui.QApplication.desktop().screen().rect().center()- self.rect().center())

    def action_Refresh_onClicked(self):
        asset = self.ui.get_asset_definition(str(self.lineEdit_2.text()))
        balance = self.ui.walletController.get_balance(asset)
        self.label_3.setText(str(balance) + " BTC")

    def action_Send_onClicked(self):
        asset = self.ui.get_asset_definition(str(self.lineEdit_2.text()))
        value = self.doubleSpinBox.value()
        target_addr = str(self.lineEdit.text())
        self.ui.walletController.send_coins(target_addr, asset, value)
