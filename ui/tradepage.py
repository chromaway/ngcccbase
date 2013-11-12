from PyQt4 import QtGui, uic


class TradePage(QtGui.QWidget):
    def __init__(self):
        QtGui.QWidget.__init__(self)
        uic.loadUi(uic.getUiPath('tradepage.ui'), self)

    def update(self):
        pass
