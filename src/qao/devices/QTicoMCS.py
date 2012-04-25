from TicoMCS import IonScanSequence, TicoMCS, DummyMCS
from PyQt4 import QtCore


class QTicoMCS(TicoMCS, QtCore.QObject):

	newData = QtCore.pyqtSignal(IonScanSequence)
	statusChanged = QtCore.pyqtSignal(int)

	def __init__(self,adwinDeviceNo=0x150):
		TicoMCS.__init__(self,self._handleNewData,self._handleStatusChanged)
		QtCore.QObject.__init__(self)
		self.start()

	def _handleNewData(self,ionScanSequence):
		self.newData.emit(ionScanSequence)

	def _handleStatusChanged(self,status):
		self.statusChanged.emit(status)

class QDummyMCS(DummyMCS, QtCore.QObject):

	newData = QtCore.pyqtSignal(IonScanSequence)
	statusChanged = QtCore.pyqtSignal(int)

	def __init__(self,delay=3,scans=2, length=1, frq=1000):
		DummyMCS.__init__(self,self._handleNewData,self._handleStatusChanged,delay=delay,scans=scans, length=length, frq=frq)
		QtCore.QObject.__init__(self)
		self.start()

	def _handleNewData(self,ionScanSequence):
		self.newData.emit(ionScanSequence)

	def _handleStatusChanged(self,status):
		self.statusChanged.emit(status)

	
	
