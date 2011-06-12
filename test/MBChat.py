import sys
from PyQt4 import QtCore, QtGui
import QMBClient

class MBChatWidget(QtGui.QWidget):
    def __init__(self,qmbClient,name,parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        self.qmbClient = qmbClient
        self.name = name
        self.setGeometry(QtCore.QRect(0, 0, 801, 531))
        
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.textEdit = QtGui.QTextEdit(self)
        self.verticalLayout.addWidget(self.textEdit)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.lineEdit = QtGui.QLineEdit(self)
        self.horizontalLayout.addWidget(self.lineEdit)
        self.sendButton = QtGui.QPushButton("Send",self)
        self.horizontalLayout.addWidget(self.sendButton)
        self.verticalLayout.addLayout(self.horizontalLayout)
        
        self.connect(self.sendButton, QtCore.SIGNAL('clicked()'), self.send)
        self.connect(self.lineEdit, QtCore.SIGNAL('returnPressed()'), self.send)
        
    def send(self):
        self.qmbClient.publishEvent("MBChat.%s"%self.name,["thomas",self.lineEdit.text()])
        self.lineEdit.clear()
        
    def addLine(self,topic,data):
        self.textEdit.append("%s: %s"%(data[0],data[1]))

class MBChatConnectDialog(QtGui.QDialog):
    def __init__(self,parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setModal(True)
        


class MBChatMainWindow(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        self.tabWidget = QtGui.QTabWidget(self)
        self.tabWidget.setGeometry(QtCore.QRect(0, 0, 811, 561))
        
        self.connected = False
        self.host, ok = QtGui.QInputDialog.getText(self, 'Input Dialog','Server to connect to:')
        self.connect(self.host,9090)
        
        
    
    def connect(self,host,port):
        self.qmbClient = QMBClient.QMessageBusClient()
        self.qmbClient.connectToServer(host,port)
        self.connected = True
        
    def addChat(self,name):
        if self.connected:
            newChatWidget = MBChatWidget(self.qmbClient,name,parent=self)
            self.qmbClient.subscribe("MBChat.%s"%name,callback=newChatWidget.addLine)
            self.tabWidget.addTab(newChatWidget,name)
            
app = QtGui.QApplication(sys.argv)
mainwin = MBChatMainWindow()
mainwin.addChat("test")
mainwin.addChat("CHat")
mainwin.show()


sys.exit(app.exec_())
