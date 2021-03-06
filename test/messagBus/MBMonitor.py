import sys,os,time
from qao.gui.qt import QtCore, QtGui
from qao.io import messageBusPP as messageBus

class MBSubWidget(QtGui.QWidget):
    def __init__(self,qmbClient,name,parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        self.parent = parent
        self.qmbClient = qmbClient
        self.name = name
        self.setGeometry(QtCore.QRect(0, 0, 801, 531))
        
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.textEdit = QtGui.QTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.verticalLayout.addWidget(self.textEdit)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.lineEdit = QtGui.QLineEdit(self)
        self.horizontalLayout.addWidget(self.lineEdit)
        self.sendButton = QtGui.QPushButton("Send", self)
        self.horizontalLayout.addWidget(self.sendButton)
        self.verticalLayout.addLayout(self.horizontalLayout)
        
        self.sendButton.clicked.connect(self.send)
        self.lineEdit.returnPressed.connect(self.send)
        
    def send(self):
        self.qmbClient.publishEvent(self.name,eval(str(self.lineEdit.text())))
        self.lineEdit.clear()
        
    def addLine(self, topic, data):
        if isinstance(data,dict):
            data = data.items()
        tableStr = "<table><tr><th rowspan='%i' style='padding-right:25px'><font color='#FF0000'>%s</font></th><td>Arg 1:</td><td style='border-top:1px solid black; margin:0px;'>%s</td></tr>"%(len(data),time.strftime("%d. %m. %H:%M:%S"),data[0])
        i=2
        for datum in data[1:]:
            tableStr += "<tr><td>Arg %i:</td><td>%s</td></tr>"%(i,datum)
            i+=1
        tableStr += "</table><br/>"
        self.textEdit.append(tableStr)

class MBSubConnectDialog(QtGui.QDialog):
    def __init__(self,parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setModal(True)
        


class MBSubMainWindow(QtGui.QWidget):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        
        self.verticalLayout = QtGui.QVBoxLayout(self)
        
        self.addButton = QtGui.QPushButton("Add Sub",self)
        self.verticalLayout.addWidget(self.addButton)
        #Tab View
        self.tabWidget = QtGui.QTabWidget(self)
        self.tabWidget.setGeometry(QtCore.QRect(0, 0, 811, 561))
        self.verticalLayout.addWidget(self.tabWidget)

        self.addButton.clicked.connect(self.subAdder)
        
        self.connected = False  
        self.host, ok = QtGui.QInputDialog.getText(self, 'Server address','Server to connect to:')
        
        self.mbConnect(self.host,9090)

    def mbConnect(self,host,port):
        self.qmbClient = messageBus.QMessageBusClient()
        self.qmbClient.connectToServer(host,port)
        self.connected = True
    
    def subAdder(self):
       SubName, ok = QtGui.QInputDialog.getText(self, 'Subscription','Sub:') 
       self.addSub(SubName)
        
    def addSub(self,name):
        if self.connected:
            newSubWidget = MBSubWidget(self.qmbClient,name,parent=self)
            self.qmbClient.subscribe(name,callback=newSubWidget.addLine)
            self.tabWidget.addTab(newSubWidget,name)
            
app = QtGui.QApplication(sys.argv)
mainwin = MBSubMainWindow()

mainwin.show()


sys.exit(app.exec_())
