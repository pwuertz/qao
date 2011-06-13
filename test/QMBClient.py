from qao.io import messageBusPP as messageBus
try:
    from PyQt4 import QtCore, QtNetwork
    from PyQt4.QtCore import pyqtSignal as qtSignal
except ImportError:
    from PySide import QtCore, QtNetwork
    from PySide.QtCore import Signal as qtSignal



class QMessageBusClient(messageBus.MessageBusClient):
    def __init__(self):
        messageBus.MessageBusClient.__init__(self)
        self.s_notify = QtCore.QSocketNotifier(self.clientSock.fileno(),QtCore.QSocketNotifier.Read)
        self.s_notify.activated.connect(self.handleEvent)



if __name__ == "__main__":
     
    import signal,time
    signal.signal(signal.SIGINT, signal.SIG_DFL) 
            
    #Variables for testing purpose
    i=0
    m=1920
    n=1080
    hugematrix = [[None for x in range(m)] for x in range(n)]
    
    def printEventReceived(topic, data):
        global i
        print "%s: %s (Dauer:%.2f)"%(topic,data[0],time.time()-float(data[1]))
        serv.publishEvent("testing",[i,time.time(),hugematrix])
        i +=1
    
    app = QtCore.QCoreApplication([])
    
    #define new client
    serv = QMessageBusClient()
    serv.connectToServer("localhost")
    
    #subscribe
    serv.subscribe("testing",printEventReceived)
    
    #publish event
    serv.publishEvent("testing",["foo","1.0"])
    app.exec_()
    
