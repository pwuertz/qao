import sys
sys.path.append("../src/qao/io")
import messageBus
try:
    from PyQt4 import QtCore, QtNetwork
    from PyQt4.QtCore import pyqtSignal as qtSignal
except ImportError:
    from PySide import QtCore, QtNetwork
    from PySide.QtCore import Signal as qtSignal

import signal,time
signal.signal(signal.SIGINT, signal.SIG_DFL)

app = QtCore.QCoreApplication([])

def retFunction(funcName, data):
	print "%s(%s): %s"%(funcName,data['args'],data['ret'])

def dummyFunction(a):
	print "remote Function call"
	return a+1


#define new client
client = messageBus.MessageBusClient()
client.connectToServer("localhost",9090)

#subscribe
client.subscribe("testing")

#register dummy function
client.rpcRegister('testing.dummy',1,1,dummyFunction)

#call dummy function with some argument
client.rpcCall('testing.dummy',[12],retFunction)

app.exec_()
