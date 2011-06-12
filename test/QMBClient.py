from qao.io import messageBusPP as messageBus
try:
    from PyQt4 import QtCore, QtNetwork
    from PyQt4.QtCore import pyqtSignal as qtSignal
except ImportError:
    from PySide import QtCore, QtNetwork
    from PySide.QtCore import Signal as qtSignal

import signal,time
signal.signal(signal.SIGINT, signal.SIG_DFL)

class QConsoleClient(messageBus.MessageBusClient):
    def __init__(self):
        messageBus.MessageBusClient.__init__(self)
        self.s_notify = QtCore.QSocketNotifier(self.clientSock.fileno(),QtCore.QSocketNotifier.Read)
        self.s_notify.activated.connect(self.handleEvent)
        
        #Variables for testing purpose
        self.i=0
        m=1920
        n=1080
        self.hugematrix = [[None for x in range(m)] for x in range(n)]
        
    def printEventReceived(self, topic, data):
        print "%s: %s (Dauer:%.2f)"%(topic,data[0],time.time()-float(data[1]))
        serv.publishEvent("testing",[self.i,time.time(),self.hugematrix])
        self.i +=1

app = QtCore.QCoreApplication([])

#define new client
serv = QConsoleClient()
serv.connectToServer("localhost")

#subscribe
serv.subscribe("testing",serv.printEventReceived)

#publish event
serv.publishEvent("testing",["foo","1.0"])



app.exec_()
