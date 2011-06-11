from qao.io import messageBus
try:
    from PyQt4 import QtCore, QtNetwork
    from PyQt4.QtCore import pyqtSignal as qtSignal
except ImportError:
    from PySide import QtCore, QtNetwork
    from PySide.QtCore import Signal as qtSignal


class ConsoleClient(messageBus.MessageBusClient):
	def __init__(self):
		messageBus.MessageBusClient.__init__(self)
		self.receivedEvent.connect(self.printEventReceived)
		
	def printEventReceived(self, topic, data):
		print "new event: %s" % str(topic)

app = QtCore.QCoreApplication([])

#define new client
serv = ConsoleClient()
serv.connectToServer("localhost")

#subscribe
serv.subscribe("testing")

#publish event
serv.publishEvent("testing",["foo","bar"])

app.exec_()
