import numpy as np
import base64
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

class ConsoleClient(messageBus.MessageBusClient):
	def __init__(self):
		messageBus.MessageBusClient.__init__(self)
		self.receivedEvent.connect(self.printEventReceived)
		self.i=0
		m=1920
		n=1080
		self.hugematrix = np.random.rand(m,n)
		
	def printEventReceived(self, topic, data):
		print "%s: %s (Dauer:%.2f)"%(topic,data[0],time.time()-float(data[1]))
		
		self.publishEvent("testing",[self.i,time.time(),base64.b64encode(self.hugematrix)])
		self.i +=1

app = QtCore.QCoreApplication([])

#define new client
client = ConsoleClient()
client.connectToServer("localhost",9999)

#subscribe
client.subscribe("testing")

#publish event
client.publishEvent("testing",["foo","1.0"])



app.exec_()
