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
	if data['success']:
		print "%s(%s): %s"%(funcName,data['args'],data['ret'])
	else:
		print "An Error occured during RPC call: %s"%(data['error'])

def dummyFunction(args):
	print "remote Function call"
	if  not 'count' in args: 
		raise Exception("Missing needed argument count")
	a = args['count']
	return a+1


#define new client
client = messageBus.MessageBusClient()
client.connectToServer("localhost",9090)

#subscribe
client.subscribe("testing")

#register dummy function
client.rpcRegister('testing.dummy',['count'],1,dummyFunction)

#call dummy function with some argument
client.rpcCall('testing.dummy',{'count':12},retFunction)

app.exec_()
