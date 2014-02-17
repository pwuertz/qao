import numpy as np

try:
	import ADwin
except:
	print "Adwin class not found. Install it!"
import threading
import time

# Data from the awinmcb_readout process
slotNum = 10
buffersize = 1000000

num_new_data = 2
num_currentSlot = 30
num_storageBuffer = 50
num_bufferLen = 51
num_seqTimestamp = 81
num_acqTimestamp = 83
num_status = 1
num_resetTico = 9

class IonSignal:
	def __init__(self,seqTimestamp,Num,rawData):
		self.seqTimestamp = seqTimestamp
		self.Num = Num
		self.rawData = rawData
	
	def __iter__(self):
		iter(self.rawData)

class IonScanSequence(object):
	def __init__(self,seqTimestamp):
		self.scans = []
		self.seqTimestamp = seqTimestamp

	def __iter__(self):
		return iter(self.scans)

	def scanCount(self):
		return len(self.scans)

	def add(self,ionsignal):
		if ionsignal.seqTimestamp == self.seqTimestamp:
			self.scans.append(ionsignal)
		else:
			raise Exception("Tried to add IonSignal to wrong sequence")

class TicoMCS(threading.Thread):
	def __init__(self,callback,statusCallback = None, adwinDeviceNo=0x150):
		threading.Thread.__init__(self)
		self.adev = ADwin.ADwin(adwinDeviceNo)
		self.currentSequence = None
		self.dataPublished = False
		self.callback = callback
		self.statusCallback = statusCallback
		self.keepRunning = True
		self.status = None

	def loadProcess(self):
		self.adev.Load_Process("./adwinmcb_readout.TB5")
		self.adev.Start_Process(5)
	
	def resetStatus(self):
		self.adev.Set_Par(num_resetTico,1)	

	def run(self):
		while self.keepRunning:
			currentSlot = numpy.frombuffer(self.adev.Get_Par(num_currentSlot), dtype=numpy.int32).copy()
            acqTimestamp = numpy.frombuffer(self.adev.Get_Par(num_acqTimestamp), dtype=numpy.int32).copy()
            seqTimestamp = numpy.frombuffer(self.adev.Get_Par(num_seqTimestamp), dtype=numpy.int32).copy()
            status = numpy.frombuffer(self.adev.Get_Par(num_status), dtype=numpy.int32).copy()
			
			if not self.currentSequence or acqTimestamp != self.currentSequence.seqTimestamp:
				self.currentSequence = IonScanSequence(acqTimestamp)
				self.dataPublished = False
			
			#if the slot number on the Adwin is higher then the number of scans in the stored IonScanSequence
			#there is new data ready to taken...
			if currentSlot > self.currentSequence.scanCount():
				for i in range(self.currentSequence.scanCount(),currentSlot):
					bufferLen = self.adev.GetData_Long(num_bufferLen,i+1,1)
					if bufferLen[0] > 0:
						data = numpy.frombuffer(self.adev.GetData_Long(num_storageBuffer, (i-1)*buffersize+1, bufferLen[0]), dtype=numpy.int32).copy()
					else:
						data = np.empty((0),dtype='int32')
					self.currentSequence.add(IonSignal(acqTimestamp,i,data))
			
			#when a new sequence started, the old one is over so the data can be emitted
			if seqTimestamp > acqTimestamp and not self.dataPublished:
				self.callback(self.currentSequence)
				self.dataPublished = True
			
			if status != self.status:
				self.statusCallback(status)
				self.status = status
			
			time.sleep(.5)
		
	def stop(self):
		self.keepRunning = False

class DummyMCS(threading.Thread):
	def __init__(self,callback,statusCallback=None,delay=3,scans=2, length=1, frq = 1000):
		threading.Thread.__init__(self)
		self.keepRunning = True	
		self.callback = callback
		self.statusCallback = statusCallback
		self.delay = delay
		self.scans = scans	#number of scans
		self.length = length #length of the gate in s
		self.frq = frq
		
	def run(self):
		while self.keepRunning:
			acqTimestamp = int(time.time())
			currentSequence = IonScanSequence(acqTimestamp)
			
			for scan in range(self.scans):
				freq = np.random.randint(0.9*self.frq,1.1*self.frq)
				data = np.asarray([np.random.randint(0,self.length*10e7) for i in xrange(int(self.length*freq))])
				currentSequence.add(IonSignal(acqTimestamp,scan+1,np.array(data)))
			self.callback(currentSequence)
			time.sleep(self.delay)

	def stop(self):
		self.keepRunning = False

if __name__ == "__main__":

	def showSequence(ionSignalSequence):
		print "Timestamp:	%i"%ionSignalSequence.seqTimestamp
		for iSig in ionSignalSequence:
			print "%i:	%i events"%(iSig.Num,len(iSig.rawData))
			
			
	
	tmcs = TicoMCS(showSequence)
	tmcs.start()
	print "Threading"
	time.sleep(200)
	tmcs.keepRunning = False
