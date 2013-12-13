from PyQt4 import QtCore, QtGui, uic

from wallet import wallet


class OverviewPage(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        layout1 = QtGui.QVBoxLayout(self)
        layout1.setMargin(0)

        self.scrollArea = QtGui.QScrollArea(self)
        layout1.addWidget(self.scrollArea)
        self.scrollArea.setLineWidth(1)
        self.scrollArea.setWidgetResizable(True)

    def update(self):
        allowTextSelection = (
            QtCore.Qt.LinksAccessibleByMouse |
            QtCore.Qt.TextSelectableByKeyboard |
            QtCore.Qt.TextSelectableByMouse)

        self.scrollAreaContents = QtGui.QWidget()
        self.scrollArea.setWidget(self.scrollAreaContents)
        self.scrollAreaLayout = QtGui.QVBoxLayout(self.scrollAreaContents)

        hbox = QtGui.QHBoxLayout()
        hbox.addItem(QtGui.QSpacerItem(20, 0))
        hbox.setStretch(0, 1)
        updateButton = QtGui.QPushButton('Update', self.scrollAreaContents)
        updateButton.clicked.connect(self.updateButtonClicked)
        hbox.addWidget(updateButton)
        self.scrollAreaLayout.addLayout(hbox)

        for moniker in wallet.get_all_monikers():
            asset = wallet.get_asset_definition(moniker)
            address = wallet.get_some_address(asset)
            balance = wallet.get_balance(asset)

            groupBox = QtGui.QGroupBox(moniker, self.scrollAreaContents)
            layout = QtGui.QFormLayout(groupBox)

            label = QtGui.QLabel(groupBox)
            label.setText('Balance:')
            layout.setWidget(0, QtGui.QFormLayout.LabelRole, label)

            label = QtGui.QLabel(groupBox)
            label.setTextInteractionFlags(allowTextSelection)
            label.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
            label.setText(asset.format_value(balance))
            layout.setWidget(0, QtGui.QFormLayout.FieldRole, label)

            label = QtGui.QLabel(groupBox)
            label.setText('Address:')
            layout.setWidget(1, QtGui.QFormLayout.LabelRole, label)

            label = QtGui.QLabel(groupBox)
            label.setTextInteractionFlags(allowTextSelection)
            label.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
            label.setText(address)
            layout.setWidget(1, QtGui.QFormLayout.FieldRole, label)

            self.scrollAreaLayout.addWidget(groupBox)

        self.scrollAreaLayout.addItem(QtGui.QSpacerItem(20, 0))
        self.scrollAreaLayout.setStretch(self.scrollAreaLayout.count()-1, 1)

    def updateButtonClicked(self):
        self.parent().parent().parent().update()
