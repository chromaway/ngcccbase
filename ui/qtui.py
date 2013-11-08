import os, sys, signal
from PyQt4 import QtCore, QtGui, uic

from overviewpage import OverviewPage
from sendcoinspage import SendcoinsPage
from receivepage import ReceivePage


def getUiPath(ui_name):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forms', ui_name)
uic.getUiPath = getUiPath


class Application(QtGui.QApplication):
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        QtGui.QApplication.__init__(self, [])


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(uic.getUiPath('ngccc.ui'), self)

        self.overviewpage = OverviewPage()
        self.stackedWidget.addWidget(self.overviewpage)
        self.sendcoinspage = SendcoinsPage()
        self.stackedWidget.addWidget(self.sendcoinspage)
        self.receivepage = ReceivePage()
        self.stackedWidget.addWidget(self.receivepage)

        self.bindActions()

        self.gotoOverviewPage()

    def bindActions(self):
        self.actionExit.triggered.connect(lambda: QtCore.QCoreApplication.instance().exit(0))

        self.toolbarActionGroup = QtGui.QActionGroup(self)

        self.toolbarActionGroup.addAction(self.actionGotoOverview)
        self.actionGotoOverview.triggered.connect(self.gotoOverviewPage)

        self.toolbarActionGroup.addAction(self.actionGotoSendcoins)
        self.actionGotoSendcoins.triggered.connect(self.gotoSendcoinsPage)

        self.toolbarActionGroup.addAction(self.actionGotoReceive)
        self.actionGotoReceive.triggered.connect(self.gotoReceivePage)

    def gotoOverviewPage(self):
        self.actionGotoOverview.setChecked(True)
        self.overviewpage.update()
        self.stackedWidget.setCurrentWidget(self.overviewpage)

    def gotoSendcoinsPage(self):
        self.actionGotoSendcoins.setChecked(True)
        self.sendcoinspage.update()
        self.stackedWidget.setCurrentWidget(self.sendcoinspage)

    def gotoReceivePage(self):
        self.actionGotoReceive.setChecked(True)
        self.receivepage.update()
        self.stackedWidget.setCurrentWidget(self.receivepage)


class QtUI(object):
    def __init__(self):
        app = Application()
        window = MainWindow()
        window.move(QtGui.QApplication.desktop().screen().rect().center() - window.rect().center())
        window.show()
        sys.exit(app.exec_())
