from PyQt4 import QtGui, uic


class SendcoinsPage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        uic.loadUi(uic.getUiPath('sendcoins.ui'), self)
