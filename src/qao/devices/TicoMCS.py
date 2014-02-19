import numpy as np

try:
    import ADwin
except:
    print "Adwin class not found. Install it!"
import threading
import time

# Data from the awinmcb_readout process
buffersize = 8000000

num_mcb_storage = 50
num_mcb_storage_len = 50
num_seqTimestamp = 81
num_acqTimestamp = 83
num_mcb_readout_status = 5

MCB_READ_STATUS_IDLE = 0
MCB_READ_STATUS_DOWNLOAD = 1
MCB_READ_STATUS_DATAREADY = 2
MCB_READ_STATUS_ERROR = 3

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
        self.mcb_status = None

    def loadProcess(self):
        pass
        #self.adev.Load_Process("./adwinmcb_readout.TB5")
    
    def resetStatus(self):
        pass

    def run(self):
        while self.keepRunning:
            mcb_status = self.adev.Get_Par(num_mcb_readout_status)
            
            if mcb_status == MCB_READ_STATUS_DATAREADY:
                # download data from the mcb process
                acqTimestamp = self.adev.Get_Par(num_acqTimestamp)
                n = self.adev.Get_Par(num_mcb_storage_len)
                data = np.frombuffer(self.adev.GetData_Long(num_mcb_storage, 1, n), dtype=np.int32).copy()
                # acknowledge retrieval of data
                self.adev.Set_Par(num_mcb_readout_status, MCB_READ_STATUS_IDLE)
                
                
                self.currentSequence = IonScanSequence(acqTimestamp)
                self.dataPublished = False
                
                blocks = []
                i = n - 1
                while i >= 0:
                    block_len = data[i]
                    blocks.append(data[i-block_len:i])
                    i -= block_len + 1
                assert i == -1, 'Bad data format'
                for i,block in enumerate(blocks[::-1]):
                    self.currentSequence.add(IonSignal(acqTimestamp, i, block))
                self.callback(self.currentSequence)
                self.dataPublished = True
            
            if mcb_status != self.mcb_status and self.statusCallback:
                self.statusCallback(mcb_status)
            
            self.mcb_status = mcb_status
            
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
        self.scans = scans  #number of scans
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
        print "Timestamp:   %i"%ionSignalSequence.seqTimestamp
        for iSig in ionSignalSequence:
            print "%i:  %i events"%(iSig.Num,len(iSig.rawData))
            
            
    
    tmcs = TicoMCS(showSequence,adwinDeviceNo=0x001)
    tmcs.start()
    print "Threading"
    time.sleep(200)
    tmcs.keepRunning = False
